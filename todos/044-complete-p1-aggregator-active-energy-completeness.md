---
status: complete
priority: p1
issue_id: "044"
tags: [code-review, life-clock, ios, data-integrity, healthkit]
dependencies: []
---

# P1: aggregator silently dropped days with only activeEnergyKcal

## Problem

`HealthKitAggregator.computeCompleteness` scored 5 signals (steps, exercise, sleep, RHR, weight). The importer's filter `sourceCompleteness > 0` would silently drop any day where ONLY `activeEnergyKcal` was present — e.g. a day the user wore Apple Watch but didn't carry their phone, recorded an energy ring but no steps. Real user data lost without notice.

## Resolution

`computeCompleteness` now scores 6 signals (1/6 weight each), including `activeEnergyKcal`. `aggregate(...)` passes the value through. Existing tests updated; new `testCompletenessIncludesActiveEnergy` pins the behavior.

## Files

- `products/life-clock-ios/Sources/Services/HealthKitAggregator.swift`
- `products/life-clock-ios/Tests/HealthKitAggregatorTests.swift`
