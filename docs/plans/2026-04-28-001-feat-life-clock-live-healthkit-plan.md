---
title: Life Clock — Live HealthKit Integration
type: feat
status: active
date: 2026-04-28
origin: docs/products/life-clock/MVP_VS_FOUNDER_PACK_AUDIT_2026-04-28.md
---

# Life Clock — Live HealthKit Integration

## Overview

Replace `MockHealthKitService` with a real `LiveHealthKitService` that talks to `HKHealthStore`. Add the HealthKit entitlement, the `NSHealthShareUsageDescription` string, the progressive authorization flow during onboarding, and a manual quick-log surface on the Today screen so the founder pack's "log a habit" step is reachable. Distinguish "missing data" from "denied permission" using the inference heuristic (Apple deliberately hides read denials).

This unlocks 0/3 PRD acceptance criteria in **Health data import** and the founder pack's wedge — "Today's habits moved your Life Clock by +X" — because v1 currently shows mock data, which is theatre.

## Scope

**In:**
- HealthKit entitlement + `NSHealthShareUsageDescription` in `Info.plist`.
- `LiveHealthKitService: HealthKitServiceProtocol` using `HKStatisticsCollectionQuery` for cumulative quantities and `HKSampleQuery` for sleep categories.
- Progressive authorization triggered from the Onboarding "permission" step — no longer fake.
- "Connect Apple Health" button in Profile → Connected data, with "missing-data inference" status per type.
- Manual quick-log sheet (HabitLog input) reachable from Today screen.
- Pure-function aggregator (`HealthKitAggregator`) so tests don't need a simulator.
- Renaming `MockHealthKitService` → keep both, with a build-time switch via `LifeClockConfiguration` (mock for tests, live in app).

**Out (deferred):**
- `enableBackgroundDelivery` + `HKObserverQuery` for push-style updates. Skeleton uses pull-on-foreground only — `bootstrap()` re-fetches when the app returns to foreground.
- HealthKit *writes* (no `NSHealthUpdateUsageDescription`). v1 is read-only.
- HRV / VO2 Max / blood pressure / glucose. These are Tier-2 in `HEALTH_DATA_STRATEGY.md`.
- Deep-link to Settings on denial. v2 polish.

## Technical approach

### Entitlement & Info.plist

Add to `project.yml`:

```yaml
LifeClock:
  entitlements:
    path: LifeClock.entitlements
    properties:
      com.apple.developer.healthkit: true
      com.apple.developer.healthkit.access: []   # empty in v1; non-empty enables clinical records
  settings:
    base:
      CODE_SIGN_ENTITLEMENTS: LifeClock.entitlements
```

Add to `Info.plist`:

```xml
<key>NSHealthShareUsageDescription</key>
<string>Life Clock reads your steps, sleep, exercise, and resting heart rate from Apple Health to estimate how today's habits move your time trajectory. Your data stays on your device.</string>
```

Do **not** add `NSHealthUpdateUsageDescription` — we don't write.

### Service layer

```
Sources/Services/
├── HealthKitServiceProtocol.swift   (existing — extend with authorize / status methods)
├── MockHealthKitService.swift       (existing — gain a "denied" mode for testing)
├── LiveHealthKitService.swift       (NEW)
├── HealthKitAggregator.swift        (NEW — pure function, no HKHealthStore)
└── HealthKitConfiguration.swift     (NEW — chooses live vs mock based on env)
```

### Protocol expansion

```swift
protocol HealthKitServiceProtocol {
    var isHealthDataAvailable: Bool { get }
    func requestAuthorization() async throws
    func authorizationKnown(for tier: HealthDataTier) async -> Bool
    func dailySnapshot(for date: Date) async -> DailyHealthSnapshot?
    func recentSnapshots(endingAt: Date, count: Int) async -> [DailyHealthSnapshot]
}

enum HealthDataTier { case core }   // expand later: .advanced, .nutrition
```

`authorizationKnown(for:)` returns `true` once `requestAuthorization` has run for the tier — used by Profile to show "Available" vs "Not configured", **not** "Connected" vs "Denied" (because we cannot know the latter for reads).

### Live service implementation

```swift
@MainActor
final class LiveHealthKitService: HealthKitServiceProtocol {
    private let store = HKHealthStore()
    private let calendar: Calendar
    private let coreReadTypes: Set<HKObjectType>
    private let asleepValues: Set<Int>
    @ObservationIgnored private var hasRequestedCore = false   // persisted via UserDefaults

    var isHealthDataAvailable: Bool { HKHealthStore.isHealthDataAvailable() }

    func requestAuthorization() async throws {
        guard isHealthDataAvailable else { throw HealthKitError.unavailable }
        try await store.requestAuthorization(toShare: [], read: coreReadTypes)
        hasRequestedCore = true
        UserDefaults.standard.set(true, forKey: "lc.hk.requestedCore")
    }

    func dailySnapshot(for date: Date) async -> DailyHealthSnapshot? {
        // Run statistics queries for steps, exercise minutes, active energy.
        // Run sample query for sleep, bucket by wake day.
        // Run discrete-average for resting HR, weight.
        // Compose -> HealthKitAggregator.aggregate(...)
    }
}
```

### Aggregator (pure, testable)

```swift
struct HealthKitAggregator {
    static func aggregate(
        date: Date,
        steps: Double?,
        exerciseMinutes: Double?,
        activeEnergyKcal: Double?,
        sleepHours: Double?,
        restingHeartRate: Int?,
        weightKg: Double?,
        sourceCompleteness: Double
    ) -> DailyHealthSnapshot { ... }
}
```

This is the only piece that engine tests should touch.

### Onboarding flow change

Replace `permissionEducationScreen` with a real "Connect Apple Health" screen that calls `requestAuthorization()` on tap. Failures (e.g., simulator without Health.app) fall through gracefully — onboarding completes; the Today screen shows the missing-data low-confidence state.

### Profile screen change

`Connected data` section becomes data-driven:
- If `authorizationKnown == false` → row reads "Not configured" with a "Connect" button.
- If `authorizationKnown == true` AND last-fetched snapshot has the field → "Available".
- If `authorizationKnown == true` AND no data found in 90-day window → "No data — open Settings → Health to enable".

We never claim "Connected" or "Denied".

### Manual quick-log sheet

Today screen's `quick log` button (currently absent) opens a sheet:

```
Sources/Features/QuickLog/
└── QuickLogSheet.swift
```

Captures: alcohol level, smoking, diet quality, stress, strength training. Persists via the store as a new `HabitLog` for today's date. Recomputes today's delta on dismiss.

### Configuration switch

```swift
enum HealthKitConfiguration {
    static func service() -> HealthKitServiceProtocol {
        #if DEBUG
        if ProcessInfo.processInfo.environment["LIFECLOCK_USE_MOCK_HEALTH"] == "1" {
            return MockHealthKitService()
        }
        #endif
        return LiveHealthKitService()
    }
}
```

`LifeClockApp` calls `HealthKitConfiguration.service()` when constructing the store.

## Acceptance criteria

- [ ] HealthKit entitlement declared; `NSHealthShareUsageDescription` in `Info.plist`; **no** `NSHealthUpdateUsageDescription`.
- [ ] `LiveHealthKitService` implements the protocol; `MockHealthKitService` retained for tests.
- [ ] Onboarding "permission" screen calls `requestAuthorization()` and proceeds gracefully on denial/cancel.
- [ ] Profile screen shows per-source state derived from real authorization + missing-data inference, never "Connected" or "Denied".
- [ ] Today screen has a quick-log button that opens `QuickLogSheet`; submitting recomputes today's delta.
- [ ] `HealthKitAggregator.aggregate(...)` is a pure function, fully unit-tested without `HKHealthStore`.
- [ ] CI grep gates remain clean: no `Date()` in `Sources/Engines/`, no medical-claim copy.
- [ ] No `HKHealthStore` is referenced in tests (only `HealthKitAggregator` + `MockHealthKitService`).
- [ ] All existing tests still pass.

## Risks

- **Silent read denials:** addressed by protocol-level `authorizationKnown` returning whether we *asked*, plus 90-day inference for "no data" rendering. Profile UX is conservative.
- **Sleep bucketing:** wake-day attribution can be wrong for naps; out of scope for v1, documented in code.
- **Threading:** `requestAuthorization` must call from `@MainActor`. `LiveHealthKitService` is annotated.
- **Simulator gap:** Live service works on simulator only if user manually seeds Health.app data. The `LIFECLOCK_USE_MOCK_HEALTH=1` env var falls back to mock for development without seeding.

## Out of scope this plan

- Persistence (separate plan — todays' snapshot still re-computes on cold start)
- StoreKit / paywall
- Background delivery
- Brand-name resolution
