# Technical Architecture

> Source: Life Clock Founder Pack (2026-04-27). Updated 2026-05-13 to reflect post-onboarding rebuild (V1.2 → V1.7 schema, Future tab + `HealthspanEngine`, full Services inventory, Notifications constraints, iOS target pin).

## Recommended stack

- iOS 17+ deployment target (SwiftData floor; see iOS target subsection below)
- Swift 5
- SwiftUI
- SwiftData
- HealthKit
- StoreKit 2
- UserNotifications
- WidgetKit — **planned (v1.2)**, not in v1
- ActivityKit — only if a live quest/timer feature emerges
- App Intents — planned, not in v1
- Cloud backend — only after local MVP proves value

### iOS target

The app targets **iOS 17 / Swift 5**, pinned by `products/life-clock-ios/project.yml` (`deploymentTarget.iOS: "17.0"`, `SWIFT_VERSION: 5.0`). The floor is set by SwiftData, which is iOS 17 only. `TARGETED_DEVICE_FAMILY = "1,2"` (iPhone + iPad build-ships); the app is designed iPhone-first per vision Decided constraint. Mac Catalyst is disabled.

## Architecture stance

Local-first. Health data stays on device. Derived app data is persisted with SwiftData and explicitly does not iCloud-sync (`LifeClockContainer.swift`: `cloudKitDatabase: .none`, plus a runtime assertion that fails fast if CloudKit is reintroduced).

Current implementation:

- `LifeClockStore` (`Sources/App/LifeClockStore.swift`) is the app-level `@Observable` state coordinator, MainActor-bound, consumed via `.environment(store)` in `LifeClockApp`.
- `LifeClockSchemaV1` (`Sources/Models/LifeClockSchema.swift`) is a versioned SwiftData schema. Current `versionIdentifier = (1, 7, 0)`. V1.0 → V1.7 are all in-place additive bumps with `MigrationStage.stages = []`; the next non-additive change (rename / custom transform) forces a real `SchemaV2` split per WWDC25 Session 291 guidance.
- `HealthKitServiceProtocol` hides the live-vs-mock data source boundary. `LiveHealthKitService` is the production path; `MockHealthKitService` is wired for simulator / tests via `HealthKitConfiguration.service()`.
- `SubscriptionStore` (`Sources/Services/SubscriptionStore.swift`) is the single source of truth for Pro entitlement state; wired into `store.entitlements` in `LifeClockApp.init()`.
- `NotificationsService` schedules **local-only** daily reminders. There is no push backend.

### Honesty-in-permissions pattern

`HealthKitServiceProtocol` exposes `authorizationKnown` so the Profile copy can honestly read **"Not configured / Available / No data"** — never "Connected" or "Denied". A `UserDefaults` flag (`lc.hk.requestedCore`) records whether we've ever asked, so a never-asked state is distinguished from a denied state. This is a load-bearing privacy / trust decision and lives in code-doc-comments today; it's noted here so a tech-arch reader doesn't accidentally regress it.

## Core models

Live schema: `Sources/Models/LifeClockSchema.swift` (V1.7). **Treat that file as the source of truth** — inline field lists drift on every schema bump. The schema currently includes:

- `UserProfile` — identity, baseline survey, onboarding completion, dial anchors, tone/palette/reminder prefs, wrap-up bookkeeping timestamps, archetype + primary goal, PSS-10 + UCLA-3 scores, parental longevity, cardio + strength rhythms, baseline healthspan, distinct-open-days, last-foreground-day.
- `DailyHealthSnapshot` — per-day HealthKit-derived signals plus override / original-HealthKit-value bookkeeping (`overridesData`, `originalHealthKitValuesData`) and `lastRecomputedAt`.
- `HabitLog` — daily user-entered habit signals (alcohol, smoking/vaping, diet quality, diet amount rhythm, whole-food anchor, stress, strength training, notes).
- `LifeClockEstimate` — projected age, projected date, healthspan score, daily delta, confidence, explanation.
- `TimeLedgerEntry` — id / date / title / delta / source / confidence / driverType / questSlug.
- `Quest` — quest pool entries including `genre` (V1.4.0). User-facing label is **"Today's Plan"** since the 2026-05-01 IA refactor; "Quest" remains the internal type name.
- `WeeklyReport` — net delta + drivers + lever + confidence.
- `DailyReflection` — short tone-aware reflection prompt response.
- `QuestEvent` — completion telemetry per Today's Plan action.
- `CumulativeSummaryCache` — derived rollups; the cache-invalidation contract is documented in the schema file header.

## Services

### HealthKitServiceProtocol (`Sources/Services/HealthKitServiceProtocol.swift`)

- `requestAuthorization`
- `dailySnapshot`
- `recentSnapshots`
- `recentSnapshotsCollection(endingAt:days:)` — 90-day backfill via single collection query (optimization over per-day fan-out)
- `authorizationKnown`
- `isHealthDataAvailable`

### `LiveHealthKitService` / `MockHealthKitService`

Implementations of the protocol. `LiveHealthKitService.coreReadTypes` is the canonical list of six Tier-1 HealthKit types (steps, exercise minutes, active energy, resting HR, sleep, body mass). See `HEALTH_DATA_STRATEGY.md` for what is and isn't read.

### ClockEngine (`Sources/Engines/ClockEngine.swift`)

Additive minutes ledger.

- `calculateBaseline`
- `calculateDailyDelta`
- `calculateWeeklyTrend`
- `populationBaseline(for:)` — CDC FastStats anchors (79.0 / 76.5 / 81.4)
- `dietDriver` — V1.2 composite (quality / rhythm / anchor)

### HealthspanEngine (`Sources/Engines/HealthspanEngine.swift`)

**The headline projection number.** Years-based healthspan projection used by the Future tab and the home-screen projection card. Coefficient table verbatim-matched to `docs/products/life-clock/healthspan-coefficients.md` (14 coefficients; +14y cap above baseline; smoking-dominance 0.3× scale; floor `max(currentAge + 1, demographicFloor)`).

- `projectWith(...)` — single-aggregate projection
- `weeklyTrajectory(...)` — interpolated past + projected forward (v1 simplification: linear interpolation, not historical sliding window)
- `Projection.ClampState` — `.normal` / `.nearCap` / `.atCap` for chart-side compression handling

### QuestEngine

- `generateDailyQuests`
- adapts to missing data (inlined; not a discrete method)
- guards against unsafe medical advice (design rule)

### SubscriptionStore

- product loading
- entitlement refresh
- purchase
- restore

### NotificationsService

- local-notification authorization
- daily reminder scheduling
- same-day reminder suppression after a check-in (`store.setDailyReminder` → suppress-until-tomorrow-hour path)
- tone-aware reminder copy

### Other shipped services

The following are live in `Sources/Services/` and `Sources/Engines/` and should be referenced explicitly when writing about the architecture:

- `HealthKitAggregator` — rolls per-day snapshots into the windows the engines consume.
- `OverrideService` — Pro-gated correction-power surface; backs `applyOverride` / `revertOverride`.
- `HistoricalImportCoordinator` — 90-day backfill orchestration.
- `TelemetryRecorder` + `OnboardingTelemetry` — privacy-preserving onboarding funnel events (`privacy: .private` on all stored values; no aggregator wired in v1).
- `AffinityEngine` — Today's Plan generation tied to user affinity signals.
- `NarrativeEngine` — long-form narrative copy for Future tab states (day0 / coldLaunch1to3 / warmingUp4to13 / full14plus).
- `WrapUpCoordinator` — schedules the in-app yesterday + weekly wrap-up sheets on cold-launch. **Pull, not push** — never calls `NotificationsService.setSchedule` for wrap-ups (vision Decided constraint 2026-05-09).

## Notifications constraints (binding — vision-Decided)

- **One notification.** Single local-reminder identifier (`daily-reminder`); `interruptionLevel = .active`.
- **Opt-in only.** Profile → Daily reminder toggles the schedule; default off.
- **Evening clamp.** Hour clamped to `[8, 22]` (`max(8, min(22, hour))`).
- **Wrap-ups are pull-only.** `WrapUpCoordinator` presents in-app sheets on cold-launch / foreground cycle; no Lock-Screen wrap-up push.
- **No re-engagement.** No analytics-triggered "we miss you" notifications. (Operator memory: `feedback_life_clock_notifications_constraints.md`.)

## Testing priorities

- deterministic `ClockEngine` + `HealthspanEngine` coverage
- confidence and aggregation behavior
- missing-data behavior
- Today's Plan generation and persistence behavior
- StoreKit entitlement and restore behavior (`EntitlementGatedWritesTests` pins `.notEntitled` on `applyOverride`, `revertOverride`, `selectPlanQuest`)
- HealthKit mock-path coverage
- cold-start restoration and reset behavior
- end-to-end app flow coverage with `MockHealthKitService` + JUMP_TO fixtures (`SwiftUI` UITest target)

## V1 engineering rule

Do not add a backend until the local daily loop proves retention. Adding any off-device data flow (analytics, backup, sync) regresses the GDPR-K local-first defense in `09_PRIVACY_COMPLIANCE.md` § "Users in the EU" — that section is a hard precondition on any backend work.
