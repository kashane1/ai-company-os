---
status: pending
priority: p2
issue_id: "035"
tags: [code-review, life-clock, ios, locale, wrap-up-coordinator]
dependencies: []
---

# Pin `firstWeekday` explicitly OR add a Monday-locale weekly test

## Problem Statement

`WrapUpCoordinator.pendingWeekly` reads `cal.firstWeekday` to decide if today is the week-start day. `EngineClock.live` builds a `Calendar` with `Calendar.current` (`Calendar(identifier: .gregorian)` + `TimeZone.current`), so `firstWeekday` follows the device locale at runtime — Sunday in US, Monday in much of Europe. `EngineClock.fixed` pins UTC and uses Gregorian (`firstWeekday == 1` / Sunday) by default. The current weekly tests pass on Sunday-locale CI but a developer in a Monday-locale environment will see the test pin Sunday while prod fires on Monday.

## Findings

- Architecture review (PR #18): "Weekly tests pass on US-locale CI but a developer in Germany running `EngineClock.live` will get Monday weeks while tests pin Sunday."
- This is a silent test/prod divergence: the test passes for the wrong reason on US locales and would fail on EU locales without anyone editing code.

## Proposed Solutions

1. **Pin `firstWeekday` in `WrapUpCoordinator` via a config / configurable constant** (recommended). Wrap-up scheduling is a product decision (e.g. "weekly summary always lands Monday morning"), not a locale decision. Add a `WrapUpCoordinator.Config(firstWeekday: Int = 2 /* Monday */)` and consult it instead of `cal.firstWeekday`. Effort: Small.
2. **Document the locale dependency and add a Monday-locale test.** Construct an `EngineClock` with a `Calendar` whose `firstWeekday = 2` and verify weekly fires on Monday. Effort: Small. Less safe — the coupling remains.
3. **Default `EngineClock.live` to `firstWeekday = 2` regardless of locale.** Aggressive — affects any other engine reading the calendar.

## Recommended Action

(Triage)

## Technical Details

- File: `products/life-clock-ios/Sources/Engines/WrapUpCoordinator.swift` (`pendingWeekly`, line ~109)
- File: `products/life-clock-ios/Sources/Engines/EngineClock.swift`

## Acceptance Criteria

- [ ] Weekly wrap-up day-of-week is fully deterministic across locales.
- [ ] Test covers at least one non-US-default locale.
- [ ] Documented in `WrapUpCoordinator` doc comment.

## Work Log

(empty)

## Resources

- PR: https://github.com/kashane1/ai-company-os/pull/18
