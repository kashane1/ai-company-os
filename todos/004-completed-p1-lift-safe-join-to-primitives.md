---
status: completed
priority: p1
issue_id: "004"
tags: [code-review, architecture, python, ecc-gap-plan, primitives]
dependencies: []
---

# Problem Statement

The ECC gap plan at [docs/plans/2026-04-15-feat-ecc-gap-recommendations-plan.md](/Users/simons/ai-company-os/docs/plans/2026-04-15-feat-ecc-gap-recommendations-plan.md) tells Phase 2 primitives to "reuse the existing `_ADAPTER_PATH_PATTERN` regex from `loader.py:42`" for its path-traversal guard, but the [primitives subpackage ADR](/Users/simons/ai-company-os/docs/adr/2026-04-14-primitives-subpackage.md) forbids primitives importing from `packages/tools/skills/` to avoid circular imports. The helper currently has no legal home.

## Findings

- Path-traversal guard is flagged as mandatory by security-sentinel and performance-oracle reviewers (Phase 2 deepening findings).
- `_ADAPTER_PATH_PATTERN` is a private module-level constant in [packages/tools/skills/loader.py:42](/Users/simons/ai-company-os/packages/tools/skills/loader.py:42).
- Architecture-strategist second pass: plan violates the ADR boundary by telling primitives to reuse a helper from the skills subpackage.
- Kieran python review second pass: the helper must live in the primitives tree and `loader.py` must import *from* primitives, inverting the dependency cleanly.

## Proposed Solutions

### Option 1: Create `packages/tools/primitives/_safe_paths.py` and invert the dependency

Move `_ADAPTER_PATH_PATTERN` and a new `safe_join(root: Path, relpath: str) -> Path` helper into a new module under the primitives subpackage. Refactor [loader.py](/Users/simons/ai-company-os/packages/tools/skills/loader.py) to import the pattern from there instead of owning it.

Pros:
- Eliminates the regex duplication at the source
- Primitives stay ADR-compliant
- `registry_drift.py` and `context_budget.py` can import it cleanly
- Sets the precedent for future path-safety helpers

Cons:
- Touches a Hermes-Phase-0 file (`loader.py`) in a non-Hermes PR
- Requires running the Hermes Phase 0 loader test suite on the refactor

Effort: small
Risk: low (mechanical refactor, well-covered by existing loader tests)

### Option 2: Duplicate the regex into the primitive

Copy `_ADAPTER_PATH_PATTERN` verbatim into `packages/tools/primitives/_safe_paths.py` and leave `loader.py` alone.

Pros:
- Zero risk to existing loader behavior
- No cross-subpackage refactor

Cons:
- Two sources of truth for the same path contract
- Drift potential when one side gets a rule the other doesn't
- Pattern-recognition reviewer would flag it

Effort: trivial
Risk: medium (drift over time)

## Recommended Action

Option 1. Add the refactor as an explicit deliverable in Phase 2a (before `skill-stocktake` lands), not in Phase 0, so the change is scoped with its first consumer.

## Technical Details

- New file: `packages/tools/primitives/_safe_paths.py`
- Modified: `packages/tools/skills/loader.py` (import from primitives)
- Test: existing loader test suite must pass unchanged

## Acceptance Criteria

- [ ] `_ADAPTER_PATH_PATTERN` and `safe_join()` live in `packages/tools/primitives/_safe_paths.py`
- [ ] `loader.py` imports the pattern from primitives, does not own it
- [ ] Existing loader path-traversal tests pass unchanged
- [ ] `tests/python/unit/test_primitives_conventions.py` passes for the new module
- [ ] Plan document updated to cite the new path instead of "reuse from loader.py"

## Work Log

### 2026-04-15 - Captured during technical review
**By:** Claude (review workflow)
**Actions:** Synthesized architecture-strategist and kieran-python-reviewer findings from the second-pass review.
