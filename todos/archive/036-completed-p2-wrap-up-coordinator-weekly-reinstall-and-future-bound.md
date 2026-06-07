---
status: pending
priority: p2
issue_id: "036"
tags: [code-review, life-clock, ios, wrap-up-coordinator, edge-cases]
dependencies: []
---

# Weekly wrap-up: apply reinstall guard + bound stale/future `weekStart`

## Problem Statement

`WrapUpCoordinator.pendingWeekly` has two correctness gaps:

1. **No reinstall guard.** A user who onboards on a Sunday morning could see a weekly wrap-up that same day for `weekStart == today` — they have not lived through any past week with the app. The yesterday path correctly enforces "lived through ≥1 full local day post-onboarding"; weekly does not.
2. **No recency bound on `mostRecentWeekStart`.** `weeks.map({ cal.startOfDay(for: $0.weekStart) }).max()` returns whatever the caller provides. If `weeks` contains only future-dated entries (clock skew, restored backup), `.max()` returns a future `weekStart` and the coordinator fires `.weekly` for a week that has not occurred. Likely a real bug.

## Findings

- Architecture review (PR #18, item 3): "`pendingWeekly` ignores reinstall guard. A user who onboards on a Sunday morning could see a weekly wrap-up that same day."
- Architecture review (PR #18, item 4): "Weekly `mostRecentWeekStart` has no recency bound. If the most recent `WeekSnapshot` is months old (long absence), it still fires."
- Spec-flow analysis: "`weeks` with only future entries causes weekly to fire."

## Proposed Solutions

1. **Add the `onboardedDay + 2` reinstall guard to `pendingWeekly`** AND **clamp `mostRecentWeekStart` to `<= today` and `>= today - 14d`** (recommended). Two small filters at the top of `pendingWeekly`. Effort: Small.
2. **Push the recency bound onto the caller.** Caller pre-filters `weeks`. Cheaper here but spreads the invariant. Less safe.

## Recommended Action

(Triage)

## Technical Details

- File: `products/life-clock-ios/Sources/Engines/WrapUpCoordinator.swift` (`pendingWeekly`, lines ~104-128)
- New tests:
  - Onboarded today, weekly weekStart == today → nil
  - `weeks` contains only future entries → nil
  - `weeks` most recent is > 14 days old → nil

## Acceptance Criteria

- [ ] Reinstall guard active on weekly path (mirror yesterday path).
- [ ] Future `weekStart` entries cannot trigger a weekly wrap-up.
- [ ] Stale `weekStart` (> 14 days) cannot trigger a weekly wrap-up.
- [ ] Three new tests added and passing.

## Work Log

(empty)

## Resources

- PR: https://github.com/kashane1/ai-company-os/pull/18
