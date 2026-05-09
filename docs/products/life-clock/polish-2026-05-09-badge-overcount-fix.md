# Polish Session — life-clock — 2026-05-09 — badge-overcount-fix

## Mode

`freeform-polish` (one-commit focused fix). Triggered by the spawn-task queued from [polish-2026-05-09-profile-section-sweep.md](polish-2026-05-09-profile-section-sweep.md). Branched off `main` (not the Profile-section-sweep PR) so the surfaces stay independent.

Iteration cap: 8. Used: 1. Final-check: source-driven repro with computer-use real touches.

## Repro (before fix)

Seed:

```
SIMCTL_CHILD_LIFECLOCK_UI_TEST_SCENARIO=onboarded
SIMCTL_CHILD_LIFECLOCK_USE_MOCK_HEALTH=1
SIMCTL_CHILD_LIFECLOCK_HEALTH_AUTH=authorized
```

Steps that surface the bug:

1. Launch on Today (default).
2. Tap **History** tab. Wait ~10s.
3. Tap **Profile** tab. Scroll to Completion badges.

Result: **"22 earned · 60 possible"** — including `data.rich.100`, `data.rich.30`, `data.rich.7`, `movement.steps7500.30`, `exercise.minutes30.30`, `sleep.goal.30`, all marked **Earned**. Captured at [`.polish/goldens/badge-overcount/03_BEFORE_22_earned_after_history_backfill.png`](../../../products/life-clock-ios/.polish/goldens/badge-overcount/03_BEFORE_22_earned_after_history_backfill.png).

The user just finished onboarding. They have not used the app for 100 days.

## Root cause

`HistoryView.onAppear` triggers a 10-year `HistoricalImportCoordinator.startIfNeeded()` when the user is Pro:

```swift
// products/life-clock-ios/Sources/Features/History/HistoryView.swift:44
.onAppear {
    if subscriptions.isPro {
        store.historicalImporter.startIfNeeded()
    }
}
```

The DEBUG simulator defaults to **Pro entitled** ([SubscriptionStore.swift:100](../../../products/life-clock-ios/Sources/Services/SubscriptionStore.swift) — `LIFECLOCK_SIMULATOR_PRO_DISABLED` is the opt-OUT). So a polish recon run that taps History inadvertently triggers a 10-year backfill of `MockHealthKitService` data: `~3,650 DailyHealthSnapshot` rows, all with `sourceCompleteness = 0.8` (≥ 0.75 the `dataRichDays` threshold), step counts in `3,500–13,000`, etc.

`LifeClockStore.completionBadgeProgress()` then aggregates those rows into a `CompletionBadgeProgress` shape that the engine reads. Predicates like `dataRichDays`, `stepTargetDays`, `exerciseTargetDays` count ALL persisted snapshots — including the years of pre-onboarding history.

This is not just a mock artifact. **Real users hit it too.** A user who upgrades to Pro on day 1 and triggers the backfill of THEIR actual Apple Health history immediately earns "100 days of step target" / "30 days of rich signal" — for days they captured in Apple Health long before LifeClock saw the data. The badge titles ("Captured a day with strong data completeness") imply days WHILE USING the app, not history pulled in retroactively.

## Fix

One change in [products/life-clock-ios/Sources/App/LifeClockStore.swift](../../../products/life-clock-ios/Sources/App/LifeClockStore.swift) — `completionBadgeProgress()` filters `habits`, `quests`, `snapshots`, `reports` by `date >= startOfDay(profile.onboardingCompletedAt)` before aggregating:

```swift
let onboardingDay: Date? = profile?.onboardingCompletedAt.map { dayKey(for: $0) }
let filterByOnboarding: (Date) -> Bool = { date in
    guard let onboardingDay else { return false }
    return date >= onboardingDay
}
let habits    = fetchAllHabits().filter    { filterByOnboarding(dayKey(for: $0.date)) }
let quests    = fetchAllQuests().filter    { filterByOnboarding(dayKey(for: $0.date)) }
let snapshots = fetchAllSnapshots().filter { filterByOnboarding(dayKey(for: $0.date)) }
let reports   = fetchAllWeeklyReports().filter { filterByOnboarding(dayKey(for: $0.weekStart)) }
```

Why this is the right shape:

- **Semantic.** Badges measure days WHILE USING the app. Pre-onboarding rows are by construction not "days the user captured strong data completeness." They're days that existed in Apple Health before LifeClock did.
- **Future-proof.** Any new badge that depends on counting historical day rows (e.g. nutrition tiers when a HabitLog import path lands) inherits the cap automatically.
- **Cheap.** Filtering 3,650 rows once per Profile render is trivial. No schema change. No migration. No additional queries.
- **No nil-profile regression.** If `profile` is somehow nil at the call site (shouldn't happen — Profile screen lives behind `RootView`'s `profiles.isEmpty` gate — but defensive), the predicate returns `false` for everything, so all tiered badges stay at zero. Only the two profile-independent starter badges (`start.first-profile`, `start.health-connected`) can still fire from their underlying flags, which is the safer default than over-counting.

## Test

New test in [Tests/LifeClockStoreTests.swift](../../../products/life-clock-ios/Tests/LifeClockStoreTests.swift):

```swift
func testCompletionBadgesDoNotCountSnapshotsBeforeOnboarding()
```

- Onboards a profile (`onboardingCompletedAt = fixedDate`).
- Inserts 200 backdated rich-signal snapshots (each step≥7,500, exercise≥30, sleep≥7.5h, sourceCompleteness=0.9).
- Asserts the two onboarding-tier badges are unlocked AND every tier-7/30/100 badge that depends on `dataRichDays`/`stepTargetDays`/`exerciseTargetDays`/`sleepGoalDays` is locked.

Pinning the regression: any future refactor that drops the filter (or accidentally re-introduces a pre-onboarding count path) flips this test red.

```
Test Case '-[LifeClockTests.LifeClockStoreTests testCompletionBadgesDoNotCountSnapshotsBeforeOnboarding]' passed (0.510 seconds).
** TEST SUCCEEDED **
```

The pre-existing `CompletionBadgeEngineTests` (catalog + tiered-progress) keep passing — the engine itself is unchanged; only the feeder shape narrowed.

## Verify (after fix)

Same 3-step repro from above:

- **"2 earned · 60 possible"** — only `start.first-profile` ("Clock started") and `start.health-connected` ("Signal linked"). Captured at [`.polish/goldens/badge-overcount/04_AFTER_2_earned.png`](../../../products/life-clock-ios/.polish/goldens/badge-overcount/04_AFTER_2_earned.png). ✓

(2 vs 22 — the delta with this fix on a fresh onboarded recon run.)

## Pre-existing test flakiness (NOT caused by this PR)

While running the wider `LifeClockStoreTests` suite, three tests failed:

- `testEveningLogDoesNotTriggerSuppressionPath` — `XCTAssertNil failed: "2027-01-16 20:00:00 +0000"` — appears to be a fixed-clock arithmetic issue around the 8…22 hour clamp.
- `testQuestCompletionSurvivesTitleRename` — `expected an emitted quest with slug sleep.consistency.v1; got slugs [activity.balance-stand-1min.v1, diet.breakfast-within-1hr.v1, sleep.bedtime-routine.v1]` — quest-pool seed drift.
- `testColdRestartLoadsPersistedProfile` (line 704 weekStart) — week boundary calendar drift.

**These also fail on clean `main` without this PR's diff applied** — confirmed by `git stash` + retest. Out of scope here; queue for a separate flake-fix session.

## Files changed

```
M  products/life-clock-ios/Sources/App/LifeClockStore.swift   (+17 -4)
M  products/life-clock-ios/Tests/LifeClockStoreTests.swift    (+53 -0)
A  docs/products/life-clock/polish-2026-05-09-badge-overcount-fix.md
```

## Next pass

- The DEBUG sim's "default Pro on" continues to bite recon runs (caught for the second time in two days — also flagged in [polish-2026-05-09-profile-section-sweep.md](polish-2026-05-09-profile-section-sweep.md)). Worth a `chore` commit to flip the env-var sense from `LIFECLOCK_SIMULATOR_PRO_DISABLED` to `LIFECLOCK_SIMULATOR_DEFAULT_PRO`, default off.
- The `LifeClockStoreTests` flakes above need a focused session — likely just clock fixtures drifting or quest-pool seed expectations needing a refresh.
