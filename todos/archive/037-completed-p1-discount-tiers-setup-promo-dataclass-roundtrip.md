---
status: pending
priority: p1
issue_id: "037"
tags: [code-review, schema, agency, data-integrity]
dependencies: []
---

# Problem Statement

The plan adds a top-level `discount_tiers` block and a per-bundle `setup_promo` to `catalog.yaml`, but `ServiceCatalog.from_dict` only reads `services` and `bundles` (`offer.py:177-187`) — any other top-level key is silently dropped. A "typed accessor" that reads raw YAML would bypass the frozen-dataclass `to_dict`/`from_dict` round-trip the module is built around (`offer.py:9-11`). Silent-drop = the discount engine loads with no tiers.

## Findings (pattern-recognition P1-3)

1. `Bundle` (`offer.py:103-127`) has explicit `to_dict`/`from_dict`; `setup_promo` must be a real field wired through both with a default, like its peers.
2. `discount_tiers` must be a typed field on `ServiceCatalog` (e.g. `tuple[DiscountTier, ...]` of a new frozen dataclass with its own `to_dict`/`from_dict`), parsed in `from_dict`, re-emitted in `to_dict`.
3. Validation belongs in `ServiceCatalog.validate()` alongside the existing bundle checks (`offer.py:147-157`): 0 ≤ pct ≤ 100, contiguous/monotonic count ranges, `setup_promo ≥ 0`.

## Proposed Solutions

### Option 1 (recommended)
- `Bundle.setup_promo: int = 0` (cents) or `float = 0.0` (dollars) — match the cents decision from #034/#038; wire `to_dict`/`from_dict`.
- New frozen `DiscountTier(min, max, pct)` with round-trip; `ServiceCatalog.discount_tiers: tuple[DiscountTier, ...]`; parse + emit + validate.

## Recommended Action

(leave blank for triage)

## Technical Details

- Affected: `packages/schemas/offer.py` (⚠️ founder-gated) `Bundle`, new `DiscountTier`, `ServiceCatalog.from_dict`/`to_dict`/`validate`; `packages/agency/catalog.yaml`.

## Acceptance Criteria

- [ ] `setup_promo` + `discount_tiers` survive a `from_dict`→`to_dict` round-trip (no silent drop).
- [ ] `validate()` rejects malformed tiers (bad pct, non-contiguous ranges) and negative promo.
- [ ] Loading the real catalog yields the expected tiers + promos.

## Work Log

(to be filled in)

## Resources

- /workflows:review round 2 (2026-06-06): pattern-recognition-specialist P1-3
