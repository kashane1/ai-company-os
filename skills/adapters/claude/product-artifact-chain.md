---
description: Validate and extend the founder-to-spec artifact chain for a managed product. Run this when creating or reviewing product artifacts like founder briefs, product briefs, MVP specs, or backlogs.
canonical_source: skills/canonical/shared/product-artifact-chain.md
---

# Product Artifact Chain

You are running the product-artifact-chain skill from `skills/canonical/shared/product-artifact-chain.md`. Follow the canonical definition.

## Quick reference

The expected artifact chain for any product:

1. `founder-brief.md`
2. `product-brief.md`
3. `mvp-spec.md`
4. `backlog.md`
5. Platform-specific (e.g. `ios-architecture.md`, `app-store-positioning.md`)
6. Domain-specific (e.g. `insight-rules.md`)

## Steps

1. Read `infra/products.json` to find the product's `docs_root`
2. Check each artifact in the chain for existence and completeness
3. Produce a gap report listing missing or empty artifacts
4. If asked to create an artifact, read all upstream artifacts first, then draft
5. Place new artifacts at `<docs_root>/<artifact-name>.md`
6. Do not modify files outside `docs/products/`

## Boundaries

- **May edit**: `docs/products/` only
- **Must not touch**: `apps/`, `packages/`, `infra/`, `state/`, `products/`
- **Do not invent** product decisions — flag uncertainties for founder review
