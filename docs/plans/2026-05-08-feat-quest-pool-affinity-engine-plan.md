---
title: "feat: Quest Pool & Per-Genre Affinity Engine"
type: feat
status: active
date: 2026-05-08
origin: docs/products/life-clock/plan-quest-generation-affinity.md
---

# feat: Quest Pool & Per-Genre Affinity Engine

## Overview

Replace Life Clock's ~15 hardcoded daily quests with a 90-quest pre-authored pool (30 per genre × 3 genres: `activity / diet / sleep`), tone-keyed at the slug level (gentle / coach / firmDirect), selected via per-genre affinity scores plus driver- and HealthKit-derived need-weights. Adds a four-event tracking table (`shown / picked / replaced / completed`) so the system can detect refusals without an explicit dismiss UI. Absorbs the previously-planned V3 78-string tone-keying pass.

This plan is the implementation blueprint for design decisions D1–D10 in [the brainstorm](docs/products/life-clock/plan-quest-generation-affinity.md). Decisions are not re-litigated here; they are translated into file-level work, ordering, migrations, and acceptance criteria.

## Enhancement Summary

**Deepened on:** 2026-05-08
**Sections enhanced:** Architecture (file consolidation), Schema (type-safe tone keying, performance fields), Migration (additive vs in-place), Phases (split cutover, transactional resolver), Risk Table (new rows for retention/race/Set<Date>), Performance Acceptance (rephrased budget), Sources (recommender-systems + iOS framework citations).
**Research agents used:** best-practices-researcher, framework-docs-researcher, architecture-strategist, code-simplicity-reviewer, data-integrity-guardian, performance-oracle, pattern-recognition-specialist.

### Key improvements applied

1. **File consolidation 6 → 3.** `QuestPool.swift` (types + loader + dictionary store + tone resolution), `QuestSelector.swift` (affinity EMA + need-weight + selection + EOD resolution), plus new types in `Sources/Models/QuestPoolTypes.swift`. Matches the existing engine convention (`QuestEngine.swift`, `ClockEngine.swift`).
2. **Type-safe tone key.** `[ToneMode: ToneCopy]` with custom `Codable` validating all three cases at load — surfaces missing-tone bugs as decode failures, not nil access at render.
3. **Incremental affinity cache.** `UserProfile.affinityState: Data` stores per-genre EMA scalar + lastUpdatedDate. New events fold in O(events-since-last-emit), not O(all events) — bounds the year-3 user at 30k events.
4. **Daily NeedWeight snapshot.** HK p50 reads cached per calendar day; reused across emits within the day.
5. **O(1) pool lookup.** `QuestPool` is backed by `Dictionary<String, PoolQuest>`; tone resolution is a single dictionary lookup per render.
6. **Additive migration, not in-place rewrite.** Add `Quest.genre: String = ""` (defaulted), populate from a slug→genre map at bootstrap, leave `Quest.category` intact. Avoids strand-on-rollback risk and the cross-table vocabulary split with `WeeklyReport.topPositiveDriver` strings.
7. **VersionedSchema migration plan.** SchemaV1 (current) → SchemaV2 (adds `QuestEvent`, adds `Quest.genre`, adds `UserProfile.distinctOpenDays: Int = 0` and `UserProfile.affinityState: Data = Data()`). All non-optional adds carry property-level defaults.
8. **JSON load failure: fail loud.** Production-pool malformed JSON crashes loud at app start in both DEBUG and RELEASE — it's a build defect, not a runtime condition. The fixture pool is test-only and never used as a release fallback.
9. **EOD resolver: idempotent, ScenePhase-driven, bounded walk.** `applicationWillEnterForeground` / `ScenePhase.active` is the load-bearing trigger; `BGAppRefreshTask` is opportunistic. Resolver is keyed by `yyyy-MM-dd` so double-fire is safe. Bulk batch-update for unresolved rows older than 30 days.
10. **Midnight race resolution.** Resolver and emit run in a single `ModelContext` transaction; resolver gates `resolvedKind` writes by "row written ≥ N seconds before midnight cutoff" to avoid stomping a `picked` placed at 23:59:30.
11. **`QuestEvent` retention policy.** 365-day rolling window; older rows roll up into a per-genre summary stored on `UserProfile`. Privacy-conscious, perf-bounded.
12. **Recommender-system math grounded.** EMA α=0.2 (half-life ≈ 3 events) is defensible but aggressive — pinned as `AffinityEngine.alpha` constant for retunability without code archaeology. recencyDecay curve set to `exp(-Δt/τ)` with τ=3.5 days (canonical Ding & Li 2005). Greedy + exclusion groups is provably optimal at slate=3 (matroid theory; Edmonds 1971).
13. **Phase 5 split.** Phase 5a: flip feature-flag default to true; bake ≥1 week. Phase 5b: delete inlined constructors + remove flag. Two PRs, not one.
14. **Test file naming corrected.** `<SourceFile>Tests.swift` convention: `QuestPoolTests`, `QuestPoolToneParityTests`, `QuestSelectorTests` (property-style is an implementation detail, not a separate file).
15. **Swift Testing coexists with XCTest.** New tests use Swift Testing (`#expect`, `@Test(arguments:)` for parameterized cases). PropertyBased library for selector property tests.

### New considerations discovered

- **No `Resources/` group exists in `project.yml` today** — this plan introduces the precedent for bundled JSON. Document the convention so CatchBook fishing-template work inherits it cleanly.
- **`WeeklyReport` strings encode old vocabulary** (`"movement"` / `"nutritionHabit"`). Additive migration prevents a vocabulary split here.
- **Drivers ↔ Quests still don't cross-feed.** ClockEngine reads drivers; QuestSelector reads drivers via NeedWeightEngine. Two engines independently interpreting drivers is duplication risk — flagged as out-of-scope but explicit so we don't pretend the boundary is clean.
- **Selector deadlock telemetry.** When the bounded conflict-resolution loop hits its cap, log a structured `selector.deadlock` event (slug pair, exclusion group, day) — not a console line. With 5–10 exclusion groups across 90 slugs, deadlock should be near-impossible; if it triggers, that's authoring rot, not normal operation.

## Problem Statement

[QuestEngine.generateDailyQuests](products/life-clock-ios/Sources/Engines/QuestEngine.swift) returns three quests per day from inlined Quest constructors across three categories that don't cleanly match Life Clock's mental model (`movement / sleepRecovery / nutritionHabit`), tone-monotone (same title and detail rendered for every `ToneMode`), with no driver feedback loop and no refusal signal. The same quest reappears regardless of whether the user has skipped it five days running. Day-1 onboarding signals (`dietQualityBaseline`, `smokingStatus`, `alcoholFrequency`, `sleepGoalHours`) and weeks of HealthKit history sit on disk unused by the quest engine.

This is a four-axis problem:
1. **Authoring scale.** 15 → 90 slugs × 3 tones = 270 strings + targets, deterministic at runtime.
2. **Personalization without LLM.** Selection must be explainable, testable, deterministic given inputs + seed, and yet feel personal.
3. **Hidden-affinity escape valve.** Affinity is invisible to the user with no override UI, so refusal detection has to be loud enough that "I hate this genre" surfaces in selection without an explicit dismiss button.
4. **Tone parity correctness.** Once tone-keyed copy is per-slug authored, drift between `gentle / coach / firmDirect` for a given slug becomes a build-time correctness bug, not a polish issue.

## Proposed Solution

A data-driven quest pool stored in JSON resource files, loaded into a typed in-memory pool at app start, scored daily by an `AffinityEngine` (preference EMA per genre) × `NeedWeightEngine` (driver/HK/onboarding-derived priority per genre), selected by a `QuestSelector` that respects exclusion-group conflict avoidance and a hard genre floor, and observed via four lifecycle events stored in a new `QuestEvent` SwiftData entity.

**See brainstorm for the rationale on every major decision** — this plan does not re-derive D1 (genre rename), D2 (intent grid), D3 (parity tuple anchor), D4 (slug convention), D5 (four-event surface), D6 (EMA × need-weight, hard floor), D7 (cold-start with HK trump), D8 (greedy selector + exclusion groups), D9 (four-layer test plan), or D10 (5-phase delivery).

## Technical Approach

### Architecture

#### New types

```swift
// products/life-clock-ios/Sources/Models/QuestPoolTypes.swift  (new)

enum Genre: String, CaseIterable, Codable { case activity, diet, sleep }

struct QuestTarget: Codable, Equatable {
    let metric: String      // "steps", "minutes", "hours-sleep", "servings", "instances"
    let value: Double
    let unit: String
}

struct ToneCopy: Codable, Equatable {
    let title: String
    let detail: String
}

struct EligibilityFilter: Codable, Equatable {
    let requiresSmoker: Bool?           // nil = any; true = smokingStatus != .none; false = == .none
    let requiresDrinker: Bool?          // nil = any; true = alcoholFrequency != .none
    let requiresStrengthRoutine: Bool?  // nil = any
    let coldStartReachable: Bool        // false = excluded during 7-distinct-open-day discovery window
    let timeOfDay: TimeOfDayWindow?     // .morning / .midday / .evening / .anytime
}

struct PoolQuest: Codable, Identifiable {
    var id: String { slug }
    let slug: String                    // "<genre>.<intent-shortname>.v<n>"
    let genre: Genre
    let intent: String                  // parity anchor (D3)
    let target: QuestTarget?            // parity anchor (D3) when present
    let copy: [ToneMode: ToneCopy]      // type-safe tone key; custom Codable (see below)
    let exclusionGroups: [String]
    let eligibility: EligibilityFilter
}

// Custom Codable so JSON can use string keys ("gentle"/"coach"/"firm_direct")
// while in-memory storage stays type-safe. Decode FAILS if any tone is missing —
// surfaces incomplete authoring as a load-time error, not a render-time nil.
extension PoolQuest {
    private enum CodingKeys: String, CodingKey { case slug, genre, intent, target, copy, exclusionGroups, eligibility }
    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        slug = try c.decode(String.self, forKey: .slug)
        genre = try c.decode(Genre.self, forKey: .genre)
        intent = try c.decode(String.self, forKey: .intent)
        target = try c.decodeIfPresent(QuestTarget.self, forKey: .target)
        let raw = try c.decode([String: ToneCopy].self, forKey: .copy)
        var typed: [ToneMode: ToneCopy] = [:]
        for tone in ToneMode.allCases {
            guard let entry = raw[tone.rawValue] else {
                throw DecodingError.dataCorruptedError(forKey: .copy, in: c,
                    debugDescription: "PoolQuest \(slug) missing tone \(tone.rawValue)")
            }
            typed[tone] = entry
        }
        copy = typed
        exclusionGroups = try c.decode([String].self, forKey: .exclusionGroups)
        eligibility = try c.decode(EligibilityFilter.self, forKey: .eligibility)
    }
    // encode mirrors with rawValue keys; omitted for brevity
}
```

#### New SwiftData entity

```swift
// products/life-clock-ios/Sources/Models/LifeClockSchema.swift  (extend)

@Model
final class QuestEvent {
    // CRITICAL: every non-optional must have a property-level default per the
    // SwiftData mandatory-attribute migration landmine
    // (docs/solutions/integration-issues/swiftdata-mandatory-attribute-migration-landmine.md).
    @Attribute(.unique) var id: UUID = UUID()
    var date: Date = Date()             // calendar-day this event belongs to (user local TZ at emit)
    var slug: String = ""
    var genre: String = ""              // denormalized for affinity computation without cross-table join
    var kind: String = ""               // "shown" | "picked" | "replaced" | "completed"
    var resolvedAt: Date? = nil         // EOD resolver fills this when shown→passed-over or picked→abandoned
    var resolvedKind: String? = nil     // "passed_over" | "abandoned" — only set on resolution
    init() {}                           // default-init survives lightweight migration
}
```

Also extended on existing entities (each non-optional carries a property-level default):

```swift
// Quest — additive genre column; category preserved for rollback safety
extension Quest {
    var genre: String = ""              // populated from slug→genre map at bootstrap
}

// UserProfile — discovery-window counter and incremental affinity cache
extension UserProfile {
    var distinctOpenDays: Int = 0       // EXPLICITLY Int, never Set<Date>
    var affinityState: Data = Data()    // encoded {[Genre: (ema, lastUpdated)]} — see perf section
}
```

#### SwiftData migration plan

```swift
// VersionedSchema-based migration plan (NOT lightweight-only — we add a new
// model AND new fields on existing models in one stage).
enum LifeClockSchemaV1: VersionedSchema {
    static var versionIdentifier = Schema.Version(1, 0, 0)
    static var models: [any PersistentModel.Type] =
        [Quest.self, TimeLedgerEntry.self, WeeklyReport.self, UserProfile.self, /* ... */]
}
enum LifeClockSchemaV2: VersionedSchema {
    static var versionIdentifier = Schema.Version(1, 1, 0)
    static var models: [any PersistentModel.Type] =
        [Quest.self, TimeLedgerEntry.self, WeeklyReport.self, UserProfile.self, QuestEvent.self]
}
enum LifeClockMigrationPlan: SchemaMigrationPlan {
    static var schemas: [any VersionedSchema.Type] = [LifeClockSchemaV1.self, LifeClockSchemaV2.self]
    static var stages: [MigrationStage] = [
        .lightweight(fromVersion: LifeClockSchemaV1.self, toVersion: LifeClockSchemaV2.self)
    ]
}
let container = try ModelContainer(
    for: LifeClockSchemaV2.self,
    migrationPlan: LifeClockMigrationPlan.self,
    configurations: ...
)
```

The v1 → v2 stage is lightweight-eligible *because* every new field has a property-level default. Real-device verification (per the [migration landmine](docs/solutions/integration-issues/swiftdata-mandatory-attribute-migration-landmine.md)) is required on every PR touching this stage — the simulator skips migration on fresh installs and never catches the trap.

The four-event lifecycle:
- `shown` — logged at engine emit (one row per slug in today's emitted slate of 3, plus alternates surfaced in plan editor).
- `picked` — logged when user adds to today's plan.
- `replaced` — logged when user swaps slug A→B in today's plan editor.
- `completed` — logged on tick (existing `Quest.completedAt` continues to drive UI; this row is for affinity).
- End-of-day resolver fills `resolvedKind`: unresolved `shown` → `passed_over`, unresolved `picked` → `abandoned`.

#### New engines (consolidated to 3 files)

```text
products/life-clock-ios/Sources/Engines/
  QuestPool.swift              — types + JSON loader + Dictionary<String, PoolQuest>
                                 + copy(slug:tone:) accessor (O(1) lookup).
  QuestSelector.swift          — affinity EMA + need-weight + greedy selector +
                                 exclusion-group conflict resolution + EOD resolver
                                 (private static methods on a single struct).

products/life-clock-ios/Sources/Models/
  QuestPoolTypes.swift         — Genre, QuestTarget, ToneCopy, EligibilityFilter,
                                 PoolQuest, TimeOfDayWindow.
```

`QuestEngine.swift` stays the orchestrator (matches `ClockEngine` shape — single file, free-function-style statics on a struct). It wires `QuestPool` + `QuestSelector` and emits `Quest` rows. The 15 inlined constructors are deleted in Phase 5b.

The collapse from 6 to 3 files matches existing project convention ([QuestEngine.swift](products/life-clock-ios/Sources/Engines/QuestEngine.swift), [ClockEngine.swift](products/life-clock-ios/Sources/Engines/ClockEngine.swift), `WrapUpCoordinator.swift` are each one cohesive unit). `AffinityEngine`, `NeedWeightEngine`, and `EndOfDayResolver` collapse into private static methods inside `QuestSelector`. `QuestPoolLoader` collapses into `QuestPool.init(fromBundle:)`.

#### Data files

```text
products/life-clock-ios/Resources/QuestPool/
  activity.json    — 30 PoolQuest entries, authored Phase 4
  diet.json        — 30
  sleep.json       — 30
  fixture.json     — 6–9 entries used by tests; checked in alongside production pool
```

#### Tone resolution

Quest model stays slug-keyed; tone is resolved on render, not at emit. `Quest.title` and `Quest.detail` become **derived** from `slug` + current `UserProfile.toneMode` at render time. This avoids a snapshot-vs-live ambiguity if the user toggles tone mid-day. (See gap G2 below.)

To support this, `LifeClockStore.fetchQuests(on:)` continues to return `Quest` rows, but the title/detail render path consults `QuestPool.copy(slug, tone: profile.toneMode)`. Existing `Quest.title` and `Quest.detail` columns become read-only legacy; new emits leave them empty. (Phase 2 keeps them populated to a frozen snapshot for backwards compat; Phase 5 retires them.)

### Implementation Phases

#### Phase 2: Schema & Storage  *(this is the first session of code)*

**Goal:** every type, table, and loader exists; tests pass against a 6–9 slug fixture pool; no production behavior changes.

Tasks:

1. Add `Genre`, `QuestTarget`, `ToneCopy`, `EligibilityFilter`, `PoolQuest`, `TimeOfDayWindow` to a new file `products/life-clock-ios/Sources/Models/QuestPoolTypes.swift`.
2. Extend [LifeClockSchema.swift:295](products/life-clock-ios/Sources/Models/LifeClockSchema.swift) with the `QuestEvent` `@Model`. Every non-optional gets a property-level default. `init()` is empty. Add to the `Schema` enumeration in the SwiftData container builder.
3. Add `QuestPool.init(fromBundle:)` that loads `Resources/QuestPool/*.json` at app start, validates against schema, builds an in-memory `Dictionary<String, PoolQuest>` keyed by slug for O(1) tone resolution. Failure mode: **fail loud in both DEBUG and RELEASE** via `fatalError` — a missing or malformed pool JSON is a build defect, not a runtime fallback condition. The fixture pool is test-only and is never used as a release fallback. (Decision per the architecture + framework reviewers: silently shipping the 6-slug fixture to users is worse than crashing on the next TestFlight build before App Store rollout.) Decoder is invoked on a background queue during launch to keep main-thread time low (~5–15ms decode budget on iPhone 12 for ~160KB JSON).
   - Note: this introduces the **first `Resources/` group in `project.yml`**. Document the pattern in CLAUDE.md so future product-policy bundling (e.g., CatchBook fishing templates) inherits this convention.
4. Add `Resources/QuestPool/fixture.json` with 6 slugs (2 per genre) for tests. Production `activity.json / diet.json / sleep.json` ship empty arrays in this phase — the schema validator must accept empty arrays.
5. Tests (D9 layers 1, 2, 4 against fixture). Naming follows `<SourceFile>Tests.swift` convention; new tests use **Swift Testing** (`#expect`, `@Test(arguments:)`) coexisting with existing XCTest.
   - `Tests/QuestPoolTests.swift` — schema validity (decode failure on missing tone), slug uniqueness, slug format regex, fixture-pool non-empty.
   - `Tests/QuestPoolToneParityTests.swift` — for each fixture slug: all three tone keys present (enforced at decode); `intent` and `target` identical across tones (parity); tone strings differ pairwise (distinctness); vocabulary smoke-test using `@Test(arguments: ToneMode.allCases)`.
   - `Tests/QuestSelectorTests.swift` — placeholder for Phase 3; this phase asserts the dictionary lookup path (`QuestPool.copy(slug:tone:)` returns expected ToneCopy).

Acceptance:
- [x] `xcodebuild` clean on iOS Simulator; 26 new unit tests pass (`QuestPoolTests`, `QuestPoolToneParityTests`, plus 4 new `LifeClockSchemaMigrationTests`). Pre-existing UI-test and SubscriptionStore failures on main are unrelated.
- [ ] App launches with empty production pool + populated fixture pool without crash.
- [ ] SwiftData migration runs cleanly on a build with the previous schema (verify on a real device build, not just simulator — per the migration landmine).

#### Phase 3: Selector + Cold-Start + Event Emission  *(second session)*

**Goal:** the engine *runs* against the fixture pool. No production pool authored yet. UI surfaces emit events.

Tasks:

6. **AffinityEngine** (private static methods on `QuestSelector`) — given `UserProfile.affinityState` (cached EMA scalar per genre + `lastUpdatedDate`) and any new `QuestEvent` rows since `lastUpdatedDate`, return `affinity_g: [Genre: Double]`.
   - Cached state is the load-bearing structure: `[Genre: (ema: Double, lastUpdatedDate: Date)]` encoded as `Data` on `UserProfile.affinityState`.
   - On event write, fold incrementally: `ema_new = (1 - α·w) × ema_old + α·w × target` where `α = AffinityEngine.alpha = 0.2` (pinned constant for retunability), `target` and `w` from D6 event signal table.
   - Bounded fetch on emit: query only `QuestEvent.date >= lastUpdatedDate` (typically <10 rows). Fold those, advance `lastUpdatedDate`, write back.
   - Initial value `0.5` for any genre with zero events.
   - **Math justification** (best-practices-researcher): half-life ≈ 3 events at α=0.2 (formula `t½ = -ln(2) / ln(1-α)`). Defensible but on the aggressive side for a 1–3 event/day cadence; α=0.1 would be more conservative. Pinning α as a named constant lets us retune without code archaeology. Asymmetric event weights (1.5×/1.0×/0.5×) follow Hu/Koren/Volinsky 2008 confidence-weight ordering; magnitudes are heuristic and worth empirical calibration after Phase 4.

7. **NeedWeightEngine** (private static methods on `QuestSelector`, with daily snapshot caching) — given `(profile, snapshot, recentSnapshots, drivers)`, return `needWeight_g: [Genre: Double]`.
   - Cached daily: `UserProfile.needWeightSnapshot: Data?` keyed by calendar-day. Compute on first foreground per day; reuse for all subsequent emits within the day. Invalidate on HK permission change.
   - **Activity**: HK steps p50 over recent 14 days; below 5k → 0.9, 5–8k → 0.6, >8k → 0.3.
   - **Sleep**: HK sleep p50 over recent 14 days; below 6.5h → 0.9, 6.5–7.5h → 0.5, ≥7.5h → 0.3.
   - **Diet**: `dietQualityBaseline` ('rough'→0.9, 'okay'→0.6, 'great'→0.3). Override upward if `alcoholFrequency == 'heavy'` (max 0.9).
   - HK trumps onboarding self-report on disagreement: clamp activity/sleep to HK-derived value regardless of onboarding self-rating.
   - **HK p50 implementation** (framework-docs-researcher): `HKStatisticsCollectionQuery` only exposes `cumulativeSum / discreteAverage / discreteMin / discreteMax / mostRecent` — no built-in median. Pull daily values into an array, sort, take `array[count/2]` in Swift. Sleep needs `HKSampleQuery` over `HKCategoryType(.sleepAnalysis)` (categories don't support stats collection); aggregate `endDate − startDate` per night.
   - Threshold values configurable via static constants for test override.

8. **QuestSelector.select(...)** — greedy algorithm in [D8](docs/products/life-clock/plan-quest-generation-affinity.md):
   ```text
   1. Filter pool by hard EligibilityFilter using profile + cold-start day count.
   2. For each genre, score eligible slugs: score = affinity_g^discoveryDamp × needWeight_g
        × recencyDecay(slug, [QuestEvent]) × timeOfDayFit.
   3. Pick highest-scored slug per genre (one per genre — the hard floor).
   4. Conflict pass: if any pair shares an exclusionGroup, replace the lower-scored
      with the next-best non-conflicting eligible slug in its genre.
   5. Termination: max 5 conflict passes. If still conflicting, drop the lowest-need-weight
      genre's slot and surface the consistency.open-app-tomorrow.v1 fallback.
   6. Emit Quest rows; log a `shown` event per emitted slug.
   ```
9. **EndOfDayResolver** (private static methods on `QuestSelector`) — invoked from `applicationWillEnterForeground` / `ScenePhase.active` if `lastResolvedDate < today`. Walks unresolved `QuestEvent` rows where `date < today`, fills `resolvedKind`.
   - **Trigger reliability** (framework-docs): `BGTaskScheduler` (`BGAppRefreshTask`) is best-effort with no execution guarantees, with documented iOS 18.x flakiness. The load-bearing trigger is `ScenePhase.active`; `BGAppRefreshTask` is opportunistic warmup only.
   - **Idempotent**: keyed by `(date: yyyy-MM-dd, slug, kind)`. Double-fire from foreground + background race is safe.
   - **Bounded walk**: cap at 30 days. Older unresolved rows get a single `WHERE date < (today - 30) AND resolvedAt IS NULL` batch update setting `resolvedKind = 'passed_over'`. Avoids per-day transactions degrading on long offline gaps.
   - **Midnight race mitigation**: resolver and the next emit run in a single `ModelContext` transaction. Resolver gates `resolvedKind` writes by "row written ≥ 60 seconds before midnight cutoff" — protects a `picked` placed at 23:59:30 that the user is about to complete.
10. Wire event emission at four call sites:
    - **shown**: `QuestSelector.emit()` — one row per slug in today's slate; one row per alternate offered to the plan editor.
    - **picked**: `LifeClockStore.applyPlanOverride(...)` — when a quest is added to today's plan.
    - **replaced**: same call site, when an existing slot's slug changes.
    - **completed**: `LifeClockStore.toggleQuestCompletion(...)` ([LifeClockStore.swift:716](products/life-clock-ios/Sources/App/LifeClockStore.swift)).
11. Wire the cold-start day counter: a new `UserProfile.distinctOpenDays: Int` (or compute from `firstOpenDate` + a `Set<Date>` of opens). The `discoveryDamp` factor in step 8 above is `0.3 + 0.7 * min(distinctOpenDays / 7.0, 1.0)`.
12. Tests (`<SourceFile>Tests.swift` convention; Swift Testing for new tests):
    - `Tests/QuestSelectorTests.swift` — pins EMA math against synthetic event histories; table-driven `@Test(arguments:)` over (HK p50, onboarding) combinations including HK-trumps-onboarding cases; property-style tests using **PropertyBased** (Swift Testing-compatible, see [forums.swift.org/t/82222](https://forums.swift.org/t/propertybased-easy-quickcheck-for-swift-testing-on-all-platforms/82222)) — 50 random `(HK history + onboarding + event history)` states asserting 3 distinct slugs / 3 genres / no exclusion violation / determinism / all tone variants resolved. Failing seeds are logged for reproducibility.
    - `Tests/EndOfDayResolverTests.swift` (or fold into `QuestSelectorTests`) — multi-day app-offline scenarios: 3-day gap, 30-day gap (asserting batch update path), time-zone shift (assertion that `QuestEvent.date` is preserved at emit, not re-bucketed), midnight cold-launch (assertion that the 60-second cutoff protects the 23:59:30 pick).
    - **Property test trial budget**: 50 trials per CI run (was 200) — performance-oracle estimates 50 trials at <1s wall-clock; 200 trials would push 30s and slow merge feedback. Scale up if a real bug slips through.

Acceptance:
- [ ] Behind a feature flag (`UserProfile.useQuestPoolEngine: Bool`, default false), the new engine runs against fixture pool and emits 3 quests/day.
- [ ] All four event kinds appear in `QuestEvent` table on the right UI actions.
- [ ] Property test (200 trials) passes deterministically with a seed.
- [ ] HK denied path: selector still emits 3 quests using `needWeight_g = 0.5` defaults and `coldStartReachable` slugs only.

#### Phase 4: Pool Authoring  *(third session, parallelizable per genre)*

**Goal:** populate `activity.json / diet.json / sleep.json` to 30 entries each, all four test layers green per genre.

Subtasks:

13. Settle the final intent grid per genre (≥8 intents per genre, target 8–10).
14. Settle the final exclusion-group vocabulary (target 5–10 group names; documented in `docs/products/life-clock/quest-pool-vocab.md`).
15. Author 30 quests per genre across three iterations (10/10/10), running the four-layer test gate after each batch.
16. Tone parity review per slug: a senior tone-aware reviewer (or dedicated reviewer skill) walks every slug and signs off that gentle/coach/firmDirect carry the same intent + target with distinct voice.
17. Lint pass: cosine-similarity / edit-distance check between titles within genre to flag close-duplicates (variant blindness guard, D9 layer 3 supplemental).

Acceptance per genre:
- [ ] 30 entries; all four test layers green.
- [ ] Manual review sign-off on tone parity.
- [ ] Reachability: every slug eligible under at least one realistic synthetic user state.

#### Phase 5: Cutover (split into 5a + 5b per architecture review)

**Goal:** retire the inlined hardcoded quests; flip the feature flag default to true; clean up legacy fields. Split into two PRs to bake the flag-flip in production for ≥1 week before deleting code.

##### Phase 5a — Flag flip

Tasks:

18a. Flip `UserProfile.useQuestPoolEngine` default to `true`.
18b. Phase out direct reads of `Quest.title` / `Quest.detail` from views; route through `QuestPool.copy(slug, tone:)`. Add a `LegacyQuestCompatShim` interface listing every reader retired in this PR; tests assert zero direct accesses to retired fields outside the shim.
18c. Bake in production for ≥1 week. Monitor `selector.deadlock` telemetry, p99 emit latency, and Phase 4's four-layer test gate.

##### Phase 5b — Delete the dead code

Tasks:

19. Delete the 15 inlined `Quest(...)` constructors from [QuestEngine.swift:100-301](products/life-clock-ios/Sources/Engines/QuestEngine.swift).
20. Bootstrap-time backfill of `Quest.genre` for historical rows using the slug→genre map (no rewrite of `Quest.category` — additive migration leaves it intact for rollback safety).
21. Remove the `useQuestPoolEngine` feature flag.
22. Update `Tests/QuestEngineTests.swift` — old assertions over inlined slugs deleted; replace with selector-output assertions over the production pool.

Acceptance:
- [ ] No call site reads `Quest.title` / `Quest.detail` directly except via `LegacyQuestCompatShim`.
- [ ] Feature flag removed.
- [ ] `Quest.category` still readable for rollback; `Quest.genre` populated for all historical rows.
- [ ] Existing completion records still load correctly (the slug match path in [LifeClockStore.swift:1073-1107](products/life-clock-ios/Sources/App/LifeClockStore.swift) carries forward).

## Migration Mapping (current categories → new genres)

| Existing slug | Existing category | New genre | Notes |
|---|---|---|---|
| `movement.steps-target.v1` | movement | activity | Direct rename. |
| `movement.walk-after-meal.v1` | movement | activity | Direct rename. |
| `movement.stairs-instead.v1` | movement | activity | Direct rename. |
| `sleep.consistency.v1` | sleepRecovery | sleep | Direct rename. |
| `sleep.wind-down.v1` | sleepRecovery | sleep | Direct rename. |
| `recovery.hydration-early-night.v1` | sleepRecovery | sleep | Recovery+hydration re-homes to sleep. |
| `nutrition.one-better-meal.v1` | nutritionHabit | diet | Direct rename. |
| `nutrition.log-diet-quality.v1` | nutritionHabit | diet | Direct rename. |
| `nutrition.whole-food-meal.v1` | nutritionHabit | diet | Direct rename. |
| `nutrition.walk-after-dinner.v1` | nutritionHabit | activity | Reclassify — primary action is the walk. |
| `nutrition.water-with-meal.v1` | nutritionHabit | diet | Direct rename. |
| `nutrition.add-protein.v1` | nutritionHabit | diet | Direct rename. |
| `nutrition.eat-meal-slowly.v1` | nutritionHabit | diet | Direct rename. |
| `nutrition.less-processed.v1` | nutritionHabit | diet | Direct rename. |
| `consistency.open-app-tomorrow.v1` | consistency | (out-of-pool) | Stays as engine-machinery fallback. |

The migration is **additive**: a new `Quest.genre: String` column is added (defaulted) and populated by a one-shot SwiftData backfill in `LifeClockStore.bootstrap()` using the slug→genre map. **`Quest.category` is left intact** for rollback safety and to preserve cross-table vocabulary alignment with `WeeklyReport.topPositiveDriver` / `topNegativeDriver` strings (which are free-form and may already encode `"movement"` / `"nutritionHabit"` from prior weekly aggregations). Slugs are unchanged.

This is a behavior change from the original brainstorm wording ("category rewrite") — see data-integrity-guardian review for the rationale: in-place mutation is destructive on rollback and creates a vocabulary split.

## Edge Cases & Gap Resolutions

The brainstorm left 10 edge cases under-specified; the SpecFlow analyzer surfaced the same set. Each is resolved here.

- **G1. EOD resolver trigger.** No iOS cron. Trigger on `applicationWillEnterForeground` if `lastResolvedDate < today`, plus opportunistic `BGAppRefreshTask` (best-effort; not relied on). Multi-day gaps are walked: if the app reopens after 3 days offline, the resolver processes days N-2, N-1 in order before today's emit.
- **G2. Tone-mode mid-day toggle.** Live re-resolve. `Quest` is slug-keyed; views render via `QuestPool.copy(slug, tone: profile.toneMode)`. Toggling tone refreshes the rendered title/detail; emitted history is preserved (the user sees the same intent in a new voice).
- **G3. Slug versioning.** When a slug retires (`v1` → `v2`), `QuestEvent` rows pointing at `v1` continue to feed `affinity_g` (genre-level — the user's preference for diet doesn't reset because we tweaked one diet slug). Slug-level `recencyDecay` discards them (we want the new slug to surface freely).
- **G4. HK denied or disconnected.** `needWeight_g = 0.5` for activity and sleep; diet falls through to onboarding-only. Selector surfaces `coldStartReachable: true` slugs preferentially. Documented as a graceful-degradation path, not an error state.
- **G5. Discovery window "day".** Counted as **distinct calendar days the app has been opened**, not calendar days since first-launch. A user who opens day 1 then returns day 30 is on day 2 of discovery. Stored in `UserProfile.distinctOpenDays: Int`, incremented on first foreground per day.
- **G6. Floor + exclusion deadlock.** Selector loop is bounded at 5 conflict passes (D8 step 5 above). If still in deadlock, drop the lowest-`needWeight_g` genre's slot and surface `consistency.open-app-tomorrow.v1` as the third quest. **Telemetry**: emit a structured `selector.deadlock` event (slug pair, exclusion group, day) — not a console log — so deadlock instances can be tracked. With 5–10 exclusion groups across 90 slugs, deadlock should be near-impossible; if it triggers, that's authoring rot, not normal operation, and the telemetry catches the regression.
- **G7. Replaced A→B→A.** Both `replaced` events log. EMA absorbs the noise — net zero is the right behavior because affinity should reflect the back-and-forth as low signal, not as a strong negative.
- **G8. Time-zone shift.** "Today" is computed in the user's current local TZ at app open. If a user crosses TZs mid-day, the EOD resolver may see today's date "rewind" — handled by storing `QuestEvent.date` as the calendar-day at emit, never re-bucketed. Worst case: a single day with a half-emit; affinity math is robust to this.
- **G9. Multi-device divergence.** SwiftData is local-only; `QuestEvent` is per-device. **Documented as accepted behavior** — multi-device sync is out of scope for Phase 3. If users ask, the answer is "your affinity learns per device today; we may add iCloud sync later."
- **G10. The `consistency.open-app-tomorrow.v1` fallback.** Stays as out-of-pool engine machinery. Emitted only when (a) selector deadlocks (G6) or (b) all eligible slugs in a genre are filtered out (zero-eligible state).

- **G11. `QuestEvent` retention.** Rolling 365-day window. On daily resolver run, batch-delete events older than 365 days *after* folding them into per-genre rollup totals stored on `UserProfile.affinityHistorySummary: Data` (encoded `[Genre: {totalCompleted, totalPicked, totalReplaced, totalShown, lastEventDate}]`). Affinity computation prefers the live event window; the rollup feeds genre-level priors when the live window is empty. Privacy-conscious (refusal patterns don't accumulate indefinitely on-device) and perf-bounded (active event window stays small).

- **G12. Recency decay curve.** `recencyDecay(slug, today) = exp(-Δt / τ)` where `Δt` is days since the slug's last `shown` event and `τ = 3.5` days. After 7 days a slug's recencyDecay drops to `e^-2 ≈ 0.13`, effectively rotating it back to the front. Curve grounded in Ding & Li 2005 (canonical time-weight collaborative filtering); shape is exponential, not linear or step. Pinned as `QuestSelector.recencyTau` for retunability.

- **G13. Drivers ↔ Quests cross-feed (out-of-scope, flagged).** Today's `ClockEngine` and the new `QuestSelector.NeedWeightEngine` independently read `TimeLedgerEntry.driverType` totals. This is duplication risk — divergent interpretations could create surprising mismatches between weekly-report messaging and daily-quest selection. **Out of scope for this plan** but explicitly tracked: revisit consolidating driver-interpretation into a shared `DriverInterpreter` if the duplication causes user-visible inconsistency.

## Alternative Approaches Considered

The brainstorm covered most alternatives; brief recap of the rejected paths:

- **LLM at runtime** — rejected for determinism, latency, offline behavior, and cost.
- **Parameter-slot templates** ("walk N minutes" with N varying) — rejected for variant blindness and authoring shallowness.
- **Single composite affinity score** — rejected for conflating preference and need; refusal escape valve gets confounded.
- **Counter-based affinity, no decay** — rejected for failing to track user change-of-mind over months.
- **Pairwise slug-on-slug conflict rules** — rejected for combinatorial growth; exclusion groups scale linearly with vocabulary.
- **Variable slate size 2–4** — rejected for risk of overwhelming users on bad-day cycles.
- **Onboarding-only cold-start without HK** — rejected because HK history is on disk day 1 and richer than self-report; HK trumps self-report on disagreement.

## System-Wide Impact

### Interaction Graph

```text
applicationDidBecomeActive
  → LifeClockStore.refresh()
    → if lastResolvedDate < today: EndOfDayResolver.run()  (fills resolvedKind on stale rows)
    → QuestEngine.generateDailyQuests(profile, snapshot, recent, habits)
      → AffinityEngine.computeAffinities(QuestEvent rows)        [reads]
      → NeedWeightEngine.compute(profile, snapshot, recent)      [reads HK]
      → QuestSelector.select(pool, affinity, need, today, profile)
        → emits Quest rows (slug-keyed)
        → emits QuestEvent(kind=shown) per emitted slug + alternates  [writes]
    → LifeClockStore.applyPersistedCompletions(...)              [unchanged]

UI: TodayPlanEditor.swap(slugA, slugB)
  → LifeClockStore.applyPlanOverride(...)
    → emits QuestEvent(kind=replaced, slug=slugA)                [writes]
    → emits QuestEvent(kind=picked, slug=slugB)                  [writes]

UI: QuestRow.toggleComplete()
  → LifeClockStore.toggleQuestCompletion(quest)
    → updates Quest.completedAt                                   [unchanged path]
    → emits QuestEvent(kind=completed, slug=quest.slug)          [writes]
```

### Error & Failure Propagation

- `QuestPoolLoader` failure (malformed JSON): DEBUG asserts; RELEASE logs and falls back to fixture pool. App does not crash.
- `AffinityEngine` with zero events for a genre: returns initial `0.5`. No error.
- `NeedWeightEngine` with no HK data: returns `0.5` defaults. Not an error.
- `QuestSelector` deadlock: surfaces fallback quest after 5 passes. Logged to console with the conflicting slugs for debugging.
- `EndOfDayResolver` failure mid-walk: each day's resolution is its own transaction; partial completion is safe — the next foreground tick picks up unresolved rows.
- `QuestEvent` write failure (disk full, etc.): swallowed with a log; affinity loses one signal, system continues. Not a hard failure.

### State Lifecycle Risks

- **Orphaned QuestEvent rows from retired slugs.** Mitigated: events feed affinity at the genre level even if the slug is gone (G3).
- **Duplicate `shown` rows on a single day if app foregrounds twice.** Mitigated: emit dedup by `(date, slug, kind="shown")` at write time — `shown` is idempotent per day.
- **`picked` without subsequent `completed` or end-of-day resolution.** Mitigated: EOD resolver fills `resolvedKind="abandoned"` on next foreground past midnight.
- **`Quest.title` / `Quest.detail` snapshot drift.** Mitigated: views render through `QuestPool.copy(...)`. Phase 5 retires the legacy fields entirely.
- **SwiftData mandatory-attribute migration.** Mitigated: every non-optional `@Model` property has a property-level default per the documented landmine ([swiftdata-mandatory-attribute-migration-landmine.md](docs/solutions/integration-issues/swiftdata-mandatory-attribute-migration-landmine.md)).

### API Surface Parity

The selector is the only emit path. Legacy `availableQuests(for:)` ([QuestEngine.swift:79-96](products/life-clock-ios/Sources/Engines/QuestEngine.swift)) — used by the today's plan editor — is rewritten to read from `QuestPool` filtered by genre + eligibility. No new public surface; Phase 5 removes the legacy variant pools.

### Integration Test Scenarios

These are the cross-layer scenarios the unit tests with mocks won't catch:

1. **Three-day offline gap then foreground.** App last opened Mon. User opens Thu. EOD resolver walks Mon, Tue, Wed in order; Thu's slate emits with up-to-date affinity that includes Mon's resolved events. Property test seed.
2. **Tone toggle mid-day.** User picks 3 quests at 8am in coach. Toggles to gentle at 3pm. Three quests re-render with gentle copy on next view appear. Quest rows in DB unchanged. Snapshot test.
3. **HK permission revoked between days.** Day N: HK permitted, full need-weight. Day N+1: user revokes. Selector still emits 3 quests using fallback need-weight + `coldStartReachable: true` filter. No crash.
4. **Plan editor swap-twice.** User picks A, swaps A→B, swaps B→A. Three `QuestEvent` rows: `picked(A)`, `replaced(A) + picked(B)`, `replaced(B) + picked(A)`. Affinity update absorbs the noise. Integration test with property assertion.
5. **Cold-start through discovery window.** Synthetic user at days 1, 4, 7, 8. Property assertion: discoveryDamp factor at each day matches `0.3 + 0.7 * min(d/7, 1)`; affinity-score variance in selection grows with day count.

## Acceptance Criteria

### Functional

- [ ] All 90 production-pool slugs (when authored Phase 4) load and validate at app start.
- [ ] Selector emits exactly 3 quests per day, one per genre, deterministic given (profile, HK history, event history, date).
- [ ] All four `QuestEvent` kinds emit at the four UI hook points.
- [ ] EOD resolver fills `resolvedKind` on next foreground after midnight.
- [ ] Tone toggle re-renders quest copy live without DB mutation.
- [ ] HK-denied path emits 3 quests with safe-default need-weights.
- [ ] Cold-start day 1 emits a personalized slate (HK-informed need-weight + onboarding eligibility) without ever picking a contraindicated slug.

### Non-Functional

- [ ] **Selector pure logic** (post-cache) p99 < 5ms on iPhone 12 with 90-slug pool.
- [ ] **End-to-end emit** (cache-warm path: hit AffinityEngine cache, hit NeedWeightEngine daily snapshot, run selector, write events) p99 < 50ms.
- [ ] **End-to-end emit cold-start** (first-foreground-of-day, NeedWeight cache miss, HK p50 query) p99 < 200ms — matches the qualitative cold-start metric.
- [ ] AffinityEngine emit cost is O(events-since-last-fold), not O(all events). Verified at 30k-event synthetic load (year-3 user).
- [ ] No new privacy-sensitive data leaves the device. `QuestEvent` is local SwiftData only.
- [ ] `QuestEvent` retention enforced: rolling 365-day window, with rollup summary preserved (G11).
- [ ] Pool JSON files are < 200KB each; total decode budget < 15ms on iPhone 12.

### Quality Gates

- [ ] D9 layer 1 (schema validity + uniqueness): green for production pool.
- [ ] D9 layer 2 (tone parity + distinctness): green for every authored slug.
- [ ] D9 layer 3 (coverage + reachability): every slug eligible under ≥1 realistic synthetic user; every genre has ≥8 intents.
- [ ] D9 layer 4 (selector property tests): 200 random states, all assertions hold.
- [ ] Real-device build cycle (not just simulator) passes — verifies the SwiftData migration landmine.
- [ ] Existing `QuestEngineTests.swift` updated; no skipped tests.

## Success Metrics

- **Refusal recovery rate** — for users who replace a slug N≥3 times, the slug stops surfacing within 7 days. Measured by per-user telemetry on slug → days-to-suppression.
- **Genre coverage at day 14** — every active user has touched all three genres at least once by day 14 (the floor working as intended).
- **Tone parity bug count** — zero in-the-wild reports of "this tone says X, that tone says Y" for the same slug. Measured by support tickets.
- **Authoring throughput** — Phase 4 ships at one genre per week (3-week total) without dropping the four-layer test gate.
- **Cold-start qualitative** — onboarding-completion → first-quest-emit is under 200ms; first slate "feels personal" per a 5-user qualitative review.

## Dependencies & Prerequisites

- HealthKit baselines: existing steps p50 stays; new sleep p50 (clamped 4–10h) is added in Phase 3.
- `ToneMode.allCases` parity-test pattern ([ToneModeTests.swift:77-99](products/life-clock-ios/Tests/ToneModeTests.swift)) is the test scaffold — no new infra.
- SwiftData schema version bumps once for `QuestEvent` add — verify on a real-device build with the previous schema before merge (per migration landmine).
- The brainstorm doc is the design source of truth; this plan does not duplicate its rationale.

## Risk Analysis & Mitigation

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| SwiftData migration breaks existing installs | Medium | High | Property-level defaults on every non-optional; `distinctOpenDays: Int` (never `Set<Date>`); real-device verification on every PR touching schema. |
| Selector deadlock on exclusion groups | Low | Medium | Bounded loop + fallback quest (G6). Structured `selector.deadlock` telemetry, not console log. |
| Tone-parity drift in pool authoring | Medium | High | Build-time test gate (D9 layer 2); decode failure on missing tone (custom Codable); reviewer sign-off. |
| Pool authoring stalls Phase 4 | Medium | Medium | Phase 3 ships against fixture pool; Phase 4 is genre-parallel; cutover gated behind feature flag. |
| HK permission UX regresses | Low | Medium | Graceful fallback already specified (G4); explicit integration test (#3 above). |
| EOD resolver loses signal on long offline | Low | Low | Multi-day walk on foreground; bounded at 30 days then bulk batch-update; opportunistic BGAppRefreshTask. |
| Multi-device divergence surprises a user | Medium | Low | Documented accepted behavior; no UI claims of cross-device personalization. |
| Variant blindness despite intent grid | Medium | High | Lint pass on title cosine-similarity; reviewer veto. |
| Authoring rot 6+ months out | High | Medium | Quarterly review ritual logged in `docs/products/life-clock/quest-pool-vocab.md`; PR gate runs four-layer test on any pool edit. |
| In-place `Quest.category` rewrite strands rollback | Eliminated | High | **Additive migration**: add `Quest.genre`, leave `category` intact. (See migration table.) |
| AffinityEngine slows at year-3 (30k events) | Eliminated | Medium | **Incremental EMA cache** (`UserProfile.affinityState`); query bounded to events since last fold. |
| Midnight race overwrites a 23:59 pick | Low | Medium | Resolver + emit in single `ModelContext` transaction; `resolvedKind` writes gated by 60-second cutoff before midnight. |
| `QuestEvent` unbounded growth (privacy + perf) | Medium | Medium | 365-day rolling retention with per-genre rollup summary (G11). |
| Silent fixture-pool fallback ships to users | Low | High | Production pool malformed JSON crashes loud at app start (no fallback to fixture); fixture is test-only. |
| BGTaskScheduler unreliability swallows resolver | Medium | Low | `ScenePhase.active` is the load-bearing trigger; `BGAppRefreshTask` is opportunistic warmup only. |
| Phase 5 atomic flag-flip + delete amplifies bug surface | Low | Medium | Split into Phase 5a (flag flip + bake ≥1 week) + Phase 5b (constructor delete). |

## Resource Requirements

- Phase 2: 1 engineer × ~0.5 week.
- Phase 3: 1 engineer × ~1 week.
- Phase 4: 1 engineer + 1 tone-aware reviewer × ~3 weeks (one genre per week).
- Phase 5: 1 engineer × ~0.5 week.
- Total: ~5 weeks E2E if serialized; Phase 4 genre work parallelizable.

## Future Considerations

- **iCloud sync** for `QuestEvent` to deduplicate affinity across devices (deferred from Phase 3).
- **User-visible "I'm done with this kind"** override if refusal-detection proves insufficient in practice. Currently rejected; the four-event model + recencyDecay + replaced-weight 1.5× should suffice.
- **Streak-aware quest selection** — bias toward easy quests when a streak is at risk. Out of scope here.
- **Multi-quest dependencies** — "if you completed walk-after-dinner today, unlock a harder activity quest tomorrow." Out of scope.
- **Adaptive slate size** — re-evaluate after 6 months of usage data.
- **A/B testing harness** — currently the engine is deterministic-by-design; an A/B layer could ride on top of the seed.

## Documentation Plan

- [ ] `docs/products/life-clock/quest-pool-vocab.md` — exclusion-group vocabulary and the intent grid per genre. Authored Phase 4 sub-task 14.
- [ ] Inline doc comment at top of `QuestPool.swift` linking to the brainstorm + this plan.
- [ ] CLAUDE.md note under "Skills" or "Conventions" if any new pattern emerges (tentative; only if needed).
- [ ] Phase 5 — update `docs/products/life-clock/12_TECHNICAL_ARCHITECTURE.md` to reflect the new selector pipeline.
- [ ] Compound a new entry in `docs/solutions/` after Phase 3 ships (the EMA + need-weight + exclusion-group pattern is greenfield in this codebase per the learnings researcher; worth documenting).

## Sources & References

### Origin

- **Brainstorm document:** [docs/products/life-clock/plan-quest-generation-affinity.md](docs/products/life-clock/plan-quest-generation-affinity.md). Key decisions carried forward: (1) intent-grid diversity (D2); (2) slug+intent+target parity tuple (D3); (3) four-event refusal taxonomy with `replaced` weighted 1.5× the standard EMA step (D5/D6); (4) hard genre floor + exclusion-group conflict resolution (D6/D8); (5) HK trumps onboarding self-report on cold-start (D7).

### Internal References

- [QuestEngine.swift:40-301](products/life-clock-ios/Sources/Engines/QuestEngine.swift) — current engine; selector + 15 inlined constructors are retired.
- [LifeClockSchema.swift:295-334](products/life-clock-ios/Sources/Models/LifeClockSchema.swift) — Quest model; QuestEvent extends here.
- [ToneMode.swift](products/life-clock-ios/Sources/App/ToneMode.swift) — tone enum + per-tone string conventions (`switch self`).
- [LifeClockStore.swift:716-733](products/life-clock-ios/Sources/App/LifeClockStore.swift) — completion toggle; new event hook.
- [LifeClockStore.swift:1073-1107](products/life-clock-ios/Sources/App/LifeClockStore.swift) — `applyPersistedCompletions` slug-match path that survives migration.
- [ReflectionPrompts.swift:18-69](products/life-clock-ios/Sources/Shared/ReflectionPrompts.swift) — closest existing precedent for tone-keyed pools.
- [LiveHealthKitService.swift](products/life-clock-ios/Sources/Services/LiveHealthKitService.swift) — HK reads.
- [HistoricalImportCoordinator.swift](products/life-clock-ios/Sources/Services/HistoricalImportCoordinator.swift) — HK backfill; powers cold-start need-weight.
- [ToneModeTests.swift:77-99](products/life-clock-ios/Tests/ToneModeTests.swift) — `for tone in ToneMode.allCases` parity-test pattern.
- [docs/solutions/integration-issues/swiftdata-mandatory-attribute-migration-landmine.md](docs/solutions/integration-issues/swiftdata-mandatory-attribute-migration-landmine.md) — every non-optional `@Model` property needs a property-level default to survive lightweight migration.
- [docs/solutions/integration-issues/catchbook-angler-ux-parity-rollout.md](docs/solutions/integration-issues/catchbook-angler-ux-parity-rollout.md) — phased multi-surface rollout precedent (informs Phase 2–5 sequencing).

### External References

#### Recommender systems (D6 affinity math grounding)

- [Hu, Koren, Volinsky — *Collaborative Filtering for Implicit Feedback Datasets* (ICDM 2008)](http://yifanhu.net/PUB/cf.pdf) — canonical confidence-weight asymmetry; informs replaced=1.5× / picked=1.0× / shown=0.5× ordering.
- [*Leveraging Explicit Negative Feedback in Large-Scale Recommendation Systems* (RecSys 2025)](https://dl.acm.org/doi/10.1145/3705328.3748145) — current treatment of explicit dismiss vs non-click signals.
- [*Dynamic Prior Thompson Sampling for Cold-Start Exploration* (arXiv 2602.00943, 2026)](https://arxiv.org/abs/2602.00943) — validates HK-derived priors over flat 0.5 cold-start; matches D7.
- [Stanford CS369P Lec 8 — Greedy on Matroids](https://theory.stanford.edu/~jvondrak/CS369P/lec8.pdf) — proves greedy is optimal on partition matroids (slate=3 + at-most-one-per-exclusion-group).
- [Ding & Li — *Time Weight Collaborative Filtering* (SIGIR 2005)](https://cseweb.ucsd.edu/classes/fa17/cse291-b/reading/p485-ding.pdf) — exponential `exp(-Δt/τ)` recencyDecay precedent.
- [Bittensor EMA docs (half-life formula)](https://docs.learnbittensor.org/learn/ema) — confirms `t½ = -ln(2)/ln(1-α)` math used for α=0.2 justification.

#### iOS 17/18 framework references

- [HKStatisticsOptions](https://developer.apple.com/documentation/healthkit/hkstatisticsoptions) — confirms no built-in median; daily-bucket-then-Swift-sort pattern.
- [HKStatisticsCollectionQuery](https://developer.apple.com/documentation/healthkit/hkstatisticscollectionquery) — query shape used in NeedWeightEngine.
- [VersionedSchema (Hacking with Swift)](https://www.hackingwithswift.com/quick-start/swiftdata/how-to-create-a-complex-migration-using-versionedschema) — migration-plan code shape adopted in this plan.
- [BGTaskScheduler](https://developer.apple.com/documentation/backgroundtasks/bgtaskscheduler) — best-effort scheduling, no guarantees.
- [*Don't rely on BGAppRefreshTask for your app's business logic*](https://mertbulan.com/programming/dont-rely-on-bgapprefreshtask-for-your-apps-business-logic) — confirms `ScenePhase.active` as the load-bearing trigger.
- [iOS 18 Background Survival Guide](https://blog.stackademic.com/ios-18-background-survival-guide-part-1-smarter-scheduling-with-bgtaskscheduler-in-ios-18-fee4b31c0c5b) — current iOS 18 BGTaskScheduler behavior.
- [Migrating XCTest to Swift Testing](https://useyourloaf.com/blog/migrating-xctest-to-swift-testing/) — coexistence pattern; no need to migrate XCTest wholesale.
- [PropertyBased — easy QuickCheck for Swift Testing](https://forums.swift.org/t/propertybased-easy-quickcheck-for-swift-testing-on-all-platforms/82222) — selector property-test library; logs failing seeds.

#### Behavior-change context

- Behavior-change research on intent-action models (informational only, not binding) — used as a sanity check for the intent grid taxonomy in D2.

### Related Work

- Recent commits: `8f94363` (firmDirect softening), `13bffcc` (reflection accusation prompt softening), `9e09e85` (V1+V2 landed, V3 scoped). This plan formally subsumes V3.
- Polish docs: `polish-2026-05-07-vision-bad-day-three-tones.md` (informs tone-vocabulary smoke-test).
