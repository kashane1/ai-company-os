---
status: open
change_id: open-tcg-openflip-export-p6
owner: founder
last_reviewed: 2026-10-25
---

# OpenTCG store monitoring P6: store offers into OpenFlip

**Parent plan:** [independent store monitoring](2026-10-23-open-tcg-indie-store-monitoring.md), phase P6 (design in its §7).
**Status:** Radar side built 2026-10-25. The export and OpenFlip bridge changes wait on the founder (see "Blocked").

## What exists

- **Store observations (P4):** every store change that leaves a matched English listing newly buyable becomes a radar observation. Fields: `source = "stores"`, the store as `author`, `retailer` (store name), `product_text` (catalog product name), `price` and `url`.
- **The v1 export and bridge:**
  - `radar export-observations` (`radar/export.py`) writes observations as v1 NDJSON.
  - OpenFlip's bridge (`packages/openflip/bridge.py`) validates it into source evidence.
  - Both are **uncommitted work from another session**, last edited 2026-10-05.
- **What v1 already carries:** the export maps `retailer` to `retailer_hint`, `product_text` to `item_hint`, and `price` to `price_hint`, so store offers fit the v1 contract unchanged. The bridge requires the v1 fields and ignores, then drops, any extra ones.

## Built

- **`store_offer_details`** has one row per store observation, written when the observation is recorded. It holds:
  - store id and trust
  - catalog product id
  - price, MSRP and MSRP basis
  - price class and market price
  - whether the offer is alert-eligible
- **Who decides:** every newly buyable offer is recorded, not only MSRP hits. OpenFlip's qualification decides what is worth reselling, and the radar records the class so OpenFlip can filter.

## Blocked: the export and bridge fields

To finish P6, the export and the bridge each need a small additive change, kept at `schema_version` 1 because the fields are optional:

- **`radar/export.py`:**
  - `LEFT JOIN store_offer_details d ON d.observation_id = observations.id`
  - add `msrp_cents`, `msrp_basis`, `price_class`, `store_trust` and `catalog_product_id`, all null for non-store observations
- **`packages/openflip/bridge.py`:** keep those fields when present, validating integers and the class and trust enums.
- **Done when:** an `at_msrp` store offer, exported by `radar export-observations`, parses through `parse_observations` with its class and MSRP intact.

Both files belong to the uncommitted OpenFlip work. Changing them, or committing them, is the founder's call.
