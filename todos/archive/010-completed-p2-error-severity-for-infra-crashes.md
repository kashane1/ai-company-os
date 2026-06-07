---
status: completed
priority: p2
issue_id: "010"
tags: [code-review, flow-completeness, verification-loop, ecc-gap-plan]
dependencies: []
---

# Problem Statement

The ECC gap plan's Phase 3 canonical body declares a three-severity model `{info, warn, fail}` for verification-loop sub-checks and says "fail-closed wrapper" converts sub-check exceptions into fail verdicts. But this conflates a platform bug (stocktake crashing mid-walk) with a real drift signal (stocktake finding orphan files). An operator seeing `hard_fail` can't tell whether they need to fix drift or file a bug report.

## Findings

Spec-flow-analyzer flow-gap #3:
> "Fail-closed wrapper is ambiguous: does a crashed `skill_stocktake.run()` produce `verdict: hard_fail`, `unknown`, or a soft-fail with a `CRASHED` severity? The three-severity model defines `info|warn|fail`, no `unknown`/`error` state. A caught exception in sub-check #2 silently maps to `fail` and the operator gets `hard_fail` on a platform bug, not a drift signal."

## Proposed Solutions

### Option 1: Add a fourth severity `error` with soft-fail mapping

Extend the severity enum to `{info, warn, fail, error}`. `error` means "sub-check crashed or returned malformed output". Aggregator rule: any `error` → overall verdict `soft_fail` with explicit `infra_errors: list[str]` field. Never propagates to `hard_fail`.

Pros:
- Clear distinction between drift and platform bugs
- Soft-fail ensures operator sees the error without blocking CI
- Matches Danger.js / reviewdog severity conventions

Cons:
- One more enum value

Effort: trivial
Risk: low

### Option 2: Raise platform bugs as exceptions, not verdicts

Let the sub-check exception bubble up. `verification-loop` doesn't produce a verdict at all — the caller sees an unhandled exception and knows it's a platform bug.

Pros:
- No new severity state

Cons:
- Exceptions in one sub-check mask drift from others (fail-fast by accident)
- Breaks the "run all, report all" convention from the best-practices pass

Effort: trivial
Risk: medium

## Recommended Action

Option 1. Add the fourth severity and update the aggregator contract.

## Acceptance Criteria

- [ ] Severity enum is `{info, warn, fail, error}` in the verification-loop contract
- [ ] Aggregator rule: `error → soft_fail` with `infra_errors: list[str]`; never hard_fail
- [ ] Fixture `adversarial_subcheck_crashes.yaml` simulates a stocktake crash, asserts `verdict == "soft_fail"` and `infra_errors` non-empty
- [ ] Plan canonical body documents the four-severity model explicitly
- [ ] `packages/policies/verification_loop.py` `_run_sub_check` helper traps exceptions and converts to `error` severity

## Work Log

### 2026-04-15 - Captured during technical review
**By:** Claude (review workflow)
