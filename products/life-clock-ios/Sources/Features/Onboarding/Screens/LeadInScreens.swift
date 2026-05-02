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
            ClockMascotView(estimate: nil, baseline: nil)
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

    @Environment(OnboardingTelemetryHolder.self) private var telemetry

    var body: some View {
        VStack(spacing: 16) {
            Spacer()
            Text("Welcome to Life Clock.")
                .font(.largeTitle.bold())
                .multilineTextAlignment(.center)
            Text("Make your time visible.")
                .font(.title3)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
            Spacer()
            Button(action: advance) {
                Text("Let's go")
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
        .onAppear { telemetry.value.screenAppeared("welcome") }
        .accessibilityIdentifier("onboarding.welcome")
    }

    private func advance() {
        telemetry.value.screenAdvanced("welcome", durationMs: 0)
        onContinue()
    }
}

// MARK: - MeetYourClockView

/// Personifies the clock mascot. Sets up the metaphor that the user will
/// see again throughout the flow.
struct MeetYourClockView: View {
    let onContinue: () -> Void

    @Environment(OnboardingTelemetryHolder.self) private var telemetry

    var body: some View {
        VStack(spacing: 24) {
            Spacer()
            ClockMascotView(estimate: nil, baseline: nil)
                .frame(width: 180, height: 180)
            VStack(spacing: 12) {
                Text("This is your clock.")
                    .font(.title.bold())
                Text("The more you show up, the more time it gives back.")
                    .font(.body)
                    .foregroundStyle(.secondary)
                    .multilineTextAlignment(.center)
                    .padding(.horizontal)
            }
            Spacer()
            Button(action: advance) {
                Text("Continue")
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
        .onAppear { telemetry.value.screenAppeared("meetYourClock") }
        .accessibilityIdentifier("onboarding.meetYourClock")
    }

    private func advance() {
        telemetry.value.screenAdvanced("meetYourClock", durationMs: 0)
        onContinue()
    }
}

// MARK: - ReactiveSliderView

/// Interactive demo BEFORE any questions: user drags between extremes
/// (sedentary ↔ active demo), the mascot crossfades positive ↔ negative,
/// and a sample number animates. Demo only — captures no data.
///
/// Why: Brainrot's "see for yourself" pattern. Lets the user feel the
/// metaphor before answering anything.
struct ReactiveSliderView: View {
    let onContinue: () -> Void

    @Environment(OnboardingTelemetryHolder.self) private var telemetry
    @State private var sliderValue: Double = 0.5

    private var demoYears: Double {
        // Map slider 0..1 to a sample year band 76..86 around a baseline 81
        76.0 + (sliderValue * 10.0)
    }

    private var demoBaseline: LifeClockEstimate {
        let e = LifeClockEstimate(date: Date())
        e.projectedAgeYears = 81.0
        return e
    }

    private var demoEstimate: LifeClockEstimate {
        let e = LifeClockEstimate(date: Date())
        e.projectedAgeYears = demoYears
        return e
    }

    var body: some View {
        VStack(spacing: 24) {
            Spacer()
            ClockMascotView(estimate: demoEstimate, baseline: demoBaseline)
                .frame(width: 160, height: 160)
            Text(String(format: "%.0f years", demoYears))
                .font(.system(size: 56, weight: .semibold, design: .rounded))
                .contentTransition(.numericText(value: demoYears))
                .animation(.snappy, value: sliderValue)
            Text("Drag to feel how your habits move the clock.")
                .font(.subheadline)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
            Slider(value: $sliderValue, in: 0...1)
                .padding(.horizontal)
                .accessibilityIdentifier("onboarding.reactiveSlider.slider")
            HStack {
                Text("Less active").font(.caption2).foregroundStyle(.secondary)
                Spacer()
                Text("More active").font(.caption2).foregroundStyle(.secondary)
            }
            .padding(.horizontal)
            Spacer()
            Button(action: advance) {
                Text("Show me mine")
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
        .onAppear { telemetry.value.screenAppeared("reactiveSlider") }
        .accessibilityIdentifier("onboarding.reactiveSlider")
    }

    private func advance() {
        telemetry.value.screenAdvanced("reactiveSlider", durationMs: 0)
        onContinue()
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
}

#Preview("ReactiveSlider") {
    ReactiveSliderView(onContinue: {})
        .environment(OnboardingTelemetryHolder(StubTelemetry()))
}
#endif
