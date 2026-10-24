---
status: open
change_id: open-tcg-store-msrp-p3
owner: founder
last_reviewed: 2026-10-24
---

# OpenTCG store monitoring P3: MSRP references and price classes

**Parent plan:** [independent store monitoring](2026-10-23-open-tcg-indie-store-monitoring.md), phase P3 (design in its §4).
**Builds on:** P2 (`86dd04f`): stores are matched to a reference catalog of every English set.
**Status:** Built 2026-10-24.

## Starting point (2026-10-24)

- **Matched stock:** about 2,400 in-stock listings are matched to a catalog product. The largest forms are ETBs (396 listings, 85 products), booster packs (290), tins (275), booster boxes (197) and booster bundles (174).
- **No MSRP data:** no MSRP exists anywhere in the repository. The newer watches carry a Best Buy first-party price as `alert_at`, labeled "not MSRP".
- **Target set:** the catalog has 57 ETBs, booster bundles and booster displays released from 2025 onward. These are P3's "done when" set.

## Design

### Data: `products/open-tcg/msrp.toml` is the source of truth

The file is reviewable in git. It holds evidence rows and estimate rules.

- **`[[reference]]` rows** have these fields:
  - `product_id`: the tcgcsv product id
  - `name`: for readability
  - `msrp`
  - `basis`: `official_listing`, `big_box_first_party` or `distributor_or_press`
  - `evidence_url`
  - `checked_on`
  - `note`
- **`[[form_default]]` rules** cover a form, a release window (`since`, `until`) and an optional exclusive retailer, with a dollar value. They are basis 4, `form_default`, and are marked estimated.
- **`[[pack_price]]` rules** give the pack MSRP by release window. They price products whose catalog name states a pack count (basis 5, `per_pack_estimate`, estimated).

**Watchlist references also count.** A watch whose `ceiling_basis` is a Best Buy first-party price, and whose name matches one catalog product exactly, contributes a `big_box_first_party` reference. Its evidence URL is the watch's Best Buy link. An explicit `msrp.toml` row with the same basis wins.

`radar` syncs these into a `msrp_references` table (basis 1–3 only) on every store run and on `radar msrp`. Joins and the OpenFlip export (P6) can read MSRPs from SQL. Estimates are computed in code and never stored.

### Resolution

A product's MSRP comes from the first of these that exists:

1. Its strongest evidence row, by basis rank 1–3. Ties go to the newest `checked_on`.
2. The newest `form_default` rule matching its form, exclusive retailer and release date.
3. A `per_pack_estimate`, when the catalog name gives a pack count.

### Price classes

The rules follow the parent plan. Prices are item prices; Shopify JSON has no shipping.

| Class | Rule |
|---|---|
| `below_msrp` | under 0.95 × MSRP |
| `at_msrp` | 0.95–1.10 × MSRP |
| `near_msrp` | 1.10–1.25 × MSRP |
| `market` | above 1.25 × MSRP and at most 1.05 × market (or market unknown) |
| `marked_up` | above 1.25 × MSRP and above 1.05 × market |
| `no_msrp` | no reference or estimate |

- **Alert-eligible** means `below_msrp` or `at_msrp` with a basis 1–3 MSRP. Estimated MSRPs rank and digest but never make a listing alert-eligible.
- **P4 adds the rest of the alert rule:** watched sets and `alert_at`.

### Commands

- `radar msrp`: coverage of the target set (2025+ ETBs, bundles and displays) by basis.
- `radar msrp missing [--since DATE] [--forms ...]`: products with no basis 1–3 evidence. This is the input for the weekly refresh: add presale products' prices when they're published.
- `radar stores` gains:
  - an MSRP class column on the cheapest offer per product
  - class counts across in-stock offers
  - the list of alert-eligible offers, with the unvetted-store warning on below-MSRP rows

### Weekly refresh

The weekly refresh is manual for now. Run `radar msrp missing`, research the new products at basis 1–2, and add `[[reference]]` rows. Scheduling it as a recurring Claude task is a founder decision, because it has a running cost.

## Done when

- Every 2025+ ETB, booster bundle and booster display in the catalog has a basis 1–3 MSRP, or is listed by `radar msrp missing` with the reason in `msrp.toml`.
- Unit tests cover resolution order, the class boundaries, estimates never being alert-eligible, and watchlist-derived references.
- `radar stores` shows classes on live data.
