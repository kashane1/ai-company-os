---
status: completed
priority: p2
issue_id: "023"
tags: [code-review, life-clock, ios, info-plist, swift-concurrency]
dependencies: []
---

# Problem Statement

Two unrelated but cheap fixes that the skeleton inherits.

## Findings

1. **`UIRequiredDeviceCapabilities` declares `armv7`** in `products/life-clock-ios/Info.plist:30`. iOS 17 deployment target is 64-bit only — `armv7` is wrong and will either be silently ignored or surface an App Review note. Should be `arm64` or omitted entirely (the App Store handles 64-bit requirements).

2. **`LifeClockStore` is `@Observable` but not `@MainActor`.** It mutates UI-bound properties from `bootstrap()` after `await healthService.dailySnapshot(...)`. Under Swift 6 strict concurrency this becomes a warning or error. After Plans correctly marks its store `@MainActor` (see `products/after-plans-ios/Sources/App/AfterPlansStore.swift`).

## Proposed Solutions

### Option 1: Apply both fixes now

- Remove the `UIRequiredDeviceCapabilities` block, or replace `armv7` with `arm64`.
- Annotate `LifeClockStore` as `@MainActor`. Tests already use `@MainActor` (`LifeClockStoreTests`).

Pros:
- Both are one-line changes with zero behavioral risk.
- Aligns with After Plans pattern.

Cons:
- None.

Effort: trivial
Risk: low

## Recommended Action

(Filled during triage.)

## Acceptance Criteria

- [ ] `Info.plist` does not declare `armv7`.
- [ ] `LifeClockStore` is annotated `@MainActor`.
- [ ] `xcodebuild` still passes; tests still pass.

## Work Log

- 2026-04-27: Created from PR #14 security + architecture reviews.

## Resources

- PR: https://github.com/kashane1/ai-company-os/pull/14
- Reference: `products/after-plans-ios/Sources/App/AfterPlansStore.swift`
