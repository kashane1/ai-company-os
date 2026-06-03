---
status: pending
priority: p2
issue_id: "072"
tags: [code-review, quality, portfolio, better-business-web, agency]
dependencies: []
---

# Problem Statement

§6 wants first-party `/work/<slug>` pages at slugs `auto-repair`, `barbering`,
`baked-goods`, `dog-grooming`, `plumbing`, `nails`. The existing
`build_portfolio_demos.py` uses different genre keys
(`auto_repair`, `barber_shop`, `bakery`, `dog_groomer`, `plumber`,
`nail_salon`) and emits to a separate portfolio dir, not `dist/work/`. "Just
repoint the output" is not a 1:1 rename — without a key→slug map, the portfolio
grid links (§5) and the emitted pages (§6) won't agree and every card 404s.

## Findings

- Desired slugs — [LANDING_PAGE_PLAN.md:138](../docs/products/better-business-web/LANDING_PAGE_PLAN.md:138).
- Actual genre keys: [build_portfolio_demos.py:38](../scripts/agency/build_portfolio_demos.py:38) (`auto_repair`, `barber_shop`, `bakery`, `dog_groomer`, `plumber`, `nail_salon`).
- Output path is a separate dir, not `dist/work/`: [build_portfolio_demos.py:32](../scripts/agency/build_portfolio_demos.py:32) `OUT_ROOT = products/better-business-web/portfolio`.
- `render_portfolio_section(manifest)` (§5) assumes a fully populated manifest — if a genre fails to render, behavior is unspecified (dead cards).

## Proposed Solutions

### Option 1: Single canonical genre→slug map consumed by both sides (recommended)
Define one map used by the emitter's output path and the grid generator; add a
test that every grid link resolves to an emitted `dist/work/<slug>/index.html`.
Render guard drops/placeholders missing genres.

Pros:
- One source of truth; broken links become a test failure

Cons:
- Small refactor of the demo builder's output paths

Effort: small-medium
Risk: low

### Option 2: Rename genre keys to the public slugs
Change keys in `build_portfolio_demos.py` to match the URLs directly.

Pros:
- No map indirection

Cons:
- Touches existing keys/manifest other consumers may rely on

Effort: small
Risk: medium

## Recommended Action

Adopt Option 1; add the link-resolves test and an empty/partial-manifest guard.

## Acceptance Criteria

- [ ] One genre→slug map drives both emitter output and grid links.
- [ ] Test asserts every grid card resolves to an emitted page.
- [ ] Missing genres are dropped/placeholdered, not rendered as dead cards.

## Work Log

### 2026-06-02 - Initial review capture
Verified key/slug divergence against build_portfolio_demos.py during `/review`.
