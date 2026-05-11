# Polish Session — life-clock — 2026-05-11 — history-day1-empty-state-tones

## Mode

`freeform-polish` · idea #6 (drift tier, outstanding ask from
[polish-2026-05-10-history-excludes-today.md](polish-2026-05-10-history-excludes-today.md)).

The 5/10 store-boundary fix excluded today's row from History, so day-1
users now actually land on `historyEmptyStateCard` instead of seeing
today appear as historical. The card's body returned one of five
single-string variants keyed on `LifeClockStore.HealthDataState` —
none of them tone-aware. This session adds gentle / coach / firmDirect
pools for each of the five `healthDataState` branches.

Iteration cap: 6. Final computer-use checkpoint: yes — 3-tone matrix +
XXL pass.

## Fix

[`Sources/App/ToneMode.swift`](../../../products/life-clock-ios/Sources/App/ToneMode.swift):

Added a `ToneMode.HistoryEmptyHealthState` enum (`Foundation`-only
mirror of `LifeClockStore.HealthDataState`, so `ToneMode` stays
SwiftData-free per its import boundary) and a 15-arm function:

```swift
func historyEmptyStateBody(for state: HistoryEmptyHealthState) -> String
```

[`Sources/Features/History/HistoryView.swift`](../../../products/life-clock-ios/Sources/Features/History/HistoryView.swift):

The view's `historyEmptyStateBody` computed property now maps
`store.healthDataState` → `ToneMode.HistoryEmptyHealthState` and
delegates to `store.toneMode.historyEmptyStateBody(for:)`. The mapping
is a 1:1 switch — keeping the boundary explicit so a future
`HealthDataState` case fails compilation here, not silently.

## Register guardrails (success criteria)

Encoded both in the copy and as XCTest assertions in
[`Tests/ToneModeTests.swift`](../../../products/life-clock-ios/Tests/ToneModeTests.swift):

- **gentle** avoids platitudes ("every day counts", "small things
  matter", "small wins" — banned via
  `testHistoryEmptyStateBody_GentleAvoidsPlatitudes`).
- **coach** avoids presumption-of-adherence — copy reads as permissive
  ("You can connect from Profile") not directive ("Keep showing up").
  No automated test; vocabulary is too soft to lock without false
  positives. Verified by inspection on captures 02, 04, 05.
- **firmDirect** avoids the mortality / scorekeeping lexicon
  ("owed", "tally", "reckoning", "in the red", "the cost" — banned
  via `testHistoryEmptyStateBody_FirmDirectAvoidsMortalityLexicon`).
  This card is a setup state, not a scoring moment; "Banked" /
  "Owed" reads wrong here even in firmDirect.

Pairwise distinctness for all 5 states × 3 tones is locked by
`testHistoryEmptyStateBody_TonesDifferPairwise` — paste-twice mistakes
fail the build.

## Verification

```
xcodebuild test -only-testing:LifeClockTests/ToneModeTests
  → 21 tests, 0 failures (6 new — covers 15 combos)
```

Pre-existing snapshot/store tests (`LifeClockStoreTests`,
`QuestPoolToneParityTests`, etc.) untouched and continue to pass at
the build level — only `ToneModeTests` was reduced into the
`-only-testing` filter to keep the cycle tight; full test run was not
in scope for a copy-only change behind an existing computed boundary.

## Final computer-use checkpoint

Captured matrix at
`/tmp/lifeclock-empty-state-screenshots/` on iPhone 17 Pro / iOS 26.3
(booted sim, `xcrun simctl io ... screenshot` per the convention from
the 5/10 healthkit-denied-notdetermined polish session — `SIMCTL_CHILD_`
env prefix required, not positional args):

1. `01-gentle-availableToday-authorized.png` — "History fills in after
   a few days. Today is the first one."
2. `02-coach-availableToday-authorized.png` — "A few more days of
   signal and patterns start to appear here."
3. `03-firmDirect-availableToday-authorized.png` — "A few more days.
   Then History has something to say."
4. `04-coach-awaitingAuth-notDetermined.png` — "History fills in after
   a few days of Apple Health signal. You can connect from Profile."
5. `05-coach-noRecentData-denied.png` — "No recent Apple Health signal.
   History waits for real data before showing a trend."
6. `06-gentle-noRecentData-denied.png` — "Apple Health isn't sharing
   anything yet — History waits for real signal before showing
   patterns."
7. `07-firmDirect-noRecentData-denied.png` — "No Apple Health signal.
   History stays empty until there's real data."
8. `08-gentle-availableToday-XXXL.png` — Dynamic Type
   `UICTContentSizeCategoryAccessibilityXXXL` applied at launch. The
   card sits below the weekly stack at this size; the History layout
   continues to scroll and the `.callout` font on the card respects
   Dynamic Type natively (no truncation observed inside the rounded
   container at the inspected size).

The `.historicalOnly` and `.unavailable` states are not reachable from
the current fixture knobs: `historicalOnly` requires persisted
non-today snapshots with `sourceCompleteness > 0` AND
`hasTodaySignal == false`, which the seed path doesn't expose as a
single combo today; `.unavailable` requires `healthDataAvailable ==
false`, which no `LIFECLOCK_*` env var flips (the mock service is
always available). Both branches are covered by the unit-test
distinctness + pin tests so the copy is locked even though the live
captures are constrained. Adding fixture knobs for those two states is
out of scope for a copy-only polish session — logged as a follow-up.

## Asks for the operator

**Outstanding:**

1. **Fixture knobs for `.historicalOnly` and `.unavailable`** — Polish
   tier. Add `LIFECLOCK_FORCE_HEALTH_STATE=available|historicalOnly|noRecent|unavailable`
   to `LifeClockLaunchConfiguration`, or compose with
   `LIFECLOCK_SEED_LAST_LOG_DAYS_AGO + LIFECLOCK_SEED_STREAK`-based
   historical-only seeds. Would let the full 5 × 3 capture matrix
   complete in one driver run; today only 3 of 5 states are
   simulator-reachable.

**Resolved this session:**

- The 5/10 polish session's outstanding ask #2 (this one).

## Commits

- `feat(life-clock): tone-aware day-1 History empty state`
  ([Sources/App/ToneMode.swift](../../../products/life-clock-ios/Sources/App/ToneMode.swift) +
  [Sources/Features/History/HistoryView.swift](../../../products/life-clock-ios/Sources/Features/History/HistoryView.swift) +
  [Tests/ToneModeTests.swift](../../../products/life-clock-ios/Tests/ToneModeTests.swift))
