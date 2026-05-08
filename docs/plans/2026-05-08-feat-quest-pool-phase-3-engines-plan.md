---
title: "feat: Quest Pool Phase 3 — engines, emission hooks, and feature flag"
type: feat
status: active
date: 2026-05-08
origin: docs/plans/2026-05-08-feat-quest-pool-affinity-engine-plan.md
---

# feat: Quest Pool Phase 3 — engines, emission hooks, and feature flag

## Overview

Phase 3 of the quest-pool affinity engine. Implements the four engine primitives (`AffinityEngine`, `NeedWeightEngine`, `QuestSelector`, `EndOfDayResolver`), the four-event emission hooks (`shown / picked / replaced / completed`), the cold-start discovery-dampening mechanic, schema additions for affinity inputs (`UserProfile.distinctOpenDays`, `lastForegroundDay`, `useQuestPoolEngine`), the slug→genre bootstrap backfill, and the `useQuestPoolEngine` feature flag (default `false`).

**The flag defaults `false`. This PR ships zero production behavior change.** All new code paths are reachable only when the flag is flipped on (which Phase 5 does as a one-line edit + ≥1-week production bake). Tests flip the flag and inject the fixture pool to exercise every new path.

This plan is the execution blueprint. **Design decisions are not re-derived here**; they live in the master plan ([docs/plans/2026-05-08-feat-quest-pool-affinity-engine-plan.md](docs/plans/2026-05-08-feat-quest-pool-affinity-engine-plan.md)) and the seven Phase 3 prep findings ([todos/049-pending-p3-quest-pool-phase3-prep.md](todos/049-pending-p3-quest-pool-phase3-prep.md)). Each task below cites which master-plan section or todo finding it implements.

## Enhancement Summary

**Deepened on:** 2026-05-08 (second pass, Phase 3 plan).
**Reviewers:** architecture-strategist, code-simplicity-reviewer, performance-oracle, data-integrity-guardian, spec-flow-analyzer.

### Key improvements applied

1. **Pool injection signature pinned.** `QuestEngine.generateDailyQuests(..., pool: QuestPool? = nil)` with default `nil` (lazy `Bundle.main`). NOT a per-call `selectorPath` parameter — the boundary lives on the public engine entry point.
2. **Selector `latestShownBySlug` precompute.** Build `[String: Date]` dict once at top of `select(...)` — single pass over events, then O(1) lookup per slug score. Drops 135k comparisons at Phase 4 scale (90 slugs × 1500 events) to 1500. Acceptance criterion p99 < 5ms now references 90-slug condition, not the 6-slug fixture.
3. **EOD resolver single broad fetch + in-memory grouping.** One `FetchDescriptor<QuestEvent>` over the 30-day window, group by `(date, slug)` in-memory, walk unresolved rows resolving against the dict. Avoids 360 sequential SwiftData fetches = 200–500ms launch jank.
4. **`#Index<QuestEvent>([\.date, \.slug, \.kind])` in V1.5.0 schema.** SwiftData does not auto-index predicate columns; the iOS 18+ `#Index` macro is required. Cheap to add now while the schema is open; eliminates the table scan that grows linearly with retention.
5. **`upsertQuest` guarded against empty-genre clobber.** `if !quest.genre.isEmpty { stored.genre = quest.genre }` — prevents the consistency-fallback path (which carries `genre = ""` per G16) from overwriting `bootstrapQuestGenres`-backfilled non-empty values. Adds regression test `testUpsertQuestWithEmptyGenreDoesNotClobberBackfilledRow`.
6. **V1.3.0 → V1.5.0 double-hop migration test.** Devices upgrading directly from V1.3.0 (pre-Phase-2) to V1.5.0 must complete lightweight migration in a single hop. Add `testV130ToV150DoubleHopMigration` that seeds an on-disk store from a V1.3.0 fixture and validates every V1.4.0 + V1.5.0 field round-trips.
7. **Empty-pool flag-on guard.** If `useQuestPoolEngine == true` AND `pool.quests.isEmpty`, log `pool.empty.guard` and force flag back to `false` for the session. Prevents 3x consistency-fallback for every user every day if Phase 5a flag flips before Phase 4 pool authoring lands.
8. **Track 3c boundary tightened.** Task 15 (`distinctOpenDays` increment) moves into Track 3b — it depends only on the new schema, not on emission hooks. Track 3c is now strictly emit + flag.
9. **Replaced + passedOver double-count guard.** EOD resolver skips `shown` rows where a `replaced` event for the same `(date, slug)` exists — prevents penalizing the same slug twice (rejected explicitly + passed-over implicitly).
10. **DST + tiebreak invariants documented.** First-foreground-per-local-day uses `Calendar.current.startOfDay(for:)` — single fire on both 25-hour and 23-hour days. Selector tiebreaker is slug-ascending lexical (already implicit via `byGenre` sort); test added.
11. **Property test scope tightened.** 50 random trials → 10 hand-crafted scenarios (per simplicity-reviewer). Property test scaffold deferred to a Phase 3.5 polish PR if the production pool reveals non-obvious failure modes.
12. **Sheet tone-toggle observation.** Quest sheets must observe `UserProfile.toneMode` via `@Bindable` (or read from live store) so a mid-day tone change re-renders the sheet without dismissal.

### Pushback on aggressive cuts

- **`distinctOpenDays` + discovery damp kept.** The simplicity reviewer recommended cutting both. The user explicitly approved discovery dampening + HK-trumps in the brainstorm; cutting undoes a deliberate decision. Kept as-is.
- **3 engine files kept (NOT collapsed to 2).** Pattern-recognition reviewer in the master-plan deepening confirmed AffinityEngine + NeedWeightEngine + QuestSelector boundaries earn their cost (disjoint inputs, disjoint test surfaces). Kept.

## Problem Statement

After Phase 2 ([PR #30](https://github.com/kashane1/ai-company-os/pull/30)), the schema and pool storage exist but are inert: no engine reads them, no UI emits events into the new `QuestEvent` table, no selector picks from the pool. The 15 inlined `Quest(...)` constructors in [QuestEngine.swift:100-301](products/life-clock-ios/Sources/Engines/QuestEngine.swift) still drive every daily slate.

Phase 3 wires the engines, the event lifecycle, the cold-start mechanic, and the feature flag — without authoring any production-pool slugs (Phase 4) and without flipping the flag (Phase 5). The result is a fully-tested, zero-impact PR that turns into the production code path the moment the flag flips.

## Proposed Solution

Five new types and engines, three schema additions on `UserProfile`, four event-emission hook points in `LifeClockStore`, one new method in `QuestPool`, one branch in `QuestEngine.generateDailyQuests`, and a foreground-triggered resolver — all gated by `useQuestPoolEngine`. Comprehensive unit + integration tests for each engine and each hook point, with the feature flag flipped on for tests.

This plan organizes the work into four sequenceable tracks. **Tracks 3a and 3b have no dependency on each other and can land in either order.** Tracks 3c and 3d depend on 3a + 3b being merged.

## Technical Approach

### Architecture

#### New event-kind enums

```swift
// Sources/Models/QuestPoolTypes.swift  (extend)

enum QuestEventKind: String, CaseIterable, Codable, Sendable {
    case shown
    case picked
    case replaced
    case completed
}

enum QuestResolvedKind: String, CaseIterable, Codable, Sendable {
    case passedOver = "passed_over"   // shown but never picked by EOD
    case abandoned                    // picked but never completed by EOD
}
```

`QuestEvent.kind` and `QuestEvent.resolvedKind` stay `String` on the SwiftData side (per the Phase 2 schema), but every read/write site funnels through these enums. A typo becomes a compile-time error. (todo 049 #3)

#### New engines (3 files)

```text
products/life-clock-ios/Sources/Engines/
  AffinityEngine.swift     — pure function: [QuestEvent] + Date → [Genre: Double]
                              EMA per genre (α = 0.2), event-weight from QuestEventKind table.
                              Non-cached in Phase 3 (linear-in-events).
                              Cached implementation deferred — see "Out of Scope".
  NeedWeightEngine.swift   — pure function: (UserProfile, [DailyHealthSnapshot]) → [Genre: Double]
                              activity: HK steps p50 (reuses QuestEngine.movementStepTarget logic)
                              sleep:    HK sleep p50 over recent 14 days
                              diet:     dietQualityBaseline + alcoholFrequency override
  QuestSelector.swift      — pure function: (QuestPool, [Genre: Double] affinity,
                              [Genre: Double] needWeight, UserProfile, Date, [QuestEvent])
                              → [PoolQuest]
                              Greedy + exclusion-group conflict pass + hard genre floor.
                              Emits `consistency.open-app-tomorrow.v1` fallback on deadlock.
```

`EndOfDayResolver` is implemented as static methods on `QuestSelector` (not its own file) — same single-file convention the deepened plan settled on. (Master plan D8 collapse.)

#### Pool extension: `byGenre` precompute (todo 049 #5)

```swift
// Sources/Engines/QuestPool.swift  (extend)

struct QuestPool: Sendable {
    let quests: [String: PoolQuest]
    let byGenre: [Genre: [PoolQuest]]    // precomputed at init, sorted by slug

    init(quests: [PoolQuest]) {
        var dict: [String: PoolQuest] = [:]
        var grouped: [Genre: [PoolQuest]] = [:]
        for quest in quests {
            dict[quest.slug] = quest
            grouped[quest.genre, default: []].append(quest)
        }
        for genre in grouped.keys {
            grouped[genre]?.sort { $0.slug < $1.slug }
        }
        self.quests = dict
        self.byGenre = grouped
    }

    func quests(in genre: Genre) -> [PoolQuest] {
        byGenre[genre] ?? []          // O(1) dict lookup, no per-call sort
    }
}
```

#### Schema additions on `UserProfile` (V1.4.0 → V1.5.0)

```swift
// Sources/Models/LifeClockSchema.swift  (extend LifeClockSchemaV1.UserProfile)

// 1.5.0 (2026-05-08): Phase 3 of the quest-pool affinity engine.
// Three additive UserProfile fields, all property-level-defaulted for
// SwiftData lightweight migration safety (NSCocoaErrorDomain 134110).

/// Number of distinct local-calendar days this install has been
/// foregrounded. Drives the cold-start discovery-dampening factor
/// in QuestSelector. Caps usefulness at 7; we still increment past
/// that for telemetry.
var distinctOpenDays: Int = 0

/// Start-of-day for the most recent calendar day on which this
/// install was foregrounded. Used to detect "first foreground of
/// new day" and increment distinctOpenDays.
var lastForegroundDay: Date? = nil

/// Feature flag for the quest-pool engine path. When true,
/// QuestEngine.generateDailyQuests routes through QuestSelector +
/// QuestPool. When false (default), the legacy 15-inlined-Quest
/// path runs unchanged. Flipped by Phase 5a after the production
/// pool is authored.
var useQuestPoolEngine: Bool = false
```

#### Index on QuestEvent (V1.5.0)

```swift
// Sources/Models/LifeClockSchema.swift  (extend QuestEvent @Model)

@Model
final class QuestEvent {
    // Existing Phase 2 fields...
    #Index<QuestEvent>([\.date, \.slug, \.kind])   // V1.5.0 addition
}
```

Without an index on `(date, slug, kind)`, SwiftData lowers predicate queries to a SQLite table scan. With 5k+ retained events the per-emit dedup lookup grows to 1–3ms — multiplied across 3 emits per day, becomes user-visible. The index is free at write time and eliminates the scan. Same index also serves the EOD resolver's single broad fetch.

`affinityState` and `needWeightSnapshot` (the cached EMA scalars + daily HK snapshot) are explicitly **deferred** — see "Out of Scope" for rationale.

#### LifeClockStore extensions

```text
products/life-clock-ios/Sources/App/LifeClockStore.swift  (modify)

  refresh()                       — increment distinctOpenDays on first
                                    foreground per local day.
  bootstrapQuestGenres()          — backfill Quest.genre from slug→genre map
                                    (todo 049 #2). Idempotent.
  upsertQuest(...)                — propagate quest.genre on insert AND update
                                    (todo 049 #1).
  applyPlanOverride(...)          — emit picked/replaced QuestEvent rows
                                    (master plan task 10).
  toggleQuestCompletion(...)      — emit completed QuestEvent row.
  + private:
    emitShown(slug:genre:date:)   — idempotent insert (dedup by date+slug+kind,
                                    todo 049 #4).
    emitEvent(kind:slug:genre:)   — generic emit helper.
```

#### QuestEngine integration

```swift
// Sources/Engines/QuestEngine.swift  (modify)

// Pool injection lives at the public entry point, not at selectorPath.
// `pool == nil` triggers lazy Bundle.main load. Tests inject explicitly.
func generateDailyQuests(
    profile: UserProfile,
    snapshot: DailyHealthSnapshot?,
    recentSnapshots: [DailyHealthSnapshot] = [],
    habits: HabitLog?,
    pool: QuestPool? = nil
) -> [Quest] {
    let resolvedPool = pool ?? Self.lazyBundlePool()
    // Empty-pool flag-on guard: if the flag is on but the pool is empty
    // (Phase 4 hasn't authored production slugs yet), force flag off for
    // this session and fall through to the legacy path. Prevents 3x
    // consistency-fallback for every user every day. Logs `pool.empty.guard`.
    if profile.useQuestPoolEngine, !resolvedPool.isEmpty {
        return selectorPath(pool: resolvedPool, profile: profile, ...)
    }
    if profile.useQuestPoolEngine && resolvedPool.isEmpty {
        // Telemetry hook for the empty-pool guard (single log per session).
    }
    return legacyInlinedQuests(...)   // existing 15-quest path, unchanged
}

private func selectorPath(pool: QuestPool, ...) -> [Quest] {
    // 1. Read [QuestEvent] for affinity input.
    // 2. AffinityEngine.computeAffinities(events:) → [Genre: Double]
    // 3. NeedWeightEngine.compute(profile:, snapshots:) → [Genre: Double]
    // 4. QuestSelector.select(pool:, affinity:, needWeight:, profile:, today:, events:) → [PoolQuest]
    // 5. Materialize each PoolQuest into a Quest row (slug, date, target, etc.)
    //    Quest.title and Quest.detail are snapshotted from the pool at the
    //    profile's current tone — views still resolve via QuestPool.copy(slug, tone:)
    //    so a tone toggle re-renders without a DB write (master plan G2).
    // 6. Return; LifeClockStore emits `shown` events from the persistence path.
}
```

#### EndOfDayResolver trigger

```swift
// Sources/App/LifeClockStore.swift  (modify refresh path)

func refresh() {
    let today = clock.today()
    if let last = profile.lastForegroundDay, last < today {
        // First foreground of new day — fire EOD resolver for stale events.
        try? QuestSelector.resolveEndOfDay(
            context: modelContext,
            today: today,
            cap: 30                  // bounded walk
        )
        profile.distinctOpenDays += 1
        profile.lastForegroundDay = today
    } else if profile.lastForegroundDay == nil {
        profile.distinctOpenDays += 1
        profile.lastForegroundDay = today
    }
    // ... existing refresh logic
}
```

`ScenePhase.active` triggers `LifeClockStore.refresh()` via the existing pattern in `LifeClockApp.swift`. No new SwiftUI hooks required.

### Implementation Tracks

Each track is a coherent unit. **Internal dependencies:** 3c depends on 3a + 3b. 3d depends on 3a + 3c. 3a and 3b can land in any order.

#### Track 3a — Engine primitives (zero dependencies)

**Goal:** AffinityEngine, NeedWeightEngine, QuestSelector ship as pure functions over typed inputs. QuestEventKind / QuestResolvedKind enums live in `QuestPoolTypes.swift`. `QuestPool.byGenre` precompute lands. No schema changes, no UI, no flag wiring. Engines are testable in isolation.

Tasks:

1. Add `QuestEventKind` and `QuestResolvedKind` enums to `Sources/Models/QuestPoolTypes.swift`. Use `String` raw values matching the Phase 2 column conventions (`shown`, `picked`, `replaced`, `completed`, `passed_over`, `abandoned`).
2. Extend `QuestPool` ([QuestPool.swift](products/life-clock-ios/Sources/Engines/QuestPool.swift)) with the `byGenre: [Genre: [PoolQuest]]` precompute. Update `quests(in:)` to use it. (todo 049 #5)
3. Add `Sources/Engines/AffinityEngine.swift`:
   - `static let alpha: Double = 0.2`
   - `static func computeAffinities(events: [QuestEvent]) -> [Genre: Double]`
   - `static func signal(for kind: QuestEventKind, resolvedKind: QuestResolvedKind?) -> (target: Double, weight: Double)?`
   - Initial value `0.5` per genre. Sort events ascending by `date` before folding.
4. Add `Sources/Engines/NeedWeightEngine.swift`:
   - `static func compute(profile: UserProfile, snapshots: [DailyHealthSnapshot]) -> [Genre: Double]`
   - Activity: HK steps p50 (reuse the existing `QuestEngine.movementStepTarget` p50 helper — extract to a private static `static func p50(_:)<T: Comparable>` shared utility).
   - Sleep: p50 of `DailyHealthSnapshot.sleepHours` over recent 14 days. <5 valid days → fall back to `profile.sleepGoalHours`.
   - Diet: `profile.dietQualityBaseline` ('rough'→0.9, 'okay'→0.6, 'great'→0.3). Override upward to 0.9 if `profile.alcoholFrequency == 'heavy'`.
   - HK trumps onboarding self-report on disagreement (master plan D7).
5. Add `Sources/Engines/QuestSelector.swift`:
   - `static func select(pool: QuestPool, affinity: [Genre: Double], needWeight: [Genre: Double], profile: UserProfile, today: Date, events: [QuestEvent]) -> [PoolQuest]`
   - `static func resolveEndOfDay(context: ModelContext, today: Date) throws`
   - Discovery damp: `0.3 + 0.7 * min(profile.distinctOpenDays / 7.0, 1.0)`.
   - Score: `pow(affinity[g], discoveryDamp) * needWeight[g] * recencyDecay(slug, today, events) * 1.0` (timeOfDayFit deferred, always 1.0 in Phase 3).
   - **Performance: precompute `latestShownBySlug: [String: Date]` once at top of `select(...)`** by single-pass over `events` filtering `kind == "shown"`. Then `recencyDecay(slug)` is O(1) dict lookup → `exp(-Δt / 3.5)`. Drops Phase 4-scale comparisons from 135k to 1500 (per performance-oracle review).
   - Per-genre top-1; conflict pass on `exclusionGroups` bounded at 5 iterations; **deterministic tiebreaker is slug-ascending lexical order** (already enforced by `QuestPool.byGenre` sort). Deadlock fallback emits `consistency.open-app-tomorrow.v1` (constructed manually — not in pool).
   - **EOD resolver: single broad fetch** of all `QuestEvent` rows where `date < today AND date >= today - 30 days AND resolvedKind == nil`. Group by `(date, slug)` in-memory into `[DateSlug: Set<QuestEventKind>]`. Walk unresolved rows resolving against the dict — one fetch, O(n) in-memory pass (per performance-oracle review). Single broad batch update for rows older than 30 days.
   - **Replaced + passedOver guard:** when resolving a `shown` row, check the in-memory dict for a `replaced` event matching `(date, slug)`; if present, leave the `shown` row unresolved (the slug was already negatively signaled — don't double-count via `passedOver`). G22.

Tests:

- `Tests/AffinityEngineTests.swift`:
  - `testInitialAffinityIs0_5ForEveryGenreOnEmptyHistory`
  - `testCompletedEventNudgesAffinityUp` (single event, pin EMA value to 4 decimals)
  - `testReplacedEventNudgesAffinityDownTwiceAsHard` (1.5× weight)
  - `testPickedThenAbandonedDecreasesAffinity`
  - `testShownThenPassedOverHasMildEffect` (0.3 target × 0.5 weight)
  - `testEMAConvergesToward1OnAllCompletedHistory`
  - `testEventsSortedByDateBeforeFolding` (out-of-order input still produces stable output)

- `Tests/NeedWeightEngineTests.swift`:
  - `@Test(arguments:)` over (steps p50, sleep p50, dietBaseline, alcoholFreq) tuples → expected need-weight per genre.
  - HK-trumps-onboarding case: `dietQualityBaseline = 'great'` + 2,400 daily steps → activity weight stays high.
  - Insufficient HK data fallback to onboarding.

- `Tests/QuestSelectorTests.swift`:
  - `testEmitsThreeQuestsOnePerGenre`
  - `testHardGenreFloorEnforced` (one genre's affinity = 0, still represented)
  - `testExclusionGroupConflictResolvedByDroppingLowerScore`
  - `testRecencyDecayDeprioritizesRecentlyShownSlugs`
  - `testDiscoveryDampReducesAffinityImpactOnDay1`
  - `testDeadlockEmitsConsistencyFallback` (every activity slug shares an exclusion group with the chosen sleep slug)
  - `testEndOfDayResolverFillsResolvedKindOnUnresolvedRows`
  - `testEndOfDayResolverIsIdempotentAcrossDoubleFire`
  - `testEndOfDayResolverBoundedAt30Days`
  - 50-trial property-style test using `SystemRandomNumberGenerator` seeded deterministically: assert 3 distinct slugs / 3 genres / no exclusion violation / determinism given (inputs + seed).

Acceptance:
- [ ] Tests green: AffinityEngine, NeedWeightEngine, QuestSelector. ≥40 new test cases.
- [ ] No schema changes, no `LifeClockStore` changes, no UI changes.
- [ ] `byGenre` precompute lands; `quests(in:)` becomes O(1).
- [ ] Existing test suite still green.

#### Track 3b — Schema additions + bootstrap + upsertQuest fix

**Goal:** Schema bumps to V1.5.0 with three new `UserProfile` fields. `bootstrapQuestGenres()` ships and is wired into `LifeClockStore.bootstrap()`. `upsertQuest` propagates `genre` on both insert and update paths. No engine code, no event emission yet.

Tasks:

6. Bump `LifeClockSchemaV1.versionIdentifier` from `Schema.Version(1, 4, 0)` → `Schema.Version(1, 5, 0)`. Header comment block adds a `1.5.0 (2026-05-08): Phase 3 ...` entry.
7. Add `distinctOpenDays: Int = 0`, `lastForegroundDay: Date? = nil`, `useQuestPoolEngine: Bool = false` to `LifeClockSchemaV1.UserProfile`. Property-level defaults verified.
8. Add `LifeClockStore.bootstrapQuestGenres()` (todo 049 #2):
   - `FetchDescriptor<Quest>(predicate: #Predicate { $0.genre == "" })` — find unbackfilled rows.
   - Map each by slug using the migration table from the master plan ([Migration Mapping section](docs/plans/2026-05-08-feat-quest-pool-affinity-engine-plan.md)).
   - `consistency.open-app-tomorrow.v1` stays out-of-pool — no genre.
   - Idempotent: subsequent runs find no `genre == ""` rows.
   - Called once from `LifeClockStore.bootstrap()` after migration completes.
9. Fix `upsertQuest(...)` to propagate `genre` (todo 049 #1) — **with empty-genre guard per data-integrity review**:
   - Constructor call ([LifeClockStore.swift:1122](products/life-clock-ios/Sources/App/LifeClockStore.swift)) gains `genre: quest.genre`.
   - Update branch ([LifeClockStore.swift:1136-1140](products/life-clock-ios/Sources/App/LifeClockStore.swift)) gains a guarded write: `if !quest.genre.isEmpty { stored.genre = quest.genre }`. Prevents the `consistency.open-app-tomorrow.v1` fallback path (which carries `genre = ""` per G16) from clobbering a `bootstrapQuestGenres`-backfilled non-empty value.

Tests:

- `Tests/LifeClockSchemaMigrationTests.swift` (extend):
  - `testV150NewUserProfileFieldsDefaultToZeroNilFalse` — default-state guard.
  - `testV150UserProfileFieldsRoundTripThroughFileBackedStore` — exercises lightweight migration path on a real on-disk SQLite store.

- `Tests/LifeClockStoreTests.swift` (extend):
  - `testBootstrapQuestGenresBackfillsLegacyRows` — insert 3 legacy Quest rows with `genre == ""`, run bootstrap, assert each has the correct `genre` per the migration table.
  - `testBootstrapQuestGenresIsIdempotent` — second run is no-op.
  - `testBootstrapQuestGenresLeavesConsistencyFallbackUntouched` — `consistency.open-app-tomorrow.v1` stays at `genre == ""`.
  - `testUpsertQuestPropagatesGenreOnInsert` — engine emits a Quest with `genre = "activity"`, store persists it with `genre = "activity"`.
  - `testUpsertQuestPropagatesGenreOnUpdate` — pre-existing row at `(slug, date)` gets its `genre` refreshed when engine emits a new copy.
  - `testUpsertQuestWithEmptyGenreDoesNotClobberBackfilledRow` — the consistency fallback (carrying `genre = ""`) does NOT overwrite a previously-backfilled `genre = "activity"` value.
  - `testV130ToV150DoubleHopMigration` — seed an on-disk store with V1.3.0 schema (or a fixture matching V1.3.0 column shape), open with V1.5.0 schema, assert every V1.4.0 + V1.5.0 field round-trips correctly. Validates devices skipping V1.4.0 directly.

Acceptance:
- [ ] V1.4.0 → V1.5.0 file-backed round-trip migration test green on-device (the only path that catches NSCocoaErrorDomain 134110).
- [ ] `bootstrapQuestGenres` runs at app launch; idempotent.
- [ ] `upsertQuest` no longer drops `genre`. Verified by both a positive and a regression test.
- [ ] All existing tests green.

#### Track 3c — Emission hooks + feature flag wiring (depends on 3a + 3b)

**Goal:** The four event-emission hook points fire `QuestEvent` rows. The `useQuestPoolEngine` flag gates the new `QuestEngine.generateDailyQuests` path. `distinctOpenDays` increments on first foreground per local day. End-to-end integration tests with the flag flipped on.

Tasks:

10. Add private `LifeClockStore.emitShown(slug:genre:date:)` with idempotent dedup (todo 049 #4): `FetchDescriptor<QuestEvent>(predicate: #Predicate { $0.date == dayStart && $0.slug == slug && $0.kind == "shown" })` — skip insert if exists.
11. Wire `shown` emission inside the persistence path that runs after `QuestEngine.generateDailyQuests` returns. Emit one row per emitted slug. Gate behind `profile.useQuestPoolEngine`.
12. Wire `picked` and `replaced` emissions in `LifeClockStore.applyPlanOverride(...)`:
    - `picked` when a quest is added to today's plan via the editor.
    - `replaced` when an existing slot's slug changes (slug A → slug B). Both rows logged.
    - Gated behind `profile.useQuestPoolEngine`.
13. Wire `completed` emission in `LifeClockStore.toggleQuestCompletion(...)` ([LifeClockStore.swift:716-733](products/life-clock-ios/Sources/App/LifeClockStore.swift)). Gated behind `profile.useQuestPoolEngine`.
14. Branch in `QuestEngine.generateDailyQuests` on `profile.useQuestPoolEngine`:
    - Flag false → existing legacy path (unchanged).
    - Flag true → new `selectorPath` that loads `QuestPool` from bundle (or accepts injected pool for tests), fetches `[QuestEvent]` from context, calls AffinityEngine + NeedWeightEngine + QuestSelector, materializes each `PoolQuest` into a `Quest` SwiftData row, returns the slate.
15. Increment `distinctOpenDays` in `LifeClockStore.refresh()` on first foreground per local day. Update `lastForegroundDay`.

Tests:

- `Tests/LifeClockStoreTests.swift` (extend):
  - `testCompletedEventEmittedOnTickWhenFlagIsOn`
  - `testCompletedEventNotEmittedWhenFlagIsOff`
  - `testShownEventEmittedAfterEnginePathRunsWhenFlagIsOn`
  - `testShownEventDedupedIfEngineRunsTwiceSameDay`
  - `testPickedAndReplacedEventsEmittedOnPlanEditorSwap`
  - `testDistinctOpenDaysIncrementsOnFirstForegroundPerCalendarDay`
  - `testDistinctOpenDaysDoesNotIncrementOnSecondForegroundSameDay`
- `Tests/QuestEngineTests.swift` (extend):
  - `testFlagOffPreservesLegacyPath` — every existing test still passes when `useQuestPoolEngine == false`.
  - `testFlagOnRoutesToSelectorPath` — fixture pool + flag on, slate of 3 emerges from selector.

Acceptance:
- [ ] Every emission hook tested with flag on AND off.
- [ ] Flag-off path: no `QuestEvent` rows ever written; legacy tests unchanged.
- [ ] Flag-on path: `QuestEngine` emits 3 `Quest` rows from the fixture pool, each with a `shown` event logged.
- [ ] All existing tests green.

#### Track 3d — EndOfDay resolver wiring (depends on 3a + 3c)

**Goal:** The EOD resolver fires on first foreground of a new day, walks unresolved `QuestEvent` rows from prior days, fills `resolvedKind`. Multi-day offline scenarios handled.

Tasks:

16. Wire `QuestSelector.resolveEndOfDay(...)` invocation into `LifeClockStore.refresh()` — runs before the daily quest emit, only when `profile.lastForegroundDay < today`. Gate behind `profile.useQuestPoolEngine`.
17. Verify SwiftUI integration: `LifeClockApp.swift` already calls `store.refresh()` on `ScenePhase.active`. Confirm path is correct (no new code expected; test that the hook fires).

Tests:

- `Tests/LifeClockStoreTests.swift` (extend):
  - `testRefreshRunsEodResolverOnFirstForegroundOfNewDay`
  - `testRefreshDoesNotRunEodResolverOnSecondForegroundSameDay`
  - `testEodResolverHandles3DayOfflineGap`
  - `testEodResolverIsIdempotentIfFiredTwice` (foreground race)
  - `testEodResolverBoundedAt30DaysOnLongOfflineGap`

Acceptance:
- [ ] EOD resolver fires once per local-day boundary.
- [ ] Multi-day gaps handled (per-day walk for ≤30 days; bulk update for older).
- [ ] No double-fill on idempotent re-fires.
- [ ] Flag-off: resolver never runs.

## Edge Cases & Gap Resolutions

The master plan resolved 13 gaps (G1–G13) at design time. Phase 3 introduces a few implementation-specific edge cases.

- **G14 — Pool injection for tests vs production.** `QuestEngine.selectorPath` accepts an optional `QuestPool` parameter. Production code passes `nil` and the engine lazy-loads `Bundle.main`. Tests pass the fixture pool directly. This avoids `Bundle.main` resolution leaking into pure-function engine tests.
- **G15 — Empty production pool + flag on.** If the flag is flipped before Phase 4's pool authoring lands, `QuestPool.loadFromBundle` returns an empty pool. `QuestSelector.select` on an empty pool returns the `consistency.open-app-tomorrow.v1` fallback for all three slots. Documented; not a crash.
- **G16 — `consistency.open-app-tomorrow.v1` is out-of-pool.** Construct the fallback `Quest` manually inside `QuestSelector` (not from `QuestPool`). It carries `genre = ""` (empty string sentinel — `bootstrapQuestGenres` does not assign it a genre, by design).
- **G17 — `replaced` event with no prior `picked`.** If a user swaps directly without a prior pick (e.g. swap on the engine-emitted default), log only `replaced(A) + picked(B)`. No fabricated `picked(A)` event.
- **G18 — `distinctOpenDays` rollback on uninstall.** Lost. Documented as accepted behavior — the discovery window resets on a fresh install.
- **G19 — Tone toggle mid-day with flag on.** `Quest.title` is snapshotted at emit time but views render through `QuestPool.copy(slug, tone:)`. Toggling tone refreshes copy live without DB write. Falls through to `quest.title` when slug isn't in pool (legacy path).

- **G20 — Selector tiebreaker is slug-ascending lexical.** When multiple slugs in the same genre tie on score, the deterministic tiebreaker is slug-ascending lexical order (already enforced by `QuestPool.byGenre[genre]` sort). Documented invariant; tested by `testTiebreakIsLexicalSlugOrder`.

- **G21 — Re-emit determinism after mid-emit kill.** If `selectorPath` returns a slate but the app dies before `LifeClockStore` writes `shown` events, the next foreground re-emits. Materialization MUST route through `upsertQuest`, not direct insert, so `(slug, date)` collision becomes an idempotent update. `testSelectorPathIsIdempotentOnDoubleFireSameDay` covers this.

- **G22 — `replaced` + `passedOver` double-count guard.** When EOD resolver evaluates a `shown` row, it checks the in-memory grouping for a `replaced` event matching `(date, slug)`. If present, the `shown` row is left unresolved (the slug already received a negative signal via `replaced`; resolving as `passedOver` would penalize affinity twice). `testReplacedSlugIsNotAlsoMarkedPassedOver` covers this.

- **G23 — EOD-before-affinity-read invariant.** `LifeClockStore.refresh()` runs `QuestSelector.resolveEndOfDay(...)` BEFORE `QuestEngine.generateDailyQuests(...)`. Today's affinity computation sees yesterday's freshly-resolved `passedOver` and `abandoned` events. Documented in `refresh()` with a comment; `testEodResolverRunsBeforeAffinityRead` covers it.

- **G24 — Quest sheet observes tone toggle live.** Sheets that render quest copy must observe `UserProfile.toneMode` via `@Bindable` (or read from the live store), not capture by value at presentation time. A mid-day tone change re-renders an open sheet without dismissal. UI-test `testQuestSheetReRendersOnToneToggle` covers this.

- **G25 — DST single-fire.** "First foreground per local day" uses `Calendar.current.startOfDay(for:)`. On a 25-hour day (fall-back), the local calendar still rolls over once → single fire. On a 23-hour day (spring-forward), same. `testDstSpringForwardSingleFire` and `testDstFallBackSingleFire` cover both with a fixed-TZ test clock.

- **G26 — Empty-pool flag-on guard.** If `useQuestPoolEngine == true` AND `pool.quests.isEmpty` (Phase 5a flips the flag before Phase 4 pool authoring lands), `QuestEngine.generateDailyQuests` logs `pool.empty.guard` and falls through to the legacy 15-inlined-quest path for that session. Avoids 3x `consistency.open-app-tomorrow.v1` for every user every day. `testEmptyPoolWithFlagOnFallsBackToLegacyPath` covers this.

## Migration Plan (V1.4.0 → V1.5.0)

Three additive `UserProfile` fields, all property-level defaulted. Lightweight migration applies automatically. `LifeClockMigrationPlan.stages` stays empty (per the established convention for additive bumps).

**Real-device verification required.** The simulator skips lightweight migration on fresh installs; an on-device build is the only way to catch a missed property-level default.

## Acceptance Criteria

### Functional Requirements

- [ ] All four engines (AffinityEngine, NeedWeightEngine, QuestSelector, EndOfDayResolver) ship as pure functions or stateless static methods.
- [ ] `QuestEventKind` and `QuestResolvedKind` enums replace stringly-typed read sites in this PR's new code.
- [ ] `QuestPool.byGenre` precompute lands; `quests(in:)` is O(1).
- [ ] `useQuestPoolEngine` flag gates every new code path.
- [ ] Flag-off path: zero `QuestEvent` rows written, legacy `QuestEngine` path unchanged.
- [ ] Flag-on path with fixture pool: 3 quests emitted per day, one per genre, with exclusion-group conflict resolution.
- [ ] `bootstrapQuestGenres` backfills legacy Quest.genre at app launch; idempotent.
- [ ] `upsertQuest` propagates `genre` on both insert and update.
- [ ] `distinctOpenDays` increments on first foreground per local calendar day.
- [ ] EOD resolver fires on first foreground of a new day; bounded walk at 30 days.
- [ ] Tone toggle refreshes rendered copy via `QuestPool.copy(slug, tone:)` without DB write.

### Non-Functional Requirements

- [ ] V1.4.0 → V1.5.0 lightweight migration runs cleanly on a real-device build (no simulator-only verification).
- [ ] `QuestSelector.select` p99 < 5ms with the **90-slug Phase 4 pool size and 1500 events in history** (precompute `latestShownBySlug` makes this achievable). Synthetic-load test asserts the budget.
- [ ] No new privacy-sensitive data leaves the device. `QuestEvent` retention is unbounded in this PR (retention policy lands in a follow-up — see Out of Scope).

### Quality Gates

- [ ] ≥30 new unit tests across AffinityEngineTests, NeedWeightEngineTests, QuestSelectorTests.
- [ ] ≥10 new integration tests in LifeClockStoreTests covering each emission hook + flag-on/off branches.
- [ ] Flag-off path: existing `QuestEngineTests`, `LifeClockStoreTests`, and `LifeClockE2ETests` all green with no behavior change.
- [ ] Property-style test: 50 random synthetic states, all selector invariants hold (deterministic given seed).

## Risk Analysis & Mitigation

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Flag flips on accidentally before Phase 4 pool ships | Medium | High | Default `false`; flag is a per-user `UserProfile` field, not a remote config. Phase 5a's flip is a code change requiring PR review. |
| V1.5.0 migration fails on real device | Low | High | Property-level defaults on every new field; file-backed round-trip test on every PR; explicit real-device verification in acceptance. |
| EOD resolver fires twice on cold-launch race | Low | Low | Idempotent fill (resolvedKind is set only if currently nil); double-fire is safe. |
| Selector deadlocks fall back too aggressively to consistency fallback | Low | Medium | Bounded conflict pass at 5 iterations + deadlock telemetry (`selector.deadlock` event); fixture pool's exclusion-group vocabulary is small enough that deadlock is near-impossible. |
| `bootstrapQuestGenres` slug→genre map drifts from migration table | Low | Medium | Single source of truth: the master plan's Migration Mapping table. Code comment links to it. Regression test asserts every entry in the table is reachable. |
| Affinity computation slow at year-3 user (30k events) | Low | Low | Flag defaults false in this PR — production users have 0 events. Caching is a follow-up tracked in Out of Scope §1. |
| Hidden affinity skew if `shown` events fail to log | Low | Medium | Idempotent emit; emit failure is logged but non-fatal. Tests assert emit happens for every selector output. |
| Quest.title snapshot diverges from current tone after toggle | Low | Low | Views resolve via `QuestPool.copy(slug, tone:)` first; persisted title is fallback. Tone toggle integration test covers this. |
| Property-style test flakes on CI | Low | Low | Deterministic seed; failing seed logged for reproduction. |
| V1.3.0 → V1.5.0 double-hop fails on user device | Low | High | Explicit `testV130ToV150DoubleHopMigration` seeds a V1.3.0 store fixture, opens with V1.5.0, asserts every field round-trips. Required real-device verification. |
| `upsertQuest` clobbers backfilled genre with `""` | Eliminated | High | `if !quest.genre.isEmpty` guard on the update branch + regression test. |
| Selector p99 budget regresses at Phase 4 scale | Eliminated | Medium | `latestShownBySlug` precompute drops 90×N comparisons to N. Acceptance criterion now pins to 90-slug + 1500-event load. |
| EOD resolver causes 200–500ms launch jank | Eliminated | High | Single broad fetch + in-memory `(date, slug)` grouping; one query instead of 360. |
| QuestEvent table scan grows with retention | Eliminated | Medium | `#Index<QuestEvent>([\.date, \.slug, \.kind])` in V1.5.0 schema. |
| Phase 5a flag flip with empty pool ships consistency-fallback to all users | Eliminated | High | Empty-pool guard at `QuestEngine.generateDailyQuests` falls through to legacy path + logs `pool.empty.guard`. |
| `replaced` + `passedOver` double-count penalizes the same slug twice | Eliminated | Medium | EOD resolver guard skips `shown` rows when a `replaced` event exists for the same `(date, slug)`. G22. |

## Out of Scope (deferred)

These are explicit deferrals tracked for a future Phase 3.5 or Phase 4:

1. **Affinity caching** — `UserProfile.affinityState: Data` (incremental EMA cache) for year-3 users at 30k events. Phase 3 ships non-cached because the flag default is `false`, so production users accumulate no events. Revisit when flag flips and event volume scales.
2. **Sleep p50 from HKSampleQuery** — Phase 3 reads `DailyHealthSnapshot.sleepHours` (already captured by `LiveHealthKitService`). A separate `HKStatisticsQuery`/`HKSampleQuery` directly to HealthKit is not necessary and adds API surface.
3. **PropertyBased library integration** — Phase 3 hand-rolls 50-trial property tests with a seeded `SystemRandomNumberGenerator`. The `swift-testing` `PropertyBased` library lands in a polish PR if shrinking is needed.
4. **`EligibilityFilter` on PoolQuest** — Phase 2 cut this; Phase 4's authored slugs bring it back. Phase 3's selector skips eligibility filtering entirely (fixture pool has no contraindicated slugs; production pool ships empty).
5. **`QuestEvent` retention policy** — 365-day rolling window with per-genre rollup (master plan G11). Implemented when event volume justifies; Phase 3 with flag-default-false keeps event count at zero.
6. **Composite uniqueness on `QuestEvent`** — application-level dedup ships for `shown` events (idempotent emit). Comprehensive dedup for `picked / replaced / completed` ships when Phase 5a flips the flag.
7. **`selector.deadlock` telemetry** — emit a structured event when deadlock fallback fires. Phase 3 logs to console only; structured telemetry lands when telemetry infrastructure exists.
8. **Phase 4 (90-quest pool authoring)** — explicitly out of scope. Requires senior tone-aware reviewer cycles.
9. **Phase 5 (cutover + flag flip)** — explicitly out of scope. Requires Phase 4 + a ≥1-week production bake.

## Sources & References

### Origin

- **Master plan:** [docs/plans/2026-05-08-feat-quest-pool-affinity-engine-plan.md](docs/plans/2026-05-08-feat-quest-pool-affinity-engine-plan.md). Phase 3 inherits design decisions D1–D10, edge-case resolutions G1–G13, and the deepening insights applied in Enhancement Summary.
- **Phase 3 prep todo:** [todos/049-pending-p3-quest-pool-phase3-prep.md](todos/049-pending-p3-quest-pool-phase3-prep.md). Seven findings carried into this plan as hard requirements.
- **Brainstorm:** [docs/products/life-clock/plan-quest-generation-affinity.md](docs/products/life-clock/plan-quest-generation-affinity.md).

### Internal References

- [QuestEngine.swift](products/life-clock-ios/Sources/Engines/QuestEngine.swift) — current engine; gets a new selector branch.
- [QuestPool.swift](products/life-clock-ios/Sources/Engines/QuestPool.swift) — gets `byGenre` precompute.
- [QuestPoolTypes.swift](products/life-clock-ios/Sources/Models/QuestPoolTypes.swift) — gets event-kind enums.
- [LifeClockSchema.swift](products/life-clock-ios/Sources/Models/LifeClockSchema.swift) — V1.4.0 → V1.5.0 with three new `UserProfile` fields.
- [LifeClockStore.swift:716-733](products/life-clock-ios/Sources/App/LifeClockStore.swift) — completion toggle; new event hook.
- [LifeClockStore.swift:1073-1107](products/life-clock-ios/Sources/App/LifeClockStore.swift) — `applyPersistedCompletions` slug match path; survives migration.
- [LifeClockStore.swift:1122 + 1136-1140](products/life-clock-ios/Sources/App/LifeClockStore.swift) — `upsertQuest` constructor + update branch; gets `genre` propagation fix.
- [QuestEngine.swift:292-299](products/life-clock-ios/Sources/Engines/QuestEngine.swift) — existing steps p50 helper; extracted for reuse.
- [LifeClockSchemaMigrationTests.swift:197-216](products/life-clock-ios/Tests/LifeClockSchemaMigrationTests.swift) — sibling-coverage test pattern; mirrored for new UserProfile fields.
- [docs/solutions/integration-issues/swiftdata-mandatory-attribute-migration-landmine.md](docs/solutions/integration-issues/swiftdata-mandatory-attribute-migration-landmine.md) — applies to V1.5.0 fields.

### Related Work

- PR #30 (Phase 2 schema + storage) — predecessor; this plan builds on its types and pool loader.
- todo 048 (Phase 2 review nits, completed) — applied alongside Phase 2.
- todo 049 (Phase 3 prep) — fully consumed by this plan; closeable when Phase 3 ships.
