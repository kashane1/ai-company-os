# Polish Session — life-clock — 2026-05-10 — history-excludes-today

## Mode

`fix-list`. Observer = operator-supplied fix list. Single bug: the
History tab surfaced today's row at the top; History is
yesterday-and-earlier, today's data belongs on Today.

Iteration cap: 5. Final computer-use checkpoint: attempted, see
"Checkpoint" below.

## Root cause

`LifeClockStore.recentSnapshots(limit:)` returned everything
`fetchRecentSnapshots(limit:)` produced, including the today-keyed
`DailyHealthSnapshot` that `refreshFromHealthKit` persists on every
foreground. Both call sites of the public accessor are in
`HistoryView` ([Sources/Features/History/HistoryView.swift:87](../../../products/life-clock-ios/Sources/Features/History/HistoryView.swift),
[:129](../../../products/life-clock-ios/Sources/Features/History/HistoryView.swift)).
The three internal call sites that legitimately need today
(line 537 — today's quest generation context; line 608 — wrap-up
coordinator; line 670 — completion-badge tally) use
`fetchRecentSnapshots(limit:)` directly, not the public accessor.
Filtering at the public boundary is therefore both safe and the
lowest-blast-radius fix.

## Fix

`Sources/App/LifeClockStore.swift`:

```swift
func recentSnapshots(limit: Int, includingToday: Bool = false) -> [DailyHealthSnapshot] {
    if includingToday {
        return fetchRecentSnapshots(limit: limit)
    }
    let raw = fetchRecentSnapshots(limit: limit + 1)
    let todayStart = clock.calendar.startOfDay(for: clock.now())
    let filtered = raw.filter { !clock.calendar.isDate($0.date, inSameDayAs: todayStart) }
    return Array(filtered.prefix(limit))
}
```

- Uses the injected `EngineClock` rather than `Calendar.current` /
  `Date()` so the test pin (`.fixed(_:)`) drives the filter
  deterministically.
- Widens the internal fetch by 1 so callers asking for N still see
  N rows when a today-snapshot exists. With a 14-day seed
  (today + 13 prior) this surfaces 13 rows; with a fully-backfilled
  Pro user (today + ≥90 prior) the prefix-90 stays at 90.
- Default is `includingToday: false` — both `HistoryView` callers
  get the new behavior with no call-site change. The opt-in path
  exists for legitimate future readers (none today).

## Edge cases reasoned through

1. **Midnight rollover** — snapshots are persisted with
   `dayStart = calendar.startOfDay(for: ...)` (`persistSnapshot` +
   the seed path), so `isDate(_:inSameDayAs:)` against
   `clock.now()`'s startOfDay correctly identifies today without
   tripping on yesterday-evening or today-just-past-midnight
   timestamps. No normalization fix needed.
2. **Long absence** — `recomputeYesterdayDelta` reads via
   `fetchSnapshot(for: yesterday)`, not the public accessor, so the
   yesterday card / long-absence card path is unaffected.
   `hasOlderSnapshots` (the predicate that switches between the
   yesterday card and the long-absence card) uses
   `recentSnapshots(limit: 3).count >= 2`. With today excluded:
   - returning user with 14-day-old streak → 3 historical rows
     visible → predicate true → long-absence card shows ✓
   - day-1 user with only today's snapshot → 0 historical rows →
     predicate false → no false-positive long-absence card ✓
   - day-2 user (yesterday + today) → 1 historical row → predicate
     false → yesterday card shows via `yesterdayDeltaMinutes` (real
     yesterday data exists). Prior behavior would have falsely
     fired the long-absence card here too — the fix tightens that.
3. **Free-tier visible row count** — `HistoryView`'s
   `dailyHistorySection` takes `prefix(freeRowLimit=3)` of the
   returned list. With the internal +1 fetch, the visible count
   stays at exactly 3 unblurred rows for a Pro-imported user.
   For a fresh seed where there are fewer total snapshots than
   `freeRowLimit + 1`, the visible count legitimately shrinks by 1
   — but that's correct, because that 1 row was today and never
   belonged on History.
4. **Day-1 user / null state** — with today excluded, a brand-new
   user lands on the empty path
   ([HistoryView.swift:147](../../../products/life-clock-ios/Sources/Features/History/HistoryView.swift)
   — Pro shows the import banner + `historyEmptyStateCard`;
   non-Pro shows `historyEmptyStateCard` alone). Copy is
   `historyEmptyStateBody`, currently single-string (not
   tone-aware). Logged as a follow-up below; not fixed inline.

## Iterations

- [14:12] Confirmed inputs (product, scheme, mode, seed). Regenerated
  `LifeClock.xcodeproj` via `xcodegen`. Headless baseline build
  → `** BUILD SUCCEEDED **`.
- [14:20] Edited `Sources/App/LifeClockStore.swift:800` to add the
  `includingToday: Bool = false` parameter with internal +1 fetch
  + today filter via injected clock. Re-built green.
- [14:25] Wrote two `LifeClockStoreTests` cases:
  - `testRecentSnapshotsExcludesTodayByDefault` — seeds today + 13
    priors, asserts default fetch returns 7 rows without today and
    that the first row is yesterday; asserts `includingToday: true`
    keeps today.
  - `testRecentSnapshotsAfterLongAbsenceReturnsOldSnapshots` —
    seeds three snapshots 30+ days ago (no today), asserts the
    today-exclusion path is a no-op and all three surface.
  Both pass: 0.022s + 0.059s.
- [14:30 – 14:55] Attempted a History UI test
  (`testHistoryFirstRowIsYesterdayNotToday`). Tripped on
  test-scaffolding issues unrelated to the fix — the "Past days"
  heading didn't surface within the wait window with my chosen
  seed + dismiss flow. Burned three iterations chasing the
  wrap-up-sheet / wall-clock-vs-fixed-calendar interaction without
  pinning it. **Removed the UI test** rather than ship a flaky one;
  the unit tests already lock the store-boundary contract. Queued
  as a follow-up below.
- [15:25 – 16:40] Final computer-use checkpoint. First two attempts
  failed because `xcrun simctl launch ... --setenv FOO=BAR` passes
  the flags as ARGV, not as environment vars — env vars for simctl
  must be prefixed `SIMCTL_CHILD_` in the caller's environment.
  Once corrected, launched with `LIFECLOCK_INITIAL_TAB=history` to
  land directly on History, dismissed the auto-presenting Yesterday
  wrap-up sheet, and confirmed visually: fixed clock = 2027-01-14,
  History row 1 = **"Wed, Jan 13"** (yesterday), rows descend
  cleanly through Jan 6 with the seeded `+58 min / 8400 steps /
  7.4h sleep` values. Today's row absent. Fix confirmed end-to-end.

## Asks for the operator (resolved + outstanding)

**Outstanding:**

1. **History UI test recon** — extend `LifeClockUITests.swift` (or
   add a sibling recon file) once the wrap-up-on-launch +
   seeded-onboarded interaction is pinned. The intended assertion is
   trivial: with `LIFECLOCK_SEED_STREAK=14`, after dismissing any
   wrap-up sheet, on History the first row's `staticTexts` label is
   not today's `"EEE, MMM d"` formatted string. Currently relying
   on the unit-test contract.
2. **Day-1 History empty state — tone-aware copy** — Polish-tier.
   `historyEmptyStateBody` currently returns one of five
   single-string variants keyed on `healthDataState`. None of them
   are tone-aware (gentle / coach / firmDirect). Now that the
   day-1 user actually lands on this card (was previously masked by
   today's row appearing as historical), the copy gets more
   foot-traffic. Separate session — fits the "first-day no-history
   user" pass already on the prompt backlog.

**Resolved during this cycle:**

- None — single-fix session.

## Verification

```
xcodebuild test -only-testing:LifeClockTests/LifeClockStoreTests/testRecentSnapshotsExcludesTodayByDefault
  → passed (0.022s)
xcodebuild test -only-testing:LifeClockTests/LifeClockStoreTests/testRecentSnapshotsAfterLongAbsenceReturnsOldSnapshots
  → passed (0.059s)
```

## Commits

- `fix(life-clock): exclude today from History via store boundary`
  ([Sources/App/LifeClockStore.swift](../../../products/life-clock-ios/Sources/App/LifeClockStore.swift) +
  [Tests/LifeClockStoreTests.swift](../../../products/life-clock-ios/Tests/LifeClockStoreTests.swift))
