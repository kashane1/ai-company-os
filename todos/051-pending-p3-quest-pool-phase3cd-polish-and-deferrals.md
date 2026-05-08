---
status: pending
priority: p3
issue_id: 051
tags: [code-review, life-clock, ios, cleanup, quest-pool, phase-3-polish]
dependencies: []
pr: https://github.com/kashane1/ai-company-os/pull/32
---

# Quest Pool Phase 3c+3d — polish + deferrals from PR #32 review

## Problem Statement

Multi-agent review of PR #32 (Phase 3c + 3d wiring) surfaced 1 CRITICAL + 2 IMPORTANT items (all resolved inline on the PR — see commit history) plus several P3 nits and design deferrals. This todo bundles the P3 work as one followup.

## Findings

### Resolved inline (CRITICAL + IMPORTANT)

The review fixes are already on PR #32 — listed here so the synthesis is complete:

- **CRITICAL #7 (data-integrity)**: `emitCompleted` after un-tick + re-tick let stale `completed` events poison affinity. **Fixed**: un-tick now calls `removeCompleted(slug:date:)` to delete the matching row. Symmetric with the ledger-entry deletion that already happened on un-tick. Two new tests pin the corrected behavior.
- **IMPORTANT #8 (data-integrity)**: `emitPicked`/`emitReplaced` inserted into ModelContext but `selectPlanQuest` only saved UserDefaults. App force-quit between insert and next save lost events. **Fixed**: explicit `try? modelContext.save()` at end of `selectPlanQuest`.
- **IMPORTANT (architecture #3)**: `eventGenre` and inline `slugGenreMap[slug]` calls had drift risk. **Fixed**: extracted `private static func genreFor(slug:)`; both call sites route through it.
- **NICE-TO-HAVE (performance)**: defensive `fetchLimit` caps applied to `fetchAllQuestEvents` (5000, sorted desc) and `resolveEndOfDay`'s bulk pass (1000). Year-3 users at 30k+ events no longer materialize 6MB on every emit; users offline 6 months no longer see a 500ms cold-launch stall.
- **NICE-TO-HAVE (simplicity)**: dropped duplicate `testFlagOffWithPoolInjectedStillRoutesLegacy`.

### P3 still open

1. **Daily-cycle hook placement coupling** (architecture #1) — currently lives inside `refreshFromHealthKit`. Future code paths that call `refreshFromHealthKit` trigger EOD resolution; paths that bypass HK refresh (notification deep-link, future widget timeline) skip it. Cleaner shape: hoist to a dedicated `func onForeground()` called from `ScenePhase.active` in LifeClockApp.swift, and have it invoke both `runDailyCycleIfNewDay` and `refreshFromHealthKit`. Phase 4 refactor candidate.

2. **EOD resolver / increment ordering not transactional** (data-integrity #2) — if `QuestSelector.resolveEndOfDay` throws, the `distinctOpenDays += 1` and `lastForegroundDay = dayStart` updates still happen, advancing the cursor past unresolved events. Workaround: wrap all three writes in a `do/catch` that rolls back the increments on resolver failure, or use a `try modelContext.transaction { ... }` block. Bounded impact (one missed resolution; resolved on next launch since lastForegroundDay sticks at today).

3. **Daily-cycle before short-circuit on cross-midnight slate staleness** (data-integrity #4) — when the user opens the app at 23:59 and `refreshFromHealthKit` returns early via short-circuit, then re-foregrounds at 00:01, the daily-cycle hook fires before the short-circuit re-checks today's snapshot. Today's slate could be stale (still showing yesterday's emit). Mitigation: after `runDailyCycleIfNewDay` triggers, force `refreshFromHealthKit(force: true)` to regenerate today's slate. Bounded — a refresh on next user-action would correct.

4. **Calendar injection in `resolveEndOfDay`** (data-integrity #9) — `QuestSelector.resolveEndOfDay` uses `Calendar.current` directly. If a test injects a non-default-calendar clock, the resolver partitions events using a different calendar than the emit path. Latent — current code paths use `clock.calendar` for emit (start-of-day) which is `Calendar.current` in production; tests that don't override `clock.calendar` are safe. Phase 4 follow-up.

5. **`QuestEvent` retention policy** (data-integrity #10) — no GDPR right-to-erasure path. Bounded growth (~5500 rows/year) but indefinite retention. Phase 5 should add a 365-day rolling window with per-genre rollup.

6. **Four emit helpers vs unified `emit(kind:dedupe:)`** (simplicity #4) — borderline. Architecture review pushed to keep four helpers because the dedup-vs-not-dedup semantic is documented at the function level, not as a parameter flag. Revisit if a fifth event kind (e.g., `dismissed`) lands.

7. **`generateDailyQuests` signature with default-nil pool/events** (architecture #6) — caller-side mistake (forgetting to pass events/pool when flag is on) silently falls through the empty-pool guard to legacy. Correct outcome but for the wrong reason. Phase 4 should pick: (a) require params, no defaults; or (b) split into `selectFromPool(...)` entry point. (b) is the longer-term shape.

8. **`cachedQuestPool` cache invalidation** (architecture #2) — never cleared. Fine for Phase 3 (pool JSON is bundle-static). When Phase 4 lands hot-reloadable pool JSON or remote config, this becomes a footgun. Add a one-line comment at the cache definition documenting the assumption.

9. **`runDailyCycleIfNewDay` first-launch increment** (data-integrity #3) — guard is `lastForegroundDay >= dayStart`; a fresh install with `nil` falls through and increments to 1 on first launch. This is correct behavior (the user did open the app for the first time today) but worth a comment so future readers don't read it as a bug.

10. **Replaced events not deduped per G7 — citation in code** (data-integrity #6) — `emitReplaced` is intentionally non-dedupping. Add a one-line code comment citing master plan G7.

## Proposed Solutions

**Option A: Phase 4 prep PR.**
Bundle items 1, 4, 7 into a refactor PR before Phase 4 lands. Items 2, 3 are real correctness gaps but bounded — fix with item 1 (since they're related to the daily-cycle hook architecture).

**Option B: Phase 5a hardening PR.**
Items 2, 3, 5 (transactional ordering, cross-midnight staleness, retention policy) all matter at flag-flip time. Bundle them as a hardening PR right before Phase 5a.

**Option C: Defer items 6, 8, 9, 10 to comment-only changes; address rest as preconditions for Phase 5a.**
Three minutes of code comments closes 4 of 10 items. The remaining six are work for Phase 4/5a prep.

## Recommended Action

(Filled during triage)

## Acceptance Criteria

- [ ] Items 6, 8, 9, 10 documented in code comments (low-effort).
- [ ] Items 1, 4, 7 either applied in Phase 4 prep PR OR explicitly deferred to Phase 5a hardening.
- [ ] Items 2, 3, 5 closed before Phase 5a flag flip.

## Resources

- PR: https://github.com/kashane1/ai-company-os/pull/32
- Phase 3c+3d plan: [docs/plans/2026-05-08-feat-quest-pool-phase-3cd-wiring-plan.md](docs/plans/2026-05-08-feat-quest-pool-phase-3cd-wiring-plan.md)
- Phase 3 plan: [docs/plans/2026-05-08-feat-quest-pool-phase-3-engines-plan.md](docs/plans/2026-05-08-feat-quest-pool-phase-3-engines-plan.md)
- Master plan: [docs/plans/2026-05-08-feat-quest-pool-affinity-engine-plan.md](docs/plans/2026-05-08-feat-quest-pool-affinity-engine-plan.md)
- Phase 3a+3b polish todo: [todos/050-pending-p3-quest-pool-phase3-polish-and-deferrals.md](todos/050-pending-p3-quest-pool-phase3-polish-and-deferrals.md)
