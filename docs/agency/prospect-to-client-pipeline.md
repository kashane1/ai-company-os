# BBW Pipeline — Finding a Prospect → Recurring Client

> **TL;DR** — The end-to-end Better Business Web funnel, in one place: how a local
> business goes from a row in a database to a paying monthly client. Nine stages:
> **collect → verify → resolve contact → build demo → outreach → sell → onboard →
> deliver/launch → recurring ops + billing.** Each stage below links to its canonical
> doc and names the code/CLI that runs it, with an honest status and the known gaps.
> This is the map; the linked docs are the territory. For the zoom-in on promotion →
> launch (Phases 3–5) see [client-lifecycle.md](client-lifecycle.md); for stages
> 1–4 see [../waas-prospecting-lane.md](../waas-prospecting-lane.md).

## The funnel at a glance

| # | Stage | What happens | Status | Canonical doc |
|--:|---|---|---|---|
| 1 | **Collect** | Local businesses enter the warehouse from Google Places + open data (Overture/FSQ) | ✅ live | [../waas-prospecting-lane.md](../waas-prospecting-lane.md) |
| 2 | **Verify** | Confirm the "no owned website" signal is real; classify web presence | ✅ live | [manual-verification-sop.md](manual-verification-sop.md) |
| 3 | **Resolve contact** | Find the best reachable channel (email/IG/FB/booking; phone is baseline) | ✅ live | [manual-verification-sop.md](manual-verification-sop.md) |
| 4 | **Build demo** | Hand-build one bespoke preview site as the conversion edge; optionally run Conversion Lab on the current page/profile | ✅ live | [../demo-site-build-playbook.md](../demo-site-build-playbook.md), [conversion-lab.md](conversion-lab.md) |
| 5 | **Outreach** | Draft a personalized, channel-appropriate message (operator sends by hand) | ✅ draft-only (by design) | [outreach-copy-rules.md](outreach-copy-rules.md) |
| 6 | **Sell** | Stripe checkout (one-time setup + monthly), webhook → billing ledger; Conversion Lab can also sell as a paid diagnostic | ✅ live (test proven) | [first-sale-runbook.md](first-sale-runbook.md), [conversion-lab.md](conversion-lab.md) |
| 7 | **Onboard** | Promote prospect → client; intake → scaffold the real site | ✅ live | [client-lifecycle.md](client-lifecycle.md) |
| 8 | **Launch** | Final QA checklist (UX/SEO/form/GBP/DNS) → go live | ✅ live | [client-lifecycle.md](client-lifecycle.md), [domain-dns-runbook.md](domain-dns-runbook.md) |
| 9 | **Recurring** | Monthly retainer ops (SEO/GBP/booking/reports/ads) + subscription billing; Conversion Lab preflights Package C promo/ad work | ⚠️ partial | [go-live-checklist.md](go-live-checklist.md), [client-sla.md](client-sla.md), [conversion-lab.md](conversion-lab.md) |

Hard boundary across the whole funnel: **no automated outbound send and no
irreversible/external action without an approval gate.** Outreach is always a draft;
live payments, ad spend, DNS, and SMS are human-gated.

---

## Stage 1 — Collect

Businesses enter `state/prospects/records/<id>.json` (one `ProspectRecord` per file,
schema: [prospect.py](../../packages/schemas/prospect.py)) from two source types:
Google Places (data-rich: phone, rating, **review count**, Maps website field) and
open data — Overture / Foursquare (sparse: name, address, phone; **no review
count**). Code: `packages/prospecting/` (`run.py`, `connectors/`, `source_import.py`,
`cohorts.py`); CLI: `scripts/prospect_scan.py`. Each record is assigned a **cohort**
(`cohorts.py`) — `A_gold` / `A2_marketplace_review` / `S_source_candidate` (open-data,
demand unknown) / `E_has_site` (drop) / etc. — and a priority score.

**Gaps:** open-data rows arrive with `user_ratings_total = 0` (unknown demand, not
zero); the Maps "no website" flag is only a *candidate* signal (see Stage 2).

## Stage 2 — Verify

The Maps "no website" signal is unreliable — a 2026-06-02 pass found ~37% of
`A_gold` actually had an owned site Maps didn't list. So every candidate gets one web
check and a `web_verify_verdict`: `owned_site` (drop) · `marketplace_only` /
`social_only` / `none_found` (targets) · `ambiguous` (review). **Primary method:**
the no-API browser pass — an agent drives Chrome (Maps-first), sharded across N
chats. CLI: `verify-web-export` → browse → `verify-web-ingest`. Code:
[manual_verify.py](../../packages/prospecting/manual_verify.py) (reuses
`classify_web_presence` from `web_presence.py`). A legacy paid-API path
(Brave/DataForSEO) still exists for bulk runs but is no longer preferred.

**Gaps:** browse-only (no cheap automated pre-filter to skip likely-owned sites);
`derive_composite_cohort` keys off review count + Maps class — a verified `owned_site`
is pinned to `E_has_site` so it can't drift back into a target bucket.

## Stage 3 — Resolve contact

Outreach needs a reachable channel. Phone is always on the record; the **contacts-only
pass** resolves the digital channels (`contact_email` / `contact_instagram` /
`contact_facebook` / `contact_booking_url`) for already-verified targets **without
re-touching the verdict**. CLI: `verify-web-export --contacts-only` →
`verify-web-ingest --contacts-only`. Code: `export_contact_worklist` /
`ingest_manual_contacts` in [manual_verify.py](../../packages/prospecting/manual_verify.py).

**Gaps:** browse-only (no Hunter/Apollo-style API fallback for bulk); `none_found`
businesses are phone-only by definition; many marketplace-only businesses never expose
an email, so phone stays the channel.

## Stage 4 — Build demo

One **bespoke, evidence-grounded** preview site per prospect — the conversion edge.
Hand-built per the playbook (gather real data → content brief → palette from their own
signage → build `dist-v2/index.html` → Craft Pass → screenshot QA → gated deploy to a
private Netlify URL). Code: `packages/web/` + `scripts/agency/build_prospect_site.py`,
`screenshot_demo.py`. Canonical: [../demo-site-build-playbook.md](../demo-site-build-playbook.md).
A premium design track exists (`packages/web/design_studio.py`).

For higher-ticket prospects, [Conversion Lab](conversion-lab.md) can run before or
beside the demo build to turn the owner's existing page, marketplace profile, or
promo copy into a concrete conversion-teardown artifact. That report is advisory
preflight intelligence, not a guaranteed prediction of future revenue.

**Gaps:** intentionally manual (no code generator — bespoke is the moat); photo
sourcing + the Craft Pass need a human eye; Netlify draft-deploy cleanup is manual.

## Stage 5 — Outreach

A personalized draft is generated per prospect, channel chosen by what's reachable
(email-with-mockup → IG DM → FB DM → SMS/call). Code:
[outreach.py](../../packages/agency/outreach.py), `outreach_lane.py`,
`outreach_store.py`; CLI: `scripts/agency/build_outreach.py`. Rules:
[outreach-copy-rules.md](outreach-copy-rules.md).

**Hard boundary:** **never auto-sent** — the operator personalizes and sends. Reply
tracking is manual via `engagement_status` (`none → contacted → replied →
proposal_sent → won → onboarded / lost`).

## Stage 6 — Sell

On acceptance: a Stripe Checkout (one-time **setup** + **monthly** line items) →
owner pays → webhook → billing ledger → `billing_status: active`. Pricing/bundles are
the source of truth in [catalog.yaml](../../packages/agency/catalog.yaml) (rendered:
[service-catalog.md](service-catalog.md)). Code:
[payments.py](../../packages/agency/payments.py), [billing.py](../../packages/agency/billing.py),
`registry.py`; CLI: `scripts/agency/create_checkout.py`. Webhook architecture
(Netlify Function + Blobs + local poller) and the test→live sequence:
[first-sale-runbook.md](first-sale-runbook.md), [first-sale-setup-state.md](first-sale-setup-state.md).

Conversion Lab can also be sold here as a paid diagnostic before a full website
rebuild. The useful sales motion is "we will show you what is blocking calls or
bookings before we rebuild," not "we ran an AI focus group."

**Gaps:** test mode proven, live mode validated cheaply but not yet at volume; a known
idempotency-key issue on re-issuing a checkout; tax handling deferred; poller not yet
scheduled. (Confirm current state against `first-sale-setup-state.md` before go-live.)

## Stages 7–8 — Onboard & Launch (Phases 3–5)

Promote the won prospect to a client and stand up the real (Astro) site, then run the
launch checklist. Promote → intake → scaffold → build → launch. Code:
`promotion.py`, [client_lifecycle.py](../../packages/agency/client_lifecycle.py),
`launch.py`; CLI: `scripts/promote_prospect.py`, `scripts/agency/client_intake.py`,
`launch_client.py`. Custom domain: [domain-dns-runbook.md](domain-dns-runbook.md).
**Canonical detail:** [client-lifecycle.md](client-lifecycle.md).

**Gaps:** DNS steps are manual per registrar; demo→client portfolio anonymization is
semi-manual.

## Stage 9 — Recurring ops + billing

The monthly retainer: local SEO, GBP management, booking setup, monthly reports, and
ad drafts — gated on `assert_billing_active()`. Subscription lifecycle (active /
past_due / refunded / disputed / cancelled) is reconciled from Stripe webhooks into
the billing ledger; retainer work halts on refund/dispute. Code:
`local_seo.py`, `gbp.py`, `booking.py`, `monthly_report.py`, `google_ads.py`,
`meta_ads.py`, `follow_up.py`, `retainer_executor.py`; gates in
`packages/policies/agency_gates.py`. Booking recipes:
[runbooks/](runbooks/). SLA: [client-sla.md](client-sla.md).

[Conversion Lab](conversion-lab.md) is the recommended preflight for Package C
promo pages and ad copy. It should produce objections, trust gaps, rewrites, and
a ranked angle before the operator approves ad spend.

**Gaps (the least-finished stage):** retainer ops are partially built; **ads are
draft-only** (no real spend path); **review SMS / follow-up is templates-only** (no
send path; TCPA/CAN-SPAM gates unbuilt); no call-forwarding/tracking for the owner's
number; no automated reply/CRM sync.

---

## Biggest gaps across the funnel (for strategic review)

1. **Contact + verification are browse-only** — no cheap automated pre-filter or
   API fallback, so coverage is bounded by human/agent browsing time.
2. **Outreach is draft-only with no reply loop** — by design no auto-send, but also
   no CRM/reply tracking, so follow-up is fully manual.
3. **Recurring ops is the thin end** — ads, review SMS, follow-up automation, and
   call tracking are stubbed or templates-only; this is where monthly value (and
   retention) is supposed to come from.
4. **Everything assumes the small-business / low-ticket segment** — the pricing,
   the one-page demo, and the cohorts are all tuned for local SMBs. Nothing in the
   architecture *requires* that; higher-ticket segments are an open question.
5. **Demo build is a manual bottleneck** — bespoke is the moat, but it caps
   throughput; the relationship between verified-target volume and build capacity is
   unmanaged.

These are the seams a strategic (v1 → v2) audit should pressure-test.
