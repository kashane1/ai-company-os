# Life Clock iOS

Managed iOS source tree for the Life Clock app. Working title — final brand name not yet resolved (see `docs/products/life-clock/14_OPEN_QUESTIONS.md` Q1).

## Status

- iOS 17+, iPhone-first, iPad renders natively (`TARGETED_DEVICE_FAMILY = "1,2"`).
- Local-first SwiftUI + SwiftData. No backend.
- Three tabs: **Today**, **History**, **Profile** (post tab-consolidation).
- Live HealthKit reads via `LiveHealthKitService`; mock service still ships behind `LIFECLOCK_USE_MOCK_HEALTH=1` for tests and audits.
- StoreKit live with three product IDs (`com.lifeclock.pro.{monthly,annual,lifetime}`); Pro entitlement gates the override flow and full 90-day History.
- Three tone modes: `gentle`, `coach`, `firmDirect` (Coach default).
- Three palettes: `defaultNavy`, `auroraCool`, `sunsetWarm`.
- North star: `docs/products/life-clock/vision.md`. Read this before any vision-driven polish session.

## Read first

Order matters. Start at the top.

- `docs/products/life-clock/vision.md` — soul, core daily experience, decided constraints, open questions
- `docs/products/life-clock/02_PRODUCT_STRATEGY.md` — positioning + product principles
- `docs/products/life-clock/03_PRD.md` — original spec (some screens consolidated since; cross-reference the actual code)
- `docs/products/life-clock/05_CLOCK_MODEL.md` — what moves the clock
- `docs/products/life-clock/04_HEALTH_DATA_STRATEGY.md` — HealthKit boundaries
- `docs/products/life-clock/09_PRIVACY_COMPLIANCE.md` — emotional safety + crisis affordances (live in `SafetyNetView`)
- `docs/products/life-clock/12_TECHNICAL_ARCHITECTURE.md` — engines, store, services
- `docs/products/life-clock/ux-audit-2026-04-30.md` — most recent UX audit
- `docs/products/life-clock/MVP_VS_FOUNDER_PACK_AUDIT_2026-04-28.md` — what was shipped vs. founder pack as of late April

For polish sessions, also see `docs/skills/simulator-driven-polish-guide.md`.

## Scope guardrails

- Local-first. Do not add a backend until the daily loop proves retention.
- HealthKit is gated behind `HealthKitServiceProtocol`. `LiveHealthKitService` (production) and `MockHealthKitService` (tests, audits) are the two conforming services.
- The app must not present itself as medical advice or claim a real death date.
- The app must not collect, link, or transmit HealthKit-derived data off-device. No analytics on health data.
- iPad must render natively, not in iPhone-compat mode.
- Orange-not-red: negative deltas use muted orange, never alarming red. The mascot's heartbeat ECG is the one deliberate red exception (centralized in `LifeClockPalette.swift`).

## Build

XcodeGen is required:

```bash
brew install xcodegen
cd products/life-clock-ios
xcodegen generate
open LifeClock.xcodeproj
```

The generated `.xcodeproj` is gitignored — regenerate locally.

## Tests

```bash
xcodebuild test \
  -project LifeClock.xcodeproj \
  -scheme LifeClock \
  -destination 'platform=iOS Simulator,name=iPhone 17 Pro'
```

Test targets: `LifeClockTests` (unit, ~30 files covering engines, store, telemetry, schema migrations, snapshot overrides, subscription flow) and `LifeClockUITests` (`LifeClockUITests.swift`).

## Layout

```
Sources/
├── App/         # @main, scene, store, tabs, tone-mode enum, archetype, launch config
├── Engines/     # ClockEngine, QuestEngine, ConfidenceModel, EngineClock, WrapUpCoordinator,
│                #   AgeGate, CompletionBadgeEngine, MonthlyLoggingCalculator — pure, deterministic
├── Models/      # SwiftData @Model types under VersionedSchema, SnapshotOverrideMap
├── Services/    # HealthKit (Live + Mock + Protocol + Aggregator + Configuration),
│                #   SubscriptionStore + EntitlementProviding, NotificationsService,
│                #   HistoricalImportCoordinator, OverrideService, OnboardingTelemetry,
│                #   PaywallProductID, Products.storekit
├── Features/
│   ├── Today/        # TodayView, ReflectionCard, ReflectionSheet
│   ├── History/      # HistoryView (fog-gated free preview + Pro 90-day list),
│   │                 #   DayDetailView, OverrideSheet
│   ├── Profile/      # ProfileView (tone, palette, subscriptions, body units, SafetyNet entry)
│   ├── Onboarding/   # OnboardingCoordinator + ~28-screen flow under Screens/
│   ├── Paywall/      # PaywallSheet
│   ├── QuickLog/     # QuickLogSheet
│   ├── SafetyNet/    # SafetyNetView ("Take a softer path" — gentle mode + hide-clock + crisis resources)
│   └── WrapUp/       # WrapUpSheet (yesterday + weekly ceremony), ClockHandView
└── Shared/      # Disclaimer banner, confidence badge, palette, design tokens, mascot,
                 #   life-grid dot, formatters, reflection prompts, support-moment cards
Tests/           # ~30 unit-test files
UITests/         # LifeClockUITests
```

## Hard rules (verified by CI greps + tests)

- Engines never call `Date()`, `Date.now`, `Calendar.current`, or `TimeZone.current` — all injected via `EngineClock`.
- Production code constructs `HKHealthStore` only inside `LiveHealthKitService`. Test code uses `MockHealthKitService`.
- No medical-claim language in user-facing copy (`diagnose`, `cure`, `prescribe`, `guarantee`).
- No alarming red for negative-delta UI; only `LifeClockPalette.heartbeatRed` may render red, and only on the mascot ECG.

## Launch-config env vars (DEBUG only — stripped from Release)

Layered fixture knobs in `LifeClockLaunchConfiguration.swift` and `SubscriptionStore.swift`. Compose freely.

| Env var | Values | Effect |
|---|---|---|
| `LIFECLOCK_UI_TEST` | `1` | Marks the run as a UI test; turns on mock HealthKit + in-memory store. |
| `LIFECLOCK_UI_TEST_SCENARIO` | `onboarding` (default) / `onboarded` | Onboarding state. `onboarded` seeds a UserProfile so the app boots past onboarding. |
| `LIFECLOCK_USE_MOCK_HEALTH` | `1` | Force the mock HealthKit service even outside UI tests. |
| `LIFECLOCK_HEALTH_AUTH` | `authorized` / `denied` / `notDetermined` | Mock health auth state. Takes precedence over the legacy `LIFECLOCK_UI_TEST_AUTHORIZED=1`. |
| `LIFECLOCK_UI_TEST_AUTHORIZED` | `1` (legacy) | Maps to `LIFECLOCK_HEALTH_AUTH=authorized` for back-compat. |
| `LIFECLOCK_FORCE_PAYWALL` | `1` | Present `PaywallSheet` on launch (for paywall.close XCUITest). |
| `LIFECLOCK_SIMULATOR_PRO_DISABLED` | `1` | **Inverted:** simulator runs default to Pro. Set this to test the Free experience. |
| `LIFECLOCK_SEED_STREAK` | integer | Seeds N days of diet-logged HabitLog entries (drives the streak banner). Requires `scenario=onboarded`. |
| `LIFECLOCK_SEED_QUESTS_COMPLETED` | integer | Seeds N completed quests for today. Requires `scenario=onboarded`. |
| `LIFECLOCK_FIXED_DATE` | ISO-8601 (e.g. `2026-04-30T00:00:00Z`) | Pin the engine clock for deterministic flows. |

Common compositions:

```bash
# Day-7 returning Pro user
LIFECLOCK_UI_TEST_SCENARIO=onboarded LIFECLOCK_SEED_STREAK=7 LIFECLOCK_HEALTH_AUTH=authorized

# Free user with full History fog gate
LIFECLOCK_UI_TEST_SCENARIO=onboarded LIFECLOCK_SEED_STREAK=20 LIFECLOCK_SIMULATOR_PRO_DISABLED=1

# Permission-denied empty state
LIFECLOCK_UI_TEST_SCENARIO=onboarded LIFECLOCK_HEALTH_AUTH=denied
```

Release builds always return production defaults regardless of `ProcessInfo.environment` — the fixture surface is removed from the App Store binary entirely.
