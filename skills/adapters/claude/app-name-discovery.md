---
description: Consume an existing founder pack at docs/products/<product_id>/ and produce a 4×6 matrix of candidate app names organized by emotional register × naming archetype, plus a 5-name shortlist that satisfies an archetype-spread rule. Each candidate scored on the canonical 8-dimension rubric. Hard gates auto-reject offensive cross-language collisions, App Store exact-match duplicates, and same-class trademark conflicts. Names only — taglines remain owned by app-store-positioning-pack.
canonical_source: skills/canonical/app-name-discovery/skill.md
---

# App Name Discovery

Run the canonical skill at `skills/canonical/app-name-discovery/skill.md`.
The canonical body owns the rubric, weights, gates, spread rule, and
validation list. Read it first, then return here for Claude-runtime guidance.

## Quick reference

- **Prerequisite:** `docs/products/<product_id>/` contains `founder-brief.md`,
  `product-brief.md`, `brand-guidelines.md`, `competitive-analysis.md`. Optional:
  `app-store-positioning.md`. Abort if any required file is missing.
- **Output:** `docs/products/<product_id>/naming/<YYYY-MM-DD>-candidates.md`.
- **Boundaries:** read-only on the founder pack; write only inside
  `docs/products/<product_id>/naming/`.
- **Scope:** names only. Taglines are owned by `app-store-positioning-pack`.
- **Strictly do not:** pick the winning name, run live availability lookups,
  or write the chosen name back into the founder pack.

## Steps (defer to canonical for details)

1. **Validate founder pack & capture reproducibility** — canonical Phase 0.
   Capture `git rev-parse HEAD`; mark `dirty: true` if the product dir has
   uncommitted changes.
2. **Synthesize the naming brief** — canonical Phase 1.
3. **Generate the matrix** — canonical Phase 2. 24 cells (4 registers × 6
   archetypes), 8 candidates per cell, fixed traversal order to mitigate
   archetype bias.
4. **Apply hard gates** — canonical Phase 3. Cross-language safety,
   App Store exact-match collision, trademark (same-class only). Log every
   rejection.
5. **Score on the 8-dimension rubric** — canonical Phase 4. Default weights
   and `app_store_fitness` sub-signals are defined there.
6. **Build the shortlist with the archetype-spread rule** — canonical
   Phase 5. Top 5 by total, swap to satisfy ≥3 archetypes, mark every row
   `needs_verification: true`.
7. **Write the output** — canonical Phase 6, using
   `skills/canonical/app-name-discovery/output-template.md`.
8. **Validate** — canonical Phase 7 (4 checks).

## Boundaries

- **May edit:** `docs/products/<product_id>/naming/*.md`.
- **Must not touch:** `apps/`, `packages/`, `infra/`, `state/`, `products/`,
  any other `docs/products/<product_id>/*` artifact.
- **Read-only:** the founder pack.
