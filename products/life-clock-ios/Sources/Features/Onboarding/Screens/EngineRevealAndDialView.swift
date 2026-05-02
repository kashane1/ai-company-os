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
    @Environment(OnboardingTelemetryHolder.self) private var telemetry

    @State private var dialYears: Double = 0
    @State private var showConfirmDialog = false

    private var engineYears: Double {
        let snapshot = draft.materialize()
        return ClockEngine(clock: store.clock)
            .calculateBaseline(profile: snapshot)
            .projectedAgeYears
    }

    private var displayedYears: Double {
        engineYears + dialYears
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 24) {
            VStack(alignment: .leading, spacing: 8) {
                Text("Your projected healthspan")
                    .font(.headline)
                    .foregroundStyle(.secondary)
                Text(String(format: "%.1f years", displayedYears))
                    .font(.system(size: 56, weight: .semibold, design: .rounded))
                    .contentTransition(.numericText(value: displayedYears))
                    .animation(.snappy, value: displayedYears)
                    .accessibilityIdentifier("onboarding.dialYears")
                if let projected = projectedDate {
                    Text("(\(projected, style: .date))")
                        .font(.caption)
                        .foregroundStyle(.tertiary)
                }
            }
            VStack(alignment: .leading, spacing: 8) {
                Text("Adjust if your gut says something the questions missed.")
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
            Text("One-time only — locks for life.")
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
            .alert("Lock your clock?", isPresented: $showConfirmDialog) {
                Button("Cancel", role: .cancel) {}
                Button("Lock") {
                    telemetry.value.dialAdjusted(
                        yearsBucket: DialAdjustmentBucket.bucket(for: dialYears)
                    )
                    onConfirm(dialYears)
                }
            } message: {
                Text("Once locked, this can't be re-adjusted.")
            }
        }
        .padding(24)
        .accessibilityIdentifier("onboarding.engineRevealAndDial")
        .onAppear { telemetry.value.screenAppeared("engineRevealAndDial") }
    }

    private var projectedDate: Date? {
        guard let dob = draft.birthDate else { return nil }
        let totalDays = displayedYears * 365.2425
        return Calendar.current.date(byAdding: .day, value: Int(totalDays.rounded()), to: dob)
    }
}
