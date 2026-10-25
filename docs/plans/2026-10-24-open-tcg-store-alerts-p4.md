---
status: open
change_id: open-tcg-store-alerts-p4
owner: founder
last_reviewed: 2026-10-24
---

# OpenTCG store monitoring P4: store alerts and the deals digest

**Parent plan:** [independent store monitoring](2026-10-23-open-tcg-indie-store-monitoring.md), phase P4 (design in its §5).
**Builds on:** [P3](2026-10-24-open-tcg-store-msrp-p3.md), which supplies MSRP references and price classes.
**Status:** Built 2026-10-24.

## Design

### What becomes an observation

After every store read (the 15-minute sync, and the immediate read a drop email triggers), the radar looks at listing snapshots from the last 15 minutes. A snapshot qualifies when it leaves a matched (`exact` or `confirmed`) English listing in stock and makes it newly buyable:

- **Appeared:** first seen, outside the store's baseline sweep.
- **Back in stock.**
- **Cheaper:** the price dropped while in stock.

A price rise or an out-of-stock change is never a candidate.

Each candidate becomes an observation with these fields:

- `source_id = "stores"`, with the store id as author, so the scorecard ranks stores individually (`stores:<store_id>`)
- `signal` is `preorder` when the title says pre-order, otherwise `in_stock`
- `retailer` is the store's name, `product_text` the catalog product name, plus the price and the listing URL

Episodes use the usual 60-minute grouping, so a store that flickers in and out of stock is one episode and one alert.

### When it alerts

The rules come from the parent plan and the founder decisions of 2026-10-23.

| Case | Alerts when |
|---|---|
| Any product naming an `[exclude]` term | never |
| Watched product (a watch matches the catalog product exactly) | price at or below `alert_at` and, when the MSRP has evidence, class `at_msrp` or `below_msrp`. That is `min(alert_at, 1.10 × MSRP)`. With no evidence MSRP, the `alert_at` alone decides. |
| Unwatched product from a watched set | class `at_msrp` or `below_msrp` on an evidence MSRP (basis 1–3) |
| Product from an unwatched set | never; it appears in the digest only |
| `marked_up` | never |

- **Watched sets** are:
  - the sets of watches that match a catalog product exactly
  - sets named inside other watch names, where "Mega Evolution Delta Reign ETB" names Delta Reign and not the Mega Evolution era
- **Alert text:**
  - Title: "At MSRP · Wulf Gaming" or "Below MSRP (unvetted store) · …"
  - Body: the product, price, MSRP and its basis, market price, the store's trust, the reason, and the link
  - Below MSRP on an `unvetted` store adds "Unvetted store, below MSRP: check it before paying."
- **Delivery:** one Mac notification per episode, through the existing notifications outbox and its dedupe.
- **No assisted open:** store links are never opened in Brave until a store reaches `trust = purchased_ok`.

### Deals digest

`radar deals` (and `make deals`) prints the cheapest in-stock offer per catalog product, grouped by class, with the change since a day earlier.

- **Listed classes:** below, at and near MSRP, and market.
- **Counted but not listed:** `marked_up` offers and offers with no MSRP.

## Done when

- Unit tests cover:
  - an at-MSRP alert that fires once
  - the unvetted below-MSRP warning
  - `marked_up` never alerting, even when watched
  - excluded terms and unwatched sets
  - estimates never alerting
  - baseline sweeps being silent
  - price rises not counting, and stale changes being ignored
  - the digest's daily change
- The live sync runs the alert pass, and `radar deals` renders on live data.

## As built (2026-10-24)

- **Where it runs:** the alert pass runs at the end of every store sync and after each drop-email store check.
  - The sync summary line now reports store observations and alerts.
  - Watched sets resolve to 30th Celebration, Ascended Heroes, Chaos Rising, Delta Reign, Destined Rivals, Perfect Order, Pitch Black, Prismatic Evolutions and the 2026 First Partner collection.
  - Chaos Rising and Pitch Black never alert, because they are `[exclude]` terms.
- **Not built yet:** assisted open stays off until a store is `purchased_ok`.

