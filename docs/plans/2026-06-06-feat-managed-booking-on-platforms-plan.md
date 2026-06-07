---
title: Reframe booking_native → Managed Booking on proven platforms (Calendly / Square / Acuity)
type: feat
date: 2026-06-06
status: draft
owner: kashane
decision: "Reframe to Managed Booking (chosen over custom-build and retire-entirely)"
related:
  - docs/plans/2026-06-05-feat-agency-packages-go-live-readiness-plan.md
  - docs/agency/service-catalog.md
  - docs/agency/client-sla.md
  - packages/agency/catalog.yaml
---

# 📅 Reframe `booking_native` → Managed Booking on proven platforms

> **Decision (locked):** Do **not** build custom booking software. Reframe the
> recurring `booking_native` product from "booking built into your site, no
> third-party subscription" (vaporware — flagged highest-risk in the go-live
> readiness audit) into **"Fully Managed" booking that we set up and run for the
> client on a proven platform** (Square Appointments / Acuity / Calendly). We sell
> setup + management; the platform handles the hard parts (timezones, double-booking,
> reminders, deposits, reschedules, no-shows, PII). This matches the ChatGPT
> recommendation and the agency's "sell setup, not SaaS" thesis.

## Overview

Better Business Web's booking offer is a **pick-one base + stackable modifiers**
family in `packages/agency/catalog.yaml` (lines 75–166), enforced by an
`exclusive_group: booking_base` / `requires_group: booking_base` model:

- **`booking_connect`** ($150) — Connect: embed the client's *existing* tool.
- **`booking_setup`** ($350) — Done-for-you: pick + configure a platform from scratch.
- **`booking_native`** ($450 + $35/mo) — **the problem child.** Sold as a recurring,
  "built into your site, no third-party subscription, I manage your calendar"
  product. **No such software exists** — it maps to the same generic embed stub as
  the others. Selling a recurring product we can't deliver is a refund/chargeback risk.
- Modifiers: `booking_deposits` ($120), `booking_multistaff` ($150), `booking_classes`
  ($200), `booking_intake` ($90), `booking_management` ($35/mo).

This plan **reframes `booking_native` into "Booking — Fully Managed"**: we set it up
*and* run it for the client on a proven platform, the client owns the account, and we
hold delegated admin access. No custom code, no new SKUs, no price change. We then
build the delivery and retainer that's currently missing, and add a **platform-routing
layer** so the three paths are explicit.

### The three paths (ChatGPT's model, mapped to our existing bases)

These are **platform recommendations**, not new catalog line items — the routing lives
in operator runbooks + builder copy, decided at intake based on the client's needs:

| Path | Platform | When | Maps to base |
|---|---|---|---|
| **Connect** | the client's existing tool | they already book somewhere | `booking_connect` |
| **Simple** | **Calendly** | appointments, discovery calls, estimates, consults | `booking_setup` or `booking_native` |
| **Local-service** | **Square Appointments** or **Acuity** | needs payments, deposits, staff, classes, forms, reminders | `booking_setup` or `booking_native` |

## Problem Statement

Three forces point the same way:

1. **ChatGPT's advice (the user's context):** custom booking gets messy fast —
   timezones, double-booking, refunds, reminders, cancellation windows, staff
   permissions, payment disputes, reschedules, recurring appointments, SMS costs,
   customer data. Let proven platforms handle that; sell the setup + integration.
2. **The go-live readiness audit:** flagged `booking_native` as vaporware / highest
   risk — a recurring product on sale with zero delivery path.
3. **The agency's own thesis** (`docs/solutions/architecture/agency-layer-reuse-and-repo-mechanism-footguns.md`):
   "reuse over rebuild / sell setup not SaaS — the high-leverage work is a thin
   connective seam." We already have a multi-provider embed injector
   (`packages/agency/booking.py` supports calendly/square/acuity/booksy/fresha/vagaro/mindbody).

Building a booking engine would also re-import the **A2P 10DLC / TCPA** burden we
already gated off for review-SMS (our own reminder texts would need brand+campaign
registration). Platforms send reminders on **their own** registration — a compliance
win we'd throw away by building.

## Proposed Solution

**Reframe, don't build.** Keep the catalog structure and prices; change copy to be
honest; build the delivery + retainer + platform routing.

1. **`booking_native` → "Booking — Fully Managed."** Same `service_id` (no id churn;
   it's not referenced by any bundle — Packages B/C use `booking_setup`), same price
   ($450 + $35/mo). New copy: *"We set up and run your booking on a proven platform
   (Square or Acuity) under your account — you never touch it. Ongoing management
   included. You keep + pay your platform; we do the work."* Drop "built into your
   site / no third-party subscription."
2. **Platform routing layer** — a capability/pricing/routing matrix (below) in an
   operator runbook + light builder copy, so Connect/Simple/Local-service is explicit.
3. **Per-platform done-for-you setup runbooks** (Calendly / Square / Acuity), written
   as **one batch** (shared scaffold), each with the agency-delegated-access model and
   client-owns-account ownership.
4. **Managed-booking retainer SLA** — bound the $35/mo to ~2 change requests/mo +
   monthly no-show glance; client pays the platform fee separately.
5. **Small code touch-ups** — make the embed injector platform-correct, wire
   `retainer_ops` to plan monthly booking work, and make the `BOOKING.md` scaffold +
   `BookingSetup` record platform-aware.
6. **Compliance guardrail** — use platform-native reminders only; never wire our own
   Twilio for client reminders (keeps A2P/TCPA on the platform, not us).

### Platform capability + routing matrix (research-grounded, 2026)

| Need (modifier) | Calendly | Square Appointments | Acuity | Default advice |
|---|---|---|---|---|
| `booking_deposits` | full-pay only | full-prepay / card-hold (no partial) | **true % deposit** | **Acuity** for partial deposits |
| `booking_multistaff` | weak | **unlimited staff (Free)** | up to 6 (Standard) | Square for many staff |
| `booking_classes` | ✗ | ✓ (Plus) | ✓ (Standard) | Acuity/Square |
| `booking_intake` | basic | ✓ | **rich forms** | Acuity |
| SMS reminders | 250/seat/mo cap | **Premium only ($149)** | **Standard, no extra fee** | **Acuity Standard** |
| Free tier | ✓ | ✓ (pay processing) | trial only | — |
| Paid entry | Std $12 | Plus $49 | Standard $27–34 | — |

**Routing rule for the runbook:** deposits + classes + SMS + intake on one cheap plan →
**Acuity Standard (~$27–34/mo)**. POS/payments unification + no-show card holds, already
on Square → **Square Plus ($49)** (Premium $149 only if SMS is required — usually steer
to Acuity instead). Just "let people book a call" → **Calendly Free/Standard**. The
client pays the platform; our fee is labor only.

### Compliance: SMS reminders are the platform's job (a win)

All three send appointment reminders from **their own** numbers under **their own** A2P
registration (Square system number; Acuity's Twilio integration; Calendly's pooled
numbers), with STOP/HELP handled by the platform. Appointment reminders are
**transactional** (customer-initiated booking), not marketing. So:
- The agency does **not** register A2P 10DLC for platform-sent reminders.
- **Guardrail:** never wire a separate Twilio/Zapier SMS path for a client (that
  re-imposes A2P/TCPA on us); keep reminder text strictly transactional (no offers).

This is the opposite of our review-SMS lane (where *we* are the sender and must register).

## Technical Approach

### Touch-points (from the repo map)

| Area | File | Change |
|---|---|---|
| Catalog (SoT) | `packages/agency/catalog.yaml` (booking_native lines ~102–114; clarify connect/setup copy) | Copy-only reframe; **prices unchanged** |
| Mirror (frontend) | `products/.../src/data/packages.json` | **Regenerate** via `scripts/agency/render_catalog_json.py` (never hand-edit) |
| Mirror (docs) | `docs/agency/service-catalog.md` | **Regenerate** via `scripts/agency/render_catalog_md.py` |
| Embed injector | `packages/agency/booking.py` | Calendly add `data-resize="true"`; Acuity → `<iframe>` + `embed.js` (auto-resize); add optional `square_widget` provider (operator-pasted snippet, since Square's real embed isn't URL-derivable) |
| Retainer loop | `packages/agency/retainer_ops.py` (lines ~28–52) | **Add** booking actions: `booking_native`/`booking_management` → monthly "process ≤2 change requests + no-show glance + link/calendar-sync check" |
| Client scaffold | `packages/agency/templates.py` (BOOKING.md stub ~263–267) | Platform-aware stub (chosen platform, access model, setup checklist link) |
| Setup record | `packages/agency/booking.py` `BookingSetup` | Capture `platform`, `managed: bool`, delegated-access note |
| Builder copy | `BundleBuilder.tsx` / `build.astro` | Light copy only ("Fully Managed — we run it for you"); **no group-logic change** (still `booking_base`) |

### Guardrails (from institutional learnings — do not violate)

- **Catalog is the only source of truth.** Edit `catalog.yaml`, then run **both**
  render scripts; `test_agency_catalog_json.py` + `test_agency_service_catalog_render.py`
  enforce byte-equality. Hand-editing `packages.json` will fail CI.
- **No founder-gated schema change required.** This reframe is copy + delivery; platform
  is captured at delivery time in `BookingSetup`, **not** a new catalog field. (Adding a
  catalog field would touch the founder-gated `packages/schemas/offer.py` + the strict
  typed loader — avoid it.)
- **Prices unchanged → no pricing churn.** Keep `booking_native` at $450 + $35/mo so
  `setup_promo` for Package B (uses `booking_setup`, not native) and the cross-language
  pricing test (`test_agency_pricing_cross_language.py`) stay green untouched.
- **No new approval gate needed** — managed booking has no irreversible platform action
  we take (deposits/payments live in the client's own platform account).
- **3.10-importable** — any new timestamp logic uses `datetime.now(timezone.utc)`.
- **Injector is idempotent** — re-running replaces the `<!-- bbw:booking:start/end -->`
  block, so a client switching platforms (Calendly→Square) just re-injects cleanly.
- **Verify owner-managed booking URL**, never an aggregator's unaffiliated listing
  (demo-site-learnings.md) — add to the setup runbook.
- **No partial refactor** — remove all "custom-built / no third-party" copy; don't leave
  it as a fallback.
- **Write the 3 runbooks as one batch**, not parallel agents racing the same files.

### Implementation Phases

#### Phase 1 — Honest catalog reframe (small, ship first)
- Rewrite `booking_native` copy in `catalog.yaml` → "Booking — Fully Managed"; clarify
  `booking_connect` = "Connect (your tool)" and `booking_setup` = "Done-for-you Setup".
- Regenerate `packages.json` + `service-catalog.md`; confirm drift + pricing tests green.
- Light builder/landing copy so the three paths read clearly.
- **Exit:** nothing on sale claims custom-built booking; copy matches what we deliver.

#### Phase 2 — Delivery runbooks + platform routing (the real value)
- `docs/agency/booking-platform-routing.md` — the capability/pricing/routing matrix + the
  "which platform" decision rule + the SMS-compliance guardrail.
- `docs/agency/runbooks/booking-setup-calendly.md`, `-square.md`, `-acuity.md` (one batch,
  shared scaffold): account-under-client's-email, add operator as delegated admin/
  contributor/team-member, services/buffers/availability/staff/intake/deposits/calendar-
  sync/reminders, embed + live test booking + test refund, owner-managed-URL check.
- **Exit:** an operator can fully deliver a managed booking on any of the three platforms
  from a checklist.

#### Phase 3 — Code touch-ups (make delivery real & repeatable)
- `booking.py`: Calendly `data-resize`; Acuity iframe + `embed.js`; optional
  `square_widget` provider; `BookingSetup` gains `platform` + `managed`.
- `retainer_ops.py`: booking_native / booking_management → monthly planned action.
- `templates.py`: platform-aware `BOOKING.md` scaffold.
- Tests: extend `test_agency_booking.py`, `test_agency_retainer_ops.py`.
- **Exit:** the injector matches each platform's real embed; recurring booking work is in
  the monthly loop; the workspace scaffold tells the operator which platform + checklist.

#### Phase 4 — SLA + offer language
- Managed-booking section in `docs/agency/client-sla.md`: $35/mo scope (~2 changes/mo,
  no-show glance), **client pays the platform fee separately**, out-of-scope list ("not a
  receptionist"; refunds/live monitoring excluded), clean offboarding (remove delegated
  access; client keeps the account + data).
- **Exit:** the offer accurately bounds what "managed" means and who pays for what.

## Alternative Approaches Considered

- **Build custom native booking software** — rejected. ChatGPT + the audit + the agency
  thesis all warn against it; it duplicates free, battle-tested platforms, re-imposes
  A2P/TCPA on us, and owns the client's customers' payment data + PII. Largest scope by
  far for a solo+AI shop, for negative differentiation.
- **Retire `booking_native` entirely** — rejected. Gives up a real, sellable recurring
  line (managed booking is a genuine SMB pain reliever) for no benefit once delivery is a
  thin platform seam.

## Flows & Edge Cases (inline spec-flow)

- **Client has no booking platform yet** → operator creates the account **under the
  client's email + card**, adds self as delegated admin (per platform §3 of routing doc).
- **Client switches platform mid-engagement** → idempotent injector re-injects; update
  `BookingSetup.platform`; re-test a live booking.
- **Client wants partial deposits** → route to **Acuity** (Square has no partial deposit);
  encode in the routing rule so we don't upsell Square Premium by accident.
- **Client insists on SMS reminders** → Acuity Standard (cheapest with SMS); avoid Square
  Premium ($149) unless they need POS too; never our own Twilio.
- **Managed retainer cancellation** → remove delegated access; client keeps account +
  history; nothing to migrate (clean offboarding).
- **Aggregator link risk** → verify the booking URL is the owner's direct account, not a
  Fresha/Booksy unaffiliated listing, before embedding.
- **Booking link/calendar sync silently breaks** → the monthly retainer glance includes a
  link + sync sanity check.

## Acceptance Criteria

- [x] No surface (catalog, `packages.json`, landing, builder) claims custom-built / "no
      third-party" booking; `booking_native` reads as "Booking — Fully Managed."
- [x] `render_catalog_json.py` + `render_catalog_md.py` re-run; drift + cross-language
      pricing tests green; **`booking_native` price still $450 + $35/mo**.
- [x] An operator can deliver a managed booking end-to-end on Calendly, Square, **and**
      Acuity from the runbooks (`docs/agency/runbooks/booking-setup-*.md`): account-under-client,
      delegated access, services, availability, deposits where supported, reminders, embed,
      live test booking.
- [x] `booking.py` injects a correct, auto-resizing embed per platform (Calendly `data-resize`,
      Acuity `embed.js`) + a raw-snippet path for Square; `BookingSetup` records the `managed`
      flag (`provider` already captures the platform); `test_agency_booking.py` covers it.
- [x] `retainer_ops` plans a monthly `manage_booking` action for `booking_native` /
      `booking_management`; `test_agency_retainer_ops.py` covers it.
- [x] `client-sla.md` states the $35/mo scope, that the client pays the platform fee, the
      out-of-scope list, and the offboarding step.
- [x] Runbooks + routing doc state: platform-native reminders only (no agency Twilio);
      reminders stay transactional.

## Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Hand-editing `packages.json` → CI fail | Edit catalog only; run render scripts; tests enforce |
| Accidentally upselling Square Premium for SMS | Routing rule defaults SMS→Acuity Standard |
| Client confusion on who pays the platform | SLA + offer state platform fee is the client's |
| Operator wires own Twilio for reminders | Runbook guardrail: platform-native only |
| "Custom-built" copy lingers somewhere | Phase 1 greps every surface; no fallback copy |
| booking_management already $35/mo overlaps native | Native = setup+managed bundled; management = add-on for connect/setup. Keep catalog note consistent |

## Documentation Plan / New docs

- `docs/agency/booking-platform-routing.md` (matrix + decision rule + compliance)
- `docs/agency/runbooks/booking-setup-calendly.md`
- `docs/agency/runbooks/booking-setup-square.md`
- `docs/agency/runbooks/booking-setup-acuity.md`
- Managed-booking section appended to `docs/agency/client-sla.md`

## References

### Internal (cited this session)
- Catalog: `packages/agency/catalog.yaml` (booking family ~75–166)
- Mirror + render: `products/better-business-web/site/src/data/packages.json`; `scripts/agency/render_catalog_json.py`, `render_catalog_md.py`; drift tests `test_agency_catalog_json.py`, `test_agency_service_catalog_render.py`
- Pricing parity: `src/lib/pricing.mjs` ↔ `packages/schemas/offer.py` (founder-gated); `test_agency_pricing_cross_language.py`
- Delivery: `packages/agency/booking.py`, `scripts/agency/inject_booking.py`; scaffold `packages/agency/templates.py` (~237–283); retainer `packages/agency/retainer_ops.py` (~28–52)
- Builder: `products/.../src/components/BundleBuilder.tsx`, `src/pages/build.astro`
- Learnings: `docs/solutions/architecture/agency-layer-reuse-and-repo-mechanism-footguns.md`; `docs/demo-site-learnings.md` (owner-managed URL)
- Readiness audit: `docs/plans/2026-06-05-feat-agency-packages-go-live-readiness-plan.md`

### External (platform docs)
- Calendly: [embed options](https://calendly.com/help/embed-options-overview) · [API/Event-Type CRUD + Scheduling API](https://developer.calendly.com/api-docs) · [payments](https://calendly.com/help/calendly-stripe) · [SMS opt-out](https://help.calendly.com/hc/en-us/articles/1500000442702-How-invitees-can-opt-out-or-back-in-to-texts)
- Square: [Appointments pricing](https://squareup.com/us/en/appointments/pricing) · [Bookings API](https://developer.squareup.com/docs/bookings-api/what-it-is) · [prepayment/deposits](https://squareup.com/help/us/en/article/5676-customer-prepayment-for-square-appointments) · [authorized reps / delegated access](https://squareup.com/help/us/en/article/6316-add-an-administrator-or-authorized-representative)
- Acuity: [embedding](https://help.acuityscheduling.com/hc/en-us/articles/16676884389133) · [API](https://developers.acuityscheduling.com/reference/quick-start) · [deposits / how clients pay](https://help.acuityscheduling.com/hc/en-us/articles/28051014042125) · [SMS reminders](https://help.acuityscheduling.com/hc/en-us/articles/16676915777293) · [inviting contributors](https://help.acuityscheduling.com/hc/en-us/articles/16676924963341)
- Compliance: [Twilio A2P 10DLC](https://www.twilio.com/docs/messaging/compliance/a2p-10dlc)

---

*Idea-refinement chose "Reframe to Managed Booking." Research: 1 repo map + 1 learnings
pass + 2 external (platform capability/pricing/managed-model + embed/API). Flow/edge-case
analysis performed inline. No code written — research + plan only.*
