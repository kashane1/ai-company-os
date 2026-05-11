# Polish Session — life-clock — 2026-05-10 — protouchpoints-t8-baseline-repair

## Mode

`fix-list` — fix-list payload from operator (Tier: regression-risk):

> Repair the `ProTouchpointsRecon` T8 baseline on main.
> `testTouchpoint8_RestorePurchasesFromProfile` and
> `testFinalAcceptance_PaywallSwipeDownDismissal` both fail on a clean
> iPhone 17 Pro simulator against current main. Suspected scrollUntilVisible
> attempt count too low after 5/9 Profile section reorder.
>
> Success criteria: `xcodebuild test -only-testing:.../testTouchpoint8…` and
> `…/testFinalAcceptance…` both green on iPhone 17 Pro from a cold
> `simctl erase`. Iteration cap 6. No final computer-use checkpoint.

## Iterations

- [22:50] *(baseline reproduction)* — both target tests fail at line 152 /
  line 200. Failure debug snapshot for `testFinalAcceptance` shows the
  Today tab still **Selected** with only `today.*` elements in the AX tree
  even after `app.tabBars.buttons["Profile"].tap()` was driven. This rules
  out the brief's suspected cause (scrollUntilVisible attempt count) — the
  scroll loop runs against the wrong screen because the Profile tap never
  navigates.
- [22:56] *(diagnosis)* — re-ran `testTouchpoint5_ProfileUpgradeEntry` and
  `testTouchpoint9_CancelFromPaywallRecovery`; both fail at the same
  `XCTAssertTrue(upgrade.waitForExistence(...))` step. Same root cause
  affects every Profile-touching test, not just T8.
- [23:05] *(diagnosis, cont.)* — installed the fresh Debug build to the
  simulator and launched with the test fixture env-vars
  (`LIFECLOCK_UI_TEST_SCENARIO=onboarded`, `LIFECLOCK_SEED_STREAK=12`).
  Cold-launch screenshot shows `WrapUpSheet` (yesterday's wrap-up,
  `wrapup.dismissCTA`) auto-presenting modally over the tab bar.
  `git log -- LifeClockLaunchConfiguration.swift` traces the regression
  to **commit `2b3f1a4` (5/7) — `fix(life-clock): seed harness reaches the
  wrap-up flow`**, which back-dates `onboardingCompletedAt` by
  `max(2, seedStreak)` days when `LIFECLOCK_SEED_STREAK > 0` so the
  reinstall guard is past. Net effect on ProTouchpointsRecon: every
  `launch(scenario: "onboarded", proDisabled: true, seedStreak: 12)`
  call now lands on a sheet-blocked tab bar.
- [23:11] *(fix)* — `chore(life-clock): dismiss WrapUpSheet in
  ProTouchpointsRecon launch` — Polish — UITests/ProTouchpointsRecon.swift.
  Added `dismissWrapUpIfPresent()` helper called at the end of the
  shared `launch(...)` helper. Taps `wrapup.dismissCTA` if it appears
  within 3s; idempotent for the Monday-return double-sheet case
  (yesterday → weekly). No product-source changes.
- [23:11] *(target verify)* —
  `xcodebuild test … testTouchpoint8_RestorePurchasesFromProfile
   … testFinalAcceptance_PaywallSwipeDownDismissal` from a fresh
  `simctl erase` of `iPhone 17 Pro (73298B82…)` → **`** TEST SUCCEEDED **`,
  2/2 passed in 90.9s. Success criteria met.
- [23:17] *(suite verify)* — full ProTouchpointsRecon suite (7 tests)
  from another fresh erase: 6/7 pass. T3, T5, T6, T8, T9, finalAcceptance
  all green. T5 and T9 are **collateral wins** — both were failing on
  baseline main with the same modal-blocks-tab-bar cause; the harness fix
  recovers them too. T12 (`testTouchpoint12_HistoryFogGateAndLockedRows`)
  fails at line 83 — see Asks below.

## Stretch decisions (operator review)

None — the fix is a single Polish-tier harness-only change with no design
alternatives. The brief proposed three options ("bump scroll attempts,
switch to id-anchored firstMatch waits, or split T8 into a reachability
vs interaction step"); none of them would have helped because the actual
failure mode is **modal-sheet-blocks-tab-bar**, not scroll geometry.

## Asks

### Resolved this session

None.

### Outstanding (cycle-end batch)

**Q1 — `testTouchpoint12_HistoryFogGateAndLockedRows` baseline failure
(pre-existing, surfaced by this session).** Confirmed failing on
unmodified main with the same assertion (`fogged paywall CTA must surface
on History for free users`, line 83). Was masked on main by the same
wrap-up-sheet-blocks-tabs root cause T8 hit; History.tap() didn't navigate
either, so the test died at the `app.scrollViews.firstMatch` precondition
on line 67 instead of getting deep enough to fail on `history.foggedUnlock`.
With the harness fix the History tap navigates, scroll runs, and the
genuine missing-affordance issue surfaces.

The brief explicitly scoped this session to T8 + finalAcceptance, so I
didn't extend the fix-list. But T12 will need the same kind of triage
before any History-touching polish session can ship a UITest-backed
final-check. Two options:

1. **Spin a follow-up fix-list session** with payload "T12 baseline repair —
   investigate why `history.foggedUnlock` doesn't surface for free users
   on `LIFECLOCK_SEED_STREAK=12, onboarded` after wrap-up dismissal.
   Likely the fogged stack only renders below a row-count threshold, or
   the `seedStreak=12` fixture seeds enough real days to short-circuit
   the placeholder fill path documented at `HistoryView` line ~80." This
   is the cleaner path; this PR stays surgical.

2. **Extend this PR** to investigate T12. Risk: scope creep; T12's fix
   may touch product source (HistoryView fog rendering threshold) rather
   than test harness, which is a different change class than the brief
   asked for.

Recommend Option 1.

## Regressions caught

None. Only `UITests/ProTouchpointsRecon.swift` changed — pure test
harness, zero product-source surface area, no goldens to refresh. The
suite went from 4 fails / 3 passes (baseline) to 1 fail / 6 passes
(post-fix), with the remaining failure being a separate pre-existing
issue.

## A11y identifiers added

None — the fix uses the existing `wrapup.dismissCTA` identifier
(`Sources/Features/WrapUp/WrapUpSheet.swift:76`).

## Vision updates

None proposed. This is a test-harness regression fix; vision.md is
unaffected.

## Next pass

- T12 baseline repair (see Q1 above; recommend Option 1 — separate
  session).
- Post-T12, re-attempt the UITest-backed final-check that the
  `subscription-lifecycle-states` polish session
  ([polish-2026-05-10-subscription-lifecycle-states.md](polish-2026-05-10-subscription-lifecycle-states.md))
  had to skip — Q0 in that log explicitly waited on this fix.
- Once both T8 and T12 are green, the "no subscription-touching polish
  session can ship a UITest-backed final-check" gate from the prior log
  closes for good.
