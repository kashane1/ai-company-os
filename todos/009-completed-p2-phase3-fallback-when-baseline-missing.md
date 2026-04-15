---
status: completed
priority: p2
issue_id: "009"
tags: [code-review, flow-completeness, ecc-gap-plan]
dependencies: []
---

# Problem Statement

The ECC gap plan's Phase 3 `verification-loop` composes three sub-checks including `skill_stocktake.run()` and (deferred) `context_budget.run()`. But if Phase 2b ships broken, or the baseline JSON under `state/benchmarks/skill-estate/` is missing or stale, Phase 3 has no specified fallback. The current "fail-closed wrapper" pattern from `release_readiness.py:107-154` translates a missing input into a hard-fail verdict, but missing context-budget baselines should be a soft-skip, not a hard fail.

## Findings

Spec-flow-analyzer flow-gap #1:
> "Phase 3 never states what happens if Phase 2b lands broken or `<date>-baseline.json` is missing at Phase 3 time. Phase 3 sub-check (3) depends on `packages/policies/testing.py` which is itself unshipped. Add a Phase 3 precondition: if `context-budget` baseline JSON absent or stale > 7 days, verification-loop runs without it and records `context_budget: skipped` in the report — never errors."

## Proposed Solutions

### Option 1: Sub-check skip semantics with explicit `skipped` state

Each sub-check returns one of `{ok, warn, fail, skipped}` — not just `{ok, warn, fail}`. `skipped` is set when input is absent, stale, or the sub-check's dependency is unshipped. Aggregator rule: `skipped` never affects the verdict; reported as metadata only.

Pros:
- Explicit skip is self-documenting
- Tolerates Phase 2b being broken or deferred
- Extends naturally when new sub-checks land

Cons:
- Adds a verdict state to the aggregator contract

Effort: small
Risk: low

### Option 2: Defer context-budget composition until Phase 2b baseline stable

Don't compose context-budget into verification-loop at all until the baseline has 7 consecutive days of clean runs.

Pros:
- Avoids the failure mode entirely

Cons:
- Delays full verification-loop coverage by weeks
- Deferral logic needs its own tracking

Effort: trivial
Risk: low

## Recommended Action

Option 1. Add `skipped` to the severity enum in the verification-loop contract. Update the composition pseudocode in the canonical body and the aggregator rule in `packages/policies/verification_loop.py`.

## Acceptance Criteria

- [ ] `verification-loop` contract.yaml includes `skipped` as a sub-check severity
- [ ] Aggregator rule: `skipped` sub-checks produce `skipped: true` entries in the report, never affect verdict
- [ ] Fixture `boundary_baseline_missing.yaml` asserts a context-budget baseline absent → sub-check reports `skipped`, overall verdict stays `pass`
- [ ] Plan document updated: Phase 3 deliverables mention the skip path

## Work Log

### 2026-04-15 - Captured during technical review
**By:** Claude (review workflow)
