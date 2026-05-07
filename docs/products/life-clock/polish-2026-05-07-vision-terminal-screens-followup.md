# Polish Session — life-clock — 2026-05-07 — vision-terminal-screens-followup

## Mode

Vision-driven follow-up to [polish-2026-05-06-vision-terminal-onboarding-screens.md](polish-2026-05-06-vision-terminal-onboarding-screens.md). Two outstanding Asks from that session resolved by operator pick:

- **Ask #1 — `EntryView` placement:** drop it (Option B). The placeholder is a one-frame safety-net during the parent gate flip, doesn't earn its place, and Option C (celebratory beat) is Feature-tier scope outside this session.
- **Ask #2 — `LifeGridDotView` race under JUMP fixture:** fix it in the fixture (defer the path swap), not in the production view, since production navigation through the dial-confirm path renders correctly.

Iteration cap 6, computer-use checkpoint mandatory.

## Iterations

- [14:35] `<sha>` — feat(life-clock): drop post-paywall entryView placeholder — Polish — onboarding terminal
- [14:38] `<sha>` — fix(life-clock): defer JUMP fixture path swap to settle NavigationStack first — Polish — debug fixture

## Stretch decisions (operator review)

None this session — both fixes were Polish-tier per operator pick.

## Asks

### Resolved this session

- **Ask #1 (drop EntryView):** `paywallPrimary.onClose` now writes the profile and stops there. `RootView`'s `@Query private var profiles` swaps to `MainTabView` on the next runloop tick. `EntryView` struct, `.entryView` enum case, `noBackScreens` membership, and the path-advance call all removed. `OnboardingScreen.deprecatedScreens` maps `"entryView" → .paywallPrimary` so historical `screenAppeared("entryView")` telemetry rolls forward.
- **Ask #2 (fixture race):** `applyJumpFixtureIfNeeded` now wraps the `path = [target]` mutation in `DispatchQueue.main.asyncAfter(deadline: .now() + 0.05)`. Confirmed via `NSLog`-instrumented run that the fixture fires (`env=recoveryPreview, path.count=0`); after the fix, the `recoveryPreview` destination renders cleanly instead of welcome being pushed on top.

### Outstanding (cycle-end batch)

- **Polish (deferred, NEW) — `LifeGridDotView` Canvas dots not painting on `recoveryPreview`.** Confirmed via computer-use that the dot grid is empty even in the live Simulator window (not a `simctl io screenshot` artifact). Reproduces with the JUMP fixture in both light and dark mode. Hypothesis: `Canvas(rendersAsynchronously: true)` + `GeometryReader` interaction is dropping the first paint and never re-scheduling. Likely affects production navigation too — the dial-confirm path also pushes via `path = [.recoveryPreview]`, and the natural flow has never been audited via headless screenshot. Worth a focused next session (test in a dedicated build with `rendersAsynchronously: false` to confirm hypothesis).
- **Polish (carry-over from prior session) — `RecoveryPreviewCopy.headline` `yearsBack == 0` fallback** ("More years ahead / of loving") still reads weak. Not addressed this session.

## Regressions caught

- None. Goldens diff intentionally for `recoveryPreview` (cycling phrase mid-fade visible — pre-existing, not introduced) and were re-captured for `healthKitAuth` and `paywallPrimary` (no visible change).

## A11y identifiers added

- None. Removing `EntryView` removed its `onboarding.entryView` identifier from the surface.

## Vision updates

- Open Questions appended: nothing.
- Decided constraints proposed (operator-only edit): nothing this session.

## Files touched

- `products/life-clock-ios/Sources/Features/Onboarding/OnboardingCoordinator.swift` — drop EntryView struct + path advance, defer JUMP path swap by 50ms, update fixture doc comment.
- `products/life-clock-ios/Sources/Features/Onboarding/OnboardingScreen.swift` — remove `.entryView` case, add to `deprecatedScreens` map.
- `docs/products/life-clock/onboarding-funnel.md` — update post-paywall transition (`→ MainTabView` instead of `→ entryView`), note 2026-05-07 deprecation.
- `docs/products/life-clock/onboarding-copy/v2.md` — remove `entryView` copy section, add to "Removed in v2" with rationale.

## Next pass

- File the `LifeGridDotView` empty-grid bug. Hypothesis to test: set `rendersAsynchronously: false` in `recoveryPreview` mode and check whether dots paint.
- Carry over the `recoveryPreview` `yearsBack==0` fallback copy polish from the prior session.
