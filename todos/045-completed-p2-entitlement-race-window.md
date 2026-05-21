---
status: complete
priority: p2
issue_id: "045"
tags: [code-review, life-clock, ios, ux, entitlements]
dependencies: []
---

# P2: entitlement source wired in .task — first-frame race window

## Problem

`store.entitlements = subscriptions` was set inside `.task`. View body and History row "Edit" buttons were tappable from frame 1. A Pro user could land in History → DayDetail → Override and tap Save before `.task` ran, hitting `entitlements?.isPro == true` → false (nil entitlements) → `.notEntitled` thrown. Confusing UX for paying users; potential refund/churn signal.

## Resolution

`SubscriptionStore` is constructed in `LifeClockApp.init` and assigned to `store.entitlements` BEFORE `_store = State(wrappedValue: store)`. First frame is already wired. The `.task` wire-up is gone.

## Files

- `products/life-clock-ios/Sources/App/LifeClockApp.swift`
