---
title: History Feature Hardening Pass — Pro Gate, Performance, Simplification, Tests
type: refactor
status: active
date: 2026-05-01
origin: docs/brainstorms/2026-05-01-history-deferred-followups-brainstorm.md
---

# History Feature Hardening Pass — Pro Gate, Performance, Simplification, Tests

## Enhancement Summary

**Deepened on:** 2026-05-01
**Sections enhanced:** all four phases + acceptance criteria + risks
**Research agents used:** architecture-strategist, performance-oracle, code-simplicity-reviewer, data-integrity-guardian, framework-docs-researcher

### Major scope cuts applied (simplicity reviewer)

The original plan over-spec'd Phase 1's downgrade machinery and Phase 2's speculative perf optimizations. Trimmed:

- **Cut downgrade banner persistence + transition observer**. The `.notEntitled` error surfaced inline in `OverrideSheet` is the banner — at the moment of friction, where the user can act on it. No `lastSeenIsPro` field, no `evaluateDowngrade`, no `showsDowngradeBanner` flag, no separate banner row in `HistoryView`, no `LifeClockStoreDowngradeTests`.
- **Cut NSCache for decoded override map**. Self-admitted ≤1ms total decode cost. Adds invalidation logic + the `Data.hashValue` collision bug flagged by the data-integrity review (`hashValue` is per-launch and can collide across snapshots → silent data corruption). YAGNI.
- **Cut `recomputeYesterdayDelta` debounce**. `OverrideSheet` is modal + single-field with explicit Save tap; the "4 rapid edits" scenario is contrived. Cancellation race is real (architecture review item 7) but only matters if we add the debounce in the first place.
- **Cut `@Query` switch from the proxy method**. No measurement; risk of destabilizing sheet presentation flagged by architecture review. Keep the existing proxy, revisit after profiling shows a real problem.
- **Cut hand-rolled snapshot test infrastructure** for `ClockHandView`. PNG baselines + SHA256 hashing + `__Snapshots__/` directory + Xcode-version rebaseline dance for 4 visual variants is the worst trade in the plan. Visual regressions in this view are visible in a 2-second simulator glance.
- **Cut `PaywallTeaser` extraction** (only 2 sites — extract on the third), `DayHistoryRow` file move, and `SnapshotOverrideAccess` inline. Pure shuffling.

### Critical correctness fixes applied (data-integrity reviewer)

- **The plan's claim "engine ignores overrides while !isPro" was factually wrong.** `effectiveValue` reads through `overrideMap.value(for:)` unconditionally, so existing overrides remain effective post-downgrade. Resolution chosen: **(A) honor existing overrides post-downgrade as a grace period.** No new overrides can be made (write-site `.notEntitled` throw) and the `OverrideSheet` error message says exactly this: *"New adjustments are paused — Pro only. Existing adjustments stay active."* Existing overrides are inert only in the limited sense that the user can no longer modify or revert them through the editor. This avoids the entitlement leak into the engine read site.
- **Sleep cannot use `HKStatisticsCollectionQuery`** — it's a `HKCategoryType`, not a quantity type; the collection query has no aggregator for sleep enums. Plan's "4 queries total" was wrong. Real shape: 3 collection queries (steps, exercise, active energy) + ~90 per-day sample queries for sleep = ~93 queries total. Still a 5-6× win, not 100×.
- **Wall-clock target revised**: `<8s cold launch, <3s warm` (was `<3s` flat, which assumes warm HK cache).
- **Pin `anchorDate` to `EngineClock.startOfDay(for: endingAt) - days.days`** so HK's bucket boundaries align with our day keys. DEBUG assertion that bucket count == requested days. Add a parity test that runs both paths against the same mock and asserts per-day-key equality (excluding sleep).
- **Drop blur entirely; use `.opacity(0.35)` + lock chip** for locked rows. Performance reviewer notes blur is ~3-5ms/frame on iPhone 12 even as a single overlay. Opacity + chip reads as locked, costs nothing on the GPU.

### Architectural refinements (architecture reviewer)

- **`EntitlementProviding` protocol instead of closure DI** for `isPro` source. Greppable, mockable, signals intent at the type level.
- **Wrap two-step persist + banner-flag write inside `evaluateDowngrade`** as a single method (no inline call sites). Add a save-failure test.
- **Forbid behavioral additions to `FieldSpec`** via a doc comment — keep it data + 2 closures only.

### Net impact

Phase 1: 0.75d → ~0.2d. Phase 2: 1.5d → ~0.75d. Phase 3: 0.5d → ~0.3d. Phase 4: 1d → ~0.5d. **Total: ~3-4d → ~1.75d.** Every measurable correctness/perf win retained; speculative scaffolding cut.

## Overview

Bundled cleanup + hardening pass on the History/Wrap-Ups/Overrides feature shipped in [PR #18](https://github.com/kashane1/ai-company-os/pull/18). The base feature works end-to-end, but the multi-agent review of the last commit surfaced a list of items that were intentionally deferred so the user-visible feature could ship first. This plan consolidates those items into a coherent next slice.

Four buckets, ordered by risk:

1. **Functional correctness** — Pro-tier gate on overrides + downgrade banner.
2. **Performance** — `HKStatisticsCollectionQuery` for the 90-day import; `LazyVStack` + single blur in History; `@Query` for the snapshot list; decoded-override cache; recompute debounce.
3. **Simplicity** — `FieldSpec` collapses 5 switch tables; shared `PaywallTeaser`; file extractions.
4. **Tests** — `ClockHandView` snapshot tests; re-edit-after-revert pin; wrap-up UITests.

(see brainstorm: [docs/brainstorms/2026-05-01-history-deferred-followups-brainstorm.md](docs/brainstorms/2026-05-01-history-deferred-followups-brainstorm.md))

## Problem Statement

PR #18 shipped the user-visible history surface and the Pro override flow end-to-end (40+ tests, 5 commits, P1 review findings remediated). But several items were intentionally cut from scope to keep the PR shippable:

- **Pro→Free downgrade leaves overrides authoritative.** `OverrideService.applyOverride` writes the override value through to the raw HK field so the engine sees it. There is currently no `isPro` gate at either the write site or the engine read site, so a downgraded user keeps seeing corrected values forever (or, if the persister later reconciles HK back over the raw, sees the override silently disappear). The plan called for "overrides remain stored but engine ignores them while !isPro" — not implemented.
- **No downgrade notice.** Plan called for a one-time "Your adjustments are paused" tone-aware banner. Not implemented; no `lastSeenIsPro` tracking exists.
- **90-day import is slow.** Current path issues ~540 HK queries (per-day fan-out × 6 metrics). The deepening pass called for a single `HKStatisticsCollectionQuery` per metric across the 90-day window — 4 queries total. Estimated improvement: 45-120s → <3s.
- **Performance hot paths in History list.** `ScrollView { ForEach }` builds all 83 blurred rows up front; `effectiveValue` decodes JSON per access (12 decodes per `DayDetailView` render, 90 per History list); `recentSnapshots(limit: 90)` re-fetches on every observed mutation; redundant `recomputeYesterdayDelta` on rapid edits.
- **Code repetition.** 5 separate `switch on Field` tables (`isValid`, `assignRawValue`, `prefill`, `keyboardType`, `bounds`, `format`, `rawValue(for:)`). Adding a 5th overridable field today means editing 6+ sites.
- **Test gaps.** No `ClockHandView` snapshot tests (positive/negative/zero/reduce-motion). No pin on the re-edit-after-revert behavior the data-integrity reviewer flagged. No UITests for the wrap-up first-open flow.

Bundling these into one PR (vs. one-PR-per-item) avoids constant rebase churn — most touch the same files (`HistoryView`, `OverrideService`, `SnapshotOverrideMap`, `LifeClockStore`).

## Proposed Solution

A **single follow-up PR** that lands the four buckets in dependency order so each phase compiles + tests cleanly on its own commit. Total target: ~3-4 days.

### High-level shape

- **Phase 1 (Functional)**: add `lastSeenIsPro: Bool = true` to `UserProfile`. `LifeClockStore` observes `subscriptions.isPro`; on transition true→false, set a `showsDowngradeBanner` flag and persist `lastSeenIsPro = false`. `OverrideService.applyOverride` and `revertOverride` short-circuit with `OverrideError.notEntitled` when `!isPro`. `effectiveValue(for:)` is unchanged (overrides remain in storage); the engine read site is shielded by the write-site refusal — no overrides can be added or modified while not Pro, and existing ones revert to raw via the override-aware persister's nil-guard already in place.
- **Phase 2 (Performance)**: Refactor `LiveHealthKitService` to add a `recentSnapshotsCollection(endingAt:days:)` method that issues one `HKStatisticsCollectionQuery` per metric. `HistoricalImportCoordinator` switches to the collection path. `HistoryView` switches to `LazyVStack` and renders one blur overlay over the locked region. `HistoryView` switches to `@Query` for the snapshot list. `SnapshotOverrideAccess` caches the decoded `SnapshotOverrideMap` keyed on `overridesData`. `LifeClockStore.applyOverride` debounces the recompute via a 300ms trailing timer keyed on `dayStart`.
- **Phase 3 (Simplicity)**: Define `FieldSpec` on `SnapshotOverrideMap.Field` with `(keyboardType, bounds, formatter, rawGetter, rawSetter)`. Replace 5 switch tables with single-spec lookups. Extract `PaywallTeaser(title:body:cta:onTap:)` shared component. Move `DayHistoryRow` to its own file. Inline `SnapshotOverrideAccess` into `SnapshotOverrideMap.swift`. Extract `OverrideService` private `commit(snapshot:overrides:originals:recomputedAt:)` helper.
- **Phase 4 (Tests)**: Add `ClockHandViewSnapshotTests` (4 variants). Add `OverrideServiceTests.testReEditAfterRevertReCapturesOriginal`. Add `WrapUpFlowUITests` covering tab title, first-open trigger, dismiss path.

## Technical Approach

### Architecture

```
                  ┌──────────────────────────────┐
                  │   SubscriptionStore (existing) │
                  │     isPro: Bool                │
                  └────────────┬─────────────────┘
                               │ observed by store on isPro change
                               ▼
┌──────────────────────────────────────────────────────────┐
│                    LifeClockStore                        │
│  • showsDowngradeBanner: Bool        (NEW, Phase 1)      │
│  • applyOverride: refuses if !isPro  (NEW, Phase 1)      │
│  • debouncedRecompute(dayStart:)     (NEW, Phase 2)      │
│  • Uses recentSnapshotsCollection()  (NEW, Phase 2)      │
└──────────────────────────────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────┐
│   LiveHealthKitService                                   │
│  • recentSnapshotsCollection(endingAt:days:)  (NEW)      │
│    → 1 HKStatisticsCollectionQuery per metric            │
└──────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────┐
│                    HistoryView                           │
│  • @Query<DailyHealthSnapshot>     (NEW, Phase 2)        │
│  • LazyVStack + single blur overlay (NEW, Phase 2)       │
│  • Downgrade banner row             (NEW, Phase 1)       │
│  • Uses shared PaywallTeaser        (NEW, Phase 3)       │
└──────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────┐
│   SnapshotOverrideMap                                    │
│  • Field.spec: FieldSpec             (NEW, Phase 3)      │
│  • Cached decoded map (NSCache)      (NEW, Phase 2)      │
└──────────────────────────────────────────────────────────┘
```

### Data Model

Schema delta is tiny — one new optional field on `UserProfile`:

```swift
// In LifeClockSchemaV1.UserProfile (additive, lightweight migration safe):
/// Tracks `subscriptions.isPro` across launches so we can detect a
/// Pro→Free transition and show the downgrade banner exactly once.
/// Default `true` so existing pre-feature users (likely free) get the
/// "first-time downgrade" path on first open of this build, not the
/// "unchanged" path. Reset to current `isPro` after the banner is shown.
var lastSeenIsPro: Bool = true
```

No other schema changes.

### Implementation Phases

#### Phase 1 — Pro gate (TRIMMED post-deepening)

**Tasks:**

1. **Add `OverrideService.OverrideError.notEntitled`**. `LifeClockStore.applyOverride(field:value:on:)` and `revertOverride(field:on:)` check entitlement before delegating to the service. Throws `.notEntitled` if `!isPro`.

2. **`EntitlementProviding` protocol** ([Sources/Services/EntitlementProviding.swift](products/life-clock-ios/Sources/Services/EntitlementProviding.swift), NEW):
   ```swift
   protocol EntitlementProviding {
       var isPro: Bool { get }
   }
   extension SubscriptionStore: EntitlementProviding {}
   ```
   `LifeClockStore` takes an `entitlements: EntitlementProviding?` (optional so existing test ctors don't need updating). When nil, `applyOverride` always throws `.notEntitled`. `LifeClockApp` injects `subscriptions` after constructing both.

3. **`OverrideSheet` error path**: catch `.notEntitled`, surface tone-aware inline copy: *"New adjustments are paused — Pro only. Existing adjustments stay active. Re-subscribe in Profile."* This IS the downgrade notice — at the moment of friction. No separate banner row in HistoryView.

4. **Tone copy**: `ToneMode.overrideNotEntitledMessage` (gentle / coach variants). Both convey "stays active" — honors existing-overrides-grace product decision (see Enhancement Summary).

**Deliverables:**
- `Sources/Services/EntitlementProviding.swift` (NEW protocol)
- `Sources/Services/SubscriptionStore.swift` (conformance)
- `Sources/Services/OverrideService.swift` (.notEntitled case)
- `Sources/App/LifeClockStore.swift` (entitlements injection + .notEntitled throw)
- `Sources/App/LifeClockApp.swift` (inject `subscriptions` as EntitlementProviding)
- `Sources/App/ToneMode.swift` (1 new copy key)
- `Sources/Features/History/OverrideSheet.swift` (.notEntitled error UI)
- `Tests/OverrideServiceTests.swift` (test apply/revert throw .notEntitled when entitlements absent or `isPro == false`)

**Success criteria:** 2 new test cases pin the gate. Manual TestFlight: downgrade via StoreKit sandbox refund, attempt edit → tone-aware error appears in sheet; existing overrides still affect History/Today scores.

**Estimated effort:** 0.2 day.

#### Phase 2 — Performance (TRIMMED post-deepening)

**Tasks:**

1. **`LiveHealthKitService.recentSnapshotsCollection(endingAt:days:)`** ([Sources/Services/LiveHealthKitService.swift](products/life-clock-ios/Sources/Services/LiveHealthKitService.swift)):
   - **Quantity metrics via `HKStatisticsCollectionQuery`**: one query each for steps (`.cumulativeSum`), exercise (`.cumulativeSum`), active energy (`.cumulativeSum`). `intervalComponents = DateComponents(day: 1)`. **`anchorDate` pinned to `clock.startOfDay(for: endingAt - days.days)`** so HK's bucket boundaries align with our day keys (data-integrity reviewer item 4). `initialResultsHandler` only — no `statisticsUpdateHandler`.
   - **Sleep stays per-day** via the existing `HKSampleQuery` path. `HKStatisticsCollectionQuery` doesn't support category samples; wake-day attribution must stay in app code (framework-docs reviewer items 1-2).
   - **DEBUG assertion**: bucket count for each collection query == requested days.
   - Add to the protocol:
     ```swift
     func recentSnapshotsCollection(
         endingAt: Date, days: Int
     ) async -> [DailyHealthSnapshot]
     ```
   - Default-implement on the protocol falling back to `recentSnapshots(endingAt:count:)` so `MockHealthKitService` doesn't need updating.

2. **`HistoricalImportCoordinator.importChunk` switches to collection path** for the chunk's quantity metrics; sleep continues per-day within the chunk. Net: ~3 collection queries + ~90 sleep sample queries = ~93 queries for 90-day import (was ~540). Idempotent per-day upsert preserved. **Single `try modelContext.save()` per chunk** (data-integrity reviewer item 6 — verify current code is per-chunk; pin with a save-count test).

3. **`HistoryView` LazyVStack + opacity-locked rows** (NOT blur):
   - `ScrollView { LazyVStack { ForEach } }` for deferred materialization.
   - Locked rows render with `.opacity(0.35)` + a centered lock chip. **No `.ultraThinMaterial` overlay, no `.blur()`** — performance reviewer item 5: blur is ~3-5ms/frame on iPhone 12 even as a single overlay; opacity + chip costs nothing on the GPU and reads as locked.

4. **Parity test** (`Tests/HistoricalImportCollectionQueryTests.swift`, NEW):
   - Mock that supplies the same per-day fixture data via both paths.
   - Assert per-`dayKey` equality for stepCount, exerciseMinutes, activeEnergyKcal across at least 7 days **including a DST boundary** (2026-03-08 in `America/Los_Angeles`).
   - Sleep parity NOT asserted (different code path by design).

**Deliverables:**
- `Sources/Services/HealthKitServiceProtocol.swift` (new method + protocol default)
- `Sources/Services/LiveHealthKitService.swift` (collection-query impl, sleep stays sample-based)
- `Sources/Services/HistoricalImportCoordinator.swift` (use collection path; pin per-chunk save)
- `Sources/Features/History/HistoryView.swift` (LazyVStack + opacity-locked rows)
- `Tests/HistoricalImportCollectionQueryTests.swift` (NEW — parity test incl. DST boundary)

**Success criteria:**
- 90-day import wall-clock: **<8s cold launch, <3s warm** (revised from `<3s` per perf reviewer item 1).
- ~93 HK queries on import path (was ~540).
- HistoryView scrolls 60fps with 90 rows on iPhone 12 / iOS 17 (manual check).
- Parity test passes for DST boundary day.

**Estimated effort:** 0.75 day.

#### Phase 3 — Simplicity (TRIMMED post-deepening)

**Tasks:**

1. **`FieldSpec`** on [Sources/Models/SnapshotOverrideMap.swift](products/life-clock-ios/Sources/Models/SnapshotOverrideMap.swift):
   ```swift
   extension SnapshotOverrideMap.Field {
       /// Static metadata + raw-field accessors per overridable field.
       /// DELIBERATELY DATA-ONLY — do not add behavior (rendering,
       /// validation pipelines, etc.) to this type. The whole point is
       /// that adding a new overridable field becomes one Spec entry, not
       /// edits across 7 switch sites. Behavior belongs on the consumers.
       struct Spec {
           let displayName: String
           let keyboard: UIKeyboardType
           let bounds: ClosedRange<Double>
           let boundsCopy: String
           let format: (Double) -> String
           let rawGetter: (DailyHealthSnapshot) -> Double?
           let rawSetter: (DailyHealthSnapshot, Double) -> Void
       }
       var spec: Spec { ... single switch returning the spec ... }
   }
   ```
   Replace switches in: `OverrideService.isValid` → `field.spec.bounds.contains(value)`; `OverrideService.assignRawValue` → `field.spec.rawSetter(snapshot, value)`; `SnapshotOverrideAccess.rawValue(for:)` → `field.spec.rawGetter(snapshot)`; `OverrideSheet.prefill/keyboardType/bounds` → `field.spec.{format,keyboard,boundsCopy}`; `DayDetailView.format` → `field.spec.format(value)`.

2. **`OverrideService.commit(snapshot:overrides:originals:recomputedAt:)`** private helper. `applyOverride` and `revertOverride` both end with this 5-line block; extract.

**Cuts (per simplicity reviewer):**
- ~~Shared `PaywallTeaser` extraction~~ — 2 sites isn't a pattern; extract on the third.
- ~~`DayHistoryRow` file move~~ — pure shuffling.
- ~~Inline `SnapshotOverrideAccess`~~ — pure shuffling.

**Deliverables:**
- `Sources/Models/SnapshotOverrideMap.swift` (add `FieldSpec` extension)
- `Sources/Services/SnapshotOverrideAccess.swift` (use spec for `rawValue(for:)`)
- `Sources/Services/OverrideService.swift` (use spec for isValid/assignRawValue + commit helper)
- `Sources/Features/History/OverrideSheet.swift` (use spec for prefill/keyboard/bounds)
- `Sources/Features/History/DayDetailView.swift` (use spec for format)

**Success criteria:** All Phase 1 + Phase 2 tests still pass. `grep -r "switch.*Field" Sources/` returns only the single `var spec` accessor.

**Estimated effort:** 0.3 day.

#### Phase 4 — Tests (TRIMMED post-deepening)

**Tasks:**

1. **`OverrideServiceTests.testReEditAfterRevertReCapturesOriginal`** — pins the data-integrity reviewer's verified-but-untested behavior:
   - Apply override 12_000 (captures original 8_000).
   - Revert (clears override + original; raw restored to 8_000).
   - Apply override 9_000 again (re-captures original 8_000 from current raw).
   - Revert (raw restored to 8_000).
   - Two snapshot fetches confirm `originalHealthKitValue` re-population at each step.

2. **`SnapshotOverrideMapDecodeFailureTests`** (small) — write garbage bytes to `overridesData`, fetch via accessor, assert empty map. Use `XCTExpectFailure` to capture the DEBUG `assertionFailure`.

3. **`WrapUpFlowUITests`** ([UITests/WrapUpFlowUITests.swift](products/life-clock-ios/UITests/WrapUpFlowUITests.swift), NEW):
   - **Tab rename**: launch app, assert tab bar has "History" not "Weekly"; tap → assert nav title "History".
   - **First-open trigger** (with `LIFECLOCK_LAUNCH_FORCE_WRAP_UP=1` env override that pre-seeds yesterday data + `lastShownYesterdayWrapUpDay = nil + onboarded 2 days ago`): launch app → assert wrap-up sheet appears within 5 seconds of `.active`. Tap dismiss → assert sheet disappears.
   - **Single-show**: relaunch app (sheet would have been dismissed in step 2) → assert NO wrap-up sheet appears within 5s.

   Add a `LaunchConfiguration.forceWrapUpScenario` flag mirroring `forcePaywall`; pre-seed the database in `seedInitialStateIfNeeded` when set.

**Cuts (per simplicity reviewer):**
- ~~`ClockHandViewSnapshotTests` + hand-rolled snapshot infrastructure~~ — adding new test infra (PNG baselines, SHA256 hashing, `__Snapshots__/` dir, Xcode-version rebaseline dance) for 4 visual variants of one view is a poor trade. Visual regressions in `ClockHandView` are visible in a 2-second simulator glance. Revisit if `swift-snapshot-testing` lands as a project-wide dep.

**Deliverables:**
- `Tests/OverrideServiceTests.swift` (1 new case)
- `Tests/SnapshotOverrideMapDecodeFailureTests.swift` (NEW, 1 case)
- `UITests/WrapUpFlowUITests.swift` (NEW, 3 cases)
- `Sources/App/LifeClockLaunchConfiguration.swift` (add `forceWrapUpScenario` flag)

**Success criteria:** Test count rises by 5 cases (1 re-edit + 1 decode + 3 UITests). Targeted test command runs in <60s.

**Estimated effort:** 0.5 day.

## Alternative Approaches Considered

- **One PR per item.** Rejected — most touch the same 4-5 files; rebase churn would dominate.
- **Full SwiftData V2 schema bump for `lastSeenIsPro`.** Rejected — additive optional Bool with default `true` is lightweight-migration safe; same precedent as PR #18's wrap-up date fields.
- **`isPro` checked at engine read site (in `effectiveValue`)** rather than at the write site. Rejected — would require the engine or the accessor to consult the SubscriptionStore, leaking entitlement concerns into pure code paths. Refusing the write keeps the engine ignorant of Pro state.
- **`swift-snapshot-testing` SPM dep for `ClockHandView` tests.** Rejected for this slice — adds a new dep for 4 test cases. Hand-rolled snapshot approach is small enough.
- **Async iteration over `HKStatisticsCollectionQuery` results with backpressure.** Rejected — collection query returns all buckets at once via `enumerateStatistics`; no streaming concern.

## System-Wide Impact

### Interaction Graph

**Override write path (post-Phase 1):** user taps "Save" in `OverrideSheet` → `store.applyOverride` → `guard isProForOverrides else throw .notEntitled` → `OverrideService.applyOverride` → `commit(...)` → `try modelContext.save()` → `refreshDerivedStateAfterOverride` → debounced 300ms timer → `recomputeYesterdayDelta + recomputePendingWrapUp` → SwiftUI re-render via Observable.

**Downgrade path (post-Phase 1):** `subscriptions.isPro` flips false → `LifeClockStore` observes via Phase 1's reactive hook (or scenePhase + bootstrap) → `evaluateDowngrade(currentIsPro: false)` → if `profile.lastSeenIsPro` was true: set `showsDowngradeBanner = true`, persist `profile.lastSeenIsPro = false`, `try modelContext.save()` → `HistoryView.downgradeBannerSection` renders → user dismisses → `showsDowngradeBanner = false` (banner gone for the session; persisted state ensures no re-show next launch).

**Import path (post-Phase 2):** user opens History tab → `historicalImporter.startIfNeeded()` → `Task { @MainActor in run() }` → for each chunk → `recentSnapshotsCollection(endingAt:days:)` → 4 `HKStatisticsCollectionQuery` callbacks land in parallel → assemble snapshots → idempotent upsert per dayKey → `try? modelContext.save()` per chunk → `status` mutation triggers UI re-render via @Observable.

### Error & Failure Propagation

- **`.notEntitled` from override write**: caught in `OverrideSheet`, surfaces tone-aware error inline; the snapshot is never mutated. No cleanup needed.
- **`HKStatisticsCollectionQuery` throws** (e.g. authorization revoked mid-import): collection query's error handler is called instead of `initialResultsHandler`. We catch and treat as "no data for this metric this chunk"; partial-snapshot-with-other-metrics still upserts. Status surfaces `.failed` only on full-import collapse.
- **`@Query` failures**: SwiftData returns empty array on fetch error; UI shows "Past days" header with no rows. Identical degraded-empty-state behavior.

### State Lifecycle Risks

- **`lastSeenIsPro` persistence atomicity**: setting `profile.lastSeenIsPro = false` and `showsDowngradeBanner = true` is two writes. The persistent one (lastSeenIsPro) MUST happen before the in-memory one — otherwise a crash mid-display could re-show the banner. Code path: `try modelContext.save()` on `profile.lastSeenIsPro = false` BEFORE setting `showsDowngradeBanner = true`.
- **Debounce + dismiss race**: if user dismisses the wrap-up sheet (which calls `markWrapUpShown` → save `lastShown*` to profile) while a debounced recompute is in flight from a prior override, the recompute lands and may produce a stale `pendingWrapUp`. Mitigation: `recomputePendingWrapUp` reads the current persisted profile state (via fresh fetch), not a snapshot from when the timer was scheduled.
- **`HistoricalImportCoordinator` cancellation while a chunk is mid-`enumerateStatistics`**: enumerateStatistics is synchronous-callback; cancellation is checked between chunks, not within a chunk. Acceptable — chunks are weekly so the worst-case overrun is ~1s.

### API Surface Parity

- `MockHealthKitService` does not need to implement `recentSnapshotsCollection` because of the protocol default-implementation falling through to `recentSnapshots(endingAt:count:)`. New tests targeting the collection path use a dedicated mock (file-private, like `ProvidedMockHealthKit` in `SnapshotPersisterOverrideAwareTests`).
- `OverrideService` API shape unchanged externally; adding `.notEntitled` is additive on the error enum (callers that didn't switch on it still compile).
- `LifeClockStore.applyOverride` signature unchanged; the `notEntitled` throw is new but flows through the existing `throws` declaration.

### Integration Test Scenarios

1. **Pro→Free→Pro round trip**: user is Pro, applies override 12_000; downgrades; apply throws `.notEntitled`; re-upgrades; apply succeeds. Verify `lastSeenIsPro` resets correctly.
2. **Banner shown exactly once per downgrade event**: simulate two foregrounds after downgrade; banner shows on first, not on second.
3. **Re-edit after revert re-captures original**: covered by Phase 4 test.
4. **`HKStatisticsCollectionQuery` partial-data day**: mock returns `nil` for steps on day N within the chunk; assert snapshot for day N is upserted with `stepCount = nil` (no zero-substitution).
5. **`@Query` re-renders on override write**: rendered snapshot count → `applyOverride` → re-render fires → updated row visible. Pin via SwiftUI ViewInspector or by counting body invocations.

## Acceptance Criteria

### Functional Requirements

- [ ] `UserProfile.lastSeenIsPro: Bool = true` persists across launches.
- [ ] `LifeClockStore.applyOverride` and `revertOverride` throw `.notEntitled` when `isPro` source returns false.
- [ ] `OverrideSheet` surfaces tone-aware copy on `.notEntitled` and does not mutate the snapshot.
- [ ] On Pro→Free transition (observed via `subscriptions.isPro` change OR via `bootstrap` discovery), banner shows once and `lastSeenIsPro` is persisted false.
- [ ] On Free→Pro transition, `lastSeenIsPro` is reset to true.
- [ ] Banner copy is tone-aware (gentle / coach variants).

### Non-Functional Requirements

- [ ] 90-day import: ≤4 HK queries on the optimized path, wall-clock <3s on iPhone 17 sim.
- [ ] HistoryView scrolls 60fps with 90 rows on iPhone 12 / iOS 17 (manual check).
- [ ] `effectiveValue(for:)` decode count: ≤1 per snapshot per render (cache hit on repeated reads).
- [ ] `recomputeYesterdayDelta` debounce: 4 rapid edits → 1 recompute.
- [ ] No regression in existing test suite (40+ existing targeted tests stay green).

### Quality Gates

- [ ] `FieldSpec` is the single source of truth — grep `switch` on `Field` returns only `spec` accessor.
- [ ] No new dependencies added (no `swift-snapshot-testing`, no third-party SDKs).
- [ ] `git diff --stat` shows net LOC reduction in HistoryView + OverrideSheet + DayDetailView.
- [ ] No `Date()`, `Date.now`, `Calendar.current`, `TimeZone.current` outside `EngineClock.swift` (CI grep continues to pass).
- [ ] No occurrences of `diagnose|prescribe|guarantee` in new copy (extends existing forbidden-vocab grep).
- [ ] DEBUG `LifeClockContainer` assertion still fires correctly (confirmed via test).

## Success Metrics

- **Code quality**: switch-on-Field count drops from 7 to 1; LOC across HistoryView + OverrideSheet + DayDetailView decreases ~150 lines.
- **Performance**: 90-day import on real device <3s (vs. 45-120s); History list re-render <5ms on override edit.
- **Correctness**: Pro→Free downgrade banner fires exactly once per transition (proven by integration test); overrides are inert post-downgrade (proven by `.notEntitled` test).

## Dependencies & Risks

| Risk | Severity | Mitigation |
|---|---|---|
| `HKStatisticsCollectionQuery` differs from per-day fan-out in ways the mock can't replicate (e.g. wake-day attribution for sleep) | Medium | Keep the per-day path as fallback in production for sleep specifically; opt collection-only for steps/exercise/active energy in Phase 2; convert sleep in a follow-up after live-device validation. |
| `@Query` causes unexpected re-renders that destabilize sheet presentation | Medium | A/B keep the proxy method available; if regressions surface, revert just that piece. |
| NSCache eviction under memory pressure causes a single-snapshot decode storm | Low | Bounded `countLimit = 90` (matches max snapshots in History); decode is fast enough that worst-case is acceptable. |
| Hand-rolled snapshot tests are brittle to font-rendering deltas across simulator versions | Medium | Use `XCTExpectFailure` at sim-version mismatches; record baselines on iPhone 17 / iOS 26.4 only; document that rebaseline is expected on Xcode major bumps. |
| `lastSeenIsPro` default `true` for upgrade users means they see the banner on first install of this build IF they happen to be on Free at that moment | Low | Acceptable: the banner is supportive ("re-subscribe to keep them"), and upgrade users would not have any overrides anyway. Document in PR. |

## Resource Requirements

- 1 iOS engineer. 3-4 calendar days end-to-end across 4 phases.
- Founder review at end of Phase 1 (downgrade UX) and Phase 4 (snapshot baselines) before TestFlight cut.

## Future Considerations

- **`HKStatisticsCollectionQuery` for daily refresh path** — current `LifeClockStore.refreshFromHealthKit` still uses `dailySnapshot(for:)` for today. Could collapse to a 1-day collection query for parity. Not blocking; only saves ~5 HK calls per foreground refresh.
- **Per-day cache invalidation on the collection import** — if the same day re-imports while overridden, the override-aware persister handles it. But could pre-filter `dayKey`s before issuing the collection query to avoid unnecessary network/HK work. Optimization-of-an-optimization; defer.
- **Background delivery for fresh-day data** — `enableBackgroundDelivery` so wrap-ups can fire without requiring a foreground. Needs entitlement review and a separate brainstorm.
- **`swift-snapshot-testing` adoption** — once snapshot tests prove valuable and a critical mass of UI components ships, add the dep and migrate hand-rolled tests.

## Documentation Plan

- Update [docs/products/life-clock/MONETIZATION.md](docs/products/life-clock/MONETIZATION.md) — document the downgrade banner copy + behavior.
- Update [docs/products/life-clock/PHASE_STATUS.md](docs/products/life-clock/PHASE_STATUS.md) — mark History feature as fully shipped (post-merge).
- Update [docs/products/life-clock/TECHNICAL_ARCHITECTURE.md](docs/products/life-clock/TECHNICAL_ARCHITECTURE.md) — document `FieldSpec` pattern + decoded-override cache.
- Add new solution doc when shipped: `docs/solutions/integration-issues/swiftdata-codable-data-fields-with-cache.md`.

## Sources & References

### Origin

- **Brainstorm document:** [docs/brainstorms/2026-05-01-history-deferred-followups-brainstorm.md](docs/brainstorms/2026-05-01-history-deferred-followups-brainstorm.md). Key decisions carried forward:
  - Bundle all deferred items into one PR (vs. one per item) to avoid rebase churn.
  - Functional correctness first (Pro gate + banner), then performance, then simplicity, then tests.
  - `isPro` check at write site, not engine read site (keeps engine ignorant of entitlement).
  - `HKStatisticsCollectionQuery` 1-query-per-metric (4 queries total).
  - Hand-rolled snapshot tests (no `swift-snapshot-testing` dep yet).

### Internal References

- Origin PR: [PR #18](https://github.com/kashane1/ai-company-os/pull/18) — base feature implementation.
- Plan that produced PR #18: [docs/plans/2026-04-30-feat-history-wrapups-and-overrides-plan.md](docs/plans/2026-04-30-feat-history-wrapups-and-overrides-plan.md).
- Override service: [products/life-clock-ios/Sources/Services/OverrideService.swift](products/life-clock-ios/Sources/Services/OverrideService.swift)
- Override map: [products/life-clock-ios/Sources/Models/SnapshotOverrideMap.swift](products/life-clock-ios/Sources/Models/SnapshotOverrideMap.swift)
- History view: [products/life-clock-ios/Sources/Features/History/HistoryView.swift](products/life-clock-ios/Sources/Features/History/HistoryView.swift)
- Subscription store: [products/life-clock-ios/Sources/Services/SubscriptionStore.swift](products/life-clock-ios/Sources/Services/SubscriptionStore.swift)
- Engine clock: [products/life-clock-ios/Sources/Engines/EngineClock.swift](products/life-clock-ios/Sources/Engines/EngineClock.swift)

### External References

- Apple — [`HKStatisticsCollectionQuery`](https://developer.apple.com/documentation/healthkit/hkstatisticscollectionquery) — single-query-per-metric pattern.
- Apple — [`@Query` (SwiftData)](https://developer.apple.com/documentation/swiftdata/query) — incremental observer for SwiftUI lists.
- Apple — [`LazyVStack`](https://developer.apple.com/documentation/swiftui/lazyvstack) — lazy materialization for long lists.

### Related Work

- Resolved review todos from PR #18: `todos/03[4-8]-complete-*.md`, `todos/04[0-3]-complete-p1-*.md`.
- Outstanding deferred todos: none — all consolidated into this plan.
