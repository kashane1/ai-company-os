---
status: pending
priority: p3
issue_id: "037"
tags: [code-review, life-clock, ios, testing, wrap-up-coordinator]
dependencies: ["035"]
---

# Add edge-case tests to `WrapUpCoordinatorTests`

## Problem Statement

The 12 tests cover the main decision branches but miss specific edge cases that the spec-flow analyzer identified.

## Findings

Spec-flow analysis flagged these missing cases:

- **DST spring-forward**: `cal.date(byAdding: .day, value: -1, to: today)` and `value: 2` arithmetic — needs a test pinned to America/Los_Angeles around 2026-03-08 to confirm `today < earliestEligibleToday` doesn't off-by-one.
- **Future `onboardedAt`** (clock skew / restored backup): the guard correctly returns nil, but no regression test pins this.
- **Empty `snapshots` array**: implicit but untested.
- **`lastShownYesterdayWrapUpDay` set to a future date**: `lastDay >= today` correctly suppresses but worth pinning.

(`firstWeekday != 1` and future-week tests are covered by todos #035 and #036.)

## Proposed Solutions

1. **Add 4 tests** mirroring the existing pattern. Each ~15 lines. Effort: Small.

## Recommended Action

(Triage)

## Technical Details

- File: `products/life-clock-ios/Tests/WrapUpCoordinatorTests.swift`
- DST test needs a non-UTC `EngineClock` — may require adding `EngineClock.fixed(_:tz:)` or testing the pure `Calendar` math in isolation.

## Acceptance Criteria

- [ ] DST spring-forward test added and passing.
- [ ] Future `onboardedAt` test added and passing.
- [ ] Empty `snapshots` test added and passing.
- [ ] Future `lastShownYesterdayWrapUpDay` test added and passing.

## Work Log

(empty)

## Resources

- PR: https://github.com/kashane1/ai-company-os/pull/18
