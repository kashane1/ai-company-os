---
title: Life Clock — StoreKit 2 Paywall
type: feat
status: active
date: 2026-04-28
origin: docs/products/life-clock/MVP_VS_FOUNDER_PACK_AUDIT_2026-04-28.md
---

# Life Clock — StoreKit 2 Paywall

## Overview

Add the v1 monetization layer: three subscription products (monthly, annual, lifetime) via StoreKit 2, an entitlement-aware `SubscriptionStore`, a `PaywallSheet`, and feature gating that respects `MONETIZATION.md`. Local-test via a `Products.storekit` configuration file so the paywall renders on simulator without ASC.

This unblocks the four PRD acceptance criteria in **Paywall** and the Roadmap Phase 1 paywall feature.

## Scope

**In:**
- Three products: `com.life-clock.pro.monthly`, `com.life-clock.pro.annual`, `com.life-clock.pro.lifetime`. Annual + monthly in one Subscription Group; lifetime non-consumable.
- `SubscriptionStore: @Observable @MainActor` with `Transaction.updates` listener started in `init` (before any UI render), `currentEntitlements` refresh on launch, `tx.finish()` on every verified transaction.
- `Products.storekit` configuration file for local testing — paywall renders fully on simulator.
- `PaywallSheet` showing all three tiers, annual pre-selected, restore button, Terms/Privacy links, "auto-renews unless cancelled" disclosure.
- One feature gate to demonstrate the pattern: **Weekly Report** is preview-only for free; full report behind paywall after the user taps "See full week".
- Profile "Restore purchases" becomes real (`AppStore.sync()`).
- Tests with `SKTestSession` covering purchase → entitlement, restore, refund.

**Out (deferred):**
- Tone-mode gating (founder pack lists this as Pro). Skipping in v1 because tone is core to the emotional-safety contract — paywalling it conflicts with the founder pack's "no doom default" rule. Revisit after retention data.
- Trial flows. The pack says "7-day on annual if app has enough immediate value" — we don't yet. Land later.
- Custom quests, advanced HK metrics, widgets gating. Those features don't exist yet; gating ungrown surface is YAGNI.
- Family-sharing intricacies and ask-to-buy edge cases beyond what `Transaction.updates` already handles.
- Offer codes / promotional offers.

## Technical approach

### Layout

```
Sources/Services/
├── PaywallProductID.swift           (NEW — typed product IDs)
├── SubscriptionStore.swift          (NEW — @Observable @MainActor)
└── Products.storekit                (NEW — local test config)

Sources/Features/Paywall/
└── PaywallSheet.swift               (NEW)

Sources/Features/WeeklyReport/
└── WeeklyReportView.swift           (modified — preview-vs-full gate)

Sources/Features/Profile/
└── ProfileView.swift                (modified — wire real Restore Purchases)

Sources/App/
└── LifeClockApp.swift               (modified — inject SubscriptionStore)

Tests/
└── SubscriptionStoreTests.swift     (NEW — SKTestSession)
```

### Product IDs

```swift
enum PaywallProductID: String, CaseIterable {
    case monthly  = "com.life-clock.pro.monthly"
    case annual   = "com.life-clock.pro.annual"
    case lifetime = "com.life-clock.pro.lifetime"
}
```

### SubscriptionStore

```swift
@MainActor @Observable
final class SubscriptionStore {
    private(set) var products: [Product] = []
    private(set) var entitledProductIDs: Set<String> = []
    private(set) var purchaseInFlight: Bool = false
    private(set) var lastError: String?
    private var updatesTask: Task<Void, Never>?

    var isPro: Bool { !entitledProductIDs.isEmpty }

    init() {
        // Listener must start before any UI renders so we don't miss
        // transactions delivered at launch (e.g., after reinstall).
        updatesTask = Task.detached { [weak self] in
            for await result in Transaction.updates {
                await self?.handle(result)
            }
        }
    }

    deinit { updatesTask?.cancel() }

    func loadProducts() async { ... }
    func purchase(_ product: Product) async { ... }
    func restore() async { try? await AppStore.sync(); await refreshEntitlements() }
    func refreshEntitlements() async { ... }
    private func handle(_ result: VerificationResult<Transaction>) async { ... }
}
```

### App wiring

`LifeClockApp.init` constructs both stores and injects each:

```swift
@State private var lifeClockStore: LifeClockStore
@State private var subscriptionStore = SubscriptionStore()

var body: some Scene {
    WindowGroup {
        RootView()
            .environment(lifeClockStore)
            .environment(subscriptionStore)
            .task {
                await lifeClockStore.bootstrap()
                await subscriptionStore.loadProducts()
                await subscriptionStore.refreshEntitlements()
            }
    }
    .modelContainer(container)
}
```

### Feature gate

```swift
// In WeeklyReportView
if subscriptionStore.isPro {
    fullReportView
} else {
    weeklyPreviewView
    Button("See full week") { paywallPresented = true }
        .buttonStyle(.borderedProminent)
}
```

The preview shows the net delta number only — full report (drivers, lever, confidence) is gated.

### Paywall UX checklist (App Review)

- [x] Each tier shows price + billing period (`product.displayPrice` + period label)
- [x] Subscriptions show "Auto-renews unless cancelled in iOS Settings"
- [x] Restore Purchases button visible
- [x] Terms of Use link (Apple's standard EULA URL acceptable)
- [x] Privacy Policy link (in-app or web URL)
- [x] No misleading copy

### Testing strategy

`SKTestSession` for in-process tests:

```swift
final class SubscriptionStoreTests: XCTestCase {
    var session: SKTestSession!

    override func setUp() async throws {
        session = try SKTestSession(configurationFileNamed: "Products")
        session.resetToDefaultState()
        session.disableDialogs = true
        session.clearTransactions()
    }

    @MainActor func test_purchase_grants_pro() async throws { ... }
    @MainActor func test_restore_recovers_entitlement() async throws { ... }
    @MainActor func test_refund_revokes_entitlement() async throws { ... }
}
```

## Acceptance criteria

- [ ] Three products configured in `Products.storekit`.
- [ ] `SubscriptionStore.isPro` reflects actual `currentEntitlements`, not a local cache.
- [ ] `Transaction.updates` listener starts in `init`, persists for app lifetime, and finishes every verified transaction.
- [ ] Paywall shows price, period, restore, ToS, Privacy.
- [ ] Weekly Report shows preview to free users + full report to Pro.
- [ ] Profile "Restore purchases" calls `AppStore.sync()` and refreshes entitlements.
- [ ] No paywall presents on launch; only on user-initiated intent.
- [ ] Tests cover purchase + restore (refund test optional given SKTestSession quirks).
- [ ] CI grep gates remain clean.

## Risks

- **Product IDs differ between local config and ASC.** Local IDs are test-only. The same IDs must be configured in App Store Connect before submission. Capture a checklist item in `PHASE_STATUS.md`.
- **`Transaction.updates` is `AsyncSequence` of `VerificationResult<Transaction>`.** `.unverified` results must not grant entitlement. The `handle` method only acts on `.verified`.
- **`AppStore.sync()` triggers a password prompt.** Only call from explicit user tap (the Profile button), never on launch.
- **Gating Weekly Report risks the founder pack's "weekly report is the retention hook" stance.** Mitigation: free users see the *number* (the hook), only the breakdown is gated. The paywall trigger ("See full week") is a known good conversion moment per `MONETIZATION.md` § paywall timing #3.
