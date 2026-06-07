---
status: pending
priority: p1
issue_id: "038"
tags: [code-review, data-integrity, frontend, agency, drift-guard]
dependencies: []
---

# Problem Statement

The plan says "emit integer cents end-to-end" and replace `_num()`, but keeps the same `bundles` array in `packages.json`. Today `render_catalog_json` emits whole-dollar `bundles[].setup`/`.monthly` (`templates.py:151-172`) and `LandingBody.astro`'s live Packages cards read those dollar keys. Renaming/retyping them to cents silently breaks the production landing page, not just the new `/build/` page. The plan also leaves room for a separate "trusted pricing table" the function imports — a second artifact = a second drift guard.

## Findings (pattern-recognition P1-1 + P2-1, architecture-strategist P2-drift)

1. **Live cards break** if `bundles[].setup`/`.monthly` change type/name without migrating the Astro markup in the same change.
2. **One artifact, not two:** the Netlify function should import the same emitted `packages.json` (now carrying `services` + `discount_tiers` + cents), so there is exactly one pricing artifact guarded by exactly one drift test.
3. `_num()` int/float coercion (`templates.py:146-148`) is the documented float-vs-int trap; cents end-to-end retires it. Markdown render keeps dollar display (`_money`); JSON goes cents.

## Proposed Solutions

### Option 1 (recommended): cents keys + atomic markup migration
Emit `*_cents` integer fields (`setup_gross_cents`, `setup_after_cents`, `monthly_cents`) on `bundles` + a `services` array + `discount_tiers`. Migrate `LandingBody.astro` Packages markup to format cents→dollars in the same commit. Function imports the same `packages.json`.

### Option 2: dual keys (transition)
Keep dollar `setup`/`monthly` for back-compat AND add `*_cents`. Less risky to the live page now, but leaves two representations to drift — only as a stepping stone.

## Recommended Action

(leave blank for triage)

## Technical Details

- Affected: `packages/agency/templates.py` (`render_catalog_json`, `_num`), `scripts/agency/render_catalog_json.py`, `products/better-business-web/site/src/data/packages.json`, `products/better-business-web/site/src/components/LandingBody.astro`, `create-checkout.mjs` (imports same JSON).

## Acceptance Criteria

- [ ] Live Packages cards render correctly after the migration (no broken/zero prices).
- [ ] Exactly one emitted pricing artifact, imported by island + function + drift test.
- [ ] `_num` trap removed; JSON is integer cents; markdown still shows dollars.

## Work Log

(to be filled in)

## Resources

- /workflows:review round 2 (2026-06-06): pattern-recognition P1-1/P2-1, architecture-strategist (drift chain)
