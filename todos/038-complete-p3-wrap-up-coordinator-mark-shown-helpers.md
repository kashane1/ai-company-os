---
status: pending
priority: p3
issue_id: "038"
tags: [code-review, life-clock, ios, wrap-up-coordinator, ergonomics]
dependencies: []
---

# Add `markYesterdayShown` / `markWeeklyShown` helpers

## Problem Statement

After presentation, callers need to atomically advance `lastShownYesterdayWrapUpDay` (or weekly equivalent). Leaving this to each call site risks divergent implementations of the day-key write.

## Findings

Architecture review (PR #18, item 5): "Missing for Phase 1b: no `markShown(...)` helper to atomically advance `lastShown*` after presentation — leaving that to the caller risks each call site re-implementing the day-key write."

## Proposed Solutions

1. **Add static methods returning a new `ProfileSnapshot`** with the appropriate field set (recommended). Pure, testable, mirrors the rest of the engine.
   ```swift
   static func markYesterdayShown(profile: ProfileSnapshot, now: Date) -> ProfileSnapshot
   static func markWeeklyShown(profile: ProfileSnapshot, weekStart: Date) -> ProfileSnapshot
   ```
   Caller persists the returned snapshot. Effort: Small.
2. **Defer to Phase 1b** when the actual SwiftData call site lands.

## Recommended Action

(Triage — could do now or wait for Phase 1b. Defending to 1b if it lands within a week.)

## Technical Details

- File: `products/life-clock-ios/Sources/Engines/WrapUpCoordinator.swift`

## Acceptance Criteria

- [ ] Two helpers added (or explicit decision to defer).
- [ ] Tests cover round-trip: pendingWrapUp returns yesterday → markYesterdayShown → pendingWrapUp returns nil.

## Work Log

(empty)

## Resources

- PR: https://github.com/kashane1/ai-company-os/pull/18
