---
status: pending
priority: p3
issue_id: "039"
tags: [code-review, life-clock, ios, simplicity, wrap-up-coordinator]
dependencies: []
---

# Optional simplification pass on `WrapUpCoordinator`

## Problem Statement

Simplicity reviewer flagged three minor cuts that would trim ~10% LOC without changing behavior. None are blocking.

## Findings

From the simplicity review:

1. **`dayKey(_:)` on `EngineClock` is unused in production** — only used in one test assertion. Replace the test assertion with `cal.isDate(date, inSameDayAs: yesterday)` and delete the helper.
2. **`pendingYesterday`/`pendingWeekly` private helpers are over-decomposed** — each called once from a 100-line file. Inline both into `pendingWrapUp`.
3. **Three reinstall-guard tests overlap** — `testReturnsNilWhenOnboardingDateMissing`, `testReturnsNilWhenOnboardedToday`, `testReturnsNilWhenOnboardedYesterday` all exercise the same branch. Keep boundary case + `onboardedTwoDaysAgo` (the positive case). Drop the other two.

**Counter-argument**: `dayKey` may become useful in Phase 1b when wiring `lastShownYesterdayWrapUpDay` to an actual UserProfile field; the helpers document intent at a glance; the redundant tests pin different framings of the same condition cheaply.

## Proposed Solutions

1. **Apply all three cuts** as part of the next iteration. Effort: Small.
2. **Defer until Phase 1b** when usage of `dayKey` is decided (recommended). The other two cuts are ~stylistic.

## Recommended Action

(Triage — these are stylistic; not blocking merge or Phase 1b.)

## Technical Details

- Files: `products/life-clock-ios/Sources/Engines/EngineClock.swift`, `products/life-clock-ios/Sources/Engines/WrapUpCoordinator.swift`, `products/life-clock-ios/Tests/WrapUpCoordinatorTests.swift`.

## Acceptance Criteria

- [ ] `dayKey` either kept with at least one production caller, or removed.
- [ ] Either inlining decision documented or applied.
- [ ] Test count rationale documented.

## Work Log

(empty)

## Resources

- PR: https://github.com/kashane1/ai-company-os/pull/18
