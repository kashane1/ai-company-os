---
title: Domain Onboarding Automation — bring-your-own-domain, recon-first, support both DNS strategies
type: feat
date: 2026-06-07
status: in-progress
owner: kashane
related:
  - docs/agency/domain-dns-runbook.md
  - docs/agency/go-live-checklist.md
  - docs/agency/client-lifecycle.md
  - packages/web/deploy.py
  - packages/agency/intake.py
  - scripts/agency/launch_client.py
  - docs/plans/2026-06-05-feat-agency-packages-go-live-readiness-plan.md
---

# 🌐 Domain Onboarding Automation

> **TL;DR.** A client can already bring their own domain — but today it's an
> operator following [domain-dns-runbook.md](../agency/domain-dns-runbook.md) by
> hand, and the one piece of automation we have (`set_custom_domain()`) isn't
> even wired to a CLI. The insight that unlocks automation: **the registrar is
> the only variable.** What we point *at* (Netlify/Google) is constant, and
> *reading* a domain's current state is public DNS — works the instant a prospect
> types `acme.com`, **but only with strict input validation (it's user input, not
> a trusted constant — see Security).** So we build **recon + verify + instruction
> generation now** (zero new deps, registrar-agnostic), wire the existing Netlify
> method into the launch CLI, and — *only when client volume justifies it* — add a
> concrete `CloudflareDnsProvider` for the managed-DNS path. We do **not** unify
> managed + external behind one interface (they have different postconditions);
> the launch flow branches once on strategy. The irreducible human step is a
> single action at the registrar; managed-DNS shrinks it from "add 6 records" to
> "set 2 nameservers."
>
> **Deepened + reviewed 2026-06-07** — 4 best-practice research passes (RDAP/DoH,
> Netlify API, Cloudflare API, email-preserving cutover) + two review rounds
> (architecture, security, then a simplicity/right-sizing pass). All P1/P2 findings
> folded in below; see
> [Research Insights](#research-insights-deepened-2026-06-07) for cited specifics.

## Implementation status (2026-06-07)

**Phase 1 + Phase 2 shipped** (the committed scope). Branch
`feat/domain-onboarding-automation`; 34 new offline tests (MockTransport), full
suite green (1321 passed).

- ✅ **Phase 1 — recon + verify** (`8269d45`): `packages/agency/domain_recon.py`
  (RDAP + DoH, `validate_domain` input-validation, NS→provider/apex + MX→email
  classification, no-RDAP graceful degrade, Netlify instruction generator with
  email carry-over) and `packages/agency/domain_verify.py` (multi-resolver,
  propagation-aware ok/fail/propagating; catches a wiped MX). CLIs:
  `scripts/agency/{domain_recon,verify_domain}.py`. Per the lightened seam
  decision, recon emits a **transient report** — no persisted JSON contract.
- ✅ **Phase 2 — gated attach** (`576569a`): `NetlifyDeployTarget.attach_domain`
  (www-primary + apex-alias, GET-merge-PATCH), `provision_ssl`/`get_ssl` +
  `CertState`; `packages/agency/domain_attach.py` (two-part control-proof gate:
  `assert_custom_domain_allowed` + `client_confirmed_registrar`);
  `scripts/agency/attach_domain.py` (wires real target + registry site-id, stamps
  `intake.site_url`).
- ⏸️ **Deferred (volume-gated, unchanged):** Phase 3 (Cloudflare managed DNS, with
  its destructive-write/snapshot/token guardrails) and Phase 4 (Workspace).
- ⏭️ **Not built by choice:** `--transfer-to` offboarding (split to its own change,
  per review).

## Enhancement summary (what the reviews changed)

- **Architecture P1:** killed the speculative unified `DnsProvider` Protocol. The
  external path is an *instruction renderer + human step*, not a DNS provider with
  the same contract as Cloudflare (its `set_records` "write" lands minutes-to-days
  later, by a person — a Liskov violation if forced behind one interface). The
  launch flow branches on strategy instead.
- **Architecture P1 + Simplicity P1:** named the **persistence seam** (recon output
  is its *own* artifact, never on the frozen `ClientIntake`) — and then *lightened*
  it: Phase 1 emits a transient report, the frozen JSON data-contract is deferred
  to Phase 3 (its only real consumer). No file-format design for a deferred phase.
- **Simplicity P1 (the key correction):** the destructive-write contract
  (snapshot/diff-hash/rollback/TOCTOU) + Cloudflare token block were mis-scoped onto
  "before any write-path code." **Phase 2 writes nothing to the client's zone** — it
  PATCHes our own Netlify account. Those guardrails are now **Phase 3-only**;
  committed scope keeps just hostname-validation + workflow-inherent control-proof +
  propagation-aware verify. ~40% less machinery in the committed build.
- **Security P1 ×6 (re-homed to the right phase):** input-validation on recon,
  domain-control proof before any zone-write, scoped Cloudflare tokens + secret
  scanner pattern, per-write diff-and-approve, pre-write zone snapshot + rollback,
  idempotent upserts. These turn "a mistake silently kills a client's email" from
  an accepted risk into a contained one.
- **Scope:** Phase 1 + 2 are the committed deliverable. Phase 3 (Cloudflare
  managed DNS) is **volume-gated** — deferred until client count justifies it,
  written as a concrete class (no Protocol) when it lands.

## Why this plan

Audit (2026-06-07) found the bring-your-own-domain path is real but manual:
- `set_custom_domain()` ([deploy.py:302](../../packages/web/deploy.py:302)) and
  `transfer_ownership()` are coded + unit-tested but **called by nothing** —
  `--dns-approved` on [launch_client.py:58](../../scripts/agency/launch_client.py:58)
  only records a boolean; it never attaches the domain.
- No registrar/DNS connectors exist (only prospecting connectors).
- No propagation/verification in code — runbook §4 is `dig` by hand.
- `site_url` defaults to `https://example.com` ([intake.py:39](../../packages/agency/intake.py:39));
  email-domain derivation keys off it.

User decisions (2026-06-07): **support both** DNS strategies; **plan only** for now.

## The architecture: registrar is the only variable

| Bucket | Varies by client? | Needs client creds? | Automatable |
|---|---|---|---|
| **Point AT** — Netlify site, SSL, record *target values* | No | No | ✅ Fully |
| **Read state** — registrar, NS, current A/MX/TXT, TTLs | No (public DNS) | No | ✅ Fully (with input validation) |
| **Write change** — add records / change NS at registrar | **Yes** | Yes | ⚠️ 1 human step, or per-registrar API |

Two of three buckets are registrar-independent and need only the domain *name*.
Those are the preemptive builds. The third is the human-in-the-loop boundary —
and managed DNS makes that boundary smaller and uniform.

## The two DNS strategies (we support both — by *branching*, not a shared interface)

- **External DNS** (today's runbook, the v1 default): DNS stays at the client's
  registrar; operator adds A/ALIAS + www CNAME + MX/SPF/DKIM/DMARC by hand using
  our generated instructions. Safe for a human (no NS move = no email risk), but
  **registrar-specific, unautomatable** — no single API. This path is
  recon → render instructions → operator acts → `verify_domain`. It is **not** a
  "DNS provider"; it's instruction-rendering + the human step.
- **Managed DNS** (Cloudflare, volume-gated): client makes one uniform change —
  "point these 2 nameservers here" — then we own the zone via API and cutover is
  programmatic. **Cloudflare full-setup (free), DNS-only/grey-cloud records for
  the Netlify origin, apex CNAME-flattening** removes the ALIAS/A-fallback problem.

`domain_recon` recommends a strategy; the **launch flow picks the branch**. We do
*not* model both as one `DnsProvider` Protocol — see Architecture decision below.

**Why Cloudflare for managed:** free at scale, scoped per-zone API tokens, apex
CNAME-flattening on every plan, BIND zone-import to replay email records before
cutover. Route 53 is the fallback if enterprise SLAs/IAM are needed (but ~$0.50/
zone/mo). Netlify DNS works only while Netlify is always the origin.

### Architecture decision: no unified `DnsProvider` Protocol (yet)

`DeployTarget` ([deploy.py:141](../../packages/web/deploy.py:141)) earns its
Protocol because every adapter has **identical observable semantics** —
`set_custom_domain()` returns a `SiteRef` with the domain actually attached,
regardless of backend. A `DnsProvider` with `CloudflareDnsProvider` *and*
`ExternalDnsProvider` would **not** hold that property:
`CloudflareDnsProvider.set_records()` writes records that take effect;
`ExternalDnsProvider.set_records()` prints instructions and returns with **nothing
applied** — the records land later, via a human, maybe. Same signature,
incompatible postconditions; `ensure_zone`/`import_records` are structurally
meaningless for the external case. That's a leaky abstraction.

**Decision:** the managed path is a **concrete `CloudflareDnsProvider` class**
(injectable `httpx.Client`, same testability pattern as `NetlifyDeployTarget` —
worth copying). Extract a Protocol only if/when a *second managed* provider
appears. The external path stays what Phase 1 already builds: an instruction
renderer. "Support both" = the launch flow branches once on strategy, not a shared
interface.

### Architecture decision: the persistence seam (lightweight now, frozen contract only when Phase 3 needs it)

Recon is machine-derived, so it does **not** belong on the frozen `ClientIntake`
dataclass (would force edits to `from_dict`/`to_dict`/`render_brief` and collide
with the human-entered `domain_registrar`/`dns_access` fields that mean something
subtly different). Phase 2's `site_url` stamp is a separate, legitimate intake
write that needs nothing from recon (it's just the `--domain` arg).

**For the committed scope, Phase 1 emits a transient human-readable report**
(text/markdown) — *not* a versioned `domain_recon.json` data contract. The only
consumer that needs a stable persisted recon *format* is Phase 3 (replay recon'd
MX/TXT into a Cloudflare zone), which is deferred — so freeze the JSON schema when
Phase 3 is greenlit and we know what it must carry, not now. (Deciding the data
contract now would be designing a file format for a phase we've chosen not to
build — YAGNI.)

**Persistence safety (applies the moment recon writes anything durable):** any
recon artifact path **must** sit under an already git-ignored prefix. `.gitignore`
has *no bare `state/*` catch-all* — it ignores per-subdir (`state/agency/`,
`state/prospects/`, …). Land artifacts under `state/agency/domains/<client>/`
(covered by `state/agency/`) **or** add an explicit `.gitignore` entry. RDAP
responses carry **registrant PII** — **redact contact fields we don't need** (keep
registrar + nameservers + MX), never commit.

## Security guardrail contract (scoped by phase)

These are requirements, not options — but they are **scoped to the phase that
actually does the dangerous thing**, so the committed scope doesn't carry Phase 3's
weight. The dividing line: **Phase 1 only reads; Phase 2 writes only to *our own*
Netlify account (`PATCH custom_domain`), never to the client's registrar zone;
Phase 3 is the only phase that writes records into a zone we own.** So the
snapshot/diff-hash/rollback machinery below is **Phase 3-only** — it has nothing to
snapshot or roll back in Phase 1+2 (the client's MX/SPF/DKIM are still at their
registrar, untouched).

### Committed-scope guardrails (Phase 1 + 2)

**Recon input validation (Phase 1 — recon reads an operator- or form-supplied domain string):**
- **Validate hostname shape + URL-encode before any request.** Parse to a
  registrable public hostname; **reject** anything with a scheme, path, port, `@`,
  whitespace, CR/LF, or query chars; always URL-encode into RDAP/DoH URLs — never
  raw-concat. **IDN/punycode:** normalize to A-label (IDNA2008); flag confusable/
  mixed-script labels; show operator both forms. Strict `httpx` timeouts.
- *Full SSRF egress contract* (resolve-then-block private/link-local/loopback/CGNAT
  IPs before any outbound connection, redirect-host allowlisting) is **only needed
  when recon is wired to untrusted public input** — see "What we can do before"
  and the rate-limit/queue requirement there. For operator-initiated recon on a
  typed domain it's deferred; restore it if/when recon fires on raw public form hits.

**Domain-control proof (before attaching a domain to a Netlify site):**
- For Phase 2, the proof is **largely inherent in the workflow**: the client adds
  Netlify's records / sets the domain at *their own* registrar — that act proves
  control. So control-proof = the existing `--dns-approved` boolean **+ operator
  confirmation the client completed the registrar step** (and Netlify's own
  `netlify-challenge.<domain>` TXT for contested domains). Don't build a TXT-token
  challenge engine or RDAP-registrant email flow for the committed scope.

**Verify independence (Phase 1):**
- Verify must query **authoritative nameservers** (or multiple resolvers) with
  cache-busting and be **propagation-aware** — don't declare success inside the
  TTL window (recon captured the TTLs; use them); re-check after propagation. A
  verify that reads the same cached DoH used at cutover can false-pass.

### Phase 3-only guardrails (deferred with Phase 3 — do NOT build for committed scope)

**Domain-control proof, hardened:** before `create_zone`/delegation, require a real
control challenge (DNS TXT token, or email to the RDAP registrant / `admin@` /
`postmaster@`). Creating a CF zone for a domain you don't control is itself an
abuse vector — this matters once we create zones, not when we attach to Netlify.

**Destructive-write safety (DNS edits are silent: a deleted MX bounces mail with no error):**
- `assert_custom_domain_allowed()` (a single boolean) is **NOT sufficient** for
  record writes. Each cutover must compute the **exact record delta** (adds/changes/
  **deletes**, MX/NS called out) from the recon snapshot, surface it for approval,
  and **pin approval to the diff hash** so it can't drift before apply.
- **Mandatory pre-write zone snapshot** (the rollback artifact); refuse to write
  without a fresh one. **Re-recon immediately before apply**, abort if the live
  zone diverged (TOCTOU). **Idempotent upsert-by-(type,name)** — never
  delete-then-recreate MX. **`verify` failure triggers rollback-from-snapshot.**

**Secrets:** new `CLOUDFLARE_API_TOKEN` env var (mirror `NETLIFY_AUTH_TOKEN`), via
`get_api_key()`, never `PUBLIC_`/`VITE_`. **Add a Cloudflare-token regex to
`_SECRET_PATTERNS`** ([deploy.py:59](../../packages/web/deploy.py:59)) so the
deploy-time leak scanner fails closed (CF tokens are 40-char `[A-Za-z0-9_-]` — no
current pattern catches them). **Scoped tokens, per-client preferred** — one
agency-wide DNS-edit token = catastrophic blast radius (one leak → repoint MX/A for
every client). Scope to `Zone.DNS:Edit` + `Zone:Read`; keep zone-*create* on a
separate, more-guarded token; ship a **rotation/revocation runbook**.

## Build phases

### Phase 1 — Preemptive, zero-dependency, registrar-agnostic (the committed deliverable)

Uses only `httpx` (already a dep). Reads public state over HTTPS: **RDAP**
(`rdap.org/domain/<domain>`, follow redirects) for registrar + nameservers;
**DNS-over-HTTPS** (`dns.google/resolve` primary, `cloudflare-dns.com/dns-query`
cross-check) for A/AAAA/CNAME/MX/TXT/NS/SOA. *All subject to the input-validation
contract above.*

1. **`packages/agency/domain_recon.py` + `scripts/agency/domain_recon.py`** →
   emits a human-readable report (transient, per the seam decision above):
   - Registrar + nameservers → DNS provider (NS-suffix map) → **apex ALIAS/flatten
     support vs A-record fallback** (the one variable that matters: a no-ALIAS
     registrar like GoDaddy/Namecheap forces the A-record fallback).
   - **Current MX → email host that must survive cutover** (Google `smtp.google.com`,
     M365 `*.mail.protection.outlook.com` *and* the new `*.mx.microsoft`). The #1
     hazard, surfaced automatically.
   - Existing SPF/DKIM/DMARC; TTLs; DNSSEC flag; transfer-lock/expiry signals.
   - Recommended strategy (external vs managed) + the filled-in record set.
   - **Graceful degrade:** `.io`/`.co`/many ccTLDs lack RDAP — derive everything
     from DNS and label "registrar unknown," don't fail.
2. **`packages/agency/domain_verify.py` + `scripts/agency/verify_domain.py`** —
   runbook §4 as code, **independent + propagation-aware** (per contract). Asserts
   apex/www resolve to Netlify, HTTPS cert live, **MX still → original mail host**,
   SPF/DKIM/DMARC intact. The safety net.
3. **Per-client instruction generator** (folded into `domain_recon` output) —
   provider-tailored copy-paste records (Netlify www-as-primary + apex alias to
   `apex-loadbalancer.netlify.com`, A-fallback `75.2.60.5`, **no AAAA**), email
   records carried over. This **is** the external-DNS path's final form (not a
   throwaway later wrapped by a Protocol).

*Effort: small, no new deps, no connectors. Highest leverage; useful before any
client access and under either strategy.*

### Phase 2 — Wire (and modestly extend) the Netlify attach capability

Mostly wiring, but **honestly more than plumbing**: the existing
`set_custom_domain()` ([deploy.py:302](../../packages/web/deploy.py:302)) only
PATCHes `custom_domain`. The www-primary + apex-alias plan and the SSL nudge below
are **new behavior** to add to `NetlifyDeployTarget`, not just CLI wiring.

4. **`launch_client.py --domain acme.com`** → gate stays `assert_custom_domain_allowed`
   (the existing single boolean is the right gate here — Phase 2 attaches to *our*
   Netlify account, it does not write the client's zone, so the Phase 3 diff-pinned
   gate does not apply). Control-proof = `--dns-approved` + operator confirms the
   client did the registrar step. Per Netlify guidance: set
   `custom_domain = www.acme.com`, add `acme.com` as a **domain alias**
   (GET-merge-PATCH `domain_aliases` — replace semantics; **new method work**).
   Stamp the real domain into `intake.site_url`. Then `POST /sites/{id}/ssl` to
   nudge the cert and poll `GET .../ssl` (**new method work**). Handle **"domain
   already in use on another account"** as a manual TXT-verify + Netlify-support
   escalation (not API-automatable).
5. **`--transfer-to <account>`** → wire `transfer_ownership()` for offboarding.
   **Note:** *offboarding* plumbing riding along; handoff is high-consequence and
   near-irreversible — give it **its own approval gate**, distinct from "attach
   domain." (Netlify PATs are account-wide and **cannot** be capability-scoped, so
   the gate — not token scoping — is the real control; just confirm the
   destination account is correct before transferring.) Consider splitting this to
   its own tiny change rather than bundling into the onboarding PR.

*Effort: small — but it touches `NetlifyDeployTarget`, not just the CLI.*

### Phase 3 — `CloudflareDnsProvider` (VOLUME-GATED — defer until client count justifies)

Its whole payoff is shrinking the operator's per-client work and making cutover
programmatic. With few clients the Phase 1 external path is already safe and fast,
so this is deferred — and when it lands it's a **concrete class, no Protocol**:

6. **`packages/web/dns.py` → `CloudflareDnsProvider`** (injectable `httpx.Client`):
   `create_zone` (full setup; read the **per-zone `name_servers`** from the
   response — never hardcode), `import_zone` (BIND import of recon'd MX/SPF/DKIM/
   DMARC **before** NS cutover — the email-survival gate; 256 KiB / 3-req-min
   limit), `set_records` (Netlify apex CNAME + www CNAME + email records, all
   **grey-cloud/DNS-only**), `activation_check` + poll `status==active` (free zones
   = 1 check/hr), `verify`. **All writes** obey the destructive-write contract
   (snapshot → diff → pin-approval → apply → verify → rollback-on-fail).
7. **Founder-approval boundary:** managed-DNS writes are a *new outward-write
   surface* distinct from "attach a Netlify domain." If they warrant their own
   gate or a new `PolicyViolationCode`
   ([approvals.py:105](../../packages/policies/approvals.py:105) currently only has
   `DEPLOY_DNS_NOT_APPROVED`/`DEPLOY_SPEND_NOT_APPROVED`), that edits
   `packages/policies/` → **requires founder approval.** Flag at design time.
8. **DNSSEC handoff:** if the source domain has DNSSEC, disable it at the old
   provider before NS switch, re-enable in Cloudflare + push new DS to registrar
   after — or resolution SERVFAILs. **Resolve the open account-model decision
   (per-client scoped token, see Security) before writing this phase.**

### Phase 4 — (later, bigger) Google Workspace provisioning

9. Admin SDK mailbox creation + domain verification before MX switch
   (publish DKIM TXT *then* enable; single SPF; DMARC `p=none` first). Higher auth
   complexity (domain-scoped OAuth, narrowest admin scopes — no super-admin token).
   Deferred until volume justifies; until then `business_email.py` runbook +
   Phase 1 carry-over records cover it manually.

## The human-in-the-loop boundary (by design)

Exactly **one** human action remains, at the registrar; strategy picks which:
- **External:** "add these records" (varies by registrar, error-prone) — but no
  NS move, lowest client trust required. **v1 default.**
- **Managed:** "set these 2 nameservers" (foolproof, identical every client) —
  unlocks full downstream automation. **Volume-gated.**

Everything before (recon, plan, instructions, control-proof) and after (attach,
verify, SSL, handoff) is automated. We can't remove the registrar action without
per-registrar API credentials — not worth building.

## What we can do *before* knowing where the domain is from

- Run **validated** `domain_recon` the moment a prospect submits a domain — but
  **rate-limit/cache/queue** it (don't fire synchronously on every raw public form
  hit; it's an unauthenticated outbound-request generator otherwise). Attach the
  readiness report to the lead. **Reads only — no zone-create/attach until
  control is proven.**
- Build + deploy the site to a `*.netlify.app` URL immediately (already automated).
- Pre-generate the cutover plan + verification so go-live is minutes once the
  client grants the one registrar action.

## Open decisions / risks

- **Cloudflare account model** (Phase 3): now framed as a **security requirement**
  (blast radius), not billing — prefer per-client scoped tokens; record accepted
  risk + rotation plan if one agency token is chosen. Resolve before Phase 3 code.
- **RDAP coverage:** `.io`/`.co`/many ccTLDs lack RDAP → NS-only degraded path;
  log degraded-confidence recon so a TLD can't be chosen to bypass registrar checks.
- **Runbook update:** [domain-dns-runbook.md](../agency/domain-dns-runbook.md)
  says "preferred: keep DNS at registrar." Once Phase 1 (+ eventual 3) land, amend
  to "managed DNS preferred *when automation is in play* (recon + verify remove the
  email-loss risk); external when the client requires it."
- **Audit log:** record every outward DNS write (approver, diff hash, snapshot id,
  verify result) in an append-only log (repo has a `postmortem_audit_log_path`
  pattern) so "why did this client's mail break" is answerable.

## Suggested build order

**Commit:** Phase 1 → Phase 2 (with the recon-persistence seam + security contract
decided during Phase 1). **Defer (volume-gated):** Phase 3 (concrete
`CloudflareDnsProvider`) → Phase 4. Phase 1 alone makes every onboarding faster
and ships safely on its own.

---

# Research Insights (deepened 2026-06-07)

All values confirmed against live queries / current official docs on 2026-06-07.
Sources cited per section.

## RDAP + DNS-over-HTTPS recon (zero extra deps — httpx only)

- **RDAP:** `GET https://rdap.org/domain/<domain>` is a **302 redirector** — must
  follow redirects; inspect `response.history` to disambiguate a 404 (empty
  history = no RDAP for that TLD → degrade; non-empty = authoritative "domain
  available"). Registrar name lives in the entity with `roles:["registrar"]` →
  `vcardArray[1]` (array-of-arrays, parse defensively); IANA Registrar ID in
  `publicIds` is a stabler key. Nameservers in top-level `nameservers[].ldhName`
  (inconsistent case — lowercase before matching). `secureDNS.delegationSigned` =
  DNSSEC flag (cutover risk). `status` carries EPP transfer-lock codes. **Coverage
  gap:** `.io`, `.co`, `.de`, `.it` have **no RDAP** — exactly the TLDs startup
  clients use; pre-check IANA bootstrap `data.iana.org/rdap/dns.json` (cache 24h)
  and skip RDAP for uncovered TLDs. Rate limit ~10 req/10s on `rdap.org`.
- **DoH:** Google `dns.google/resolve?name=&type=` (no header) + Cloudflare
  `cloudflare-dns.com/dns-query` (requires `Accept: application/dns-json`) share a
  schema — one parser. Check `Answer` *presence*, not just `Status` (`Status:0` +
  no `Answer` = NODATA, e.g. no MX; `Status:3` = NXDOMAIN). **MX** `data` is
  `"10 smtp.google.com."` (split on first space, strip trailing dot). **TXT** may
  arrive quoted/segmented for >255 bytes — strip quotes + concatenate before
  SPF/DKIM/DMARC regex; query `_dmarc.<domain>` explicitly. **CNAME chains**
  flatten into the same `Answer` array (walk it; don't assume `Answer[0]`). TTL is
  the *remaining* cached TTL, not authoritative — recon is a point-in-time snapshot.
  **Wildcard probe:** query a random nonexistent label; if it resolves, caveat all
  subdomain findings. Normalize punycode before querying.
- **NS-suffix → provider/apex-capability map:** `*.cloudflare.com` (flatten),
  `awsdns-*` (Route 53 ALIAS), `domaincontrol.com` (**GoDaddy**, no ALIAS),
  `registrar-servers.com` (**Namecheap**, no ALIAS), `*.nsone.net`/netlify
  (flatten). Unknown suffix → assume A-record-only.
- Sources: [Google DoH JSON](https://developers.google.com/speed/public-dns/docs/doh/json),
  [Cloudflare DoH JSON](https://developers.cloudflare.com/1.1.1.1/encryption/dns-over-https/make-api-requests/dns-json/),
  [RDAP.org](https://about.rdap.org/), IANA bootstrap `data.iana.org/rdap/dns.json`.

## Netlify custom-domain attach + verify (current 2026)

- **Still `PATCH /api/v1/sites/{id}` with `{"custom_domain": ...}`** (the
  `updateSite` endpoint; no replacement). `domain_aliases` is the full list —
  **GET-merge-PATCH** (replace semantics, don't wipe). For external DNS, Netlify
  recommends **www as primary** + apex as alias (auto apex→www redirect).
  Subdomains may require a `netlify-challenge.<domain>` TXT (`txt_record_value`).
- **External DNS targets (confirmed):** apex ALIAS/ANAME/flattened-CNAME →
  `apex-loadbalancer.netlify.com`; apex A-fallback **`75.2.60.5`** (exactly one;
  multiple A = failure); www CNAME → `<site>.netlify.app`. **No AAAA/IPv6** (a
  leftover AAAA breaks cert provisioning). HPE sites have site-specific targets —
  read from the API/UI, don't hardcode. **CAA** records must authorize
  `letsencrypt.org` if present.
- **SSL:** auto Let's Encrypt once DNS resolves; retries every 10 min for 24h then
  hourly to ~72h. `POST /sites/{id}/ssl` forces provisioning; `GET /sites/{id}/ssl`
  → cert `state` + `domains[]` + `expires_at`. Verify both apex + www are covered.
- **Auth/limits:** `Authorization: Bearer <PAT>` + `User-Agent`; 500 req/min
  general, **deploys 3/min & 100/day**; `429` → back off to `X-RateLimit-Reset`.
  **"Domain already in use on another team"** is a real blocker → manual
  `verified-for-netlify.<domain>` TXT + support ticket (not API-automatable).
- Verify end-to-end out-of-band: resolve DNS + HTTPS GET apex(301→www)/www(200),
  don't trust API fields alone.
- Sources: [Adding your domain via Netlify API](https://developers.netlify.com/guides/adding-your-domain-using-netlify-api/),
  [Configure external DNS](https://docs.netlify.com/manage/domains/configure-domains/configure-external-dns/),
  [Troubleshoot SSL/HTTPS](https://docs.netlify.com/manage/domains/troubleshooting/troubleshoot-ssl-and-https/),
  [OpenAPI](https://open-api.netlify.com/).

## Cloudflare managed DNS (Phase 3 — current 2026)

- **Use `type:"full"` setup (free).** `POST /zones` → read **`result.name_servers`
  per-zone** (assigned from a pool — never hardcode the 2 NS). Partial/CNAME setup
  is paid (Business+), can't manage apex/MX — wrong tool.
- **Apex CNAME-flattening is on by default, every plan** → point apex at
  `apex-loadbalancer.netlify.com` directly (no ALIAS hack; returns A/AAAA to
  resolvers). **Keep records grey/DNS-only** for a Netlify origin — orange-cloud
  double-proxies → redirect loops + breaks Netlify cert issuance. MX/TXT are always
  DNS-only; **DKIM CNAMEs must stay grey** or Cloudflare rewrites them.
- **`POST /zones/{id}/dns_records/import`** (BIND, multipart, `proxied=false`):
  pre-load recon'd MX/SPF/DKIM/DMARC **before** NS cutover, then **diff
  `GET /dns_records` against source** (auto-scan misses records — never trust it).
  Limits: 256 KiB file, **3 req/min**, 200 records/zone (zones created ≥2024-09-01).
- **Scoped API Tokens** (not global key): `Zone.DNS:Edit` + `Zone:Read`; keep
  zone-create on a separate token. **Activation:** `PUT /zones/{id}/activation_check`
  (free = 1/hr) then poll `GET /zones/{id}` `status==active`. Unactivated zones
  GC after 28 days. Global limit 1200 req/5min → 429 blocks all calls 5 min.
- Sources: [Zone setups](https://developers.cloudflare.com/dns/zone-setups/),
  [CNAME flattening](https://developers.cloudflare.com/dns/cname-flattening/),
  [Import/export](https://developers.cloudflare.com/dns/manage-dns-records/how-to/import-and-export/),
  [API token permissions](https://developers.cloudflare.com/fundamentals/api/reference/permissions/),
  [Rate limits](https://developers.cloudflare.com/fundamentals/api/reference/limits/).

## Email-preserving cutover (the highest-stakes part)

- **Google Workspace 2026:** single MX `smtp.google.com` pri 1 (legacy 5-record
  `aspmx` set still valid — don't "fix" it); SPF `v=spf1 include:_spf.google.com
  ~all` (**exactly one**); DKIM TXT `google._domainkey` (2048-bit, **publish then
  enable**); DMARC `_dmarc` `p=none` first.
- **Microsoft 365 2026:** MX `<token>.mail.protection.outlook.com` pri 1 (token is
  tenant-specific — read it, don't guess) **and** the new `domain-com.o-v1.mx.microsoft`
  format for domains added ≥**July 1 2026** (recon must match both). SPF
  `include:spf.protection.outlook.com -all`; DKIM via **CNAMEs**
  `selector1/2._domainkey`; `autodiscover` CNAME → `autodiscover.outlook.com`
  (preserve). Recon treats MX (both patterns), any `v=spf1`/`MS=` TXT, `_dmarc`,
  anything under `_domainkey`, and `autodiscover` as **never-delete**.
- **NS-move safety pattern (the automation contract):** export full zone first →
  replay every non-NS record at the new provider → **diff until identical** →
  **lower TTLs to 300s on the *old* provider 24–48h before** (a resolver only
  learns the lower TTL on its next query) → query new NS directly to confirm →
  cut NS → verify → **live two-way email test (the actual gate)** → restore TTLs.
- **60-day ICANN lock** still the safe 2026 assumption; the trap: **changing the
  registrant/Whois contact** triggers a fresh lock. **A website cutover and even a
  managed-DNS move need no registrar transfer** — change only DNS/NS, leave
  registrant + registrar alone, and the lock is irrelevant.
- Sources: [Google MX setup](https://knowledge.workspace.google.com/admin/domains/set-up-mx-records-for-google-workspace),
  [M365 external DNS records](https://learn.microsoft.com/en-us/microsoft-365/enterprise/external-domain-name-system-records),
  [M365 mx.microsoft migration 2026](https://www.captaindns.com/en/blog/microsoft-365-mx-dnssec-migration-2026),
  [ICANN 60-day lock on registrant change](https://support.dnsimple.com/articles/icann-60-day-lock-registrant-change/).
