---
status: open
change_id: open-tcg-openflip-export-p6
owner: founder
last_reviewed: 2026-10-25
---

# OpenTCG store monitoring P6: store offers into OpenFlip

**Parent plan:** [independent store monitoring](2026-10-23-open-tcg-indie-store-monitoring.md), phase P6 (design in its §7).
**Status:** Built 2026-10-25.

## What exists

- **Store observations (P4):** every store change that leaves a matched English listing newly buyable becomes a radar observation. Fields: `source = "stores"`, the store as `author`, `retailer` (store name), `product_text` (catalog product name), `price` and `url`.
- **The v1 export and bridge:**
  - `radar export-observations` (`radar/export.py`) writes observations as v1 NDJSON.
  - OpenFlip's bridge (`packages/openflip/bridge.py`) validates it into source evidence.
  - Both were written by another session on 2026-10-05 and committed in `dd08e9d`.
- **What v1 already carries:** the export maps `retailer` to `retailer_hint`, `product_text` to `item_hint`, and `price` to `price_hint`, so store offers fit the v1 contract unchanged. The bridge requires the v1 fields and ignores, then drops, any extra ones.

## Built

- **`store_offer_details`** has one row per store observation, written when the observation is recorded. It holds:
  - store id and trust
  - catalog product id
  - price, MSRP and MSRP basis
  - price class and market price
  - whether the offer is alert-eligible
- **Who decides:** every newly buyable offer is recorded, not only MSRP hits. OpenFlip's qualification decides what is worth reselling, and the radar records the class so OpenFlip can filter.

## Export and bridge fields

The export and the bridge each got a small additive change, kept at `schema_version` 1 because the fields are optional:

- **`radar/export.py`:**
  - `LEFT JOIN store_offer_details d ON d.observation_id = observations.id`
  - add `msrp_cents`, `msrp_basis`, `price_class`, `store_trust` and `catalog_product_id`, all null for non-store observations
- **`packages/openflip/bridge.py`:** keep those fields when present, validating integers and the class and trust enums.
- **Done when:** an `at_msrp` store offer, exported by `radar export-observations`, parses through `parse_observations` with its class and MSRP intact.

## As built (2026-10-25)

- **The founder approved committing the dormant work** (commit `dd08e9d`): `radar/export.py`, the `export-observations` command, `packages/openflip/bridge.py` and their tests, as written on 2026-10-05.
  - The only change: the bridge's replay test skips when the rest of the OpenFlip service, still uncommitted, isn't present.
  - The rest of `packages/openflip` stays uncommitted.
- **Export:** it joins `store_offer_details` when the table exists, so older databases still export, and validates each field. Non-store observations carry nulls.
- **Bridge:** it keeps the fields only when an export sends them, so v1 records from before P6 parse unchanged. Unknown classes, trust levels or bases, and negative or non-integer numbers, are rejected.
- **End to end:**
  1. A store read finds a $49.99 Delta Reign ETB against a $49.99 official MSRP.
  2. The alert pass records an `at_msrp` observation and sends the alert.
  3. `radar export-observations` writes it.
  4. `parse_observations` returns `source=stores`, `price_class=at_msrp`, `msrp_cents=4999`, `msrp_basis=official_listing`, `store_trust=unvetted` and `catalog_product_id=712102`.
- **Live:** the database exports its 237 observations with the new fields, null on non-store rows.
