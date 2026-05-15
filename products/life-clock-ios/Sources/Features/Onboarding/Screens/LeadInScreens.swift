import SwiftUI
import Foundation

/// Lead-in screens for the new onboarding flow (Phase 3.5 of the
/// reveal-onboarding rebuild). These run BEFORE any data collection —
/// their job is to earn the user's attention before asking for input.
///
/// Each screen takes a generic `onContinue` closure rather than knowing
/// how to navigate; the coordinator (Phase 4) wires them up via
/// `NavigationStack(path:)`. Telemetry is read from the environment so
/// screens stay routing-agnostic.
///
/// All copy is agency-framed per CLAUDE_HANDOFF.md — no doom default,
/// no medical-claim verbs.

// MARK: - OnboardingHeader

/// Persistent header rendered ONCE at the coordinator level (above the
/// onboarding `NavigationStack`). Shows a fixed wordmark and the mascot.
/// Hands reflect either:
///   - `MascotOverride.minutes` when a screen is driving the mascot from
///     a transient input (`ReactiveSliderView`, `EngineRevealAndDialView`),
///   - otherwise the running per-answer delta on `draft.lastDelta`.
///
/// Single-instance lifetime: by living above `NavigationStack` rather
/// than inside `OnboardingScaffold`, this view's identity stays stable
/// across pushes after the first `coldOpen → welcome` transition — one
/// `onAppear` thereafter, no rebuild between screens. Hand animation is
/// continuous, not per-screen.
struct OnboardingHeader: View {
    /// True when a back affordance should be visible. Coordinator passes
    /// false on screens where back-nav is forbidden — most importantly
    /// after the dial Confirm path-clear, where stepping back would
    /// re-expose the one-time anchor dial.
    let canGoBack: Bool
    let onBack: () -> Void

    @Environment(OnboardingDraft.self) private var draft
    @Environment(MascotOverride.self) private var override

    /// Transient overshoot added on top of the steady-state delta when an
    /// answer produces a meaningful estimate change. Triumphant for clear
    /// gains, concerned (flinch) for clear losses, no extra beat for
    /// near-neutral answers — the user reads the SIGN of their answer in
    /// the kick before the hands settle on the new resting position.
    @State private var reactionOvershoot: Int = 0

    /// Steady-state minutes — the mascot's resting position when no kick
    /// is in flight. Reads `cumulativeDeltaYears` (gain/loss relative to
    /// the lifestyle-free baseline) so the hands accumulate across the
    /// onboarding flow rather than snap back to neutral on Continue.
    ///
    /// **Saturation, not clamp.** `EngineRevealPresenter`'s ±60 min cap
    /// would land the hand at ±360° on a heavily-bad answer set — one
    /// full revolution, visually indistinguishable from baseline. We
    /// instead tanh-squash the years input so the visible sweep
    /// asymptotically approaches ±`saturationMinutes` (= ±150°, well
    /// inside one revolution) — large cumulative losses saturate but
    /// never wrap. At ±2y the hand reads as a clear nudge; at ±8y it's
    /// near the cap; at ±12y it asymptotes.
    private static let saturationMinutes: Double = 25
    private static let saturationYears: Double = 8
    private var steadyStateMinutes: Int {
        if let override = override.minutes { return override }
        let years = draft.cumulativeDeltaYears
        let saturated = Self.saturationMinutes * tanh(years / Self.saturationYears)
        return Int(saturated.rounded())
    }

    /// What the mascot actually renders. Overshoot is only applied when no
    /// screen-level override is driving the mascot (reactiveSlider, dial)
    /// — those screens own the hands during their lifetime and the
    /// reaction layer must not fight their input.
    private var minutesDelta: Int {
        if override.minutes != nil { return steadyStateMinutes }
        return steadyStateMinutes + reactionOvershoot
    }

    /// Years-delta magnitude above which an answer earns an expressive
    /// reaction beat. Tuned against measured ClockEngine deltas: smoking
    /// "Daily" ≈ -0.8y (strong), alcohol "Most days" ≈ -0.25y (moderate),
    /// diet "Rough" ≈ -0.15y (mild). 0.1y catches all three; below that
    /// is rounding noise that should pass through as a smooth spring.
    private static let reactionThresholdYears: Double = 0.1

    /// Overshoot magnitude scales with delta strength so a "Rough" diet
    /// reads as a smaller flinch than "Daily smoker". Three buckets keep
    /// the dispatch obvious; finer interpolation didn't read differently
    /// at the 120pt header size during dogfood.
    private static func overshootMinutes(for years: Double) -> Int {
        let magnitude = abs(years)
        if magnitude >= 0.5 { return 30 }
        if magnitude >= 0.25 { return 20 }
        return 12
    }

    var body: some View {
        ZStack {
            // Centered wordmark + mascot.
            VStack(spacing: 12) {
                Text("Life Clock")
                    .font(.footnote.weight(.semibold))
                    .tracking(2)
                    .textCase(.uppercase)
                    .foregroundStyle(.secondary)
                    .accessibilityIdentifier("onboarding.header.wordmark")
                LifeClockMascotView(minutesDelta: minutesDelta)
                    .frame(width: 120, height: 120)
                    .accessibilityIdentifier("onboarding.header.mascot")
            }
            .frame(maxWidth: .infinity)
            .accessibilityElement(children: .ignore)
            .accessibilityLabel("Life Clock")

            // Back chevron pinned top-leading. Hidden via opacity (not
            // conditional layout) so the wordmark/mascot don't reflow
            // when navigating into a no-back screen — view identity for
            // the persistent header stays stable.
            HStack {
                Button(action: onBack) {
                    Image(systemName: "chevron.left")
                        .font(.title3.weight(.semibold))
                        .foregroundStyle(.secondary)
                        .frame(width: 44, height: 44)        // 44pt HIG min hit target
                        .contentShape(Rectangle())
                }
                .opacity(canGoBack ? 1 : 0)
                .disabled(!canGoBack)
                .accessibilityIdentifier("onboarding.header.back")
                .accessibilityLabel("Back")
                Spacer()
            }
        }
        .padding(.top, 8)
        .padding(.bottom, 16)
        .accessibilityIdentifier("onboarding.header")
        .onChange(of: draft.lastDelta) { _, new in
            triggerReaction(for: new)
        }
    }

    /// Apply an expressive overshoot when `lastDelta` changes by enough to
    /// read as a clearly-positive or clearly-negative answer; near-neutral
    /// changes pass through silently and let the spring handle them.
    /// No-ops while a screen-level override is driving the mascot.
    private func triggerReaction(for new: AnswerDelta?) {
        guard override.minutes == nil else { return }
        guard let new, abs(new.years) >= Self.reactionThresholdYears else { return }
        let direction = new.years > 0 ? 1 : -1
        reactionOvershoot = direction * Self.overshootMinutes(for: new.years)
        // Settle window: the overshoot persists ~0.42s — enough for the
        // mascot's `.interpolatingSpring()` to nearly reach the kick — then
        // releases back to 0 so the hands drift onto the new steady-state
        // position. Two-stage timing: delay matches the spring's quarter-
        // period; the release uses the same spring on the way down.
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.42) {
            reactionOvershoot = 0
        }
    }
}

/// Hide the system navigation bar on every onboarding destination.
/// `NavigationStack`-level `.toolbar(.hidden, for: .navigationBar)` does
/// not propagate to pushed destinations on iOS 17/18, so each
/// destination has to opt in. Centralizing here means: one place to
/// change, no copy/paste, and a new screen author cannot forget the
/// modifier (the coordinator's destination wrapper applies it to every
/// pushed view).
private struct OnboardingChromeModifier: ViewModifier {
    func body(content: Content) -> some View {
        content.toolbar(.hidden, for: .navigationBar)
    }
}

extension View {
    func onboardingChrome() -> some View {
        modifier(OnboardingChromeModifier())
    }
}

/// Transient view-state holder for the persistent header mascot. Lives
/// in the SwiftUI environment alongside `OnboardingDraft` but kept
/// separate so the draft (a domain-input model) doesn't churn when
/// demo / dial screens drive the mascot from a slider value.
///
/// **Why a separate env object instead of a property on `OnboardingDraft`:**
/// before this split, every dial drag mutated `draft.mascotOverrideMinutes`,
/// which invalidated every observer of `draft` — coordinator body,
/// per-screen scaffolds, the running-estimate readers — even though only
/// the header cared. By isolating override state here, only `OnboardingHeader`
/// invalidates per drag tick.
@Observable
@MainActor
final class MascotOverride {
    var minutes: Int?

    init(minutes: Int? = nil) {
        self.minutes = minutes
    }
}

// MARK: - ColdOpenView

/// First screen the user sees: clock mascot alone, no copy. Auto-advances
/// after ~2s but a tap also advances (no forced-delay UX). Builds curiosity.
struct ColdOpenView: View {
    let onContinue: () -> Void

    @Environment(OnboardingTelemetryHolder.self) private var telemetry
    @State private var hasAdvanced = false

    var body: some View {
        ZStack {
            Color(.systemBackground).ignoresSafeArea()
            LifeClockMascotView(minutesDelta: 0)
                .frame(width: 180, height: 180)
        }
        .contentShape(Rectangle())
        .onTapGesture { advance() }
        .onAppear {
            telemetry.value.screenAppeared("coldOpen")
            // Debug-only: when LIFECLOCK_JUMP_TO is set, the coordinator's
            // jump fixture has already replaced the path. Skip the timed
            // auto-advance so it doesn't push `.welcome` on top of the
            // jump target.
            #if DEBUG
            if ProcessInfo.processInfo.environment["LIFECLOCK_JUMP_TO"] != nil { return }
            #endif
            DispatchQueue.main.asyncAfter(deadline: .now() + 1.2) { advance() }
        }
        .accessibilityAddTraits(.isButton)
        .accessibilityLabel("Welcome screen — tap to begin")
        .accessibilityIdentifier("onboarding.coldOpen")
    }

    private func advance() {
        guard !hasAdvanced else { return }
        hasAdvanced = true
        telemetry.value.screenAdvanced("coldOpen", durationMs: 0)
        onContinue()
    }
}

// MARK: - WelcomeView

/// Lead headline + Let's go. The persistent wordmark above already says
/// "LIFE CLOCK"; the body title needs to add weight, not echo. Lead with
/// the value prop instead.
struct WelcomeView: View {
    let onContinue: () -> Void
    var body: some View {
        OnboardingScaffold(
            screenID: "welcome",
            title: "Earn time with better habits.",
            continueLabel: "Let's go",
            onContinue: onContinue
        ) { EmptyView() }
    }
}

// MARK: - MeetYourClockView

/// Personifies the clock mascot. The mascot itself lives in the persistent
/// header; on appear, briefly nudge the override so the hands shift the
/// instant the user reads "the hands move with you" — pay off the
/// promise instead of stating it past a static clock.
struct MeetYourClockView: View {
    let onContinue: () -> Void

    @Environment(MascotOverride.self) private var mascotOverride

    var body: some View {
        OnboardingScaffold(
            screenID: "meetYourClock",
            title: "This is your Life Clock.",
            bodyText: "Healthy habits earn time. Bad days cost it. The hands move with you.",
            onContinue: onContinue
        ) { EmptyView() }
            .onAppear { runWakeNudge() }
            .onDisappear { mascotOverride.minutes = nil }
    }

    /// Tiny demo: drift positive ~+90 min for half a second, then settle.
    /// Shows reactivity without committing to a value before any input.
    private func runWakeNudge() {
        mascotOverride.minutes = 90
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.7) {
            mascotOverride.minutes = -45
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.6) {
                mascotOverride.minutes = 0
            }
        }
    }
}

// MARK: - ReactiveSliderView

/// Interactive demo BEFORE any questions: user drags between extremes,
/// the header mascot reacts via `mascotMinutesDeltaOverride`, and a sample
/// number animates. Demo only — captures no data.
struct ReactiveSliderView: View {
    let onContinue: () -> Void

    @Environment(MascotOverride.self) private var mascotOverride
    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    /// Three-dial demo: each slider ∈ [0,1]. Aggregate average drives the
    /// demo year band and the persistent header mascot via the focused
    /// `MascotOverride` env object (kept off `OnboardingDraft` to avoid
    /// invalidating every draft observer on every drag tick).
    @State private var activity: Double = 0.5
    @State private var food: Double = 0.5
    @State private var sleep: Double = 0.5

    private static let demoBaselineYears: Double = 81.0
    private var aggregate: Double { (activity + food + sleep) / 3.0 }
    private var demoYears: Double { 76.0 + (aggregate * 10.0) }

    private var demoMinutesDelta: Int {
        EngineRevealPresenter.mascotDelta(
            displayedYears: demoYears,
            baselineYears: Self.demoBaselineYears
        )
    }

    var body: some View {
        OnboardingScaffold(
            screenID: "reactiveSlider",
            title: "Drag to see how habits move your clock.",
            continueLabel: "Show me mine",
            onContinue: onContinue
        ) {
            VStack(spacing: 16) {
                Text(String(format: "%.0f years", demoYears))
                    .font(.system(size: 56, weight: .semibold, design: .rounded))
                    .contentTransition(.numericText(value: demoYears))
                    .animation(reduceMotion ? nil : .snappy, value: aggregate)
                    .frame(maxWidth: .infinity)
                    .accessibilityIdentifier("onboarding.reactiveSlider.years")

                LifeClockSliderRow(
                    label: "Activity",
                    leadingExtremeLabel: "Sedentary",
                    trailingExtremeLabel: "Active",
                    value: $activity,
                    identifierSuffix: "reactiveSlider.activity"
                )
                LifeClockSliderRow(
                    label: "Food",
                    leadingExtremeLabel: "Junk",
                    trailingExtremeLabel: "Whole foods",
                    value: $food,
                    identifierSuffix: "reactiveSlider.food"
                )
                LifeClockSliderRow(
                    label: "Sleep",
                    leadingExtremeLabel: "5 hrs",
                    trailingExtremeLabel: "9 hrs",
                    value: $sleep,
                    identifierSuffix: "reactiveSlider.sleep"
                )
            }
        }
        .onAppear { mascotOverride.minutes = demoMinutesDelta }
        .onChange(of: aggregate) { _, _ in
            mascotOverride.minutes = demoMinutesDelta
        }
        .onDisappear { mascotOverride.minutes = nil }
    }
}

// MARK: - Telemetry env holder

/// Wraps an `OnboardingTelemetry` for `@Environment` injection. Protocols
/// can't go directly into `@Environment(_:)` in SwiftUI 5; the holder
/// pattern is the established workaround.
@Observable
final class OnboardingTelemetryHolder {
    let value: OnboardingTelemetry

    init(_ value: OnboardingTelemetry) {
        self.value = value
    }
}

#if DEBUG
#Preview("ColdOpen") {
    ColdOpenView(onContinue: {})
        .environment(OnboardingTelemetryHolder(StubTelemetry()))
}

#Preview("Welcome") {
    WelcomeView(onContinue: {})
        .environment(OnboardingTelemetryHolder(StubTelemetry()))
        .environment(OnboardingDraft())
}

#Preview("ReactiveSlider") {
    ReactiveSliderView(onContinue: {})
        .environment(OnboardingTelemetryHolder(StubTelemetry()))
        .environment(OnboardingDraft())
}
#endif
