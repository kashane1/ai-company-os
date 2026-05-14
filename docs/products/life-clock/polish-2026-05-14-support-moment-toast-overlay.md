# Polish Session — life-clock — 2026-05-14 — support-moment-toast-overlay

## Mode
`fix-list` — single operator-stated fix.

Operator request: convert the inline `SupportMoment` section on Today (which previously rendered between the projected-healthspan card and the "Why it changed" card on quest complete / quest undone / check-in saved) into a top-anchored, auto-dismissing toast overlay that appears from just below the navigation top bar at the highest z layer of the Today screen.

## Inputs decided up front
- Auto-dismiss: **3.5s**
- Stacking: **replace + reset timer** when a new moment arrives mid-toast
- Scope: **Today screen only** (all current `SupportMomentPresenter.Intent` cases originate from Today flows)

## Iterations
- [15:03] pre-flight — `xcodegen` regen (worktree was missing `LifeClock.local.xcconfig`; copied from main checkout), confirmed scheme `LifeClock`, simulator `iPhone 17 Pro (iOS 26.3, Booted)`
- [15:05] new file `Sources/Shared/SupportMomentToast.swift` — material-backed card with sparkles/heart icon, title + detail, close button, slide-from-top + opacity transition. Auto-dismiss via `.task(id: moment)` (3.5s sleep, cancellation handled by SwiftUI re-running on `id` change → replace + reset for free).
- [15:06] `TodayView.swift` — removed inline `if let moment = store.supportMoment { supportMomentCard(moment) }` slot between `rescueLine` and `driversCard`; removed the now-unused `supportMomentCard(_:)` helper; added `.overlay(alignment: .top) { … }` on the `ScrollView` with an `.animation(.spring(response: 0.42, dampingFraction: 0.86), value: store.supportMoment)` for synchronized insert/remove. `.zIndex(1)` to keep it above any future content overlays.
- [15:07] deleted unused `Sources/Shared/SupportMomentCard.swift` (no remaining references). Updated `SupportMoment.swift` doc comment to point at the new toast.
- [15:08] headless build — `xcodebuild -scheme LifeClock -destination 'platform=iOS Simulator,name=iPhone 17 Pro' build` → **BUILD SUCCEEDED**.
- [15:09] install + launch with `SIMCTL_CHILD_LIFECLOCK_UI_TEST_SCENARIO=onboarded` etc. Today screen rendered correctly with the toolbar still showing only the pencil icon (no inline title at top of scroll) and the standard headline + clock card layout.

## Stretch decisions (operator review)
- Material background (`.regularMaterial`) + 14pt corner radius + subtle hairline border + soft shadow chosen to read as a peer of the system nav bar rather than competing with section cards. If the brand convention is to use `.sectionCard()` everywhere, swap the background block in [`SupportMomentToast.swift`](products/life-clock-ios/Sources/Shared/SupportMomentToast.swift) and the toast adopts the existing card language.
- Transition is `.move(edge: .top).combined(with: .opacity)` — slides down from beneath the nav bar. Reduce-Motion users still get the opacity portion via the same combined transition (SwiftUI strips the move under reduce-motion automatically through the system animation policy).

## A11y identifiers preserved
- `today.supportMoment` (was on the card, now on the toast)
- `supportMoment.dismiss` (close button, unchanged)

## Regressions caught
- None. Inline slot between `rescueLine` and `driversCard` is gone — section spacing collapses cleanly because the `VStack` spacing token did the work, not the now-removed view.

## Next pass
- If toast feels too "system-y," consider replacing material with `DesignTokens.Palette` brand surface for tighter integration.
- Verify Dynamic Type xxxLarge — the toast can grow vertically; the slide-from-top still works but the `padding(.top, xs)` may need a re-look.
- Onboarding completion path: `supportMoment` also fires on `onboardingComplete`, which happens inside `OnboardingCoordinator`, not Today. That path no longer renders any UI because the Today-screen-only overlay is the sole consumer. Decide whether onboarding wants its own celebration surface or if the toast should be promoted to MainTabView.

## Commits
- `feat(life-clock): top-anchored support-moment toast on Today`
