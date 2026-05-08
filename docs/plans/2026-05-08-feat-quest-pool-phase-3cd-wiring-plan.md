---
title: "feat: Quest Pool Phase 3c + 3d — emission hooks, feature flag wiring, EOD resolver"
type: feat
status: active
date: 2026-05-08
origin: docs/plans/2026-05-08-feat-quest-pool-phase-3-engines-plan.md
---

# feat: Quest Pool Phase 3c + 3d — emission hooks + flag wiring + EOD resolver

## Overview

Tracks 3c + 3d of the quest-pool affinity engine. Wires the engines that landed in [PR #31](https://github.com/kashane1/ai-company-os/pull/31) to the four UI hook points (`shown / picked / replaced / completed`), the feature flag at `QuestEngine.generateDailyQuests`, the cold-start `distinctOpenDays` increment, and the EOD resolver invocation in `LifeClockStore.refresh()`.

**Flag stays default `false`. Production behavior is byte-identical to main.** All new code paths are reachable only when tests flip `useQuestPoolEngine = true`.

This plan is execution-only. Design is in the master plan ([master](docs/plans/2026-05-08-feat-quest-pool-affinity-engine-plan.md)) and the Phase 3 plan ([phase-3](docs/plans/2026-05-08-feat-quest-pool-phase-3-engines-plan.md), Tracks 3c + 3d). Both are already deepened with 5 reviewers each. **No new deepening pass.** This plan cites both as origin and lists file-level work.

## Tasks

### Track 3c — Emission hooks + feature flag wiring

10. **`LifeClockStore.emitShown(slug:genre:date:)`** (idempotent dedup per todo 049 #4 + plan G14):
    ```swift
    private func emitShown(slug: String, genre: String, date: Date) {
        let dayStart = Calendar.current.startOfDay(for: date)
        // Idempotent dedup: skip if (date, slug, "shown") already exists.
        let predicate = #Predicate<QuestEvent> { event in
            event.date == dayStart && event.slug == slug && event.kind == "shown"
        }
        if (try? modelContext.fetch(FetchDescriptor<QuestEvent>(predicate: predicate)))?.first != nil {
            return
        }
        let event = QuestEvent(date: dayStart, slug: slug, genre: genre, kind: QuestEventKind.shown.rawValue)
        modelContext.insert(event)
    }
    ```

11. **Wire `shown` after `QuestEngine.generateDailyQuests`** in the persistence path. Gate behind `profile.useQuestPoolEngine`. One emit per slug in today's emitted slate.

12. **Wire `picked` + `replaced` in `LifeClockStore.applyPlanOverride(...)`**. The plan editor calls `applyPlanOverride` to swap a slot's slug. Detection:
    - If overriding a slot that currently has a slug, log `replaced(oldSlug)` (NOT deduped — multiple replacements of the same slug log every time, per master plan G7).
    - Then log `picked(newSlug)` (deduped per (date, slug, "picked")).
    - Both gated behind `profile.useQuestPoolEngine`.

13. **Wire `completed` in `LifeClockStore.toggleQuestCompletion(...)`** ([LifeClockStore.swift:716-733](products/life-clock-ios/Sources/App/LifeClockStore.swift)). When toggling to completed (not when unchecking), log `completed(slug)`. Idempotent per (date, slug). Gated behind flag.

14. **Branch in `QuestEngine.generateDailyQuests` on flag**, with **empty-pool guard (G26)**:
    - Add optional `pool: QuestPool? = nil` parameter on the engine entry point (per architecture review on Phase 3 deepening).
    - Production callers pass `nil` → engine lazy-loads `Bundle.main`. Tests inject directly.
    - If `profile.useQuestPoolEngine && !resolvedPool.isEmpty`: route through `selectorPath`.
    - If `profile.useQuestPoolEngine && resolvedPool.isEmpty`: log `pool.empty.guard` once per session and fall through to the legacy path. Avoids 3× consistency-fallback for every user every day if Phase 5a flips the flag before Phase 4 ships authored slugs.
    - Else: legacy path (unchanged).
    - `selectorPath`:
      - Fetch `[QuestEvent]` from `modelContext` for affinity input. (Bounded — no `fetchLimit` in Phase 3; cache deferred per master plan Out-of-Scope §1.)
      - `AffinityEngine.computeAffinities(events:)` → `[Genre: Double]`
      - `NeedWeightEngine.compute(profile:, recentSnapshots:)` → `[Genre: Double]`
      - `QuestSelector.select(pool:, affinity:, needWeight:, profile:, today:, events:)` → `[PoolQuest]`
      - Materialize each `PoolQuest` → `Quest` row with `genre = poolQuest.genre.rawValue`. Tone resolution at render time (not snapshotted) per master plan G2 — store `slug` and let views call `pool.copy(for:tone:)`.

15. **Increment `distinctOpenDays` in `LifeClockStore.refresh()`** on first foreground per local calendar day. Update `lastForegroundDay`.
    - Use `Calendar.current.startOfDay(for: clock.now())` to compute today's start.
    - Guard: `profile.lastForegroundDay == nil || profile.lastForegroundDay! < todayStart`.
    - On match: increment `distinctOpenDays`, set `lastForegroundDay = todayStart`, save.
    - DST safety (G25): `Calendar.startOfDay` correctly handles 25h/23h days — single fire on either.

### Track 3d — EOD resolver wiring

16. **Wire `QuestSelector.resolveEndOfDay(...)` in `LifeClockStore.refresh()`** with explicit ordering (G23):
    - First-foreground-of-new-day branch (added by task 15) is the trigger.
    - Order in the new-day branch:
      1. EOD resolver runs (resolves yesterday's unresolved events).
      2. `distinctOpenDays` increments + `lastForegroundDay` updates.
      3. Then the existing refresh flow (HK reads + engine emit).
    - This means today's affinity computation sees yesterday's freshly-resolved `passed_over` and `abandoned` events.
    - Gated behind `profile.useQuestPoolEngine`.

17. **Verify SwiftUI integration** — `LifeClockApp.swift` already calls `store.refresh()` on `ScenePhase.active`. No new SwiftUI hook required.

## Tests

- `LifeClockStoreTests` extensions:
  - `testCompletedEventEmittedOnTickWhenFlagIsOn` — toggle a quest with flag on, assert a `QuestEvent(kind: "completed")` row appears.
  - `testCompletedEventNotEmittedWhenFlagIsOff` — same toggle with flag off, assert no `QuestEvent` row.
  - `testShownEventEmittedAfterEnginePathRunsWhenFlagIsOn` — exercise `refreshFromHealthKit` with flag on + injected fixture pool, assert `shown` events for emitted slugs.
  - `testShownEventDedupedIfEngineRunsTwiceSameDay` — double-fire engine path, assert one `shown` row per slug.
  - `testPickedAndReplacedEventsEmittedOnPlanEditorSwap` — flip a slot's slug, assert `replaced(old) + picked(new)` rows.
  - `testReplacedEventLogsEveryTimeNotDedupedG7` — A→B→A→B sequence, assert four `replaced` rows.
  - `testDistinctOpenDaysIncrementsOnFirstForegroundPerCalendarDay` — call refresh twice on different calendar days, assert increments by 2.
  - `testDistinctOpenDaysDoesNotIncrementOnSecondForegroundSameDay` — call refresh twice same day, assert single increment.
  - `testFlagOffPreservesLegacyPath` — every existing engine-path test continues to pass with flag off.
  - `testFlagOnRoutesToSelectorPathWithFixturePool` — fixture pool injected + flag on, assert 3 quests emerge from selector (slug formats match `<genre>.fixture-*`).
  - `testEmptyProductionPoolWithFlagOnFallsBackToLegacyPath` (G26) — flag on, production pool (empty) — assert legacy 15-quest path runs.
  - `testRefreshRunsEodResolverOnFirstForegroundOfNewDay` — seed unresolved events from yesterday, refresh on next day, assert resolved.
  - `testRefreshDoesNotRunEodResolverOnSecondForegroundSameDay` — refresh twice same day, assert resolver fires once.
  - `testEodResolverRunsBeforeAffinityRead` (G23) — pre-existing `shown` row from yesterday gets resolved as `passed_over` BEFORE selectorPath reads events. Verifiable by inspecting `kindsByKey` ordering in tests.

- DST tests:
  - `testDstSpringForwardSingleFire` — 23-hour day, assert single `distinctOpenDays` increment.
  - `testDstFallBackSingleFire` — 25-hour day, single increment.

## Acceptance Criteria

- [ ] Flag-off path: every existing test stays green; zero `QuestEvent` rows written; legacy `QuestEngine` path unchanged.
- [ ] Flag-on path with fixture pool: 3 quests emitted per day, each emits one `shown` event; selector greedy + exclusion-group + hard floor honored.
- [ ] Picked/replaced events fire on plan editor swap; replaced is NOT deduped; picked IS deduped.
- [ ] Completed event fires on tick (flag on); not on uncheck.
- [ ] `distinctOpenDays` increments once per local calendar day; DST 25h/23h days fire once.
- [ ] EOD resolver fires on first foreground of new day; correctly partitions before-affinity-read.
- [ ] Empty production pool + flag on: graceful fallback to legacy path with single log line.
- [ ] All Phase 2/3a/3b tests still pass; new Phase 3c/3d tests pass.

## Out of Scope

- **Authoring 90 production quests (Phase 4)** — explicitly deferred.
- **Cutover (Phase 5)** — flag flip + production bake + retire 15 inlined constructors. Requires Phase 4 + calendar time.
- **`affinityState` cache** (master plan Out-of-Scope §1) — incremental EMA cache. Phase 3 ships non-cached.
- **`#Index<QuestEvent>` macro** — iOS 18+ only; deployment target is iOS 17. Tracked in todo 050.
- **True cross-version migration test** — same as todo 050.
- **`distinctOpenDays` race protection in async refresh** (data-integrity reviewer #6 from Phase 3 plan) — refresh runs on `@MainActor`; race risk is theoretical at current architecture. Track in todo 050 if it surfaces.

## Sources

- Master plan: [docs/plans/2026-05-08-feat-quest-pool-affinity-engine-plan.md](docs/plans/2026-05-08-feat-quest-pool-affinity-engine-plan.md)
- Phase 3 plan: [docs/plans/2026-05-08-feat-quest-pool-phase-3-engines-plan.md](docs/plans/2026-05-08-feat-quest-pool-phase-3-engines-plan.md) (Tracks 3c + 3d sections)
- Predecessor PRs: [#30](https://github.com/kashane1/ai-company-os/pull/30) (Phase 2), [#31](https://github.com/kashane1/ai-company-os/pull/31) (Phase 3a + 3b)
- Phase 3 prep todo: [todos/049-pending-p3-quest-pool-phase3-prep.md](todos/049-pending-p3-quest-pool-phase3-prep.md) (closed by this PR)
- PR #31 review polish todo: [todos/050-pending-p3-quest-pool-phase3-polish-and-deferrals.md](todos/050-pending-p3-quest-pool-phase3-polish-and-deferrals.md)
