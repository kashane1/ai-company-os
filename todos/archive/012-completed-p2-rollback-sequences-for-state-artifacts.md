---
status: completed
priority: p2
issue_id: "012"
tags: [code-review, rollback, ecc-gap-plan]
dependencies: []
---

# Problem Statement

The ECC gap plan's Phase 3 Rollback section says `git revert -m 1 <phase3-sha>` is clean because verification-loop is net-additive. But `state/` is not tracked by git. If Phase 3 lands → writes `state/artifacts/verification-loop/smoke-*/report.json` during DoD smoke + Phase 4 baseline → then gets reverted, the stale reports stay on disk and will confuse a future re-land. The Phase 2 CI-wallclock-overage revert path is also underspecified — "reverts" is stated without naming what exactly gets rolled back.

## Findings

- Spec-flow-analyzer flow-gap #6: "`git revert -m 1 <sha>` leaves stale `state/artifacts/` reports. Rollback sequence: `git revert -m 1 <sha>` + `rm -rf state/artifacts/verification-loop/ state/benchmarks/skill-estate/`. Both dirs are append-only snapshots with no cross-references, safe to purge."
- Spec-flow-analyzer flow-gap #9: "CI wallclock delta >2s triggers 'revert', but revert of what? The whole Phase 2a PR, or just the CI wiring step?"

## Proposed Solutions

### Option 1: Explicit per-phase rollback sequences with exact commands

Each phase's Rollback block gets the exact shell sequence:
- **Phase 2 (CI wallclock overage):** `git revert` the `.github/workflows/` pytest invocation step only; keep the validator modules + fixtures + unit tests (they run cheaply in isolation). Full PR revert only if the unit-test suite alone exceeds the delta.
- **Phase 3:** `git revert -m 1 <sha>` + `rm -rf state/artifacts/verification-loop/`. Both are append-only snapshots, no cross-references.
- **Phase 4:** `git revert -m 1 <sha>` + `rm state/benchmarks/ecc-gap-baseline.json` (or whatever filename). Also remove the gap-analysis appendix entry in the same revert.

Pros:
- Operators don't derive rollback under time pressure
- State-dir-cleanup is explicit per phase

Cons:
- More words in each phase section

Effort: trivial
Risk: low

## Recommended Action

Option 1. Update all three Rollback sections with explicit command sequences.

## Acceptance Criteria

- [ ] Phase 2 Rollback section names the CI-only revert path as the first step, full PR revert as fallback
- [ ] Phase 3 Rollback section includes `rm -rf state/artifacts/verification-loop/`
- [ ] Phase 4 Rollback section includes the exact baseline file path to remove + gap-analysis appendix revert
- [ ] Plan states that `state/benchmarks/skill-estate/` and `state/artifacts/verification-loop/` are append-only, no cross-references, safe to purge on rollback

## Work Log

### 2026-04-15 - Captured during technical review
**By:** Claude (review workflow)
