---
description: Generate an App Store positioning pack from product artifacts. Run this when preparing App Store metadata, name direction, or screenshot strategy for a managed product.
canonical_source: skills/canonical/shared/app-store-positioning-pack.md
---

# App Store Positioning Pack

You are running the app-store-positioning-pack skill from `skills/canonical/shared/app-store-positioning-pack.md`. Follow the canonical definition.

## Quick reference

Read these product artifacts in order (each grounds the next):
1. `founder-brief.md` — vision, target user, principles
2. `product-brief.md` — thesis, value prop, MVP boundaries
3. `mvp-spec.md` — actual screens, features, acceptance criteria
4. `app-store-positioning.md` — existing positioning direction

## Steps

1. Load product from `infra/products.json`, find `docs_root`
2. Read all four source artifacts
3. Assess existing `app-store-positioning.md` for completeness (match by content, not headings — sections may be named differently)
4. If existing name/subtitle candidates exist, use them as starting point; generate 3-5 name candidates (30 char limit, grounded in founder-brief)
5. Generate 3-5 subtitle candidates (30 char limit, complement the name); evaluate as name+subtitle pairs and flag redundancy
6. Build screenshot story (6-8 frames from real mvp-spec.md screens)
7. Define keyword angle (primary, secondary, avoid)
8. Compile metadata notes (description angle, What's New, privacy messaging)
9. Write positioning pack to `state/artifacts/appstore/<product-id>/positioning-pack.md`

## Critical constraints

- Every claim must trace to a specific product artifact
- Do not promise features beyond mvp-spec.md scope
- Do not generate generic marketing copy — be specific to this product
- Respect Apple character limits: 30 chars name, 30 chars subtitle
- Screenshot story must reference real screens, not aspirational ones

## Boundaries

- **May edit**: `state/artifacts/appstore/`, `docs/products/<product-id>/app-store-positioning.md` (gap-fill only)
- **Must not touch**: `products/`, `packages/`, `apps/`, `infra/`
- **Do not invent** product decisions — flag gaps for founder review
