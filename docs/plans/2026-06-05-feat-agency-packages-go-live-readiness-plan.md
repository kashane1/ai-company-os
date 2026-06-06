---
title: Agency Packages Go-Live Readiness — A/B/C sell-and-deliver runbooks + gap closure
type: feat
date: 2026-06-05
status: draft
owner: kashane
related:
  - docs/agency/go-live-checklist.md
  - docs/agency/client-lifecycle.md
  - docs/agency/service-catalog.md
  - docs/plans/2026-06-04-feat-agency-transaction-loop-package-c-fulfillment-plan.md
  - docs/plans/2026-06-03-feat-agency-retainer-ops-phases-6-8-plan.md
  - docs/plans/2026-06-01-feat-local-smb-agency-layer-plan.md
---

# 🚀 Agency Packages Go-Live Readiness (A / B / C)

> **One-line answer to "an email comes in today to buy Package A — how fast can we execute?"**
> The *code* to do it is complete, on `main`, and tested. The *one-time* setup tax is wiring
> Stripe live (~1–2 hrs). After that: **payment collected in minutes, live site within ~48h.**
> GBP verification and Workspace email can trail by up to ~1–2 weeks because Google controls
> those clocks — so that belongs in the offer, not the promise. Below is exactly what to do,
> and the handful of gaps to close so every sale runs clean.

## Enhancement Summary

**Deepened:** 2026-06-05 · 5 external best-practice research passes (Stripe go-live, A2P 10DLC/TCPA,
GBP/Workspace/DNS SLAs, Resend deliverability, productized-service ops) + 2 internal learnings folded
in. Full detail + citations in [Research Insights](#research-insights-deepened-2026-06-05) below.

**Key findings that changed the plan:**
1. **Stripe smoke test was wrong — a refund does NOT cancel the subscription.** Must *refund AND
   cancel* on the live test, or the test card rebills next month. (→ G1, Phase 1)
2. **Review SMS is legally *marketing*, not transactional** → requires *prior express written
   consent* per recipient (not a client attestation that "they were customers"), and the
   **2026-06-30 A2P Privacy/Terms-URL deadline is confirmed** with a ~2–4 week campaign-approval lead
   time. Our consent addendum's "client's local time zone" for quiet hours is **wrong — it must be
   the recipient's timezone (9am–8pm)**. (→ G11)
3. **GBP verification is realistically 5–14 *business* days** (video verification is now standard),
   not part of the 48h promise — confirming the need for a two-bucket SLA. Agency should be GBP
   **Manager**, client the **Primary Owner**. (→ G4)
4. **Email: never send production mail from `@resend.dev`**; use an authenticated `send.` subdomain.
   Gmail enforcement went pass/fail in Nov 2025. (→ G2)
5. **Intake must collect access credentials (domain/DNS, GBP-manager, hosting) + a single named
   approver up front** — the #1 lever against onboarding back-and-forth; and **set up client-owned
   domain/email/billing from day one** for clean offboarding. (→ runbook step 0, G8)
6. **Institutional footgun:** any code change here (e.g. a new registry field, a new policy gate) must
   follow this repo's strict patterns — the product registry is a strict typed loader, an approval
   gate is a *function* not an enum member, and `.claude/skills/` pointers are operator-owned. (→ new
   Implementation Notes)

## Overview

The Better Business Web (BBW) landing page sells three bundles defined in
[`packages/agency/catalog.yaml`](../../packages/agency/catalog.yaml) (single source of truth;
human render in [service-catalog.md](../agency/service-catalog.md)):

| Pkg | Name | Setup | Monthly | Services |
|----|------|------:|--------:|----------|
| **A** | Presence | $699 | $49 | website, hosting, gbp, business_email |
| **B** | Presence + Capture | $999 | $99 | A + reviews, booking |
| **C** | Presence + Capture + Growth | $1,399 | $624 | B + local_seo, promo_landing_page, monthly_reporting, google_ads |

Pricing is internally consistent — the per-service setup/monthly fees in the catalog sum exactly
to each bundle's headline price, and the landing page renders from the same data via
`packages.json`.

**This plan is an operational-readiness audit + go-live plan, not a feature build.** The
engineering is largely done (Phases 1–8 of the agency layer shipped). The deliverable here is:
(1) a verdict on whether each package can serve a real paying customer today, (2) the clean
end-to-end **sell-and-deliver runbook** the user asked for, and (3) a prioritized **gap register**
with the minimum work to make every sale repeatable.

## Problem Statement

"Ready to serve customers" is not the same as "code complete." A business is ready when a stranger
can pay us and receive what they bought, predictably, without a scramble. Today the gap between
those two states is:

- **Money:** there is no configured way to *take a card*. Stripe live mode is built and gated but
  unconfigured (no live price IDs, no live keys, no webhook, approval not granted). See
  [go-live-checklist §2](../agency/go-live-checklist.md).
- **Awareness:** the BBW form persists every lead durably to a Netlify Blob, but operator email
  notification (Resend) is **not confirmed live** — `RESEND_API_KEY` exists in the local `.env`
  but the function reads Netlify env, which may be unset. Leads could be sitting unseen.
- **Runbooks with external clocks:** GBP verification, Google Workspace email, and domain/DNS are
  steps we *facilitate* but don't *control*. There's no client-facing SLA that sets those
  expectations, and no domain/DNS acquisition runbook.
- **Fidelity:** the preview a prospect approves is the **bespoke demo** (`dist-v2/`, build path B);
  the paid site is a fresh **Astro scaffold** (`products/<slug>-site/`, build path C). "Previewed
  before you pay" implies the preview *is* the site — we need to guarantee the paid build
  reproduces the approved design.
- **One legal blocker:** live review-request **SMS** is correctly gated off (A2P 10DLC / TCPA).
  Package B/C must scope the "reviews" service to its non-SMS parts until that lands.

None of these are code rewrites. Most are configuration, a few short runbooks, one rehearsal, and
one compliance track.

## Current-State Readiness Matrix

Legend: ✅ ready · ⚙️ needs one-time operator config · 📄 needs a runbook/SLA doc · ⛔ blocked.

### Per-service delivery readiness

| Service | Code / delivery command | State | Note |
|---|---|---|---|
| website | `packages/web/scaffold.py` → `npm run build` (via `launch_client.py`) | ✅ | Path-C Astro build |
| hosting | `packages/web/deploy.py` (gated `webdeploy`) | ⚙️ | Needs per-client Netlify site + `NETLIFY_AUTH_TOKEN` (present in `.env`) |
| gbp | `scripts/agency/draft_gbp_changeset.py` → `GBP_CHANGESET.md` | ✅ code / 📄 SLA | Operator applies by hand; **Google verification 0–14 days** |
| business_email | `scripts/agency/setup_business_email.py` → `BUSINESS_EMAIL.md` | ✅ code / 📄 SLA | Needs client domain + Workspace; depends on DNS |
| booking | `scripts/agency/inject_booking.py` (idempotent) | ✅ | Needs client's booking-provider account |
| reviews | templates + cadence; SMS gated by `assert_review_sms_allowed` | ⛔ SMS / ✅ rest | Sell non-SMS parts now; SMS post-A2P |
| local_seo | `scripts/agency/run_local_seo.py` | ✅ | Service×geo page matrix |
| promo_landing_page | `scripts/agency/build_promo_page.py` | ✅ | |
| monthly_reporting | `scripts/agency/run_monthly_report.py` + `plausible.py` | ⚙️ | Needs `PLAUSIBLE_API_KEY` + per-site `Form Lead` goal |
| google_ads | `scripts/agency/draft_google_ads.py` → `ADS.md` | ✅ draft / 📄 manual | Go-live gated on budget cap + `ad_campaign_go_live` approval; **push-to-API is manual** |

### Per-package verdict

| Package | Verdict | What stands between us and a clean sale |
|---|---|---|
| **A — Presence** | **Closest to ready.** Sellable this week. | Stripe live (P0) · confirm lead-notify (P1) · domain/DNS runbook (P1) · GBP/email SLA (P1) · preview→paid fidelity (P1) |
| **B — Presence + Capture** | Ready right behind A. | Everything in A · confirm a default booking provider · **scope "reviews" to non-SMS** in the OFFER |
| **C — Presence + Capture + Growth** | Sellable, most caveats. | Everything in B · wire Plausible reporting (⚙️) · state ads is **managed manually** · set monthly-retainer expectations · SMS still deferred |

### Transaction-loop gates (verified on `main`, clean tree)

All modules and scripts below exist and are committed; 25 `tests/python/unit/test_agency_*.py`
files cover them. The go-live checklist asserts the suite is green.

- **Lead capture (G2):** `netlify/functions/website-review.mjs` (persist-first to Blob, best-effort
  Resend email, honeypot, HTML-escaped) → `scripts/web/pull-inbound.mjs` →
  `scripts/agency/process_inbound_review.py`. ✅ code · ⚙️ Resend env.
- **Promote → intake → launch:** `scripts/promote_prospect.py`, `client_intake.py`,
  `launch_client.py` over `packages/agency/{promotion,client_lifecycle,launch}.py`. ✅
- **Payments (G1):** `create_checkout.py` + `payments.py` + `stripe_receiver.py` +
  `apps/api` `/stripe/forward` + `billing.py` reconciliation (disputes/refunds/ordering/idempotent
  acceptance stamp). ✅ code · ⛔ live config.
- **Reporting (G10):** `run_monthly_report.py` + `plausible.py`. ✅ code · ⚙️ Plausible config.
- **Approvals/gates:** `packages/agency/approvals.py` + `packages/policies/agency_gates.py`
  (`assert_billing_active`, `assert_ad_campaign_go_live` [requires daily+monthly cap],
  `assert_review_sms_allowed`, live-Stripe approval). ✅

## The Sell-and-Deliver Runbook (the centerpiece)

This is the canonical "lead → cash → live" flow. Commands are the real entrypoints; bracketed
values are per-client. **Bold = blocked or needs config today.**

```mermaid
flowchart TD
  L[Inbound: form or direct email\n"I want Package A"] --> Q{Already a verified\nprospect with place_id?}
  Q -- yes --> P[promote_prospect.py promote\n--bundle package_a]
  Q -- no --> G[gather_place.py + verify\n→ warehouse record] --> P
  P --> O[OFFER.md generated\nin docs/products/<slug>-site/]
  O --> C[**create_checkout.py** → Stripe link\nNEEDS STRIPE LIVE CONFIG]
  C --> PAY[Client pays]
  PAY --> R[Stripe webhook → forwarder → receiver\n→ billing.py reconcile → accepted_at stamp\nledger: active]
  R --> I[client_intake.py --from-prospect\n→ CLIENT_BRIEF + Astro scaffold]
  I --> B[npm run build → dist/]
  B --> LA[launch_client.py check → mark-live\n+ webdeploy gated → production URL + DNS]
  LA --> DEL[Deliver rest of bundle:\nGBP changeset · business email · hosting]
  DEL --> RET[Retainer ops begin\nassert_billing_active guards everything]
```

### Step-by-step (Package A, the warm "ready to buy" inbound)

| # | Step | Command / action | Who | Time | Blocker today |
|---|------|------------------|-----|------|---------------|
| 0 | Capture & qualify | Form path: `pull-inbound.mjs` → `process_inbound_review.py --id <id>`. Direct-email path: `gather_place.py` + verify real business / no good site → set `human_verified`. | Operator | 10–30 min | Cold-inbound path (P2) |
| 1 | Promote to client | `promote_prospect.py promote --place-id <id> --bundle package_a --approved-by kashane` → registry record + `docs/products/<slug>-site/OFFER.md` | Operator | 2 min | — |
| 2 | Send offer + pay link | `create_checkout.py --product-id <id> --bundle package_a` → Stripe URL → paste into OFFER / reply | Operator | 2 min | **Stripe live (P0)** |
| 3 | Client pays | Client opens link, pays setup + first month | Client | minutes | depends on #2 |
| 4 | Auto-reconcile | webhook → forwarder → receiver → `billing.py` flips ledger `active`, stamps `accepted_at/by` | System | seconds | **needs forwarder tunnel + webhook (P0)** |
| 5 | Intake + build | `client_intake.py --product-id <id> --from-prospect <place_id>`; `cd products/<slug>-site && npm install && npm run build` | Operator/Codex | 2–4 hrs | Preview→paid fidelity (P1) |
| 6 | Launch | inject GBP link + analytics tag; `launch_client.py check … --deploy-approved --dns-approved`; `mark-live`; `webdeploy` | Operator | ~1 hr | Domain/DNS runbook (P1) |
| 7 | GBP | `draft_gbp_changeset.py …` → apply `GBP_CHANGESET.md` by hand in Google | Operator | 1 hr work + **0–14d Google verify** | SLA expectation (P1) |
| 8 | Business email | `setup_business_email.py …` → follow `BUSINESS_EMAIL.md` (Workspace + domain MX) | Operator | 1–2 hrs + DNS propagation | Domain dependency (P1) |
| 9 | Hosting live | client Netlify site + monitoring; recurring `$49/mo` now billing | Operator | 30 min | — |

**Honest timeline once Stripe is wired:** payment in **minutes**; live, hosted website within
**~48 hours** (matches the landing-page promise); GBP fully verified + Workspace email fully
propagated can trail **up to ~1–2 weeks** on Google/registrar clocks we don't control. The
one-time Stripe setup (#2/#4) costs ~1–2 hrs *on the first sale only* — every sale after is
minutes-to-cash.

### Package-B delta

Add after #6, before retainer:
- **Booking:** `inject_booking.py --site-file … --provider <calendly|square|…> --booking-url … --product-id <id>` (idempotent). Needs the client's provider account; pick a **default provider** to reduce decisions.
- **Reviews (scoped):** deliver Google review link + request template + cadence. **Do not promise SMS.** The OFFER must say SMS review-requests activate later (post-compliance).

### Package-C delta

Add:
- **Local SEO:** `run_local_seo.py --product-id <id>` → service×geo pages + sitemap.
- **Promo page:** `build_promo_page.py --business … --headline … --out …`.
- **Reporting:** add Plausible script + `Form Lead` goal to the client site; `run_monthly_report.py --product-id <id> --month YYYY-MM --site-id <site>`. **Needs `PLAUSIBLE_API_KEY` (⚙️).**
- **Google Ads:** `draft_google_ads.py … --daily-budget N --monthly-budget M`; operator reviews caps, grants `ad_campaign_go_live`, then **creates the campaign by hand from `ADS.md`** (no auto-push). Spend stays in the client's account.

## Flow & Edge-Case Analysis

Beyond the happy path, these branches will occur and need a defined answer (folded into the gap
register below where action is needed):

1. **Cold inbound that isn't a prospect.** `promote_prospect.py` requires a `human_verified`
   warehouse record with a `place_id`. A pure walk-in buyer has neither. Need a short "create
   client from a fresh inbound" path (run `gather_place.py` for their business, verify, promote).
   → **Gap G6.**
2. **Wants to pay but not by card / wants an invoice.** Until Stripe live exists, the only way to
   take money is a hand-made Stripe invoice or off-platform (Zelle/ACH) — which **won't trip the
   reconciliation webhook**, so `assert_billing_active` stays false and blocks retainer work. Need
   a documented **manual-activation fallback** for the very first sale. → **Gap G1 (fallback).**
3. **Wants one service, not a bundle.** Landing page says "individual services available — just
   ask." The checkout + catalog are bundle-oriented. Confirm `create_checkout.py` can price a
   single `service_id` (or document that à-la-carte is a manual invoice). → **Gap G7.**
4. **Refund / dispute after paying.** Handled in code: `charge.refunded`/`dispute.created` flip the
   ledger and `assert_billing_active` halts retainer work. Operator-facing: add a one-paragraph
   "what to do on a dispute" note. → covered by monitoring; low effort.
5. **GBP / email external latency.** The 48h promise is about the *website*. GBP verification and
   Workspace can take days. Without a client-facing SLA, this reads as us being slow. → **Gap G4.**
6. **Preview→paid fidelity.** Approved preview (`dist-v2`, path B) ≠ paid build (Astro, path C).
   Risk: delivered site doesn't match what they fell in love with. → **Gap G5.**
7. **Change requests during build / post-launch.** Catalog says website includes "copy edits during
   build"; hosting includes "2 content updates/month." Make sure the OFFER states the edit limits so
   scope creep has a boundary. → low effort, copy into OFFER template.
8. **Cancellation / churn.** Subscription cancel → `customer.subscription.deleted` → ledger inactive
   → retainer halts. Define the off-boarding step (site handover, since site is `client-owned`). →
   low effort, add to lifecycle doc.

## Gap Register (prioritized)

> Each gap: impact · minimal fix · type · rough effort. Type = ⚙️config · 📄runbook · 🧪rehearsal ·
> 💻code · ⚖️legal.

### P0 — blocks taking money at all

- **G1. Stripe live not configured.** *Impact:* can't cleanly charge anyone. *Fix:* follow
  [go-live-checklist §2](../agency/go-live-checklist.md) — create test-mode prices for
  `package_a/b/c` (setup + monthly), dry-run with `4242…`, then recreate live, set
  `STRIPE_SECRET_KEY`/`STRIPE_WEBHOOK_SECRET`/`STRIPE_PRICE_MAP`, stand up the `/stripe/forward`
  receiver behind a tunnel, grant `stripe_live_subscription`, live smoke (charge own card → refund).
  *Also write* a **manual-activation fallback** for sale #1 (hand-invoice + a documented way to mark
  the ledger active so retainer guards pass). *Type:* ⚙️ + 📄. *Effort:* 1–2 hrs config + 30 min doc.

### P1 — needed before we *promise* an SLA to a real customer

- **G2. Lead notification not confirmed live.** *Impact:* leads sit unseen in the Blob store.
  *Fix:* verify the Resend sending domain (SPF/DKIM/DMARC), set `RESEND_API_KEY` + `LEAD_NOTIFY_EMAIL`
  + `LEAD_FROM_EMAIL` in **Netlify env**, deploy BBW, submit a real test lead, confirm the email
  arrives and `pull-inbound.mjs` ingests it. *Type:* ⚙️ + 🧪. *Effort:* 30–45 min.
- **G3. Confirm BBW is actually deployed with the live form.** *Impact:* the whole funnel assumes a
  public site. *Fix:* confirm production URL, form posts to the function, `/thanks/` renders. *Type:*
  🧪. *Effort:* 15 min.
- **G4. No client-facing SLA / expectations doc.** *Impact:* GBP/email/ads external clocks read as us
  being slow; scope creep on edits. *Fix:* write `docs/agency/client-sla.md` — per-service turnaround,
  what's external (Google verify, DNS, Workspace), edit limits — and reference it from the OFFER
  template. *Type:* 📄. *Effort:* 1 hr.
- **G5. Preview→paid fidelity.** *Impact:* delivered site may not match the approved preview.
  *Fix:* decide the bridge — either (a) port the approved `dist-v2` design tokens into the Astro
  scaffold, or (b) make the preview itself the Astro build for serious prospects. Document the chosen
  rule in `client-lifecycle.md`. *Type:* 📄 (+ maybe small 💻). *Effort:* 1–2 hrs to decide + doc.
- **G8. Domain & DNS acquisition runbook.** *Impact:* Package A needs the client's domain for site +
  email; no documented path. *Fix:* `docs/agency/domain-dns-runbook.md` — register/transfer, who owns
  it (client-owned), DNS records for Netlify + Workspace MX, propagation expectations. *Type:* 📄.
  *Effort:* 1 hr.

### P2 — robustness / polish

- **G6. Cold-inbound → client path.** Short runbook for promoting a non-prospect walk-in. 📄. 30 min.
- **G7. À-la-carte single-service sale.** Confirm/extend `create_checkout.py` for one `service_id`,
  or document manual invoice. ⚙️/💻. 1 hr.
- **G9. Verify secret-leak guard wired into deploy.** Confirm `assert_no_secret_leak` runs in the
  `webdeploy` path so no key ships in `dist/`. 🧪/💻. 30 min.
- **G10. Verify `packages.json` ↔ `catalog.yaml` price parity guard.** Make sure landing-page prices
  can't silently drift from the SoT (there's a render-parity test; confirm it covers the BBW JSON).
  🧪. 20 min.

### Deferred — tracked, not blocking first sales

- **G11. Review-SMS A2P 10DLC / TCPA.** ⚖️ + 💻. Register A2P brand+campaign, **live Privacy Policy +
  Terms URLs (binding 2026-06-30)**, per-recipient opt-in + STOP suppression + quiet-hours, then ship
  the Twilio sender behind `assert_review_sms_allowed`. Until then, sell "reviews" without SMS.
- **G12. End-to-end live rehearsal ("dress rehearsal").** 🧪. Run the full lead→cash→live→retainer
  loop once on a friendly/test business before the first paying stranger. Belongs in Phase 1 below.

## Phased Path to "Open for Business"

### Phase 0 — Make Package A sellable (this week)
- [ ] G1 Stripe live config — *runbook drafted ✅ ([first-sale-runbook.md](../agency/first-sale-runbook.md), incl. Payment-Link fallback); the dashboard/env config is operator-only and still pending.*
- [ ] G2 Resend domain verify + Netlify env + test lead *(operator)*
- [ ] G3 Confirm BBW production deploy + live form *(operator)*
- [x] G4 [`docs/agency/client-sla.md`](../agency/client-sla.md) — two-bucket SLA ✅
- [x] G8 [`docs/agency/domain-dns-runbook.md`](../agency/domain-dns-runbook.md) — Netlify records, MX coexistence, 60-day lock, ownership ✅
- [ ] G5 Decide + document preview→paid fidelity rule *(needs operator decision)*
- [x] Intake access-block + named approver added to the [client-intake skill](../../skills/canonical/client-intake/skill.md) ✅
- [x] G11 doc fix: [SMS consent addendum](../agency/compliance/review-sms-consent-addendum.md) quiet-hours → recipient TZ + written-consent standard ✅ *(SMS itself stays gated)*
- **Exit:** a stranger can pay for Package A and we can deliver a live site within the stated SLA.

### Phase 1 — Dress rehearsal (immediately after Phase 0)
- [ ] G12 Run the entire loop on a test/friendly client in **live** mode (small real charge → refund **AND cancel the subscription** — a refund alone leaves a live recurring sub)
- [ ] G9 Confirm secret-leak guard fires on deploy
- [ ] G10 Confirm landing-price parity guard
- **Exit:** the runbook has been executed once, end to end, with real money.

### Phase 2 — Package B ready
- [ ] Pick a default booking provider; dry-run `inject_booking.py`
- [ ] Update OFFER template: "reviews" scoped to non-SMS; edit limits explicit
- **Exit:** Package B sells with an accurate, caveat-clear offer.

### Phase 3 — Package C ready
- [ ] Wire Plausible (`PLAUSIBLE_API_KEY` + per-site `Form Lead` goal); run a real `run_monthly_report.py`.
      **Cloud vs self-host is a one-env-var config choice** — `plausible.py` defaults to
      `https://plausible.io` (Cloud: set the API key only) and honors `PLAUSIBLE_BASE_URL` for a
      self-hosted VPS. **Recommend Cloud** for a solo operator (the ~$20/mo buys zero ops); the
      decision is **non-blocking until the first Package C sale** and reversible with zero code change.
      **⚠️ Verify the Stats API (`/api/v2/query`) is included on the plan/tier you pick** — historically
      gated on Cloud's lower tiers; included on self-hosted CE. That's the real deciding factor.
- [ ] Document ads as **managed (manual push)**; set retainer + reporting cadence expectations
- **Exit:** Package C sells with reporting working and ads expectations set.

### Phase 4 — Compliance unblock (own track; deadline-driven)
- [ ] G11 A2P 10DLC + privacy/terms URLs (**before 2026-06-30**) → ship gated SMS sender
- **Exit:** "reviews" includes live SMS, fully compliant.

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| First live charge mis-reconciles | Med | High | Mandatory test-mode dry run, then live smoke (charge→refund) before any real client (Phase 1) |
| Lead arrives, nobody notified | Med (today) | High | Close G2/G3 first; monitor Blob store for `status:new` > 30 min |
| GBP/email latency disappoints client | High | Med | Client SLA doc (G4); set expectations in the OFFER, not after |
| Delivered site ≠ approved preview | Med | High | Resolve fidelity rule (G5) before first sale |
| Accidental TCPA SMS send | Low (gated) | Severe | Keep `assert_review_sms_allowed` closed; don't sell SMS until G11 |
| Secret leaks into `dist/` | Low | Severe | Verify `assert_no_secret_leak` in deploy (G9) |
| Price drift landing vs catalog | Low | Med | Parity guard (G10); catalog is SoT |

## Acceptance Criteria — "ready to serve customers"

**Package A (ready when all true):**
- [ ] A stranger can complete Stripe checkout for `package_a`; ledger flips `active` and stamps acceptance automatically.
- [ ] A real form lead reaches the operator inbox within seconds and ingests via `pull-inbound.mjs`.
- [ ] We can promote → intake → build → launch a live, hosted site on the client's domain.
- [ ] GBP changeset + business-email runbooks produced, with SLA expectations stated to the client.
- [ ] The full loop has been rehearsed once end-to-end with real money (Phase 1).

**Package B:** all of A · booking injected for a default provider · OFFER scopes reviews to non-SMS.

**Package C:** all of B · Plausible reporting produces a real monthly report · ads delivered via the
gated manual path with budget caps · retainer/reporting cadence documented.

## Research Insights (Deepened 2026-06-05)

Concrete, current (2025–2026) grounding for each gap. Each block maps to a gap ID above. Sources are
cited; treat compliance items as operational guidance, not legal advice.

### → G1 · Stripe go-live (the code is right; these are the runbook deltas)

External research **confirms our implementation choices** — `invoice.paid`-only activation,
`event.id` dedupe, the numeric out-of-order cursor, and mode-fencing all match Stripe's current
recommendations. Deltas to fold into [go-live-checklist §2](../agency/go-live-checklist.md):

- **Which keys are load-bearing (verified by grep):** the sale flow uses **hosted Stripe Checkout**
  (`create_checkout.py` → `payments.py`), so it needs **`STRIPE_SECRET_KEY` + `STRIPE_WEBHOOK_SECRET`
  + `STRIPE_PRICE_MAP`**. A **publishable key (`pk_…`) is NOT used anywhere** in the codebase (no
  client-side Stripe.js) — adding it is harmless but does **not** unblock G1. Test mode (`4242…`)
  before live.
- **Smoke test correction (important):** a refund does **not** cancel a subscription — it reverses
  one charge. The live smoke test must **refund the charge AND cancel the subscription**, then
  confirm the ledger, or the test card rebills next month.
- **Verify a real *live* `invoice.paid` reaches the receiver** (not just that the card was charged) —
  this catches the #1 go-live mistake: webhook endpoint still on test / wrong `whsec_` secret.
- **`invoice.paid` is Stripe's documented activation signal** — provision when `invoice.paid` arrives
  and subscription `status=active`. Do **not** activate on `customer.subscription.created` (may be
  `incomplete`) or `checkout.session.completed` (confirms session, not payment). Ours is correct.
- **Setup fee + monthly in one Checkout:** keep the **two-`line_items`** approach (recurring monthly
  Price + one-time setup Price) — it's the documented default and gives an itemized first invoice.
- **Stable `lookup_key` per Price** (e.g. `pkg_a_setup`, `pkg_a_monthly`) in both modes so the
  test↔live `price_…` ID divergence stops mattering — resolve by lookup_key, not raw IDs.
- **Tax:** add an explicit checkbox — either enable Stripe Tax (`automatic_tax`, registrations,
  origin address, collect billing address) **or** record "confirmed no nexus obligation for target
  states." Don't omit silently.
- **Customer comms:** enable live email **receipts + invoice emails**; set a clear **statement
  descriptor + business name** (unrecognized charges → disputes). Confirm account is activated for
  live charges **and payouts**.
- **Disputes:** funds + a non-refundable fee are pulled immediately on `charge.dispute.created`; a
  dispute does **not** cancel the sub (our `assert_billing_active` halts retainer work — good).
  Consider also subscribing to `charge.dispute.updated`, and dedupe defensively on
  `(object.id, event.type)`, not `event.id` alone. Respond within the network deadline (7–21 days)
  with proof-of-service (the live site).
- **Fallback for sale #1 (G1 fallback):** a Stripe **Payment Link** (subscription mode, two prices)
  or a hosted **Invoice** closes a deal *today* with zero webhook code — and if pointed at the same
  live endpoint, it still flows `invoice.paid` through our ledger. Use it only as break-glass for the
  first sale; don't run steady-state on it (you'd hand-maintain subscription state).
- **Retry windows (set monitoring expectations):** live webhooks retry up to **3 days** w/ backoff;
  manual resend up to **15 days** (Dashboard) / **30 days** (CLI `stripe events resend`).

*Sources:* [Go-live checklist](https://docs.stripe.com/get-started/checklist/go-live) · [Subscription webhooks](https://docs.stripe.com/billing/subscriptions/webhooks) · [Build subscriptions w/ Checkout](https://docs.stripe.com/payments/checkout/build-subscriptions) · [Disputes](https://docs.stripe.com/disputes/how-disputes-work) · [Payment Links](https://docs.stripe.com/payment-links) · [Collect tax w/ Checkout](https://docs.stripe.com/tax/checkout)

### → G2 · Resend deliverability (lead notification)

- **Use a `send.` subdomain, never the root and never `@resend.dev`** in production. Set
  `LEAD_FROM_EMAIL=…@send.<verified-domain>`. Four records: SPF `TXT` (`v=spf1 include:amazonses.com
  ~all`), bounce `MX` (priority 10), DKIM `TXT` at `resend._domainkey`, DMARC `TXT` at `_dmarc`
  starting `p=none`. Use **relaxed SPF alignment** (don't publish `aspf=s`); strict DKIM is fine.
- **Gmail/Yahoo enforcement is now pass/fail** (Postmaster Tools v2, Nov 2025). Auth (SPF+DKIM+DMARC)
  is table-stakes. One-click-unsubscribe + a DMARC record are *bulk*-only (≥5k/day) — not required
  for our low-volume operator alerts, but **route any future marketing on a separate subdomain**.
- **Preflight:** after the curl 200 check, send a real test to the operator Gmail, confirm **Primary
  inbox** + SPF/DKIM/DMARC **pass & aligned** via "Show original," and run one **mail-tester.com**
  check (target 10/10).
- **Idempotency:** already handled — the function sends `Idempotency-Key: lead-${submission_id}`
  (24h dedupe), so function retries can't double-notify. ✓ no change needed.

*Sources:* [Resend domains](https://resend.com/docs/dashboard/domains/introduction) · [Resend email auth](https://resend.com/blog/email-authentication-a-developers-guide) · [Google sender guidelines](https://support.google.com/a/answer/81126)

### → G4 / G8 · GBP, Workspace, domain/DNS — the external-clock SLA

The two-bucket SLA the plan calls for, with real day ranges:

| Item | Realistic | Worst-case | Controlled by |
|---|---|---|---|
| Static site live (post content sign-off) | ~48h | — | **Agency** |
| DNS config submitted | 1 business day | — | **Agency** |
| Email live | <1 business day | 48–72h | DNS + Google |
| **GBP verification** | **5–14 business days** | ~21 days (re-submit) | **Google** |
| Domain transfer | 5–7 days | +30–60d lock | Registrar/ICANN |

- **GBP:** video verification is now the standard method (5–14 business days). Agency should be
  **Manager**, client the **Primary Owner** (Google's stated third-party policy — clean offboarding,
  and a "give us Primary Owner" demand is a red flag). Exact, NAP-consistent address speeds the queue;
  wait the full 14 days before re-requesting a code.
- **Workspace email:** single modern MX **`smtp.google.com`** (priority 1; the old 5-record `aspmx`
  set is deprecated). Create mailboxes **before** switching MX. Email live <1 business day; full
  reliability 48–72h. Publish DKIM (`google._domainkey`) — it's **off until you do**.
- **Netlify DNS:** apex → **ALIAS/ANAME `apex-loadbalancer.netlify.com`** (or A `75.2.60.5`); `www` →
  CNAME `<site>.netlify.app`.
- **#1 avoidable failure across the whole package:** deleting MX/SPF/DKIM/DMARC while pointing the
  domain at Netlify (or moving nameservers and forgetting to recreate email records). Make **"verify
  email still flows after any DNS change"** an explicit post-cutover step. Website (A/CNAME) and email
  (MX/TXT) are independent record types on the same zone — don't wipe the wrong ones.
- **60-day transfer lock (ICANN):** changing the registrant contact on a freshly registered domain
  **locks it for 60 days**. ICANN is moving to a 30-day lock through 2026 but it's not uniformly live
  — **write the SLA against 60 days.**
- **Ownership model (offboarding-safe, set at kickoff):** client = domain registrant + GBP Primary
  Owner + Workspace billing; agency = delegated/manager access + Netlify-managed-then-transferable.

*Sources:* [GBP verify](https://support.google.com/business/answer/7107242) · [GBP for agencies](https://support.google.com/business/answer/9199701) · [Workspace MX](https://knowledge.workspace.google.com/admin/domains/set-up-mx-records-for-google-workspace) · [Netlify external DNS](https://docs.netlify.com/manage/domains/configure-domains/configure-external-dns/) · [ICANN transfer policy](https://www.icann.org/en/contracted-parties/accredited-registrars/resources/domain-name-transfers/policy)

### → G5 · Preview→paid fidelity (institutional learning)

Per [demo-site-learnings.md](../demo-site-learnings.md): the approved preview is a **bespoke
hand-built `dist-v2/`** (path B), and **"build → preview → deploy is a separate, gated step — never
auto-deploy a bespoke build"**; the full-page screenshot is the last action before deploy. The paid
site is a **path-C Astro scaffold**. The fidelity bridge (G5) must reconcile these two — recommended:
port the approved `dist-v2` design tokens (palette/fonts/section structure) into the Astro scaffold,
or promote serious prospects' previews to the Astro build. Document the rule in `client-lifecycle.md`.

### → runbook step 0 / intake · Collect access + approver up front (productized-ops)

The single biggest lever against onboarding back-and-forth: make build-start **conditional on a 100%
-complete intake** that includes the usually-missed blocks:
- **Access credentials:** domain registrar/DNS access, **GBP added as Manager**, existing
  hosting/CMS/analytics logins.
- **One named approver** (name + email) for the preview-review.
- **Brand kit + 8–15 real photos + 3–5 reviews + exact NAP.**
- **Scope control (prevent creep):** countable deliverables ("single responsive page, 2 revision
  rounds"); "copy edits included during build only; post-launch billed separately"; "2 content
  updates/mo, additional at $X"; a written exclusions list; an acceptance clause ("revisions requested
  within 5 business days of preview"). A solo agency loses real money to unbilled scope creep.
- **Monthly retainer report (C):** lead with an executive summary tied to the client's stated goal,
  and always include a **work-completed log** — for SMB retainers, *visible activity* is what
  justifies the fee while rankings/ads mature.
- **Dress rehearsal (G12):** run the entire loop on a friendly client before charging a stranger;
  time each step and turn every "had to chase the client" into a required intake field.

*Sources:* [AgencyHandy onboarding](https://www.agencyhandy.com/client-onboarding-checklist/) · [DigitalApplied scope-creep SOW](https://www.digitalapplied.com/blog/agency-scope-creep-prevention-2026-sow-framework) · [Rocket.net offboarding](https://rocket.net/blog/agency-guide-to-offboarding-client-websites) · [Arvow client reports](https://arvow.com/blog/seo-reports-for-clients)

### → G11 · Review-SMS compliance (the deferred legal track)

- **A review request is *marketing*, not transactional.** It therefore requires **prior express
  written consent (PEWC)** per recipient from *that specific business* — a client attestation that
  "these are past customers who didn't opt out" is **necessary but not sufficient.** The go-live gate
  must require **documented written opt-in proof** per number; no purchased/scraped lists.
- **2026-06-30 deadline confirmed (Twilio):** `PrivacyPolicyUrl` + `TermsAndConditionsUrl` become
  **required fields** on new A2P campaign registration (hard API rejection without them). Both must be
  live before registering regardless of date. Campaign approval has a **~2–4 week lead time** (Brand →
  Campaign-as-marketing via The Campaign Registry); nothing sends until the campaign is *approved*.
- **Fix our consent addendum:** `docs/agency/compliance/review-sms-consent-addendum.md` says quiet
  hours = "Client's local time zone" — that is **wrong.** Quiet hours are the **recipient's local
  timezone, 9am–8pm** (the FL/TX-safe intersection; off-hours marketing texts are the #1 2025–26
  class-action vector). Also require documented opt-in proof, not just attestation.
- **In force now (since 2025-04-11):** honor STOP/QUIT/END/REVOKE/OPT-OUT/CANCEL/UNSUBSCRIBE +
  free-text equivalents; process revocation within 10 business days (suppress immediately).
- **Penalties: $500–$1,500 per message, no cap** → a single unconsented blast is existential. Keep
  `assert_review_sms_allowed` closed until: per-client A2P brand+campaign approved, live Privacy/Terms
  URLs, a consent store (with proof), a per-recipient STOP suppression list, recipient-timezone
  quiet-hours, and a frequency cap are all wired and unit-tested. **Have a TCPA-literate attorney
  review the consent language and per-client registration model before the first live send.**

*Sources:* [Twilio A2P Privacy/Terms requirement (2026-06-30)](https://www.twilio.com/en-us/changelog/a2p-10dlc-campaign-registration-will-require-privacy-policy-and-) · [Twilio A2P 10DLC](https://www.twilio.com/docs/messaging/compliance/a2p-10dlc) · [FCC consent-revocation rule (Apr 2025)](https://www.fcc.gov/document/tcpa-rules-revoking-consent-unwanted-robocallsrobotexts) · [TCPA quiet-hours litigation](https://www.privacyworld.blog/2025/03/new-class-action-threat-tcpa-quiet-hours-and-marketing-messages/)

## Implementation Notes (repo footguns — read before any code lands)

From [agency-layer-reuse-and-repo-mechanism-footguns.md](../solutions/architecture/agency-layer-reuse-and-repo-mechanism-footguns.md).
Most of this plan is config + runbooks, but any code touched must respect these contracts:

1. **The product registry is a strict typed loader, not a tolerant bag.** Adding a record/field to
   `infra/products.json` is a `packages/schemas/` edit + a `packages/config/products.py` loader branch
   (founder-approved) with defaults so legacy records still load — not a JSON-only change.
2. **An approval gate is a `assert_<action>(*, approval_granted)` function, not an enum member.** New
   `PolicyViolationCode`s need their raise site + a presence assertion in
   `tests/python/unit/test_policy_violation_codes.py`, all landing together.
3. **Skills are fixture-gated** — compose the **pure callables** (`packages.web.ux_audit.audit_dist`,
   etc.), not the `kind: agentic` skill, in autonomous mode.
4. **`.claude/skills/` pointers are operator-owned** (agent-write-blocked). The clean wiring an agent
   can land is canonical + adapter + registry entry with `project_skill` omitted, leaving the pointer
   as a one-line operator follow-up (zero drift).
5. **Keep new code 3.10-importable** in the agent sandbox (`datetime.now(timezone.utc)`, not
   `datetime.UTC`) so its tests run; full suite targets 3.12.

## References

### Internal (verified this session)
- Catalog SoT: [`packages/agency/catalog.yaml`](../../packages/agency/catalog.yaml)
- Landing page: [`products/better-business-web/site/src/components/LandingBody.astro`](../../products/better-business-web/site/src/components/LandingBody.astro), [`.../pages/index.astro`](../../products/better-business-web/site/src/pages/index.astro)
- Lead function: [`.../netlify/functions/website-review.mjs`](../../products/better-business-web/site/netlify/functions/website-review.mjs)
- Operator runbooks: [go-live-checklist.md](../agency/go-live-checklist.md) · [client-lifecycle.md](../agency/client-lifecycle.md) · [agency/README.md](../agency/README.md)
- Loop code: `packages/agency/{payments,billing,stripe_receiver,promotion,client_lifecycle,launch,booking,gbp,business_email,local_seo,google_ads,promo_page,plausible,retainer_ops}.py`; gates in `packages/policies/agency_gates.py`; receiver in `apps/api`
- Scripts: `scripts/promote_prospect.py`, `scripts/agency/{client_intake,launch_client,create_checkout,setup_business_email,draft_gbp_changeset,inject_booking,process_inbound_review,run_monthly_report,draft_google_ads}.py`, `scripts/web/pull-inbound.mjs`
- Tests: 25 × `tests/python/unit/test_agency_*.py`

### Related plans
- [Transaction loop / Package C fulfillment](2026-06-04-feat-agency-transaction-loop-package-c-fulfillment-plan.md)
- [Retainer ops phases 6–8](2026-06-03-feat-agency-retainer-ops-phases-6-8-plan.md)
- [Local SMB agency layer](2026-06-01-feat-local-smb-agency-layer-plan.md)

### New docs this plan proposes
- ✅ [`docs/agency/client-sla.md`](../agency/client-sla.md) (G4) — created
- ✅ [`docs/agency/domain-dns-runbook.md`](../agency/domain-dns-runbook.md) (G8) — created
- ✅ [`docs/agency/first-sale-runbook.md`](../agency/first-sale-runbook.md) (G1) — created (Stripe go-live sequence + Payment-Link fallback)

---

*Flow/edge-case analysis performed inline (cold inbound, invoice/à-la-carte, refund/dispute,
external-clock SLAs, preview→paid fidelity, change requests, churn). No code was written for this
plan — research and planning only.*
