# Domain & DNS Runbook

> How to point a small-business domain at the Netlify-hosted site **and** keep
> Google Workspace email flowing — at the same time, on the same zone, without
> knocking either one offline. This is the single most error-prone part of
> delivering a Presence (Package A) engagement.
>
> Pairs with: [client-sla.md](client-sla.md) · [go-live-checklist.md](go-live-checklist.md) ·
> [client-lifecycle.md](client-lifecycle.md). Sources: [go-live readiness plan](../plans/2026-06-05-feat-agency-packages-go-live-readiness-plan.md).

## Automation (recon + verify)

This runbook is the manual procedure; two CLIs now automate its riskiest reads so
you don't eyeball `dig` output:

- **Before** — `python scripts/agency/domain_recon.py <domain>` reads the live zone
  (RDAP + DNS-over-HTTPS) and tells you the registrar, DNS provider (→ apex ALIAS
  vs the A-record fallback in §1), and **the email host whose MX/SPF/DKIM/DMARC
  must survive** (§2). Add `--site <name>.netlify.app` to print the exact records.
- **Attach** — `python scripts/agency/attach_domain.py --product-id <id> --domain
  <domain> --dns-approved --client-confirmed-registrar` attaches the domain to the
  Netlify site (www-primary + apex-alias) behind the approval + control-proof gates.
- **After** — `python scripts/agency/verify_domain.py <domain> --site
  <name>.netlify.app --expect-email "<host>"` runs §4's checks as code across two
  resolvers and **fails loudly if email broke**. Still send a real test email — the
  live-mail check below remains the gate.

## The one rule that prevents most incidents

A domain's zone holds **independent record types**: the website lives on
**A / ALIAS / CNAME** records; email lives on **MX + SPF/DKIM/DMARC (TXT)**
records. They do **not** conflict. **The danger is deleting the wrong ones.**

> ⚠️ **When you point the domain at Netlify, do NOT delete the MX/TXT records.
> When you set up email, do NOT delete the website records. After ANY DNS change,
> verify email still flows** (send a test to the new mailbox).

If you move nameservers to Netlify DNS, you must **re-create the MX/SPF/DKIM/DMARC
records at Netlify** or email silently dies the moment the NS cutover propagates.
**Preferred: keep DNS at the registrar (one DNS provider)** and add Netlify's
records there — avoids split-brain.

## 0. Ownership & access (set this first)

- **Client is the domain registrant** (their name + email on the registration).
  Never register in the agency's name — agency-owned domains are the #1 offboarding
  hostage scenario. If you must register on their behalf, set the **client as
  registrant immediately** (and beware the lock below).
- Get **delegated DNS access** (registrar login or DNS-only access), not ownership.
- Lower record **TTLs to 300s** *before* any planned cutover so changes propagate
  fast.

## 1. Point the website at Netlify (external DNS)

Per Netlify's current docs:

| Host | Type | Value |
|---|---|---|
| apex / root (`example.com`) | **ALIAS / ANAME / flattened CNAME** | `apex-loadbalancer.netlify.com` |
| apex (only if provider lacks ALIAS) | **A** | `75.2.60.5` |
| `www` | **CNAME** | `<site-name>.netlify.app` |

- The apex does **not** support a plain CNAME — use ALIAS/ANAME (preferred, more
  resilient) or the A-record fallback.
- Netlify's stated propagation ceiling is "up to a full day"; usually minutes–hours.
- Add the custom domain in the Netlify site settings and let it provision the
  Let's Encrypt certificate after the records resolve.

## 2. Set up Google Workspace email (same zone)

1. **Verify the domain** in Google Admin (TXT record, or instant if you control DNS
   / Search Console): minutes–few hours.
2. **Create all user mailboxes BEFORE switching MX** (Google's stated best practice
   — prevents bounces).
3. **Switch MX** to the single modern record (since April 2023 Google uses one MX,
   not the old 5-record `aspmx` set):

   | Host | Type | Priority | Value |
   |---|---|---|---|
   | `@` (root) | **MX** | 1 | `smtp.google.com` |

4. **Delete old/registrar-default MX records** (but nothing else).
5. **Publish the email TXT records** (these are what actually keep you out of spam):

   | Host | Type | Value |
   |---|---|---|
   | `@` | TXT (SPF) | `v=spf1 include:_spf.google.com ~all` (exactly **one** SPF record) |
   | `google._domainkey` | TXT (DKIM) | the 2048-bit key generated in Google Admin — **DKIM is OFF until you publish this** |
   | `_dmarc` | TXT (DMARC) | `v=DMARC1; p=none; rua=mailto:dmarc@<domain>;` (start at `p=none`, tighten later) |

> Email reliability: usually <1 business day; Google's ceiling is 48–72h. Don't
> promise faster (see [client-sla.md](client-sla.md)).

## 3. The 60-day transfer lock (don't get surprised)

ICANN imposes a **60-day lock** after (a) a new registration, (b) a prior registrar
transfer, or (c) a **change of registrant/Whois contact**. No registrar can
override it. The classic trap: registering a domain and *then* changing the owner
contact during onboarding locks it for 60 days — you can't move registrars.

- ICANN approved moving this to a **mandatory 30-day lock + opt-out**, staged
  through 2026 and **not uniformly live** — some registrars already offer opt-out,
  most still enforce 60. **Plan and quote against 60 days.**
- A normal registrar-to-registrar transfer (not blocked by a lock) takes ~5–7 days.

## 4. Post-change verification (always run)

After any DNS change:

- [ ] `dig <domain>` / `dig www.<domain>` → resolves to Netlify; site loads over
      HTTPS (cert provisioned).
- [ ] `dig MX <domain>` → `smtp.google.com`; **send a test email to a new mailbox
      and confirm it arrives.**
- [ ] `dig TXT <domain>` (SPF), `dig TXT google._domainkey.<domain>` (DKIM),
      `dig TXT _dmarc.<domain>` (DMARC) → all resolve as expected.
- [ ] Nothing on the website side broke the email records (and vice-versa).

## 5. Offboarding (clean exit, because we set ownership right)

Because the client owns the domain (registrant) and is GBP Primary Owner, exit is
trivial: remove the agency's delegated DNS access and GBP Manager access; transfer
or hand over the Netlify site (team membership or export + redeploy). No
re-verification, no hostage domain. Keep a master credential sheet (registrar,
DNS, hosting, email, analytics + owner email + renewal dates) so the handover is a
checklist, not an archaeology project.
