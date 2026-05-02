---
title: Life Clock — Animated SwiftUI Mascot Primitive
type: feat
status: active
date: 2026-05-02
---

# Life Clock — Animated SwiftUI Mascot Primitive

## Deepening Summary

**Deepened on:** 2026-05-02 (same-day, post-/workflows:plan)
**Agents used:** best-practices-researcher (SwiftUI animation perf), framework-docs-researcher (a11y + snapshot testing), performance-oracle, code-simplicity-reviewer, architecture-strategist.
**Technical review (same-day):** pattern-recognition-specialist, security-sentinel, Swift/iOS conventions sweep. Three would-not-compile blockers caught and fixed in plan: `Int.clamped(to:)` doesn't exist in stdlib; `let schedule: TimelineSchedule = ...` fails generic typing; `.onScrollVisibilityChange` is iOS 18+ (not 17). Cleanups: dead `animatableData`, asset-catalog AC reword, `mascot.clock` identifier dropped (UITests resolve on hosting screens), all magic numbers named as `private static let`, security note on future bezel asset name.

### Key changes vs. v1 draft

1. **Scope trimmed.** Data-collection screens dropped from v1 (architecture-strategist: scope creep + Open Question 4 admits the integration rule was undecided). v1 ships on Today hero + engine reveal + 3 lead-ins.
2. **API simplified.** `minutesDelta: Int?` collapsed to `minutesDelta: Int` (0 = baseline). Optional `accessibilityContext` parameter cut. Skeleton-state opacity cut entirely; if the call site has no data, it doesn't render the mascot — single signal, single job.
3. **Asset slot deferred.** v1 ships the SwiftUI-drawn bezel only. The `ClockMascotBezel` runtime check + `#if canImport(UIKit)` re-enters the day a designer-produced PNG lands, refactored as a one-shot `MascotBezelSource` enum at app launch (architecture-strategist) rather than a per-render lookup.
4. **TimelineView visibility gating elevated to v1.** Performance-oracle: `TimelineView(.animation)` does NOT auto-pause when scrolled offscreen. ~10 lines, fits the "ship now, instrument later" stance, removes the largest battery vector.
5. **Heartbeat rate halved.** 30Hz instead of 60Hz — indistinguishable for a heartbeat, halves CPU work (best-practices-researcher).
6. **Spring rationale spelled out.** `.interpolatingSpring()` (defaults) for velocity preservation under continuous input on the engine reveal dial; `.spring()` would visibly jitter on rapid retarget. False-precision tuning constants (90/14) cut.
7. **Year→minutes mapping moved out of the view.** New tiny `EngineRevealPresenter` value type owns the `*6, clamp(±60)` rule. Mascot stays a pure-input primitive (architecture-strategist).
8. **Reduce-Motion via schedule, not unmount.** `TimelineView(reduceMotion ? .explicit([.distantFuture]) : .animation)` keeps view mounted; flips behavior at the schedule layer (best-practices-researcher).
9. **Accessibility tightened.** `.accessibilityElement(children: .ignore)` + `.accessibilityAddTraits(.updatesFrequently)` + identifier `mascot.clock`. Settle-only VoiceOver announcement via `withAnimation { … } completion: { AccessibilityNotification.Announcement(...).post() }` — no spam during dial drag.
10. **Snapshot testing via `ImageRenderer`.** iOS 16+ deterministic rendering with injected `reduceMotion` env, fixed phase, and fixed `minutesDelta`. No new test dependencies.

### Cut from v1 (deferred follow-ups)

- Asset slot for `ClockMascotBezel` (re-add when designer ships PNG).
- Mascot on data-collection screens (re-add as v1.1 after primitive proves out on Today + reveal + lead-ins).
- Spring tuning constants (use defaults; tune only if jitter shows on iPhone SE 2nd gen).
- Per-surface accessibility labels (constant "Life clock" v1; per-surface only if VoiceOver users complain).
- `accessibilityContext` parameter.
- Cross-screen hand-state continuity in onboarding lead-ins (lead-ins all pass 0; no continuity to preserve).

---

## Overview

Replace the existing two-state crossfade `ClockMascotView` with a single SwiftUI-drawn animated clock primitive that becomes the brand focal point of the app. Hour and minute hands rotate from a 12:00 baseline by a `minutesDelta: Int` input. A permanent red ECG-style heartbeat line pulses subtly. v1 ships on the Today hero, the engine reveal screen, and the three onboarding lead-in screens. The 3D-rendered look in the founder's reference image is a designer-asset upgrade path — code-drawn fallback ships first, designer-produced asset enters via a `MascotBezelSource` enum follow-up when ready.

## Problem Statement / Motivation

Life Clock needs a single recognizable mascot identity that lives at the top of the daily ritual surface (Today) and accompanies the user through onboarding. Today's mascot is two static art assets (`ClockMascotPositive`, `ClockMascotNegative`) crossfaded by polarity — it's static, it falls back to SF Symbols on first launch, and it conveys direction only as a binary swap. The actual product value — minutes gained or lost by user actions — never animates. The Today screen's `clockCard` ([TodayView.swift:141](products/life-clock-ios/Sources/Features/Today/TodayView.swift:141)) is text-only despite "clock" being in the name. The engine reveal screen ([EngineRevealAndDialView.swift](products/life-clock-ios/Sources/Features/Onboarding/Screens/EngineRevealAndDialView.swift)) shows a number, not a clock.

Founder framing: *"The mascot is a focal point. It should be the clock, not a representation of one. Hands move forward when actions add minutes, back when they subtract them. Heartbeat always red. Build it correct — I don't want to box myself in later."*

## Proposed Solution

Introduce `LifeClockMascotView` as a new shared primitive at `Sources/Shared/LifeClockMascotView.swift`, drawn entirely in SwiftUI with composable layers: bezel → tick marks → heartbeat line → hour hand → minute hand → center hub. Single primary input `minutesDelta: Int` drives both hands (hour at 1/12 angular speed). Reuses the proven 6°-per-minute mapping and ±720° clamp from [ClockHandView.swift:22-28](products/life-clock-ios/Sources/Features/WrapUp/ClockHandView.swift:22). Heartbeat is a `Path`-backed `Shape` stroked with a new `LifeClockPalette.heartbeatRed`, with a subtle 30Hz `TimelineView`-driven pulse on the line and center hub — gated by visibility and reduce-motion at the schedule layer (no mount/unmount thrash).

The existing `ClockMascotView` is deleted, not gated. All three call sites in [LeadInScreens.swift](products/life-clock-ios/Sources/Features/Onboarding/Screens/LeadInScreens.swift) (lines 28, 182, 250) migrate. `EngineRevealAndDialView` integrates via a new `EngineRevealPresenter` value type that owns the year→minutes mapping (1 yr ≈ 6 min, clamp ±60). A new `LifeClockMascotHero` wrapper for Today inserts the mascot above the existing `clockCard` and respects `store.profile?.hideClock`.

## Technical Approach

### Core API

```swift
// Sources/Shared/LifeClockMascotView.swift
struct LifeClockMascotView: View {
    /// Minutes gained (+) or lost (−) relative to baseline.
    /// `0` means at-baseline; if there's no estimate yet, the call site
    /// should not render the mascot at all.
    let minutesDelta: Int
}
```

Identifier `mascot.clock` set at the outer `accessibilityElement(children: .ignore)`. Constant accessibility label "Life clock"; value via `TimeDeltaFormatter.format(minutes: minutesDelta)`.

### Sweep mapping (reuses ClockHandView convention)

- Minute hand angle: `Double(minutesDelta) * 6°` (matches [ClockHandView.swift:25-28](products/life-clock-ios/Sources/Features/WrapUp/ClockHandView.swift:25)).
- Hour hand angle: `Double(minutesDelta) * 0.5°`.
- Visual clamp: ±720° (matches [ClockHandView.swift:22](products/life-clock-ios/Sources/Features/WrapUp/ClockHandView.swift:22)). Numeric readout adjacent to the mascot is the source of truth past the cap.
- Animation: `.interpolatingSpring()` with no arguments. **Why**: physics-based with velocity preservation across re-targets. The engine reveal dial drives `minutesDelta` continuously while the user drags; `.spring(response:dampingFraction:)` would restart a duration-based curve on each retarget and visibly jitter (per [WWDC23 "Animate with springs"](https://developer.apple.com/videos/play/wwdc2023/10158/)). Defaults are fine — false-precision stiffness/damping numbers cut. Re-tune only if jitter appears on iPhone SE 2nd gen.

### Heartbeat

- Drawn as `HeartbeatLine: Shape` with ~15 normalized control points; `path(in:)` animatable via a `phase: CGFloat` `animatableData` field.
- Stroked with `LifeClockPalette.heartbeatRed` (new constant — see "Heartbeat color exception" below).
- Pulse driver: `TimelineView` at 30Hz minimum interval — visually identical to 60Hz for a heartbeat, halves CPU.
- Effects: subtle scale on the center hub (3-12% range) and stroke modulation on the line. No translation across the face.
- **Schedule per state** (cleanest reduce-motion + visibility pattern; avoids unmount/remount of the heartbeat layer):
  ```swift
  @ViewBuilder private var heartbeat: some View {
      if reduceMotion || !isVisible {
          TimelineView(.explicit([.distantFuture])) { _ in
              HeartbeatLine(phase: 0.5).stroke(...)
          }
      } else {
          TimelineView(.animation(minimumInterval: 1.0/30.0)) { ctx in
              HeartbeatLine(phase: phase(at: ctx.date)).stroke(...)
          }
      }
  }
  ```
  `.explicit([.distantFuture])` mounts once, never updates again — frozen mid-amplitude line.

  > **Swift typing note:** `.animation(...)` and `.explicit(...)` return different concrete `TimelineSchedule` types. Branching at the `TimelineView` itself (above) compiles; branching at a `let schedule:` doesn't, because `TimelineView`'s init is generic on the concrete schedule type. The visibility/reduce-motion swap will trigger a SwiftUI rebuild of just the heartbeat subtree — acceptable, infrequent.

  > **Shape `animatableData` is unused here.** Inside `TimelineView` the closure re-runs every tick with a fresh `phase`, so the path is rebuilt directly each frame. Don't add `animatableData: CGFloat` to `HeartbeatLine` — it's dead code in this configuration; `path(in:)` just reads the phase passed by the parent.

### Visibility gating (perf — elevated to v1)

`TimelineView(.animation)` does NOT auto-pause when scrolled offscreen inside a `ScrollView`. On Today, the mascot inside the daily-ritual scroll view would keep ticking when the user scrolls past it — wasted battery.

- `@State private var isVisible = true`
- **Onboarding lead-ins + engine reveal**: full-screen, no scroll → `.onAppear { isVisible = true }` / `.onDisappear { isVisible = false }` is sufficient.
- **Today (in `ScrollView`)**: `.onAppear/.onDisappear` does **not** fire on scroll for non-lazy stacks. Two paths, pick during work:
  1. **Bump deployment target to iOS 18** and use `.onScrollVisibilityChange(threshold: 0.01) { isVisible = $0 }` ([introduced WWDC24](https://developer.apple.com/documentation/swiftui/view/onscrollvisibilitychange(threshold:_:))). Cleanest. Confirm with founder whether iOS 18 minimum is acceptable.
  2. **Stay on iOS 17** and use `.onGeometryChange(for: CGRect.self) { proxy in proxy.frame(in: .global) } action: { newFrame in isVisible = newFrame.intersects(UIScreen.main.bounds) }`. iOS 17 API; works inside ScrollView.
  - Defaulting to (2) keeps deployment compatibility; only flip to (1) if the founder OKs an iOS 18 bump.
- Also gate on `\.scenePhase` (background/foreground transitions). `TimelineView` pauses on backgrounding automatically per Apple docs, but matching it explicitly avoids ambiguous frame-on-resume.

### Bezel (v1: SwiftUI-drawn only)

- Outer ring: `Circle().strokeBorder(AngularGradient(...))` — blue → red gradient mirroring the founder's reference image.
- Tick marks: 60 (12 major every 30°, 48 minor) drawn via `ForEach(0..<60)` with `Capsule().offset(y: -size * 0.42).rotationEffect(.degrees(Double(i) * 6))`. Left half blue, right half red, mirroring the reference.
- No `UIImage(named:)` runtime check in v1. Asset slot re-enters when designer ships `ClockMascotBezel.png` (no-hands, no-ECG, transparent, 1024×1024) as a one-shot `MascotBezelSource` enum at app launch (per architecture-strategist guidance).

### Year→minutes mapping (presenter, not view)

```swift
// Sources/Features/Onboarding/Screens/EngineRevealPresenter.swift (new)
enum EngineRevealPresenter {
    static let minutesPerYear: Int = 6
    static let minMinutes: Int = -60
    static let maxMinutes: Int = 60

    static func mascotDelta(displayedYears: Double, baselineYears: Double) -> Int {
        let raw = Int(((displayedYears - baselineYears) * Double(minutesPerYear)).rounded())
        return min(max(raw, minMinutes), maxMinutes)
    }
}
```

Mascot stays a pure-input primitive. Constants `6` and `±60` live in one named place. EngineReveal calls `LifeClockMascotView(minutesDelta: EngineRevealPresenter.mascotDelta(...))`.

> **Swift stdlib note:** `Int.clamped(to:)` is **not** in the stdlib — using `min(max(...))` inline avoids a one-off `Comparable` extension. If a third call site needs clamping, *then* add `extension Comparable { func clamped(to r: ClosedRange<Self>) -> Self { ... } }` in `Sources/Shared/Extensions/`.

### Per-surface inputs (v1)

| Surface | `minutesDelta` source |
|---|---|
| Today hero | `store.todayEstimate?.dailyTimeDeltaMinutes` — if `nil`, do **not** render the mascot (gate at call site, hand off to `clockCard`'s existing "—" treatment). |
| Lead-in screens (cold open, meet your clock) | `0` |
| Reactive slider | Slider value mapped through engine — no throwaway `LifeClockEstimate` instances ([LeadInScreens.swift:235-245](products/life-clock-ios/Sources/Features/Onboarding/Screens/LeadInScreens.swift:235)) |
| Engine reveal | `EngineRevealPresenter.mascotDelta(displayedYears:, baselineYears:)` |
| Data collection screens | **Deferred to v1.1.** |
| Reveal escalator (life-grid) | **Skip permanently** — `LifeGridDotView` is the focal viz |
| Paywall | **Skip permanently** — paywall hierarchy owns its own focal element |

### Reduce Motion contract

- Hands: detect `reduceMotion` and snap (omit `withAnimation` on the rotation; the value still propagates but as a single 0-duration update).
- Heartbeat: schedule swaps to `.explicit([.distantFuture])` — line drawn at mid-amplitude (NOT flatline; flatline reads as "dead", wrong metaphor for a life clock), no center-hub pulse.
- Tests inject via `.environment(\.accessibilityReduceMotion, true)` on the view under test.

### `hideClock` parity

- Today hero returns `EmptyView` when `store.profile?.hideClock == true`, mirroring [TodayView.swift:142](products/life-clock-ios/Sources/Features/Today/TodayView.swift:142).
- Onboarding is pre-profile; flag not consulted there.

### Heartbeat color exception (palette change)

- Add `LifeClockPalette.heartbeatRed: Color` in [LifeClockPalette.swift](products/life-clock-ios/Sources/Shared/LifeClockPalette.swift).
- Comment block at the constant documents the deliberate exception to the orange-not-red invariant noted at [LifeClockPalette.swift:1-5](products/life-clock-ios/Sources/Shared/LifeClockPalette.swift:1) — prevents future "fix" PRs.
- File-level comment in `LifeClockMascotView.swift` cross-references the palette comment.

### Accessibility

```swift
.accessibilityElement(children: .ignore)
.accessibilityIdentifier("mascot.clock")
.accessibilityLabel("Life clock")
.accessibilityValue(TimeDeltaFormatter.format(minutes: minutesDelta))
.accessibilityAddTraits(.updatesFrequently)
```

`.updatesFrequently` tells VoiceOver to poll less aggressively, suppressing announcement spam during continuous input.

**Settle-only VoiceOver announcement** on the engine reveal screen (where dial drag is continuous):

```swift
.onChange(of: minutesDelta) { _, newValue in
    withAnimation(.interpolatingSpring()) { ... } completion: {
        AccessibilityNotification.Announcement(
            TimeDeltaFormatter.format(minutes: newValue),
            priority: .low
        ).post()
    }
}
```

iOS 17+ animation completion closure ensures we announce after the spring settles, not on every intermediate frame. `.low` priority avoids clobbering active VO speech.

### Snapshot testing

Use SwiftUI's built-in `ImageRenderer` (iOS 16+) — no new test dependencies. Inject deterministic state:

```swift
@MainActor
func renderMascot(delta: Int, reduceMotion: Bool, phase: CGFloat = 0.5) -> UIImage {
    let view = LifeClockMascotView(minutesDelta: delta)
        .environment(\.accessibilityReduceMotion, reduceMotion)
        .frame(width: 200, height: 200)
    let renderer = ImageRenderer(content: view)
    renderer.scale = 2
    return renderer.uiImage!
}
```

For deterministic ECG phase, factor the phase argument behind a default-injected closure on `LifeClockMascotView` (`phaseProvider: () -> CGFloat = { defaultPhase(at: Date()) }`) so tests can pass `{ 0.5 }` for a frozen mid-amplitude render.

## System-Wide Impact

### Interaction Graph

`store.todayEstimate.dailyTimeDeltaMinutes` updates → SwiftUI binding propagates → `LifeClockMascotView.minutesDelta` changes → `interpolatingSpring` re-targets → hands sweep. No callbacks, no observers, no side effects beyond the visual update. The `clockCard` text directly below reads from the same `store.todayEstimate.dailyTimeDeltaMinutes` (via `TimeDeltaFormatter`), so hero and card animate from the same binding tick — no two-source-of-truth risk.

### Error Propagation

View has no failure modes by construction. No asset load, no engine call, no network. Engine errors are upstream and never reach the view.

### State Lifecycle Risks

- Cross-screen onboarding navigation re-mounts the mascot per push. Lead-ins all pass `0`, so the reset is a visual no-op. Engine reveal is a single screen; no continuity needed.
- `hideClock` toggled mid-session: parent VStack collapses; existing `clockCard` behavior unchanged.
- Backgrounding: `TimelineView` pauses automatically; `isVisible` gating provides defense-in-depth.

### API Surface Parity

Replaces `ClockMascotView(estimate:baseline:)` everywhere. UITests reference identifiers on hosting screens (`onboarding.coldOpen`, `onboarding.meetYourClock`, `onboarding.reactiveSlider`), not on the mascot itself, so identifier preservation is a wrapping-view concern.

### Integration Test Scenarios

1. **Reduce Motion ON** → hands snap (no spring), heartbeat line drawn at mid-amplitude (NOT flatline), no pulse.
2. **`hideClock = true`** → hero is absent on Today; existing `clockCard` behavior unchanged.
3. **Engine reveal dial drag −5 yrs to +5 yrs continuously** → hands sweep smoothly without jitter; clamp at ±60 minutes prevents wrap.
4. **First-launch onboarding** → identifiers `onboarding.coldOpen`, `onboarding.meetYourClock`, `onboarding.reactiveSlider` still resolve in UITests.
5. **Today first launch with no estimate** → mascot does not render; `clockCard` shows existing "—" placeholder.
6. **Today scroll past hero, dwell 30s, scroll back** → battery consumption equivalent to scenario where hero stays in view (visibility gating verifies).

## Acceptance Criteria

### Functional

- [ ] New file `Sources/Shared/LifeClockMascotView.swift` exposes `LifeClockMascotView(minutesDelta: Int)`.
- [ ] Old file `Sources/Shared/ClockMascotView.swift` deleted (not gated, not commented out).
- [ ] All three call sites in `Sources/Features/Onboarding/Screens/LeadInScreens.swift` migrated. `ColdOpenView`, `MeetYourClockView`, `ReactiveSliderView` no longer construct throwaway `LifeClockEstimate` instances.
- [ ] `Sources/Features/Today/TodayView.swift` `body` includes the mascot hero **above** `clockCard` in the parent VStack at [TodayView.swift:18](products/life-clock-ios/Sources/Features/Today/TodayView.swift:18). Mascot is gated at the call site: rendered only when `store.todayEstimate?.dailyTimeDeltaMinutes != nil` AND `store.profile?.hideClock != true`.
- [ ] New `Sources/Features/Onboarding/Screens/EngineRevealPresenter.swift` owns the year→minute mapping. `EngineRevealAndDialView` calls into it; constants `6` and `60` appear in exactly one place.
- [ ] `Sources/Shared/LifeClockPalette.swift` adds `heartbeatRed: Color` constant with comment explaining the orange-not-red invariant exception.
- [ ] Confirm no orphan `ClockMascotPositive.imageset` / `ClockMascotNegative.imageset` directories remain in `Sources/Assets.xcassets/`. (Verified during work: those names exist only as string literals in `ClockMascotView.swift` with SF Symbol fallbacks — no imagesets to delete. Reword if any are found.)
- [ ] No `ClockMascotBezel` runtime check in v1; SwiftUI bezel always renders.
- [ ] `LifeClockMascotView` declares `private static let` constants for: heartbeat update interval (`heartbeatHz: 30`), visual sweep cap (`maxSweepDegrees: 720` — duplicated from `ClockHandView`, comment cross-references), hub pulse range (`hubPulseRange: ClosedRange<CGFloat>`), and degrees-per-minute (`degreesPerMinute: 6` — comment cross-references `ClockHandView.swift:25-28`). No inline magic numbers in the view body.
- [ ] File-header doc comment for `LifeClockMascotView` cross-references both `ClockHandView` ("opposite case — TimelineView justified for continuous heartbeat") and `LifeClockPalette.heartbeatRed` (orange-not-red invariant exception).
- [ ] `#if DEBUG #Preview` block enumerates: "Baseline" (delta 0), "+30 min", "−30 min", "Reduce Motion" (delta +30 with reduceMotion env injected), "Clamp" (delta +1440 → visual at +720°).

### Non-functional

- [ ] Heartbeat is red on every surface (verified visually in 3 previews + 1 device run).
- [ ] Reduce Motion: hands snap; heartbeat line drawn at mid-amplitude with no pulse; center hub static. Verified by snapshot test with `\.accessibilityReduceMotion` injected.
- [ ] `TimelineView` pauses (schedule swaps to `.explicit([.distantFuture])`) when mascot bounds are 0% visible — verified on Today by scrolling hero offscreen and confirming no frame invalidation via Instruments Time Profiler.
- [ ] Heartbeat schedule uses `minimumInterval: 1.0/30.0` — verified in code.
- [ ] iPhone SE 3rd gen build sustains 60fps during a 5-second engine-reveal dial drag (Instruments Core Animation).
- [ ] iPhone SE 2nd gen build sustains ≥45fps during the same drag (acceptable; tune spring if it falls below).
- [ ] `TARGETED_DEVICE_FAMILY = "1,2"` in `project.pbxproj`. Mascot capped at `.frame(maxWidth: 320)` on iPad.

### Accessibility

- [ ] Outer view: `.accessibilityElement(children: .ignore)`, label `"Life clock"`, value via `TimeDeltaFormatter.format(minutes: minutesDelta)`, traits include `.updatesFrequently`. **No `accessibilityIdentifier` on the primitive itself** — UITests resolve identifiers on hosting screens (`today.healthspan`, `onboarding.coldOpen`, etc.), and putting `mascot.clock` on the inner primitive risks UITest brittleness if the same primitive ever appears twice on one screen. (Pattern consistency with existing `surface.element` namespace convention.)
- [ ] Engine reveal: `withAnimation { } completion: { AccessibilityNotification.Announcement(...).post() }` posts only after the spring settles. Verified by VoiceOver session manually + an XCTest with `XCUIApplication` accessibility-snapshot assertion.
- [ ] Existing UITests pass: identifiers `onboarding.coldOpen`, `onboarding.meetYourClock`, `onboarding.reactiveSlider` still found by `UITests/LifeClockUITests.swift`.

### Tests

- [ ] New `Tests/LifeClockMascotViewTests.swift` — snapshot tests via `ImageRenderer` for: `minutesDelta = 0, +30, −30, +720, −720, +1440 (clamp)`. Each rendered with `reduceMotion = false` AND `reduceMotion = true`, fixed phase = 0.5.
- [ ] Tests asserting on the deleted `ClockMascotPositive`/`ClockMascotNegative` asset names (if any exist) updated.
- [ ] `Tests/EngineRevealPresenterTests.swift` covers the year→minute mapping at boundary inputs (0, +5, −5, +10 clamp, −10 clamp, fractional like 2.5 → 15 min).

### Quality Gates

- [ ] `swift build` and `swift test` pass on iOS 17.0 simulator (current minimum target).
- [ ] No new compiler warnings in the touched files.
- [ ] Plan's "Out of Scope" items are not introduced (e.g., no Lottie/video bezel, no mascot on escalator screens).

## Success Metrics

- Visual fidelity to the founder's reference image at v1 (drawn fallback) is "good enough to ship"; designer asset upgrade is a follow-up improvement, not a blocker.
- TestFlight in-session crash rate on Today screen does not regress vs. the prior build.
- No regression in onboarding step-completion telemetry on the 3 affected lead-in screens (per [OnboardingTelemetryTests.swift](products/life-clock-ios/Tests/OnboardingTelemetryTests.swift)).
- Energy Log delta on Today (mascot scrolled offscreen for 30s) is within 1% of prior build — confirms visibility gating works.

## Dependencies & Risks

**Dependencies**
- None blocking. Designer-produced `ClockMascotBezel.png` (1024×1024, no-hands/no-ECG, transparent background) is a follow-up improvement; v1 ships without it.

**Security note for the v1.1 follow-up:** when the bezel asset slot returns, the asset name MUST be a compile-time string constant. Never derive it from user data, telemetry, or remote config — there's no path-injection surface today and we're not introducing one tomorrow.

**Risks**

| Risk | Severity | Mitigation |
|---|---|---|
| `interpolatingSpring()` defaults too bouncy on iPhone SE 2nd gen during dial drag | Medium | Validate on device. Fallback: `.easeInOut(duration: 0.4)`. |
| Today scroll-visibility gating depends on chosen API | Medium | iOS 18 `.onScrollVisibilityChange` is cleanest; iOS 17 fallback is `.onGeometryChange`. Pick during work and document choice in the implementation PR. |
| iPad device family not "1,2" in pbxproj | Medium | Verify pre-merge ([learning](docs/solutions/integration-issues/ios-ipad-compatibility-mode-cramped-layout.md)). Cap mascot at `.frame(maxWidth: 320)` regardless. |
| Heartbeat-red exception drift | Low | Centralize in `LifeClockPalette.heartbeatRed` with comment block. |
| TimelineView visibility gating doesn't actually pause work | Low | Verify via Instruments Time Profiler; AC #25 is the gate. |
| Snapshot tests flake due to floating-point ECG path differences | Low | Fixed phase parameter (`0.5`) + 1pt allowed pixel diff in `swift-snapshot-testing`-style tolerance OR exact match if `ImageRenderer` outputs are deterministic. Confirm during work. |

## Out of Scope (explicit)

- Animated bezel (Lottie/video). Bezel slot is static-only when it returns.
- Mascot on the life-grid escalator screens. `LifeGridDotView` is the focal viz there.
- Mascot on the paywall. Separate hierarchy.
- Mascot on data-collection screens. Deferred to v1.1.
- Cross-screen hand-state continuity in onboarding lead-ins. v1 accepts per-screen reset (lead-ins all pass 0; visually a no-op).
- Migration of `ClockHandView` (in WrapUp) to share code with the new mascot. Different role, different baseline semantics; merging is premature DRY.
- Tone-mode coupling (the mascot does not vary by tone-mode in v1).
- Skeleton-state visual for missing data. Call site decides whether to render the mascot at all.

## Open Question Flagged for Implementation

1. **Data-collection screen integration density (v1.1).** Every Q&A screen, or only the "summary" screens at end of each block? Resolve when picking up v1.1; not blocking v1 ship.

(Plan v1 draft had three additional open questions — skeleton-state visual, tick-mark count, mascot height. Cut after deepening: skeleton state is gone; tick-mark count and mascot height are 30-second decisions made in code, not plan-worthy.)

## Sources & References

### Origin

This conversation (no separate brainstorm document). Founder confirmed: *"use this convo context as the brainstorm."* Decisions locked via two `AskUserQuestion` rounds during `/workflows:plan` on 2026-05-02. Plan deepened same day.

### Internal References

- Reuse target (single-hand sweep): [ClockHandView.swift](products/life-clock-ios/Sources/Features/WrapUp/ClockHandView.swift)
- Sibling viz primitive (Canvas justified): [LifeGridDotView.swift](products/life-clock-ios/Sources/Shared/LifeGridDotView.swift)
- Today integration target: [TodayView.swift:141](products/life-clock-ios/Sources/Features/Today/TodayView.swift:141)
- Engine reveal integration target: [EngineRevealAndDialView.swift](products/life-clock-ios/Sources/Features/Onboarding/Screens/EngineRevealAndDialView.swift)
- Onboarding lead-in call sites: [LeadInScreens.swift:28, 182, 250](products/life-clock-ios/Sources/Features/Onboarding/Screens/LeadInScreens.swift)
- Engine output shape: [LifeClockSchema.swift:243-258](products/life-clock-ios/Sources/Models/LifeClockSchema.swift:243), [ClockEngine.swift:342-346](products/life-clock-ios/Sources/Engines/ClockEngine.swift:342)
- Palette invariant (heartbeat-red is documented exception): [LifeClockPalette.swift:1-5](products/life-clock-ios/Sources/Shared/LifeClockPalette.swift:1)
- UITest identifier dependencies: [LifeClockUITests.swift:25-40](products/life-clock-ios/UITests/LifeClockUITests.swift:25)
- Reduce-motion patterns: [ClockHandView.swift:76-78](products/life-clock-ios/Sources/Features/WrapUp/ClockHandView.swift:76), [LifeGridDotView.swift:21-23](products/life-clock-ios/Sources/Shared/LifeGridDotView.swift:21)

### External References (research-grounded)

- [WWDC23 — Animate with springs](https://developer.apple.com/videos/play/wwdc2023/10158/) — `.interpolatingSpring` vs `.spring(response:dampingFraction:)` for re-targetable continuous input.
- [WWDC23 — Demystify SwiftUI performance](https://developer.apple.com/videos/play/wwdc2023/10160/) — A13-class device performance budgets for SwiftUI animations.
- [Apple Developer — TimelineView](https://developer.apple.com/documentation/swiftui/timelineview) — schedule semantics, `.explicit`, `.animation` with `minimumInterval`.
- [Apple Developer — interpolatingSpring](https://developer.apple.com/documentation/swiftui/animation/interpolatingspring(stiffness:damping:initialvelocity:)).
- [Apple Developer — accessibilityReduceMotion](https://developer.apple.com/documentation/swiftui/environmentvalues/accessibilityreducemotion).
- [Apple Developer — AccessibilityNotification.Announcement](https://developer.apple.com/documentation/accessibility/accessibilitynotification/announcement) — `.low` priority for non-critical announcements.
- [Apple Developer — accessibilityElement(children:)](https://developer.apple.com/documentation/swiftui/view/accessibilityelement(children:)) — collapsing composite drawn views.
- [Apple Developer — ImageRenderer](https://developer.apple.com/documentation/swiftui/imagerenderer) — synchronous SwiftUI → UIImage rendering for snapshot tests, freezes timelines at construction time.

### Related Plans (context, not dependencies)

- [2026-05-01-feat-life-clock-reveal-onboarding-anchor-dial-plan.md](docs/plans/2026-05-01-feat-life-clock-reveal-onboarding-anchor-dial-plan.md) — origin of the existing `ClockMascotView` two-state crossfade. This plan supersedes that visual-metaphor decision.
- [2026-05-01-refactor-life-clock-tab-consolidation-plan.md](docs/plans/2026-05-01-refactor-life-clock-tab-consolidation-plan.md) — established the Today daily-ritual surface that the hero mascot sits atop.

### Institutional Learnings

- [docs/solutions/integration-issues/incomplete-refactor-auto-detection-behind-empty-state-gate.md](docs/solutions/integration-issues/incomplete-refactor-auto-detection-behind-empty-state-gate.md) — *delete the old `ClockMascotView` outright; do not gate it behind a flag.*
- [docs/solutions/integration-issues/catchbook-navigation-revamp-rollout.md](docs/solutions/integration-issues/catchbook-navigation-revamp-rollout.md) — *public struct, clean interface, test in isolation before multi-screen rollout.*
- [docs/solutions/integration-issues/ios-ipad-compatibility-mode-cramped-layout.md](docs/solutions/integration-issues/ios-ipad-compatibility-mode-cramped-layout.md) — *verify `TARGETED_DEVICE_FAMILY = "1,2"` before shipping.*
