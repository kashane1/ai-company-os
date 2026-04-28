# App Name Discovery Skill — Brainstorm

**Date:** 2026-04-28
**Status:** Brainstorm (pre-plan)
**Test case:** Naming the "life clock" iOS app (time-allocation mirror against a finite life budget)

## What We're Building

A reusable, product-agnostic skill — `app-name-discovery` — that consumes an existing founder pack for a product and produces a scored matrix of candidate app names organized by **emotional register × naming archetype**, plus a recommended shortlist.

It runs *after* the founder pack exists (founder-brief, product-brief, brand-guidelines, competitive-analysis, positioning) and *before* App Store metadata is locked in. Its job is to turn the qualitative product context into a defensible, multi-faceted naming exploration with explicit trade-offs surfaced — not to pick the name. The founder picks; the skill makes the picking honest.

## Why This Approach

Naming is the single most reused early-product decision and the one most often done by gut. Every product after life-clock will need this. Building a skill — with a written rubric, weights, and a forced spread across registers and archetypes — turns naming from a vibes exercise into a repeatable artifact that can be reviewed, version-controlled, and improved over time. The matrix shape (rather than a flat list) prevents the well-known failure mode where a founder converges early on one register and never sees the alternatives they would have preferred.

The skill follows the repo's canonical convention: source-of-truth in `skills/canonical/app-name-discovery/`, runtime translation in `skills/adapters/claude/app-name-discovery.md`, and a thin discovery pointer in `.claude/skills/`. It joins the founder-pack-consuming family alongside `app-store-positioning-pack` and `gtm-artifact-refresh`.

## Key Decisions

### Inputs
- Founder pack at `docs/products/<product-id>/` — specifically: `founder-brief.md`, `product-brief.md`, `brand-guidelines.md`, `competitive-analysis.md`, and any positioning doc.
- Skill fails fast if the pack is missing required files (no guessing the product from a one-liner).

### Output organization: register × archetype matrix
- **Registers (4):** Stark / memento mori, Calm / reflective, Sharp / motivating, Playful / warm.
- **Archetypes (5):** Descriptive, Evocative, Invented, Metaphor, Compound.
- **Volume:** 8 candidates per cell → up to ~160 candidates total.
- Output written to `docs/products/<product-id>/naming/<YYYY-MM-DD>-candidates.md`.

### Rubric: Full 8 dimensions, 1–5 with weights
1. Memorability
2. Pronounceability
3. Distinctiveness
4. Positioning fit (vs founder pack)
5. Domain / App Store availability (estimated risk)
6. Trademark risk (estimated, flag-for-manual)
7. Cross-language safety
8. Visual / icon potential

Each dimension scored 1–5; weighted sum produces a total. Default weights live in the canonical skill and can be overridden per-product in a YAML front-matter block on the output doc.

### Availability handling
Score-only, flag-for-manual. The skill estimates risk from genericness/commonness/linguistic patterns and marks shortlist candidates `needs_verification: true`. The founder runs actual App Store, USPTO, and domain checks on the shortlist — not the skill.

### Spread & gate rules
- **Cross-language safety hard gate:** Any candidate scoring 1/5 on cross-language safety is auto-rejected before entering the matrix.
- **Archetype spread rule:** The shortlist (top 5) must contain candidates from at least 3 of the 5 archetypes. If pure ranking would violate this, swap in the highest-scoring candidate from a missing archetype.

### Output structure
- Header: product id, founder-pack hash/date, rubric weights used.
- Matrix: 4 × 5 grid, each cell containing 8 named candidates with per-dimension scores + total.
- Shortlist: top 5 across the matrix with rationale and verification checklist.
- Discarded notes: rejections with reasons (cultural risk, generic, etc.).

### Wiring
- `skills/canonical/app-name-discovery/skill.md` — process, rubric, weights, output template.
- `skills/adapters/claude/app-name-discovery.md` — Claude runtime adapter.
- `.claude/skills/app-name-discovery/SKILL.md` — discovery pointer per WIRING.md.
- Trigger phrases added to `CLAUDE.md`: "find a name for this app", "name this product", "run name discovery", "explore app names".
- Entry added to `skills/registry.yaml`.

## Open Questions

_None — all resolved below._

## Resolved Questions

- **Archetype spread rule:** Enforce spread — shortlist must include candidates from ≥3 archetypes.
- **Default weights:** Single default set in canonical; per-product override via YAML front-matter on the output doc.
- **Cross-language safety:** Hard gate — 1/5 on this dim auto-rejects a candidate before it enters the matrix.
- **Scope:** Strictly names. Taglines remain owned by `app-store-positioning-pack`.
- **Founder-pack reproducibility:** Capture git SHA of the product dir + path on the output doc header.

- **Product context for life-clock:** Time-allocation mirror against a finite life budget (closer to habit/time-audit than memento mori or pure life-in-weeks).
- **Skill vs. one-shot:** Build the reusable skill first, then apply it. Life-clock is the test case, not the goal.
- **Rubric size:** Full 8 (over Lean 5).
- **Output shape:** Register × archetype matrix (over flat ranked list).
- **Volume:** 8 per cell.
- **Scoring:** 1–5 with weights.
- **Availability:** Score-only, flag-for-manual.
- **Wiring:** Canonical + Claude adapter + project pointer.
