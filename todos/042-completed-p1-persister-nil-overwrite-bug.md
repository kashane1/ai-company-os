---
status: complete
priority: p1
issue_id: "042"
tags: [code-review, life-clock, ios, data-integrity, persistence]
dependencies: []
---

# P1: persistSnapshot overwrote good raw values with nil from partial HK responses

## Problem Statement

`LifeClockStore.persistSnapshot` previously wrote HK fields to the existing snapshot unconditionally for non-overridden fields. If HealthKit returned `nil` for a field (transient — query timeout, sync glitch), the persister overwrote a previously-good raw value (e.g. yesterday's 8000 steps) with nil. Next render → empty card.

## Findings

Data-integrity review (P2): "If HK returns a partial response (e.g. `stepCount = nil` because the query timed out or HealthKit lost a sync), the persister overwrites a previously-good 5,000 steps with nil for any non-overridden field."

## Resolution Applied

`persistSnapshot` now guards every overridable AND non-overridable field assignment behind `if let v = snapshot.<field> { existing.<field> = v }`. Only `sourceCompleteness` is non-optional — that always updates so the card reflects the most recent fetch attempt's quality.

## Files

- `products/life-clock-ios/Sources/App/LifeClockStore.swift`
