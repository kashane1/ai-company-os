---
title: Life Clock iOS — Founder Pack Ingestion + MVP Skeleton
type: feat
status: active
date: 2026-04-27
origin: /Users/simons/Downloads/Life_Clock_Founder_Pack_Markdown/
---

# Life Clock iOS — Founder Pack Ingestion + MVP Skeleton

## Enhancement Summary

**Deepened on:** 2026-04-27
**Sections enhanced:** Architecture, Phase 2 (Xcode scaffold), Phase 3 (engines), Phase 4 (SwiftUI), Risk Analysis, Acceptance Criteria.
**Research agents used:** framework-docs-researcher (HealthKit / SwiftData / @Observable / XcodeGen / deterministic Swift), architecture-strategist (pattern compliance + phase-cut review), code-simplicity-reviewer (YAGNI kill list), learnings-researcher (`docs/solutions/`).

### Key Improvements

1. **HealthKit entitlement deferred entirely.** The skeleton declares no entitlement and no `NSHealthShareUsageDescription` — those land with the live `HealthKitService` plan. Eliminates an "entitlement-without-use" App Review surface that the original plan dismissed too quickly.
2. **`VersionedSchema` adopted from day one.** Avoids a known migration trap where moving from unversioned → versioned SwiftData schemas requires a separate release.
3. **`@Model` property-level defaults required on all non-optional fields** — applied a past learning (`docs/solutions/integration-issues/swiftdata-mandatory-attribute-migration-landmine.md`) that has bitten the Catchbook codebase.
4. **`TARGETED_DEVICE_FAMILY = "1,2"`** instead of `1` — applied a past learning (`docs/solutions/integration-issues/ios-ipad-compatibility-mode-cramped-layout.md`) to avoid iPhone-compat-mode rendering on iPad. Founder pack is iPhone-first but iPad must still render natively.
5. **`EngineClock` injection pattern** codified — `Date`, `Calendar`, `TimeZone`, and seeded `RNG` are all injected, never read from globals. CI grep gates added.
6. **`@Observable` migration cheat sheet** added so the team uses iOS-17-native patterns (`@State`, `@Environment(Type.self)`, `.environment(store)`) and avoids `@Published` / `ObservableObject` survivors that silently no-op under the macro.
7. **Phase 2 contradiction fixed** — original plan said "author Info.plist with `NSHealthShareUsageDescription` and `NSHealthUpdateUsageDescription`" then said `NSHealthUpdateUsageDescription` is intentionally absent. Both strings are now removed from this PR.
8. **PR-split option documented** — the work stays on one branch (founder said "begin work on it all"), but Phase 5 now offers the option to land Phase A as a separate first PR if review velocity suffers.

### New Considerations Discovered

- HealthKit `requestAuthorization` is **silent for read denials** by Apple privacy design. The Profile screen must never claim "Connected" — only "Available" or "Not configured". Already encoded; reinforced.
- "Today" is timezone-dependent. A user crossing midnight in another timezone could complete a quest twice. Anchor "today" to device timezone at session start, pinned for the session.
- iCloud-syncing the SwiftData container is an App Review violation for HealthKit-derived data. Disable CloudKit on the `ModelContainer` explicitly.

---

## Overview

Stand up **Life Clock** as a third managed iOS product alongside `catchbook` and `after-plans`. Life Clock is a HealthKit-powered longevity *game*: daily behavior moves a visible time trajectory, and the user "earns time back" by completing 1–3 daily quests. The wedge is **agency over fear** — trajectory, not prophecy.

This plan covers two coupled deliverables:

1. **Founder pack ingestion** — copy and normalize the founder pack from `/Users/simons/Downloads/Life_Clock_Founder_Pack_Markdown/` into `docs/products/life-clock/`, register the product in `infra/products.json`, and produce the canonical artifact chain (`PRODUCT_BRIEF.md`, `PRD.md`, `MVP_SPEC.md`, `IOS_ARCHITECTURE.md`, etc.) following the conventions already established by `docs/products/after-plans/` and `docs/products/catchbook/`.
2. **iOS MVP skeleton** — a compile-clean, deterministic, local-first SwiftUI app under `products/life-clock-ios/` with: SwiftData models, a mockable HealthKit service boundary, `ClockEngine` v1 and `QuestEngine` v1 as pure Swift (fully unit-tested), six core screens (Onboarding, Today, Time Ledger, Quests, Weekly Report, Profile/Settings), tone modes, and a non-blocking medical disclaimer. **No backend. No paywall enforcement (UI shell only). No AI. No HealthKit data writes.**

These two deliverables are sequenced: ingestion first (so the artifact chain is the source of truth), then skeleton (so it is built against the ingested PRD/MVP spec, not against re-paraphrased copies of the founder pack).

## Problem Statement

The founder has produced a complete 18-file founder pack for a new product (working title "Life Clock") in `~/Downloads/Life_Clock_Founder_Pack_Markdown/`. The pack already covers strategy, PRD, clock model, health data strategy, UX/game loop, monetization, privacy/compliance, GTM, roadmap, technical architecture, and a paste-ready Codex build prompt. None of this is checked into the platform. Until it is ingested:

- The product is invisible to platform tooling — `infra/products.json` does not list it, so policies, supervisor decomposition, and skill adapters cannot route to it.
- Workers cannot follow the artifact chain (`product-artifact-chain` skill) because there is no `docs/products/life-clock/` to validate.
- Any iOS work that starts before ingestion will reference the Downloads folder by absolute path, which (a) breaks for any other operator on this repo and (b) bypasses the founder→spec normalization step that other products (After Plans, Catchbook) went through.

Separately, Life Clock has no source tree. `products/life-clock-ios/` does not exist. The founder pack's `13_CODEX_BUILD_PROMPT.md` describes the first-pass implementation but it has not been executed.

## Proposed Solution

A **two-phase, single-branch** delivery:

**Phase A — Founder Pack Ingestion** (no Swift). Normalize the Downloads pack into the canonical `docs/products/life-clock/` structure. Register the product. Establish the artifact chain so subsequent iOS work has a stable, repo-relative source of truth.

**Phase B — iOS MVP Skeleton.** Stand up `products/life-clock-ios/` mirroring the After Plans pattern (XcodeGen `project.yml`, SwiftUI app target, `Sources/{App,Features,Models,Services,Shared}` layout, `Tests/`). Implement the deterministic core (models, `ClockEngine`, `QuestEngine`) with full unit coverage, then layer on six placeholder-driven screens that consume the engines via in-memory sample state. **Do not** wire HealthKit reads on first pass — gate behind a `HealthKitService` protocol with a `MockHealthKitService` fixture. Real HealthKit authorization comes in a follow-up plan.

This sequencing lets us hand the iOS work off to Codex (per the founder pack's `13_CODEX_BUILD_PROMPT.md`) once ingestion lands, rather than asking Codex to do both jobs in one PR.

## Technical Approach

### Architecture

**Phase A (docs only):**

```
docs/products/life-clock/
├── README.md                          # entry point, mirrors after-plans/README.md tone
├── FOUNDER_BRIEF.md                   # normalized from 00_EXECUTIVE_SUMMARY + 02_PRODUCT_STRATEGY
├── PRODUCT_BRIEF.md                   # alias / short-form positioning
├── PRD.md                             # from 03_PRD.md
├── MVP_SPEC.md                        # MVP scope distilled from PRD + UX game loop
├── IOS_ARCHITECTURE.md                # from 12_TECHNICAL_ARCHITECTURE.md
├── CLOCK_MODEL.md                     # from 05_CLOCK_MODEL.md
├── HEALTH_DATA_STRATEGY.md            # from 04_HEALTH_DATA_STRATEGY.md
├── UX_GAME_LOOP.md                    # from 06_UX_GAME_LOOP.md
├── MONETIZATION.md                    # from 07_MONETIZATION.md
├── APP_STORE_ASO.md                   # from 08_APP_STORE_ASO.md
├── PRIVACY_COMPLIANCE.md              # from 09_PRIVACY_COMPLIANCE.md
├── GTM_LAUNCH_PLAN.md                 # from 10_GTM_LAUNCH_PLAN.md
├── ROADMAP_METRICS.md                 # from 11_ROADMAP_METRICS.md
├── BUSINESS_PLAN.md                   # from 01_BUSINESS_PLAN.md
├── OPEN_QUESTIONS.md                  # from 14_OPEN_QUESTIONS.md
├── CODEX_BUILD_PROMPT.md              # from 13_CODEX_BUILD_PROMPT.md (verbatim, paste-ready)
├── SOURCES.md                         # from SOURCES.md (verbatim, citation list)
├── MASTER_FOUNDER_PACKAGE.md          # from MASTER_FOUNDER_PACKAGE.md (verbatim consolidated copy)
└── PHASE_STATUS.md                    # NEW — current phase = discovery, owner, next decision
```

Files are **copied verbatim** (with a one-line `> Source: founder pack vYYYY-MM-DD` header) rather than rewritten. The founder pack is already well-structured. The job here is to put it in the right place under repo-relative paths, not to "improve" it. Renames are minimal: drop the `00_`/`01_` numeric prefix that was useful for ordering in Downloads but adds noise in the repo (matching the After Plans convention of unprefixed UPPERCASE filenames).

`infra/products.json` gains a third entry:

```json
{
  "id": "life-clock",
  "name": "Life Clock",
  "slug": "life-clock",
  "platform": "ios",
  "repo_id": "life-clock-ios",
  "source_path": "products/life-clock-ios",
  "docs_root": "docs/products/life-clock",
  "phase": "discovery"
}
```

**Phase B (iOS skeleton):**

```
products/life-clock-ios/
├── README.md
├── project.yml                        # XcodeGen config, mirrors AfterPlans pattern
├── Info.plist                         # NO HealthKit usage strings in v1 — deferred to live-HealthKit PR
├── PrivacyInfo.xcprivacy
├── Sources/
│   ├── App/
│   │   ├── LifeClockApp.swift         # @main, scene + tab root
│   │   ├── LifeClockStore.swift       # observable app-level state (sample-data backed)
│   │   ├── AppTab.swift               # tab enum: Today, Ledger, Quests, Profile
│   │   └── ToneMode.swift             # gentle / coach / mementoMori
│   ├── Models/
│   │   ├── UserProfile.swift          # SwiftData @Model
│   │   ├── HealthPermissionState.swift
│   │   ├── DailyHealthSnapshot.swift
│   │   ├── HabitLog.swift
│   │   ├── LifeClockEstimate.swift
│   │   ├── TimeLedgerEntry.swift
│   │   ├── Quest.swift
│   │   └── WeeklyReport.swift
│   ├── Engines/
│   │   ├── ClockEngine.swift          # pure, deterministic, no Foundation.Date.now
│   │   └── QuestEngine.swift          # pure, deterministic, takes a clock-injected Date
│   ├── Services/
│   │   ├── HealthKitServiceProtocol.swift
│   │   ├── MockHealthKitService.swift # returns deterministic seeded snapshots
│   │   ├── LifeClockConfiguration.swift
│   │   └── PaywallServiceProtocol.swift  # protocol only — no StoreKit yet
│   ├── Features/
│   │   ├── Onboarding/                # value, safety, baseline, tone, perm education, reveal
│   │   ├── Today/                     # clock + delta + drivers + quests + quick log
│   │   ├── TimeLedger/
│   │   ├── Quests/
│   │   ├── WeeklyReport/
│   │   └── Profile/
│   ├── Shared/
│   │   ├── DesignTokens.swift         # spacing/typography constants
│   │   ├── ConfidenceBadge.swift
│   │   ├── DisclaimerBanner.swift
│   │   └── TimeDeltaFormatter.swift   # "+42 minutes", "-12 minutes"
│   └── Assets.xcassets/
└── Tests/
    ├── ClockEngineTests.swift
    ├── QuestEngineTests.swift
    ├── HealthSnapshotMissingDataTests.swift
    ├── ConfidenceModelTests.swift
    └── LifeClockStoreTests.swift
```

### Implementation Phases

#### Phase 1: Branch + Founder Pack Ingestion (no Swift)

1. Create branch `feat/life-clock-mvp-skeleton` from `main`.
2. `mkdir -p docs/products/life-clock/`.
3. Copy each file from `~/Downloads/Life_Clock_Founder_Pack_Markdown/` into `docs/products/life-clock/`, dropping the `NN_` numeric prefix and prepending each with a one-line provenance header:
   ```
   > Source: Life Clock Founder Pack (2026-04-27). Normalized for platform use.
   ```
4. Author NEW file: `docs/products/life-clock/PHASE_STATUS.md` — phase=discovery, owner=founder, next decision=brand name resolution from OPEN_QUESTIONS Q1.
5. Author NEW file: `docs/products/life-clock/README.md` — index that points at `MASTER_FOUNDER_PACKAGE.md` for the consolidated read and `CODEX_BUILD_PROMPT.md` for build handoff.
6. Edit `infra/products.json` to add the `life-clock` entry (see JSON above).
7. Run `python -c "from packages.config.products import load_product_configs; print(list(load_product_configs().keys()))"` to confirm three products load cleanly.
8. Run the `product-artifact-chain` Claude skill against `life-clock` to validate the chain.

**Success criteria:** product registry loads with `life-clock`; artifact chain validates; no Swift files touched.

#### Phase 2: Xcode Project Scaffold (compile-clean empty shell)

1. `mkdir -p products/life-clock-ios/{Sources/{App,Features,Models,Services,Engines,Shared,Assets.xcassets},Tests}`.
2. Author `project.yml` mirroring `products/after-plans-ios/project.yml`. Differences:
   - `name: LifeClock`
   - `bundleIdPrefix: io.aicompanyos.products`, bundle id `io.aicompanyos.products.lifeclock`
   - `PRODUCT_NAME: LifeClock`, scheme name `LifeClock`
   - **Remove the Supabase package dependency** — Life Clock is local-first by mandate (no `packages:` block).
   - **Drop the Supabase environment variables** from the scheme.
   - **Preserve** `gatherCoverageData: true` and `coverageTargets: [LifeClock]` on the scheme (don't lose these in translation).
   - **Preserve** `createIntermediateGroups: true` and `deploymentTarget: { iOS: "17.0" }`.
   - **`TARGETED_DEVICE_FAMILY: "1,2"`** (NOT `1`) — applies past learning [`ios-ipad-compatibility-mode-cramped-layout.md`](docs/solutions/integration-issues/ios-ipad-compatibility-mode-cramped-layout.md). Founder pack is iPhone-first but iPad must render natively, not in compatibility mode.
   - **No `entitlements:` block, no `LifeClock.entitlements` file in this PR.** HealthKit entitlement is deferred to the same plan that wires `LiveHealthKitService`. Declaring an entitlement we don't exercise is an App Review surface and dead config.
3. Author `Info.plist`:
   - `CFBundleDisplayName: Life Clock`
   - `UILaunchScreen` with `LaunchBackground` color
   - **No** `NSHealthShareUsageDescription` and **no** `NSHealthUpdateUsageDescription` in v1. Both land with the live HealthKit PR. (Original plan had a contradiction here — fixed.)
4. Author `PrivacyInfo.xcprivacy` mirroring Catchbook's, with no API access reasons yet.
5. Author placeholder `LifeClockApp.swift` with a single empty `WindowGroup { Text("Life Clock") }`.
6. Run `xcodegen generate` from `products/life-clock-ios/` to produce `LifeClock.xcodeproj`.
7. Build (`xcodebuild -project LifeClock.xcodeproj -scheme LifeClock build`) to confirm compile-clean.

**Success criteria:** project generates, builds, and launches to a "Life Clock" placeholder. No SwiftData, no engines yet. No HealthKit symbols anywhere.

### Reference: project.yml skeleton (drop-in)

```yaml
name: LifeClock
options:
  bundleIdPrefix: io.aicompanyos.products
  deploymentTarget: { iOS: "17.0" }
  createIntermediateGroups: true
settings:
  base:
    SWIFT_VERSION: 5.0
    CURRENT_PROJECT_VERSION: 1
    MARKETING_VERSION: 0.1.0
targets:
  LifeClock:
    type: application
    platform: iOS
    sources: [{ path: Sources }]
    info:
      path: Info.plist
      properties:
        CFBundleDisplayName: Life Clock
        UILaunchScreen: { UIColorName: LaunchBackground }
    settings:
      base:
        PRODUCT_BUNDLE_IDENTIFIER: io.aicompanyos.products.lifeclock
        PRODUCT_NAME: LifeClock
        TARGETED_DEVICE_FAMILY: "1,2"
        SUPPORTS_MACCATALYST: NO
        ASSETCATALOG_COMPILER_APPICON_NAME: AppIcon
        ASSETCATALOG_COMPILER_GLOBAL_ACCENT_COLOR_NAME: AccentColor
    scheme:
      gatherCoverageData: true
      coverageTargets: [LifeClock]
      testTargets: [LifeClockTests]
  LifeClockTests:
    type: bundle.unit-test
    platform: iOS
    sources: [{ path: Tests }]
    dependencies: [{ target: LifeClock }]
    settings:
      base:
        GENERATE_INFOPLIST_FILE: YES
        BUNDLE_LOADER: "$(TEST_HOST)"
        TEST_HOST: "$(BUILT_PRODUCTS_DIR)/LifeClock.app/LifeClock"
        PRODUCT_BUNDLE_IDENTIFIER: io.aicompanyos.products.lifeclockTests
```

#### Phase 3: Models + Engines + Tests (the deterministic core)

This is the **highest-leverage** phase. Engines are pure functions; the entire downstream UI is a thin renderer over their output.

1. Implement SwiftData `@Model` types under `Sources/Models/` — schema mirrors `12_TECHNICAL_ARCHITECTURE.md` § "Core models". Hard rules:
   - **Wrap all models in a `VersionedSchema`** from day one. Do not skip this — moving from unversioned → versioned later is a separate release. Use `LifeClockSchemaV1: VersionedSchema` with `versionIdentifier = Schema.Version(1, 0, 0)` and a (currently empty) `LifeClockMigrationPlan: SchemaMigrationPlan`.
   - **All non-optional stored properties must have property-level defaults** at declaration time (e.g., `var toneMode: String = "coach"`), not just init defaults. This applies the past learning [`swiftdata-mandatory-attribute-migration-landmine.md`](docs/solutions/integration-issues/swiftdata-mandatory-attribute-migration-landmine.md): without property-level defaults, lightweight migration silently fails on upgraded devices (NSCocoaErrorDomain 134110) and writes no-op invisibly. Simulators and fresh installs will hide this; real-device upgrades expose it.
   - Keep optional fields optional (HealthKit-derived numerics are almost always optional — matches the missing-data contract in `04_HEALTH_DATA_STRATEGY.md`).
   - **Avoid `@Relationship`** in v1. Use flat models with `id: UUID` foreign keys. SwiftData relationships have known crash modes on cascade delete and complicate migrations.
   - Store enums as `String` raw values (e.g., `toneMode: String`), not `@Model`-backed enums — keeps lightweight migration possible.
   - `@Attribute(.unique)` on `id: UUID` only. No compound unique constraints.
   - Disable CloudKit sync on the `ModelContainer` explicitly (HealthKit-derived data must not be iCloud-synced — App Review violation).
2. Implement `ClockEngine`:
   - `calculateBaseline(profile: UserProfile) -> LifeClockEstimate` — uses CDC life expectancy anchors (S8) and a transparent rule table for smoking/alcohol/activity adjustments. Document each rule with a comment naming the source (population anchor, **not** a clinical claim).
   - `calculateDailyDelta(snapshot: DailyHealthSnapshot, habits: HabitLog?, profile: UserProfile) -> (deltaMinutes: Int, drivers: [TimeLedgerEntry], confidence: Confidence)` — deterministic given fixed inputs.
   - `calculateWeeklyTrend(snapshots: [DailyHealthSnapshot], habits: [HabitLog]) -> WeeklyReport` — uses 7-day smoothing per the founder pack's anti-volatility rule.
   - `assignConfidence(snapshot: DailyHealthSnapshot) -> Confidence` — high/medium/low based on data-source completeness, **never** penalizes missing data with negative deltas.
3. Implement `QuestEngine`:
   - `generateDailyQuests(profile: UserProfile, snapshot: DailyHealthSnapshot?, habits: HabitLog?, calendar: Calendar, today: Date) -> [Quest]` — returns 1–3 quests, never more.
   - Quest categories: movement, sleep consistency, strength, nutrition quality, risk reduction, recovery (per `06_UX_GAME_LOOP.md`).
   - **Adapts to missing data:** if no HealthKit data, falls back to manual-log-friendly quests (e.g., "Log no alcohol today").
   - **Never recommends medical action:** no supplements, medications, or specific clinical targets.
4. Tests under `Tests/`:
   - `ClockEngineTests`: baseline determinism (same input → same output), CDC anchor sanity (40-year-old male baseline within ±2 years of 76.5), daily delta sign for clearly-good and clearly-bad days, weekly smoothing dampens single bad day.
   - `QuestEngineTests`: always 1–3 quests, never zero, never four+; missing-data fallback returns manual-log-friendly quests; same seed → same set.
   - `HealthSnapshotMissingDataTests`: a snapshot with all-nil HealthKit fields produces a low-confidence estimate, not a crash.
   - `ConfidenceModelTests`: high requires passive data; sparse data downgrades to low.
5. Run tests: `xcodebuild test -project LifeClock.xcodeproj -scheme LifeClock -destination 'platform=iOS Simulator,name=iPhone 15'`.

**Success criteria:** all unit tests green; engines have zero `Foundation.Date.now` calls (time is injected); no force-unwraps in engine code.

### Reference: `EngineClock` injection pattern (drop-in)

Engines never call `Date()`, `.now`, `Calendar.current`, `TimeZone.current`, or `Int.random(in:)`. All are injected via an `EngineClock` value type:

```swift
struct EngineClock {
    var now: () -> Date
    var calendar: Calendar
    var random: () -> Double  // [0, 1)

    static let live = EngineClock(
        now: { Date() },
        calendar: { var c = Calendar(identifier: .gregorian); c.timeZone = .current; return c }(),
        random: { Double.random(in: 0..<1) }
    )

    static func fixed(_ date: Date, seed: UInt64 = 42) -> EngineClock { /* deterministic, UTC, seeded RNG */ }
}

struct ClockEngine {
    let clock: EngineClock
    func calculateBaseline(profile: UserProfile) -> LifeClockEstimate { /* uses clock.calendar, clock.now() */ }
    func calculateDailyDelta(snapshot: DailyHealthSnapshot, habits: HabitLog?, profile: UserProfile) -> (deltaMinutes: Int, drivers: [TimeLedgerEntry], confidence: Confidence) { ... }
    func calculateWeeklyTrend(snapshots: [DailyHealthSnapshot], habits: [HabitLog]) -> WeeklyReport { /* takes the same EngineClock — windowing depends on calendar */ }
}
```

**`calculateWeeklyTrend` now takes the engine's injected calendar via `self.clock`** — addresses the original plan's gap where the weekly aggregator had no calendar but week boundaries are calendar-dependent.

**Confidence is a shared model**, not method on `ClockEngine`. Lift `Confidence` and `assignConfidence(...)` into `Sources/Engines/ConfidenceModel.swift` so `QuestEngine`'s missing-data fallback can consume it without coupling to `ClockEngine`.

### CI grep gates (codified acceptance criteria)

These run as a pre-commit / CI step:

```bash
# Engines must be deterministic
! rg -n 'Date\(\)|Date\.now|\.now$|Calendar\.current|TimeZone\.current' products/life-clock-ios/Sources/Engines/

# v1 must not construct a real HealthKit store
! rg -n 'HKHealthStore\(' products/life-clock-ios/Sources/

# No medical-claim copy in user-facing strings
! rg -ni 'diagnose|cure|prescribe|guarantee' products/life-clock-ios/Sources/Features/ products/life-clock-ios/Sources/Shared/
```

### Deterministic-engine pitfalls to avoid

- **"Today" is timezone-dependent.** A user crossing midnight in another timezone could complete the same daily quest twice. Anchor "today" to the device timezone *at session start* and pin it for the session lifetime.
- **Birthday-derived ages drift ±1 year if computed via seconds.** Always use `Calendar.dateComponents([.year], from: birthDate, to: now)`.
- **7-day windows: use day-anchored midnights from the calendar**, not `now - 7 * 86400` arithmetic (DST will bite).
- **Test the rule outputs, not population means.** Replace the original plan's "baseline within ±2 years of 76.5" assertion with documented rule-table outputs (e.g., "non-smoker, sedentary, 40yo male → +0 from baseline; smoker → -X"). Otherwise rule changes look like regressions.

#### Phase 4: SwiftUI Surfaces (sample-data driven)

1. `LifeClockStore` — `@Observable` (iOS 17 macro), holds `UserProfile`, latest `LifeClockEstimate`, today's `[Quest]`, last 7 days of `TimeLedgerEntry`, and the current `WeeklyReport`. **Use `.task { await store.bootstrap() }`** in the root view to seed from `MockHealthKitService`; do **not** do work in `init` — `@State`-held stores get re-`init`ed on every parent rebuild and side effects in `init` leak silently.

   **`@Observable` migration cheat sheet (apply throughout):**
   | Old (`ObservableObject`) | New (`@Observable`) |
   |---|---|
   | `@StateObject var store = ...` | `@State private var store = LifeClockStore()` |
   | `@ObservedObject` | plain `let store: LifeClockStore` |
   | `@EnvironmentObject` | `@Environment(LifeClockStore.self) private var store` |
   | `.environmentObject(store)` | `.environment(store)` |
   | `@Published var x` | plain `var x` (silently no-ops if you keep `@Published` under the macro) |
   | n/a | `@ObservationIgnored` on injected services and engines (avoid spurious redraws) |
   | n/a | `@Bindable var store` for two-way bindings (`$store.profile`) in child views |
2. **Onboarding flow** (8 steps from `06_UX_GAME_LOOP.md` § Onboarding flow): value, safety/disclaimer, baseline profile form, tone mode picker, HealthKit education slide, permission request *button* (no actual `HKHealthStore.requestAuthorization` yet — taps are recorded to `HealthPermissionState` as `.unknown` and the flow continues), first clock reveal, first quest. Skip-friendly: any step except disclaimer is skippable.
3. **Today screen**: large clock visualization (projected age + delta), confidence badge, top-3 drivers list, quest cards, quick-log button.
4. **Time Ledger screen**: chronological list of `TimeLedgerEntry`, source icons (HealthKit / manual / estimate), positive deltas in green / negative in muted red (not alarming red).
5. **Quests screen**: today's 1–3 quests with check-off; weekly progress bar.
6. **Weekly Report screen**: time earned / lost, top driver, top drag, next-best-lever copy.
7. **Profile/Settings screen**: baseline edit, tone mode toggle, connected data sources (mocked statuses), privacy/export/delete (placeholder buttons that no-op with toast), restore purchases (placeholder).
8. **Disclaimer banner** (`Sources/Shared/DisclaimerBanner.swift`) appears on every primary screen at least once per session: "Life Clock is an estimate, not medical advice."
9. Tests:
   - `LifeClockStoreTests`: store initialization with the mock service produces non-empty `estimate`, `quests`, and `ledger`; tone-mode change updates copy keys.
   - At least one snapshot-style test per primary screen using ViewInspector or a simple state-assertion harness (skip if test infrastructure is heavyweight — favor view-model tests).

**Success criteria:** app launches into onboarding on first run; all 6 screens render with sample data; tone mode switching changes user-facing copy; no crashes when navigating any tab.

#### Phase 5: Polish, Docs, PR

1. README at `products/life-clock-ios/README.md` — same shape as `after-plans-ios/README.md`, links to `docs/products/life-clock/CODEX_BUILD_PROMPT.md` for build handoff and `docs/products/life-clock/PHASE_STATUS.md` for status.
2. Add `products/life-clock-ios/.gitignore` (or extend repo `.gitignore`) to exclude `LifeClock.xcodeproj/` (matches After Plans' "don't commit generated project" stance).
3. Run `verification-loop` skill against the diff.
4. `git add` the worktree, commit with conventional message `feat(life-clock): ingest founder pack and stand up MVP skeleton`.
5. Push branch, open PR titled `feat: Life Clock — founder pack ingestion + iOS MVP skeleton`.

**PR-split option.** If the diff is too large for fast review, split on the same branch into two PRs:

- **PR1** — Phase 1 only (founder pack ingestion + `infra/products.json` entry + `docs/products/life-clock/`). Mergeable in isolation. Unblocks the `product-artifact-chain` skill immediately.
- **PR2** — Phases 2–4 (Xcode scaffold + engines + screens), stacked on PR1.

Default behavior in pipeline mode: **single PR.** Splitting only happens if review feedback specifically requests it.

## Alternative Approaches Considered

1. **Single PR that also wires real HealthKit reads.** Rejected: HealthKit authorization is a sensitive surface (requires real-device testing, app review implications, and at least one round of permission-string copy review). Bundling it with scaffolding inflates PR size and risks blocking a clean skeleton merge on a HealthKit issue. Defer to a focused follow-up plan.
2. **Build the iOS app first, ingest founder pack later.** Rejected: every reference would be an absolute Downloads path, and the artifact-chain skill would have nothing to validate against. Ingestion is cheap; doing it first costs ~15 min and removes a class of repo-relativity bugs.
3. **Rewrite/condense the founder pack during ingestion.** Rejected for v1: the pack is already coherent. Editorial passes are downstream work. Verbatim copy + provenance header is the lowest-risk move.
4. **Skip XcodeGen, hand-author the `.xcodeproj`.** Rejected: both Catchbook and After Plans use `xcodegen`; consistency wins.
5. **Put HealthKit calls behind `#if DEBUG` mocks instead of a protocol.** Rejected: the founder pack's `12_TECHNICAL_ARCHITECTURE.md` explicitly calls for a "mockable service boundary." A protocol with two implementations (`MockHealthKitService` for v1, `LiveHealthKitService` later) keeps tests fast and the production path clean.
6. **Use Combine + ObservableObject instead of `@Observable`.** Rejected: deployment target is iOS 17+ (matches After Plans); the new macro is leaner.

## System-Wide Impact

### Interaction Graph

- `infra/products.json` change → `packages.config.products.load_product_configs()` returns a third entry → any worker code that iterates products (supervisor decomposition, skill registry checks, build orchestration) now sees Life Clock.
- New `products/life-clock-ios/` directory → `xcodegen` invocations from any iOS build skill (notably `ios-build-and-sign`) become applicable. **Verify** the build skill discovers products by registry, not by hardcoded path — if hardcoded, file a follow-up.
- New `docs/products/life-clock/` → `product-artifact-chain` skill picks up a third product to validate. The chain validator must pass; otherwise CI / the verification loop will flag the new product as broken.

### Error & Failure Propagation

- `LifeClock.xcodeproj` is generated, not committed (per After Plans pattern — though Catchbook *does* commit its `.xcodeproj`). **Decision: follow After Plans (no commit of generated project) for Life Clock.** If this causes friction with CI, switch to committing.
- `MockHealthKitService` returning `nil` for fields must never throw; engines treat `nil` as low-confidence missing data, not as an error.
- SwiftData migrations: v1 has no migrations. Any later schema change must add a migration plan; flag this in `IOS_ARCHITECTURE.md`.

### State Lifecycle Risks

- Engines are pure; no state risk.
- `LifeClockStore` holds in-memory state seeded from the mock service. On app cold-start, store re-seeds — there is no persistence in v1. **This is intentional for the skeleton** but must be documented in the README so a future contributor doesn't conclude SwiftData is broken.
- Tone-mode change must not trigger re-computation of the clock (clock value is independent of presentation). Test this.

### API Surface Parity

- HealthKit permissions are declared in entitlements + `Info.plist` but never *requested* in v1. Make sure the app does not display "Connected to Apple Health" anywhere — it would be a lie. The Profile screen must show "Not connected" for every data source until the live service ships.

### Integration Test Scenarios

1. **Cold start with no SwiftData store** → app boots into onboarding, not Today.
2. **Onboarding completed → cold start** → app boots into Today; clock and quests are non-empty.
3. **Tone mode switched mid-session** → copy on Today screen updates; clock value unchanged.
4. **All HealthKit fields nil for 7 days** → Weekly Report renders with low-confidence label, no crash, no fabricated drivers.
5. **Quest completion** → reflected in Time Ledger as a positive entry within the same session.

## Acceptance Criteria

### Functional Requirements

- [ ] `infra/products.json` contains a `life-clock` entry; `load_product_configs()` returns it.
- [ ] `docs/products/life-clock/` contains all 18 founder-pack files plus a NEW `PHASE_STATUS.md` and `README.md`.
- [ ] Each ingested file begins with the provenance header line.
- [ ] `products/life-clock-ios/project.yml` exists; `xcodegen generate` produces a clean `LifeClock.xcodeproj`.
- [ ] `xcodebuild build` succeeds for the `LifeClock` scheme on iPhone 15 simulator.
- [ ] `xcodebuild test` succeeds; `ClockEngineTests`, `QuestEngineTests`, `HealthSnapshotMissingDataTests`, `ConfidenceModelTests`, `LifeClockStoreTests` all pass.
- [ ] App launches into Onboarding on first run; on subsequent runs (after `disclaimerAcceptedAt` is set in the store), launches into Today.
- [ ] All 6 screens render with sample data and are reachable via the tab bar / onboarding.
- [ ] Disclaimer banner is present on Today, Time Ledger, Quests, and Weekly Report at least once per session.
- [ ] Profile screen shows tone mode picker; switching tone updates user-facing copy in Today.
- [ ] No `HKHealthStore` is constructed anywhere in v1 (grep verification — see Phase 3 § CI grep gates).
- [ ] No `NSHealthShareUsageDescription` or `NSHealthUpdateUsageDescription` in `Info.plist`; no HealthKit entitlement declared.
- [ ] All SwiftData `@Model` non-optional stored properties have property-level defaults.
- [ ] `ModelContainer` constructed with CloudKit explicitly disabled.
- [ ] `TARGETED_DEVICE_FAMILY: "1,2"` in `project.yml`.

### Non-Functional Requirements

- [ ] Engines contain zero `Date()` / `.now` calls — time is injected.
- [ ] Engines contain zero force-unwraps (`!` outside of test fixtures).
- [ ] No medical-claim copy: grep for "diagnose", "cure", "prescribe", "guarantee" — must return no UI matches.
- [ ] No advertising/tracking SDKs added.
- [ ] No HealthKit data writes (no `HKHealthStore.save`).
- [ ] Build time on M-series Mac < 60s for incremental builds.

### Quality Gates

- [ ] All tests pass.
- [ ] `verification-loop` skill returns a clean verdict on the diff.
- [ ] `product-artifact-chain` skill validates `life-clock`.
- [ ] PR description links to founder pack and to `docs/products/life-clock/CODEX_BUILD_PROMPT.md` for follow-up work.

## Success Metrics

This is a foundation PR; success is binary (the platform now has a third product) plus the deterministic-core invariant. Concretely:

- **Existence:** `life-clock` is a registered product with a valid artifact chain and a buildable iOS target.
- **Determinism:** `ClockEngine` and `QuestEngine` are 100% pure and 100% covered by unit tests.
- **Safety:** zero medical-claim language ships in user-facing copy.
- **Time-to-next-slice:** the next contributor (Codex or human) can pick up `13_CODEX_BUILD_PROMPT.md` and start wiring real HealthKit reads without any scaffolding work.

## Dependencies & Prerequisites

- `xcodegen` installed locally (already used by other products).
- Xcode 15+ with iOS 17 SDK.
- `~/Downloads/Life_Clock_Founder_Pack_Markdown/` exists and is readable (verified during research).
- No new Python deps. No new Swift packages (Life Clock has no Supabase dependency in v1).

## Risk Analysis & Mitigation

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Founder pack file naming drifts during normalization (e.g., dropping a section) | Low | Med | Verbatim copy + provenance header; artifact-chain skill validates the result. |
| Engine tests are tautological ("returns what we coded") | Med | Med | Test against rule-table outputs documented in `CLOCK_MODEL.md`, not internal constants. |
| ~~HealthKit entitlement triggers App Store review surface~~ | — | — | **Eliminated.** No entitlement declared in this PR. |
| `xcodegen` config drift causes regenerated broken project | Low | Med | Run `xcodegen generate` and `xcodebuild build` locally before opening PR; `.xcodeproj` not committed (mirrors After Plans). |
| Medical-claim language slips into UI copy | Med | High | CI grep gate (see Phase 3 § CI grep gates); tone-mode review pass before merge. |
| Sample data makes the app *feel* further along than it is | Med | Low | Disclaimer banner + Profile shows "Not configured" for all data sources. Never "Connected". |
| Brand name "Life Clock" is not final (per Open Question 1) | High | Low | `LifeClock` as code identifier; all UI strings live in a single `Localizable.strings` so rename is a one-file change. |
| SwiftData lightweight migration silently fails on real-device upgrades because non-optional fields lack property-level defaults | Med | High | All `@Model` non-optional fields ship with property-level defaults from day one. Past learning encoded as a Phase 3 hard rule. |
| iPad runs in iPhone-compat mode, looks cramped | Med | Low | `TARGETED_DEVICE_FAMILY: "1,2"` from day one. Past learning. |
| `@Published` survivors silently no-op under `@Observable` | Med | Med | Migration cheat sheet in Phase 4; PR-review checklist item. |
| "Today" double-completes quests across timezone boundary | Low | Med | Pin device timezone at session start. |
| iCloud sync of HealthKit-derived SwiftData container = App Review violation | Low | High | `ModelContainer` constructed with explicit CloudKit-disabled config. |

## Resource Requirements

- ~2-3 hours for an experienced iOS engineer (or Codex run executing `13_CODEX_BUILD_PROMPT.md`).
- ~30 min for ingestion (Phase A).
- ~30 min for review pass and PR polish.

## Future Considerations

After this plan lands, the obvious follow-ups (each its own plan):

1. **Live HealthKit wiring.** Replace `MockHealthKitService` with `LiveHealthKitService`; progressive permission flow; real-device testing.
2. **SwiftData persistence.** Persist `UserProfile`, `HabitLog`, `LifeClockEstimate`, `Quest` across cold starts.
3. **StoreKit 2 paywall.** Implement `PaywallService`; annual/monthly/lifetime products; restore purchases.
4. **Widgets / Lock Screen** (per founder pack roadmap).
5. **Brand resolution** (Open Question 1): resolve to `LifeClock` or `TimeBack` / `LongGame` / `DayBank` / `Clockwise` / `HealthspanQuest`. Centralized strings file makes this a one-PR rename.
6. **App icon options** generation (mirroring `docs/products/after-plans/app-icon-options/` workflow).

## Documentation Plan

- New: `docs/products/life-clock/` (ingested founder pack + 2 new files).
- New: `products/life-clock-ios/README.md`.
- Update: `infra/products.json` (registry entry).
- No CLAUDE.md changes needed — the artifact-chain skill already discovers products via registry.

## Sources & References

### Origin

- **Founder pack:** `/Users/simons/Downloads/Life_Clock_Founder_Pack_Markdown/` (18 markdown files, 2898 lines total). Key decisions carried forward:
  1. Wedge = "earn time back with better daily habits" (not death prediction).
  2. Local-first, SwiftData, HealthKit-mockable; no backend in v1.
  3. ClockEngine and QuestEngine are deterministic pure Swift.
  4. Three tone modes (gentle / coach / mementoMori).
  5. No medical claims; non-blocking medical disclaimer required.

### Internal References

- After Plans iOS scaffold (the closest analog): [products/after-plans-ios/project.yml](products/after-plans-ios/project.yml), [products/after-plans-ios/Sources/](products/after-plans-ios/Sources/), [products/after-plans-ios/README.md](products/after-plans-ios/README.md).
- Product registry loader: [packages/config/products.py:8](packages/config/products.py).
- Product registry: [infra/products.json](infra/products.json).
- After Plans docs (canonical artifact-chain example): [docs/products/after-plans/](docs/products/after-plans/).
- Skill: `product-artifact-chain` — `skills/adapters/claude/product-artifact-chain.md`.
- Skill: `ios-build-and-sign` — `skills/adapters/claude/ios-build-and-sign.md`.

### External References (from founder pack)

- [S1] Death Clock: The Life Lab — competitive benchmark.
- [S2] RevenueCat State of Subscription Apps 2026.
- [S3] Apple HealthKit — Protecting user privacy.
- [S4] Apple HealthKit — Authorizing access to health data.
- [S5] Apple HealthKit — `HKQuantityTypeIdentifier`.
- [S6] Apple App Review Guidelines.
- [S7] Apple App privacy details on the App Store.
- [S8] CDC FastStats — Life Expectancy (population anchor for ClockEngine baseline).
- [S9] CDC Adult Activity Guidelines (anchor for movement quest target: 150 min/wk + 2× strength).

### Related Work

- `docs/plans/2026-04-20-001-feat-catchbook-app-store-submission-automation-plan.md` (precedent for new-product planning conventions).
- `docs/plans/2026-04-27-001-feat-after-plans-context-model-refactor-plan.md` (same date, separate lane).

## Pipeline Mode Notes

This plan was authored in LFG pipeline mode. Per pipeline rules, no `AskUserQuestion` prompts were issued; decisions were made automatically based on:

- The founder pack content as ingested at 2026-04-27.
- The After Plans iOS scaffold as the canonical pattern to mirror.
- The founder's stated direction in the original message ("under products/life-clock-ios").

The next pipeline step is `/compound-engineering:deepen-plan`, which will expand each phase with parallel research agents. After that, `/workflows:work` executes Phase 1 → Phase 5.
