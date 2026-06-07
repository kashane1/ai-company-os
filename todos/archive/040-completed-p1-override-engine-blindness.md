---
status: complete
priority: p1
issue_id: "040"
tags: [code-review, life-clock, ios, overrides, engine]
dependencies: []
---

# P1: Engine ignored overrides — entire override flow was cosmetic

## Problem Statement

`ClockEngine.calculateDailyDelta` reads `snapshot.stepCount`, `snapshot.sleepHours` etc. directly. The previous `OverrideService.applyOverride` only wrote to `overridesData` (the encoded blob) — the raw HK fields stayed unchanged, so the engine never saw the corrected value and the score never moved when a user adjusted a metric.

## Findings

Spec-flow review of PR #18 last commit: "`LifeClockStore.applyOverride` calls `recomputeYesterdayDelta`, but `ClockEngine.calculateDailyDelta` reads `snapshot.stepCount`/`sleepHours` directly (lines 105, 128 of `ClockEngine.swift`) — NOT `effectiveValue(for:)`. The override only changes `overridesData`, never the raw fields the engine reads. So the score does not actually change after an override."

## Resolution Applied

`OverrideService.applyOverride` now calls `assignRawValue(value, for:, on:)` to write the override value through to the raw HK field. The engine reads raw → sees the corrected value → produces a corrected score. Original HK value is captured in `originalHealthKitValuesData` for revert; revert restores the raw field from the captured original.

The override-aware persister in `LifeClockStore.persistSnapshot` already protects the raw field from being clobbered by subsequent HK refreshes.

Pinned by two new tests in `OverrideServiceTests`:
- `testApplyOverrideWritesThroughToRawFieldSoEngineSeesIt`
- `testRevertRestoresEngineVisibleValue`

## Files

- `products/life-clock-ios/Sources/Services/OverrideService.swift`
- `products/life-clock-ios/Tests/OverrideServiceTests.swift`
