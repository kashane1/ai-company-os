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

## As built (2026-10-24)

- **Evidence:** 50 of the 57 target products have an evidence MSRP: 35 Pokémon Center US listings, 14 distributor solicitations (PHD Games) and 1 Best Buy watch.
  - Every set from Prismatic Evolutions to Delta Reign has the same prices: ETB $49.99, Pokémon Center ETB $59.99, booster bundle $26.94 and 36-pack display $161.64, enhanced or not.
  - A spot check of the Chaos Rising distributor page matched the research exactly.
- **Unpriced, with reasons in `msrp.toml`:** 7 products.
  - Four booster bundle displays (bundle counts are unconfirmed)
  - The Sam's Club bundle
  - The Dollar General ETB
  - The standard Mega Evolution display, which only shipped as the enhanced box
  - Unpriced products get no estimate either.
- **Estimates:** form defaults and the $4.49 pack price start at 2025-01-01, where the evidence starts. Older sets show `no_msrp` until researched.
- **Do not use Pokémon Center Canada pages:** they show CAD prices labeled as USD.
- **First live digest:**
  - **CARDHAVEN TCG (unvetted)** lists recent sets at about 90% of MSRP: six below-MSRP offers, all carrying the unvetted warning.
  - **GoodStash TCG** has Journey Together ETBs at MSRP.

### Scarlet & Violet era (2023–2024), added 2026-10-24

- **Evidence:** 53 of 66 products released in 2023–2024 now have one: 34 Pokémon Center US listings and 19 distributor solicitations. That brings evidence to 103 of 123 products since 2023.
  - From the Scarlet & Violet base set (2023-03-31) on, prices match the 2025–2026 pattern: ETB $49.99, Pokémon Center ETB $59.99, bundle $26.94 and display $161.64.
  - Pokémon raised packs from $3.99 to $4.49 at that set. PHD solicited 2023 bundles at $26.99, while Pokémon Center lists $26.94.
  - Crown Zenith (January 2023, the last Sword & Shield set) kept $3.99 packs: its bundle is $23.94 and its Pokémon Center ETB Plus is $64.99.
  - The estimate windows now start 2023-03-31.
- **Unpriced, with reasons (13):**
  - "[Set of 2]" TCGplayer pairings
  - Two bundle displays
  - Club-store Trick or Trade bags and loose mini packs
  - The Greninja battle deck bundle
  - The retail Surging Sparks bundle
- **Fixes found on live data:**
  - "151 Booster Pack" was being read as 151 packs. Pack counts are now plural only ("10 Booster Packs").
  - An unvetted store priced far below market (under 0.6× market) now gets a warning, even at MSRP. GoodStash TCG lists out-of-print SV ETBs and displays at or below MSRP, against markets of $300–$450. All of them were listed together on 2026-10-03, which fits the "too good" risk in the parent plan.

### Sword & Shield era (2020–2022), added 2026-10-25

- **Evidence:** 45 of 55 products: 26 Pokémon Center US, 17 distributor or press (PHD Games from Astral Radiance on, plus PokeBeach and Dexerto) and 2 Best Buy first-party.
  - Main sets had $3.99 packs throughout: ETB $39.99 (8 packs), Pokémon Center ETB $49.99 (10 packs, from Chilling Reign), bundle $23.94 and display $143.64.
  - Special sets differ: Champion's Path, Shining Fates, Celebrations and Pokémon GO ETBs are $49.99, and the Celebrations and Pokémon GO Pokémon Center ETBs are $64.99.
  - A spot check of PHD's Lost Origin solicitation matched exactly.
- **Estimate rules** now cover 2020-02-07 to 2023-03-31 at those prices.
- **Unpriced (10):**
  - "[Set of 2]" pairings
  - the international-only ETB Plus
  - the Vivid Voltage display (only a CAD page was found)
  - Trick or Trade bags
- **Total:** 148 of 178 ETBs, bundles and displays since 2020 have evidence. Older sets trade far above MSRP and are left without one.

