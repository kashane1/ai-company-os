---
status: pending
priority: p2
issue_id: "039"
tags: [code-review, data-integrity, agency, money, validation]
dependencies: ["037"]
---

# Problem Statement

"Packages are always the best value" (cheaper than building the same set with the tier discount) is currently a manual spot-check, not a guarantee. Margins are razor-thin (A saves only $30.10 vs tier, B only $13.90), so a future re-split could silently flip a package into a pricing inversion where DIY is cheaper than the named package — breaking the "Best value" badge.

## Findings (architecture-strategist P2, data-integrity P2-2)

- Verified today: A $599 ≤ $629.10, B $899 ≤ $912.90, C $1,799 ≤ $1,890.40 — no inversion, but thin.
- Nothing structurally enforces `setup_promo ≤ tier-discounted setup` for the bundle's service set.

## Proposed Solutions

### Option 1 (recommended): catalog-load invariant
In `ServiceCatalog.validate()`: for every bundle carrying `setup_promo`, compute the tier-discounted setup for its `service_ids` and raise `CatalogError` if `setup_promo_cents > tier_after_cents`. One-line invariant given the tier accessor. Add a unit test so the failure mode is obvious.

## Recommended Action

(leave blank for triage)

## Technical Details

- Affected: `packages/schemas/offer.py` `ServiceCatalog.validate()`; test in `tests/python/unit/`.

## Acceptance Criteria

- [ ] Catalog load raises if any promo exceeds its tier-discounted equivalent.
- [ ] Unit test covers an intentional inversion (expects `CatalogError`) and the passing real catalog.

## Work Log

(to be filled in)

## Resources

- /workflows:review round 2 (2026-06-06): architecture-strategist P2, data-integrity-guardian P2-2
