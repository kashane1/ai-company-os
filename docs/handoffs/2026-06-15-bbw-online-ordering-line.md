# Handoff — BBW Online Ordering product line (2026-06-15)

> **TL;DR** — Added a new à-la-carte **Online Ordering** line to the BBW catalog: customers
> order + pay on the business's own website, fulfilled through the client's own POS (Square /
> Clover). Launching **hosted/embedded only** (no custom-cart "Premium" tier on the public
> site). Four SKUs, all `tier_2`, mirroring the existing `booking_*` pick-one-base + modifiers
> pattern: `ordering_connect` ($200), `ordering_setup` ($600), `ordering_menu_entry` /"Menu
> Build" ($250), `ordering_management` /"Menu Management" ($40/mo). Money always flows through
> the client's own merchant account — the agency is never a payment facilitator. **Square +
> Clover supported; Toast is gated (assess-on-request, never advertised).** Shipped: catalog +
> regenerated artifacts + a group-aware builder fix + an ops routing doc. Verified live in the
> pricing builder. Not committed.

## What shipped

| File | Change |
|---|---|
| `packages/agency/catalog.yaml` | +4 SKUs in Tier 2 (`ordering_*`), `exclusive_group: ordering_base` |
| `products/.../site/src/data/packages.json` | regenerated via `scripts/agency/render_catalog_json.py` |
| `docs/agency/service-catalog.md` | regenerated via `scripts/agency/render_catalog_md.py` |
| `products/.../site/src/components/BundleBuilder.tsx` | locked-modifier label is now group-aware (`GROUP_NEEDS_LABEL`); was hardcoded "needs a booking option" |
| `docs/agency/ordering-platform-routing.md` | **new** — operator routing guide + Toast gate + liability firewall |
| `docs/agency/INDEX.md` | regenerated via `make doc-index` |

## The SKUs (pick-one base + modifiers, like booking)

`exclusive_group: ordering_base` — pick one base:
- **`ordering_connect`** — "Online Ordering — Connect (your POS)" — $200 one-time. Order
  buttons → the client's existing Square/Clover hosted ordering page, branded.
- **`ordering_setup`** — "Online Ordering — Done-for-you Setup" — $600 one-time. We set up
  branded ordering + checkout on the client's POS, configure menu/tax/pickup, test end-to-end.

`requires_group: ordering_base` — modifiers (stack on either base):
- **`ordering_menu_entry`** — "Menu Build" — $250 one-time. Enter the full menu into the POS.
- **`ordering_management`** — "Menu Management" — $40/mo. ~2 menu change requests/mo.

## Design decisions (founder, this session)

- **À la carte only** — no "Restaurant Starter" vertical bundle. (Core A/B/C stay universal.)
- **Hosted/embedded only at launch.** No custom-cart → API → fulfillment "Premium" tier on the
  open site — that carries payment/refund/order-accuracy liability + maintenance. Premium is
  assess-on-request only, gated behind confirmed POS API access + budget.
- **Food-first, retail later.** SKUs named generically so a retail "Online Store" line can slot
  in without a rework.
- **Square + Clover supported; Toast gated.** Toast's write API is partner-gated + restaurant-
  only — confirm a client's integration tier before quoting; never list Toast as supported on
  the public site. (Consistent with the catalog-honesty standard.)
- **Liability firewall:** money flows through the client's own merchant account; the agency is
  never a payment facilitator and never owns funds/refunds/chargebacks.
- **Pitch = commission savings** (keep more vs. 15–30% to DoorDash/Uber Eats), not "nicer
  checkout." Scope fence: pickup/curbside/dine-in in; **delivery on request only**.

## Verification

- `pytest` catalog suite (28) + cross-language pricing drift (2) — **pass**.
- `npm run build` — **pass** (16 pages).
- Live check in the pricing builder: all 4 cards render in "Get found & booked"; selecting the
  $600 base unlocks Menu Build + Menu Management and totals correctly; booking modifiers still
  read "needs a booking option", ordering modifiers read "needs an ordering option".
- `make tokens-check` fails only on **pre-existing** `state/clients/.../conversion_lab/*.md`
  runtime files (untouched here); the new doc passes.

## Not done / next

- **Not committed** — review the diff and commit when ready.
- **`ordering.py` is now built** (`packages/agency/ordering.py` + `tests/python/unit/test_agency_ordering.py`
  + `scripts/agency/inject_ordering.py`, 25 tests). It mirrors `booking.py`: renders/injects an
  "Order Online" button to the client's POS hosted ordering page (idempotent), persists an
  `OrderingSetup` record, and gates the platform/tier (Square/Clover full; **Toast Setup = hard
  block, Toast Connect = warning**). It is operator-run (not yet wired into `default_safe_executors`,
  same as `manage_booking`). If/when the custom "Premium" tier is greenlit, the Square/Clover
  Orders-API integration would extend this module behind the same gate.
- Per-platform setup runbooks (`docs/agency/runbooks/ordering-setup-square.md` / `-clover.md`) still
  to be written when the first ordering client lands.
- Per-platform setup runbooks (`docs/agency/runbooks/ordering-setup-square.md` / `-clover.md`)
  not yet written — mirror the booking runbooks when the first ordering client lands.
