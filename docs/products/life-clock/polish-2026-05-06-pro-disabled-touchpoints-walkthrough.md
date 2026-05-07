# Polish Session — life-clock — 2026-05-06 — pro-disabled-touchpoints-walkthrough

## Mode

`fix-list` (9 Pro touchpoints under `LIFECLOCK_SIMULATOR_PRO_DISABLED=1` for the entire session). Iteration cap 8. Final computer-use checkpoint requested; substituted with an XCUITest swipe-down gate when the local computer-use bridge timed out (see Asks).

Touchpoints walked:

1. HistoryView fog gate (3 free unblurred + 6 fogged + paywall CTA)
2. HistoryView day-row tap routes to paywall for Free users
3. PlanEditorSheet Pro lock (`today.planEditLocked` → paywall, `planEditor.screen` never appears)
4. OverrideSheet `.notEntitled` defensive path (unreachable from Free UI; locked at the store layer)
5. Profile "Upgrade to Pro" entry → `paywall.close` returns to Profile
6. `LIFECLOCK_FORCE_PAYWALL=1` boot-paywall path
7. Onboarding `paywallPrimary` screen (covered by existing `testOnboardingV2FlowReachesPaywall`)
8. Restore-purchases path (Profile + `paywall.restore`)
9. Cancel-from-paywall recovery (open, close, app stable)

## Iterations

- [16:40] `8b32965` — `chore(life-clock): a11y ids for Pro touchpoints` — Polish — HistoryView, ProfileView, PaywallPrimaryView
- [17:25] `01d6510` — `fix(life-clock): preserve child a11y ids on questsCard` — Polish — TodayView. Outer `.accessibilityIdentifier("today.plan")` was clobbering every child id (`today.planEditLocked`, `today.planAction.<i>`); switched to `.accessibilityElement(children: .contain)` so children keep their own ids.
- [17:25] `fe566dd` — `fix(life-clock): deterministic Free entitlement state under XCUITest` — Stretch — SubscriptionStore. Under `LIFECLOCK_UI_TEST=1 + LIFECLOCK_SIMULATOR_PRO_DISABLED=1` the real `Transaction.currentEntitlements` was stalling, so forced/upgrade paywalls never reached the sheet. Added a UITest-only short-circuit to `entitledProductIDs = []`. Production sim runs still hit real StoreKit.
- [17:26] `498ea1a` — `fix(life-clock): @MainActor on MockHealthKitService auth tests` — Polish — Tests/HealthKitAggregatorTests. Pre-existing test build break left over from the recent `@MainActor` `HealthKitServiceProtocol` change; fixed to unblock the loop's test runs.
- [17:33] `f5b2e6e` — `test(life-clock): lock .notEntitled defensive path on Pro-only writers` — Polish — new `Tests/EntitlementGatedWritesTests.swift`. Asserts `applyOverride` / `revertOverride` / `selectPlanQuest` throw `OverrideService.OverrideError.notEntitled` for Free users *and* when no entitlement source is wired.
- [17:42] `02015b8` — `test(life-clock): paywall swipe-down dismissal acceptance gate` — Polish — appended `testFinalAcceptance_PaywallSwipeDownDismissal` to ProTouchpointsRecon. Stands in for the requested computer-use gesture pass (the local bridge was unreachable — see Asks).

The bulk of the session output is the new `UITests/ProTouchpointsRecon.swift` (committed inside `01d6510` along with the today.plan a11y fix that unblocked it). One test per touchpoint, plus the swipe-down acceptance test.

## Stretch decisions (operator review)

- `fe566dd` introduces a UITest-only entitlement short-circuit guarded by `LIFECLOCK_UI_TEST=1`. The alternative was to keep iterating real StoreKit and accept that `LIFECLOCK_FORCE_PAYWALL=1` flows are untestable in CI. Chose determinism for the test surface; production simulator runs still exercise real StoreKit. If we later want a "real-StoreKit-but-empty" test mode, add a third env-var.

## Asks

### Resolved this session

- **Failing pre-existing test build** (`HealthKitAggregatorTests.swift` MainActor mismatch) → resolved inline (`498ea1a`). Two `@MainActor` annotations on already-isolated init/property accesses. Polish-tier; not in scope but blocking the loop.

### Outstanding (cycle-end batch)

- **`testOnboardingV2FlowReachesPaywall` is flaky** (8 s timeout on `onboarding.coldOpen` after a series of preceding tests has run; passes in isolation on a clean sim, fails when chained). This is the existing coverage of touchpoint 7. The flake predates this session — none of the commits here touch the onboarding flow. Suggest a follow-up to either (a) bump the cold-open wait to 12 s, or (b) reset simulator state in `setUp`. **Recommendation: (a) — one-line change, minimal risk.**
- **Computer-use bridge unavailable**: `mcp__computer-use__request_access` timed out twice (300 s each). The operator's requested final checkpoint was a real-gestures pass over the purchase sheet. Best-substitute landed: `testFinalAcceptance_PaywallSwipeDownDismissal` in XCUITest. If the bridge becomes reachable again, the acceptance pass should still be done by hand once before App Store submission.

## Regressions caught

- Goldens for `01-today-free.png`, `02-force-paywall.png`, `03-today-uitest.png`, `04-today-no-scroll.png` written under `products/life-clock-ios/.polish/goldens/` for diff context across this session. No unintended visual diffs detected — the only screen the loop deliberately changed was Today's plan card a11y semantics, which has no visual effect.

## A11y identifiers added

- `history.screen` — HistoryView NavigationStack
- `history.row.pro` — Pro user's tappable history NavigationLink
- `history.row.locked` — Free user's history row (routes to paywall)
- `history.foggedUnlock` — Unlock CTA inside the fogged stack
- `history.weeklyTeaserUnlock` — Weekly teaser "See full week" CTA
- `profile.upgrade` — Profile's "Upgrade to Pro" button
- `profile.restore` — Profile's "Restore purchases" button
- `paywall.restore` (also on `PaywallPrimaryView` Restore — was previously only on `PaywallSheet`)

## Vision updates

- Open Questions appended: none this session.
- Decided constraints proposed: none. Touchpoint walk confirmed the Free path matches the documented monetization shape.

## Test surface added

- `UITests/ProTouchpointsRecon.swift` — 7 cases (touchpoints 1+2 fused, 3, 5, 6, 8, 9, plus swipe-down acceptance).
- `Tests/EntitlementGatedWritesTests.swift` — 4 cases locking the `.notEntitled` defensive path on `applyOverride` / `revertOverride` / `selectPlanQuest`.

All new tests + existing `testPaywallCloseIsAgentDriveable`, `testPlanCompletionFromTodayUpdatesQuestState`, `testTabBarHasOnlyThreeTabs` pass on the iPhone 16e simulator.

## Next pass

- Stabilize `testOnboardingV2FlowReachesPaywall` (Ask above).
- Optional: extend `ProTouchpointsRecon` with assertions on `paywall.tier.annual` pre-selection (annual rank is product-decision-load-bearing per `MONETIZATION.md`).
- Manual computer-use gesture pass once the bridge is reachable.
