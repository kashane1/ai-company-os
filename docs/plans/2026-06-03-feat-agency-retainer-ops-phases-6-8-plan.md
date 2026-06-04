---
title: "feat: Agency retainer ops (Phases 6–8)"
type: feat
status: active
date: 2026-06-03
change_id: agency-retainer-ops-6-8
related_plan: docs/plans/2026-06-01-feat-local-smb-agency-layer-plan.md
related_brainstorm: docs/brainstorms/2026-06-01-agency-layer-brainstorm.md
related_guide: docs/agency/client-lifecycle.md
owner: kashane
last_reviewed: 2026-06-03
---

# Agency retainer ops — Phases 6–8 plan

**Review this file as a whole:**  
`docs/plans/2026-06-03-feat-agency-retainer-ops-phases-6-8-plan.md`

---

## Table of contents

1. [Why this document exists](#why-this-document-exists)
2. [Operating model: monthly retainer loop](#operating-model-the-monthly-retainer-loop)
3. [Design principles](#design-principles-agent-native--beginner-safe)
4. [Locked decisions (operator)](#locked-decisions-operator-2026-06-03)
5. [Geography & markets](#geography--markets-not-seattle-locked)
6. [Phase 6 — Local SEO](#phase-6--local-seo-ship-first)
7. [Phase 7 — Monthly reporting](#phase-7--monthly-reporting-retainer-engine)
8. [Phase 8 — Demand-driven services](#phase-8--demand-driven-services-sliced-not-one-blob)
9. [Phase 8.0 — Compliance (shipped as templates)](#phase-80--compliance-templates-shipped)
10. [Phase 9 — Stripe billing](#phase-9--stripe-billing-in-repo)
11. [RetainerOps orchestrator](#cross-cutting-retainerops-orchestrator)
12. [Approval queue](#approval-queue-control-plane-first)
13. [Build sequencing](#sequencing-recommended-build-order)
14. [Ideas (not committed)](#ideas-worth-considering-not-committed)
15. [Success metrics](#success-metrics-how-we-know-phases-68-work)
16. [Related files](#related-files)
17. [Next implementation steps](#next-implementation-steps)

---

## Why this document exists

Phases **1–5** (catalog → promote → intake → launch) are implemented and documented in
[`docs/agency/client-lifecycle.md`](../agency/client-lifecycle.md). This plan covers
**what happens after a client site is live**: recurring services that justify the
monthly retainer.

Written for an operator who **leans on agents to build and run** the stack, with
**minimal human-in-the-loop** — judgment and approvals, not repetitive execution.

**Ads:** You want **Package C with Google Search ads**. Agents **draft** campaigns;
**you** connect accounts, set budgets, and approve go-live. Meta ads stay quote/add-on
until a client explicitly needs them. An **operator ads playbook** ships before the
first live campaign (Phase 8-L.0). You have not run ads before — the playbook is the
on-ramp, not optional reading.

---

## Operating model: the monthly retainer loop

```text
┌─────────────────────────────────────────────────────────────────┐
│  MONTHLY RETAINER LOOP (per client)                              │
├─────────────────────────────────────────────────────────────────┤
│  1. COLLECT   — forms, Plausible, uptime, broken links (auto)    │
│  2. DIAGNOSE  — agent reads metrics + CLIENT_BRIEF + OFFER       │
│  3. PROPOSE   — one recommended action (report + task ticket)    │
│  4. EXECUTE   — agent runs allowed services (SEO, GBP draft, …)  │
│  5. VERIFY    — ux_audit + policy gates before publish           │
│  6. NOTIFY    — draft owner report → you forward manually (v1)   │
└─────────────────────────────────────────────────────────────────┘
```

| You do | Agents do |
|--------|-----------|
| Approve deploys / DNS | Local SEO matrix + pages |
| Approve GBP live edit (v1: paste changeset) | GBP draft copy |
| Approve live review SMS **after** signed addendum | Review templates + cadence |
| Approve ad go-live + budget changes | Ad copy + keywords + geo proposal |
| Skim monthly report → forward email | Reports, monitoring, promo pages |
| Discuss pass-through costs with owner when over pool | Track Plausible usage vs pool |

**Time budget:** ~15 min/client/month steady state; ~45–60 min **once** per client for
first ad setup; weekly approval batch.

---

## Design principles (agent-native + beginner-safe)

1. **Packages drive automation** — only services in `client.services[]`.
2. **Policy before publish** — `agency_gates` + deploy gates + canonical approval records.
3. **Packages over skills** for autonomy — Python callables in workers.
4. **Draft by default** — no auto-SMS/email to customers or owners in v1.
5. **Owner language** in reports — leads and calls, not bounce rate.
6. **Ads gated** — client-owned ad spend; agents never move money.
7. **Compliance before review SMS** — signed addendum on file or sends stay blocked.
8. **Canonical approvals only** — retainer approvals use `ApprovalStore` /
   `ControlPlaneService`; client-local files may mirror state but never authorize work.

---

## Locked decisions (operator, 2026-06-03)

| # | Topic | Decision |
|---|--------|----------|
| 1 | Package C | **Includes Google Search ads** (`google_ads`) — draft-only + approval; not autonomous. `meta_ads` is quote/add-on, not default Package C |
| 2 | Analytics | **Plausible + form counts** per client site |
| 3 | Reports v1 | **Manual review + forward** (no auto-email yet) |
| 4 | Plausible cost | **~$100/mo agency pool** included in hosting/plan economics; **overage passed through** — discuss with client before invoicing |
| 5 | GBP v1 | **Copy/paste changeset** (~5 min/client); API later |
| 6 | Reviews | Package B/C include **review readiness** (GBP review link, template draft, cadence, compliance checklist). **Live SMS sends are blocked** until `COMPLIANCE.md` + **signed addendum**; templates **created** under `docs/agency/compliance/` |
| 7 | Geography | **Not Seattle-locked** — major US metros; per-client **service area** in intake/`LOCAL_SEO.md`; ads geo **client-configurable** (radius, multi-city, or not geo-locked) |
| 8 | Billing | **Stripe in repo** — subscriptions/invoicing tied to catalog bundles (Phase 9); Stripe object IDs live in `state/agency/billing/`, registry carries summary status |

### Required catalog alignment before implementation

The plan's Package C decision is load-bearing because `promote_prospect_to_client()`
writes `client.services[]` from `packages/agency/catalog.yaml`. Before Phase 6/7/9 work:

1. Add `google_ads` to `package_c.service_ids`.
2. Keep `meta_ads` out of Package C; offer it only as a quote/add-on.
3. Regenerate the rendered catalog docs/site JSON and update drift tests.
4. Update `reviews` catalog copy from live "Post-service SMS review requests" to
   review readiness: GBP review link, approved template draft, cadence, and compliance
   gate. Live SMS is an activated capability only after signed addendum.

---

## Geography & markets (not Seattle-locked)

Prospecting runs across **many top metros**, not one city. Each client’s geography
is **their** service area, captured at intake:

| Artifact | What it stores |
|----------|----------------|
| `CLIENT_BRIEF.md` | Primary city, region, travel radius, service-area notes |
| `LOCAL_SEO.md` | `primary_city`, `service_area_cities[]`, `services[]` for page matrix |
| `ADS.md` (Package C) | `geo_target` — see below |

**Local SEO:** `generate_matrix` uses cities **listed by the client/agent**, not a
global default. Agent may propose suburbs from primary city, but `run_local_seo.py`
must fail closed until the matrix is explicitly approved in `LOCAL_SEO.md`.

**Intake fields to add before Phase 6 generation:**

```yaml
service_area:
  primary_city: "Tacoma"
  region: "WA"
  radius_miles: 15
  cities: [Tacoma, Federal Way, University Place]
  notes: "No jobs north of Seattle; emergencies within 20 miles only."
  matrix_approved: false
  approved_by: ""
  approved_at: ""
```

`ClientIntake` gets `service_area_cities`, `travel_radius_miles`, and
`service_area_notes`. `apply_client_intake()` renders those into `CLIENT_BRIEF.md`
and `LOCAL_SEO.md`; the local SEO CLI refuses `_TBD_`, empty city lists, or
`matrix_approved: false`.

**Ads geo targeting** (`ADS.md` YAML):

```yaml
geo_target:
  mode: radius | cities | national   # client choice
  center: "Tacoma, WA"               # for radius mode
  radius_miles: 15                   # smaller or larger per client
  cities: []                         # for cities mode, e.g. [Tacoma, Federal Way]
  notes: ""                          # e.g. "statewide for emergency calls"
```

- **Default proposal:** radius **15–25 miles** around primary city (agent drafts).
- **Client can widen/narrow** or request **national** (rare for local SMB — flag for
  manual review).
- Agent never publishes geo without it matching signed intake/OFFER.

---

## Phase 6 — Local SEO (ship first)

**Goal:** Fulfill `local_seo` for Package C via a **service × geo** page matrix.

**In repo:** `packages/agency/local_seo.py`, `test_agency_local_seo.py`.

| Deliverable | Description |
|-------------|-------------|
| `parse_local_seo_matrix` | Read `LOCAL_SEO.md` (table or YAML) |
| `emit_seo_pages_to_site` | Astro/static pages + sitemap |
| `scripts/agency/run_local_seo.py` | generate → audit → optional deploy |

**Human:** approve deploy; approve matrix if agent inferred extra cities. Matrix
approval is a canonical approval record, then mirrored into `LOCAL_SEO.md`.

**Follow-up 6.1:** LLM-unique bodies per cell (optional quality pass).

---

## Phase 7 — Monthly reporting (retainer engine)

### 7.0 — Analytics (**locked: Plausible + forms**)

- Per-client Plausible site/snippet at launch.
- Form counts from client site webhooks / state.
- Calls: honest “not tracked” until CallRail or similar.

### 7.1 — Plausible cost pool (**locked**)

| Layer | Rule |
|-------|------|
| Agency pool | **~$100/month** baseline for Plausible (and similar tooling) — treated as cost of running hosting/analytics for the book of business |
| Per client | Included while pool covers all active client sites |
| Overage | If pool exceeded, **calculate pass-through**, **discuss with business before invoicing**, document in monthly report + `OFFER.md` override note |
| Agent | Tracks aggregate usage in `state/agency/analytics-pool.json` (to build); flags when approaching cap |

### 7.2 — Analytics adapter + report CLI

`packages/agency/analytics/`, `monthly_report.py`, `run_monthly_report.py`.

**Human (locked):** review draft (~2 min) → forward email manually.

---

## Phase 8 — Demand-driven services (sliced)

```text
8.0  Compliance templates (shipped at promotion)
8-A  GBP (copy/paste v1)
8-B  Booking embed
8-C  Review SMS live activation (blocked until addendum signed)
8-D  Promo landing pages
8-E  Follow-up automation (after 8-C)
8-F  CRM / 8-G  Fractional CTO — quote only
8-L  Ads — draft + operator playbook
```

### 8.0 — Compliance templates (**shipped**)

Created under [`docs/agency/compliance/`](../agency/compliance/):

| File | Role |
|------|------|
| `COMPLIANCE-template.md` | Per-client gate checklist |
| `review-sms-consent-addendum.md` | Signable TCPA-oriented addendum |
| `README.md` | How to use |

**Wiring:** `scaffold_client_workspace()` copies these into every promoted client at
`docs/products/<slug>-site/COMPLIANCE.md` and `compliance/review-sms-consent-addendum.md`.

**Policy (to implement before any customer-phone-number import or send path):**
`assert_review_sms_allowed` checks signed addendum on file, approved template, quiet
hours, frequency cap, and canonical approval. It is not deferred until Twilio code;
it lands with the first review-SMS-adjacent code path.

**Package wording:** `reviews` means review readiness until live activation:
GBP review link, approved draft template, cadence, compliance checklist, and owner
instructions. **Enable live SMS only after:** addendum signed + scan stored under
`compliance/review-sms-consent-signed.pdf`.

### 8-A — GBP

Agent → `GBP_CHANGESET.md`; you paste (~5 min). API in 8-A.1.

### 8-C — Review SMS

See 8.0. Agent drafts; human approves template; v2 Twilio with gate. Live sends
require a signed addendum and `assert_review_sms_allowed`.

### 8-L — Ads (Package C = Google Search)

**8-L.0** `docs/agency/operator-ads-playbook.md` — client billing, Search-first,
budget caps, geo from `ADS.md`, when to refuse. Meta ads are quote/add-on only.

**8-L.1** `packages/agency/ads.py`, `draft_ads.py`, `AD_SPEND_NOT_APPROVED`.
Drafts are created only when `google_ads` is present in `client.services[]`.

**Never:** autonomous spend.

---

## Phase 9 — Stripe billing (in repo)

**Goal:** Bill setup + monthly retainers via **Stripe**, aligned to `catalog.yaml`
bundles — not manual dashboard-only.

**Reuse:** patterns from `packages/web/stripe_monetization.py` (test/live gate,
approval for live keys).

| Deliverable | Description |
|-------------|-------------|
| `packages/agency/billing.py` | Map `package_a|b|c` → Stripe Price IDs (config) |
| `infra/agency-stripe.yaml` or env | Price IDs per bundle (setup + monthly); no secrets |
| `state/agency/billing/<product_id>.json` | Stripe customer/subscription/invoice IDs, mode, last sync, idempotency state |
| `scripts/agency/create_client_subscription.py` | After promotion: create Customer + Subscription |
| Netlify webhook receiver | Reuse existing Netlify Stripe scaffold to verify Stripe signatures and persist verified billing events for local reconciliation |
| `scripts/agency/reconcile_stripe_billing.py` | Pull verified Stripe state/events → update billing ledger + `client.billing_status` summary |
| Policy | Live Stripe charges require canonical approval (existing `PAYMENTS_LIVE` pattern) |

**Human minimal:** approve live Stripe once; per-client subscribe is CLI/agent with
confirmation. Failed payment → `billing_status: past_due` on registry (agent surfaces in report).

**Billing state model:** registry stays small and source-controlled; operational Stripe
state lives under `state/agency/billing/`:

```json
{
  "product_id": "joes-plumbing-site",
  "provider": "stripe",
  "mode": "test",
  "bundle": "package_c",
  "customer_id": "cus_...",
  "subscription_id": "sub_...",
  "setup_price_id": "price_...",
  "monthly_price_id": "price_...",
  "latest_invoice_id": "in_...",
  "billing_status": "active",
  "idempotency_key": "joes-plumbing-site:package_c:test",
  "last_synced_at": "2026-06-03T00:00:00Z"
}
```

Stripe checkout/subscription creation includes `metadata.product_id` and
`metadata.bundle`; event mapping must verify both metadata and ledger IDs. Re-running
subscription creation for the same product/bundle/mode reuses the ledger record or
fails with an explicit "already subscribed" message.

**Webhook execution model:** reuse the existing Netlify serverless Stripe scaffold
as the public receiver. Netlify verifies the Stripe signature, records the raw event
ID/type/object metadata in a minimal verified-event file or queue, and returns 200.
It does **not** directly mutate Mac-local `state/agency/billing/` or
`infra/products.json`. The local command `scripts/agency/reconcile_stripe_billing.py`
pulls verified events or reads Stripe subscriptions by `metadata.product_id`, applies
idempotency by Stripe event ID + ledger subscription ID, and then writes the local
billing ledger plus registry summary. RetainerOps runs reconciliation before monthly
reports.

**Out of scope v1:** automated dunning emails (draft only).

---

## Cross-cutting: `RetainerOps` orchestrator

`packages/agency/retainer_ops.py` + `scripts/agency/run_retainer.py` — one monthly
command per client (runs 6+7 for allowed services, lists blocked approvals).

---

## Approval queue (control-plane first)

Retainer approvals are canonical `ApprovalRecord`s created through
`ControlPlaneService` / `packages.tools.primitives.approvals`. No retainer action is
authorized by a client-local JSON file.

Approval record contract:

| Approval type | Action | Subject type | Subject ID | Required artifact |
|---------------|--------|--------------|------------|-------------------|
| `client_site_deploy` | `publish_client_site_change` | `client_site` | `product_id` | Preview URL + generated diff/audit report |
| `client_dns_change` | `update_client_dns` | `client_site` | `product_id` | Domain/DNS checklist |
| `review_sms_activation` | `activate_review_sms` | `client_site` | `product_id` | Signed addendum + template/cadence |
| `review_sms_template_change` | `change_review_sms_template` | `client_site` | `product_id` | Template diff + cadence summary |
| `ad_campaign_go_live` | `launch_google_ads_campaign` | `client_site` | `product_id` | `ADS.md` + campaign draft |
| `ad_budget_change` | `change_ad_budget` | `client_site` | `product_id` | Prior/new budget + client approval note |
| `stripe_live_subscription` | `create_live_stripe_subscription` | `client_site` | `product_id` | Offer + price IDs + customer summary |
| `analytics_overage_pass_through` | `invoice_analytics_overage` | `client_site` | `product_id` | Usage calculation + owner discussion note |

Every retainer policy gate checks the expected `approval_type`, `action`, and
`subject_id`. A granted approval for one client, one action, or one artifact must not
authorize a different client/action. High-risk approvals (`client_dns_change`,
`stripe_live_subscription`, `ad_budget_change`, `review_sms_activation`) also require
the matching review artifact path to exist.

Client-local state is allowed only as a projection:

```text
state/clients/<product_id>/
  approval-projection.json   # read-only mirror of canonical approvals
  retainer-runs/YYYY-MM.json
```

CLIs: `scripts/agency/list_retainer_approvals.py` reads canonical approvals and
groups them by client; `approve.py` is **not** a new authority. Approval decisions
continue through the existing approval reviewer / magic-link / control-plane path.

---

## Sequencing (recommended build order)

| Order | Phase | Why |
|-------|-------|-----|
| 1 | **8.0** Compliance | **Done** — templates + scaffold wiring |
| 2 | **0.1** Catalog alignment | Add Package C `google_ads`; rewrite `reviews` as readiness; regenerate mirrors |
| 3 | **0.2** Canonical retainer approvals | Define action types + projection rules before RetainerOps |
| 4 | **0.3** Intake service area | Structured fields + `LOCAL_SEO.md` render + fail-closed matrix approval |
| 5 | **6.0** Local SEO CLI | Package C value; code exists |
| 6 | **7.0** Plausible + reports | Retainer proof |
| 7 | **9.0** Stripe billing ledger | Revenue tied to registry summary + state ledger |
| 8 | **8-A** GBP changeset | Every Package A+ |
| 9 | **8-D** Promo pages | Quick wins |
| 10 | **RetainerOps** | One monthly command |
| 11 | **8-B** Booking | Package B |
| 12 | **7.5** Scheduled report drafts | launchd |
| 13 | **8-L.0** Ads playbook | Before first ad client |
| 14 | **8-L.1** Ad drafts + gate | Package C Google ads |
| 15 | **8-C** Review SMS live | After addendum + Twilio |

Phases **1–5** remain prerequisite.

---

## Implementation progress

- [x] **0.1** Catalog alignment: Package C includes `google_ads`; `reviews` is readiness; mirrors regenerated.
- [x] **0.2** Canonical retainer approvals: typed approval contract, policy gate, and listing CLI.
- [x] **0.3** Intake service area: structured fields, `LOCAL_SEO.md` render, fail-closed matrix approval input.
- [x] **6.0** Local SEO CLI: parse approved matrix, generate pages, emit Astro pages + local sitemap.
- [x] **7.0** Monthly reporting v1: owner-friendly markdown report renderer + CLI.
- [x] **9.0** Billing ledger v1: local Stripe event reconciliation + registry summary update.
- [x] **8-L.0** Operator ads playbook.
- [x] **RetainerOps** skeleton: monthly run plan + state artifact.
- [x] Review SMS policy gate: signed addendum + template + cadence + canonical approval.
- [ ] **8-A** GBP changeset generator.
- [ ] **8-B** Booking embed implementation.
- [ ] **8-D** Promo landing page workflow.
- [ ] **8-L.1** Google Ads draft generator.
- [ ] **8-C** Live Review SMS/Twilio path.

---

## Ideas worth considering (not committed)

1. Lead SMS **to owner** when form fires (not to customer).
2. Client portal `/owner-report/YYYY-MM` on their site.
3. “Growth lite” bundle (B + SEO + report, no ads).
4. Quarterly GBP refresh task in retainer loop.

---

## Success metrics (how we know Phases 6–8 work)

| Metric | Target |
|--------|--------|
| Hands-on time per client / month | &lt; 15 min median (excl. first ad setup) |
| Review SMS without signed addendum | **0** |
| Ads spend without approval | **0** |
| Plausible overage invoiced without owner discussion | **0** |
| Client-facing send without approval | **0** |
| Retainer action authorized by non-canonical approval state | **0** |
| Local SEO pages generated from unapproved/TBD matrix | **0** |
| Stripe webhook unable to map event to one client ledger | **0** |

---

## Related files

| Area | Path |
|------|------|
| **This plan** | `docs/plans/2026-06-03-feat-agency-retainer-ops-phases-6-8-plan.md` |
| Phases 1–5 | `docs/agency/client-lifecycle.md` |
| Compliance templates | `docs/agency/compliance/` |
| Catalog | `packages/agency/catalog.yaml` |
| Client workspace scaffold | `packages/agency/templates.py` |
| Stripe (web lane) | `packages/web/stripe_monetization.py` |
| Retainer approvals | `packages/agency/approvals.py`, `packages/policies/agency_gates.py` |
| Monthly reports | `packages/agency/monthly_report.py`, `scripts/agency/run_monthly_report.py` |
| Local SEO | `packages/agency/local_seo.py`, `scripts/agency/run_local_seo.py` |
| Billing ledger | `packages/agency/billing.py`, `scripts/agency/reconcile_stripe_billing.py` |
| RetainerOps | `packages/agency/retainer_ops.py`, `scripts/agency/run_retainer.py` |
| Ads playbook | `docs/agency/operator-ads-playbook.md` |
| Original agency plan | `docs/plans/2026-06-01-feat-local-smb-agency-layer-plan.md` |

---

## Next implementation steps

1. Implement **8-A** GBP changeset generator.
2. Implement **8-D** promo landing page workflow.
3. Implement **8-L.1** Google Ads draft generator using `ADS.md` + `client.services[]`.
4. Implement **8-B** booking embed helper.
5. Implement **8-C** live Review SMS/Twilio path behind `assert_review_sms_allowed`.
6. Expand RetainerOps from planning to execution once each service runner is ready.

Compliance scaffolding at promotion is **already wired** — new clients get
`COMPLIANCE.md` + addendum on promote.
