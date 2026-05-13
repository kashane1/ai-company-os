import SwiftUI

/// The engine reveal screen — Phase 5 heart of the feature. Shows the
/// engine's projected healthspan and lets the user fine-tune ±5 yrs via
/// a one-time dial. Confirm calls `onConfirm(years:)` which the
/// coordinator routes through `LifeClockStore.applyAnchorAdjustment`.
///
/// **Race-safe:** the engine gates on `anchorAdjustedAt != nil` so a
/// half-applied adjustment cannot double-count on the next launch (see
/// ClockEngine.swift's atomic gate). The store mutator wraps the two
/// writes in an explicit do/catch — no `try?` swallowing failures.
///
/// **Back-nav rule:** post-Confirm, the coordinator clears the
/// NavigationPath so this screen cannot be reached again.
struct EngineRevealAndDialView: View {
    let onConfirm: (Double) -> Void

    @Environment(LifeClockStore.self) private var store
    @Environment(OnboardingDraft.self) private var draft
    @Environment(MascotOverride.self) private var mascotOverride
    @Environment(OnboardingTelemetryHolder.self) private var telemetry
    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    @State private var dialYears: Double = 0
    @State private var showConfirmDialog = false

    /// Engine projection cached on appear. Draft inputs do not mutate
    /// while this screen is visible (it's the post-data-collection
    /// reveal), so recomputing per-tick was running the actuarial
    /// math 60×/sec for a constant. Cached value is the baseline; the
    /// dial layers ±yrs on top.
    @State private var engineYears: Double = 0
    @State private var revealHapticTrigger: Int = 0

    private var displayedYears: Double {
        engineYears + dialYears
    }

    private var mascotDelta: Int {
        EngineRevealPresenter.mascotDelta(
            displayedYears: displayedYears,
            baselineYears: engineYears
        )
    }

    @State private var hasPulsed = false

    var body: some View {
        engineDialBody
            .accessibilityIdentifier("onboarding.engineRevealAndDial")
            .onAppear {
                telemetry.value.screenAppeared("engineRevealAndDial")
                let snapshot = draft.materialize()
                engineYears = ClockEngine(clock: store.clock)
                    .calculateBaseline(profile: snapshot)
                    .projectedAgeYears
                runRevealPulse()
            }
            .onChange(of: dialYears) { _, _ in
                // Once the user starts dialing, the dial drives the
                // mascot. Don't re-pulse — that'd fight the input.
                if hasPulsed { mascotOverride.minutes = mascotDelta }
            }
            .onDisappear {
                mascotOverride.minutes = nil
            }
            .sensoryFeedback(LifeClockHaptics.firstReveal, trigger: revealHapticTrigger)
    }

    /// First glance at the user's clock should land with a beat, not a
    /// silent number. Pulse forward, ease toward the dial-zero anchor,
    /// then hand control off to the dial. Same shape as the
    /// MeetYourClock and ArchetypeReveal beats.
    private func runRevealPulse() {
        mascotOverride.minutes = 110
        revealHapticTrigger &+= 1
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.55) {
            mascotOverride.minutes = -55
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.45) {
                mascotOverride.minutes = mascotDelta
                hasPulsed = true
            }
        }
    }

    private var engineDialBody: some View {
        VStack(alignment: .leading, spacing: 24) {
            VStack(alignment: .leading, spacing: 8) {
                Text("Your projected healthspan")
                    .font(.headline)
                    .foregroundStyle(.secondary)
                Text(String(format: "%.1f years", displayedYears))
                    .font(.system(size: 56, weight: .semibold, design: .rounded))
                    .contentTransition(.numericText(value: displayedYears))
                    .animation(reduceMotion ? nil : .snappy, value: displayedYears)
                    .accessibilityIdentifier("onboarding.dialYears")
                if let projected = projectedDate {
                    Text("(\(projected, style: .date))")
                        .font(.caption)
                        .foregroundStyle(.tertiary)
                }
            }
            VStack(alignment: .leading, spacing: 8) {
                Text("Nudge it if your gut says the questions missed something.")
                    .font(.body)
                    .foregroundStyle(.secondary)
                Slider(value: $dialYears, in: -5...5, step: 0.5)
                    .accessibilityIdentifier("onboarding.dial.slider")
                HStack {
                    Text("-5 yrs").font(.caption2).foregroundStyle(.tertiary)
                    Spacer()
                    Text("Engine").font(.caption2).foregroundStyle(.tertiary)
                    Spacer()
                    Text("+5 yrs").font(.caption2).foregroundStyle(.tertiary)
                }
            }
            Spacer()
            Text("Set this once — it anchors your clock from here.")
                .font(.caption)
                .foregroundStyle(.tertiary)
                .frame(maxWidth: .infinity)
            Button(action: { showConfirmDialog = true }) {
                Text("Confirm")
                    .font(.headline)
                    .frame(maxWidth: .infinity)
                    .padding()
                    .background(Color.accentColor)
                    .foregroundStyle(.white)
                    .clipShape(RoundedRectangle(cornerRadius: 14))
            }
            .accessibilityIdentifier("onboarding.dial.confirm")
            .alert("Anchor your clock?", isPresented: $showConfirmDialog) {
                Button("Cancel", role: .cancel) {}
                Button("Anchor") {
                    telemetry.value.dialAdjusted(
                        yearsBucket: DialAdjustmentBucket.bucket(for: dialYears)
                    )
                    onConfirm(dialYears)
                }
            } message: {
                Text("Once anchored, this stays put. Daily progress still moves the hands.")
            }
        }
        .padding(.horizontal, 24)
        .padding(.bottom, 24)
    }

    private var projectedDate: Date? {
        guard let dob = draft.birthDate else { return nil }
        let totalDays = displayedYears * 365.2425
        return Calendar.current.date(byAdding: .day, value: Int(totalDays.rounded()), to: dob)
    }
}
