import SwiftUI

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
    @Environment(OnboardingDraft.self) private var draft
    @Environment(MascotOverride.self) private var override

    private var minutesDelta: Int {
        if let override = override.minutes { return override }
        let years = draft.lastDelta?.years ?? 0
        let raw = Int((years * Double(EngineRevealPresenter.minutesPerYear)).rounded())
        return min(
            max(raw, EngineRevealPresenter.minMinutes),
            EngineRevealPresenter.maxMinutes
        )
    }

    var body: some View {
        VStack(spacing: 12) {
            Text("Life Clock")
                .font(.footnote.weight(.semibold))
                .tracking(2)
                .textCase(.uppercase)
                .foregroundStyle(.secondary)
            LifeClockMascotView(minutesDelta: minutesDelta)
                .frame(width: 120, height: 120)
                .accessibilityIdentifier("onboarding.header.mascot")
        }
        .frame(maxWidth: .infinity)
        .padding(.top, 8)
        .padding(.bottom, 16)
        .accessibilityElement(children: .ignore)
        .accessibilityLabel("Life Clock")
        .accessibilityIdentifier("onboarding.header")
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
            DispatchQueue.main.asyncAfter(deadline: .now() + 2.0) { advance() }
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

// MARK: - AppPreviewsView

/// Phone-in-phone style preview of the actual app's main screens. Builds
/// confidence — "this product is real, this is what you're getting" —
/// before any data ask. Uses placeholder vector previews in the asset
/// catalog (`OnboardingPreview1` / `2` / `3`); falls back to SF Symbol
/// stand-ins until founder ships final art.
struct AppPreviewsView: View {
    let onContinue: () -> Void

    @Environment(OnboardingTelemetryHolder.self) private var telemetry
    @State private var index: Int = 0

    private let previews: [(asset: String, fallback: String, label: String)] = [
        ("OnboardingPreview1", "calendar", "Daily life clock"),
        ("OnboardingPreview2", "chart.line.uptrend.xyaxis", "Your weekly trend"),
        ("OnboardingPreview3", "heart.text.square", "Wrap-up reflections"),
    ]

    var body: some View {
        VStack(spacing: 24) {
            Spacer()
            ZStack {
                ForEach(Array(previews.enumerated()), id: \.offset) { offset, preview in
                    previewImage(preview.asset, fallback: preview.fallback)
                        .opacity(offset == index ? 1 : 0)
                }
            }
            .frame(maxWidth: .infinity, maxHeight: 360)
            Text(previews[index].label)
                .font(.headline)
                .foregroundStyle(.secondary)
            Spacer()
            Button(action: advance) {
                Text("Get started")
                    .font(.headline)
                    .frame(maxWidth: .infinity)
                    .padding()
                    .background(Color.accentColor)
                    .foregroundStyle(.white)
                    .clipShape(RoundedRectangle(cornerRadius: 14))
            }
            .accessibilityIdentifier("onboarding.continue")
        }
        .padding(24)
        .onAppear {
            telemetry.value.screenAppeared("appPreviews")
            startCarousel()
        }
        .accessibilityIdentifier("onboarding.appPreviews")
    }

    @ViewBuilder
    private func previewImage(_ name: String, fallback systemName: String) -> some View {
        if UIImage(named: name) != nil {
            Image(name).resizable().scaledToFit()
        } else {
            Image(systemName: systemName)
                .resizable()
                .scaledToFit()
                .padding(40)
                .foregroundStyle(.secondary)
        }
    }

    private func startCarousel() {
        Timer.scheduledTimer(withTimeInterval: 2.5, repeats: true) { timer in
            Task { @MainActor in
                index = (index + 1) % previews.count
            }
        }
    }

    private func advance() {
        telemetry.value.screenAdvanced("appPreviews", durationMs: 0)
        onContinue()
    }
}

// MARK: - WelcomeView

/// "Welcome to Life Clock" + tagline + Let's go.
struct WelcomeView: View {
    let onContinue: () -> Void
    var body: some View {
        OnboardingScaffold(
            screenID: "welcome",
            title: "Welcome to Life Clock.",
            bodyText: "Earn time with better habits.",
            continueLabel: "Let's go",
            onContinue: onContinue
        ) { EmptyView() }
    }
}

// MARK: - MeetYourClockView

/// Personifies the clock mascot. The mascot itself lives in the persistent
/// header; the body just frames the metaphor.
struct MeetYourClockView: View {
    let onContinue: () -> Void
    var body: some View {
        OnboardingScaffold(
            screenID: "meetYourClock",
            title: "This is your Life Clock.",
            bodyText: "Healthy habits earn time. Bad days cost it. The hands move with you.",
            onContinue: onContinue
        ) { EmptyView() }
    }
}

// MARK: - ReactiveSliderView

/// Interactive demo BEFORE any questions: user drags between extremes,
/// the header mascot reacts via `mascotMinutesDeltaOverride`, and a sample
/// number animates. Demo only — captures no data.
struct ReactiveSliderView: View {
    let onContinue: () -> Void

    @Environment(MascotOverride.self) private var mascotOverride

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
                    .animation(.snappy, value: aggregate)
                    .frame(maxWidth: .infinity)
                    .accessibilityIdentifier("onboarding.reactiveSlider.years")

                dial(label: "Activity",
                     leading: "Sedentary", trailing: "Active",
                     value: $activity, idSuffix: "activity")
                dial(label: "Food",
                     leading: "Junk", trailing: "Whole foods",
                     value: $food, idSuffix: "food")
                dial(label: "Sleep",
                     leading: "5 hrs", trailing: "9 hrs",
                     value: $sleep, idSuffix: "sleep")
            }
        }
        .onAppear { mascotOverride.minutes = demoMinutesDelta }
        .onChange(of: aggregate) { _, _ in
            mascotOverride.minutes = demoMinutesDelta
        }
        .onDisappear { mascotOverride.minutes = nil }
    }

    @ViewBuilder
    private func dial(
        label: String,
        leading: String,
        trailing: String,
        value: Binding<Double>,
        idSuffix: String
    ) -> some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(label).font(.caption.bold()).foregroundStyle(.secondary)
            Slider(value: value, in: 0...1)
                .accessibilityIdentifier("onboarding.reactiveSlider.\(idSuffix)")
            HStack {
                Text(leading).font(.caption2).foregroundStyle(.tertiary)
                Spacer()
                Text(trailing).font(.caption2).foregroundStyle(.tertiary)
            }
        }
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
