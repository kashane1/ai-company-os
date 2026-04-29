# Life Clock iOS

Managed iOS source tree for the Life Clock app. Working title — final brand name not yet resolved (see `docs/products/life-clock/OPEN_QUESTIONS.md` Q1).

## Status

- Phase: discovery
- Local-first SwiftUI shell backed by sample data via a mockable HealthKit boundary.
- Six SwiftUI screens (Onboarding, Today, Time Ledger, Quests, Weekly Report, Profile) wired to deterministic engines.
- No live HealthKit reads in v1. No StoreKit. No backend.

## Read first

Before any iOS build work:

- `docs/products/life-clock/PHASE_STATUS.md`
- `docs/products/life-clock/PRODUCT_STRATEGY.md`
- `docs/products/life-clock/PRD.md`
- `docs/products/life-clock/HEALTH_DATA_STRATEGY.md`
- `docs/products/life-clock/CLOCK_MODEL.md`
- `docs/products/life-clock/PRIVACY_COMPLIANCE.md`
- `docs/products/life-clock/TECHNICAL_ARCHITECTURE.md`
- `docs/products/life-clock/CODEX_BUILD_PROMPT.md` — paste-ready prompt for the next implementation pass

## Scope guardrails

- Local-first. Do not add a backend until the daily loop proves retention.
- HealthKit is gated behind `HealthKitServiceProtocol`. v1 ships only `MockHealthKitService`.
- The app must not present itself as medical advice or claim a real death date.
- The app must not collect, link, or transmit HealthKit-derived data off-device.
- iPad must render natively (`TARGETED_DEVICE_FAMILY = "1,2"`), not in iPhone-compat mode.

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
  -destination 'platform=iOS Simulator,name=iPhone 15'
```

## Layout

```
Sources/
├── App/         # @main, scene, store, tabs, tone-mode enum
├── Engines/     # ClockEngine, QuestEngine, ConfidenceModel, EngineClock — pure, deterministic
├── Models/      # SwiftData @Model types under VersionedSchema
├── Services/    # HealthKitServiceProtocol + MockHealthKitService + Configuration
├── Features/    # Six SwiftUI screens
└── Shared/      # Disclaimer banner, confidence badge, formatters, design tokens
Tests/           # Unit tests for engines and store
```

## Hard rules (verified by CI greps)

- Engines never call `Date()`, `Date.now`, `Calendar.current`, or `TimeZone.current` — all injected via `EngineClock`.
- v1 must not construct `HKHealthStore`.
- No medical-claim language in user-facing copy (`diagnose`, `cure`, `prescribe`, `guarantee`).
