import SwiftUI
import SwiftData

/// Forward-looking projection surface. Fourth top-level tab between
/// History and Profile.
///
/// V1.7.0 — Phase 2 ships the shell + day-state machine + headline
/// stack. The chart lands in Phase 3, the slider + Pro narrative in
/// Phase 4. The tab is hidden from RELEASE builds (via
/// `LifeClockLaunchConfiguration.futureTabUnlocked`) until Phase 4
/// flips the release default.
///
/// Day-state semantics (plan §Phase 2):
///
///   day0          — install day; baseline-only render, no chart, no
///                   slider, "your projection arrives tomorrow."
///   coldLaunch1to3 — days 1–3; baseline + cold-launch line; no chart,
///                   no slider.
///   warmingUp4to13 — days 4–13; chart + slider active, N-aware
///                   transparency line.
///   full14plus     — days ≥14; full Future tab.
struct FutureView: View {
    @Environment(LifeClockStore.self) private var store
    @Environment(SubscriptionStore.self) private var subscriptions

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: DesignTokens.Spacing.lg) {
                    headlineStack
                    daySpecificContent
                }
                .padding(DesignTokens.Spacing.lg)
                .readableColumn()
            }
            .navigationTitle("Future")
            .accessibilityIdentifier("future.screen")
        }
    }

    // MARK: - Day-state machine

    /// Computed daily — depends on `clock.now()` and
    /// `profile.onboardingCompletedAt`. Recomputed every render pass
    /// since SwiftUI re-evaluates the view on store changes.
    private var dayState: DayState {
        guard let onboarded = store.profile?.onboardingCompletedAt else {
            // Defense-in-depth: MainTabView already hides the tab when
            // onboardingCompletedAt == nil, but the view body should
            // still render harmlessly if invoked. Treat as day0.
            return .day0
        }
        let now = store.clock.now()
        let calendar = store.clock.calendar
        let installDay = calendar.startOfDay(for: onboarded)
        let today = calendar.startOfDay(for: now)
        let days = max(0, calendar.dateComponents([.day], from: installDay, to: today).day ?? 0)
        switch days {
        case 0: return .day0
        case 1...3: return .coldLaunch1to3
        case 4...13: return .warmingUp4to13
        default: return .full14plus
        }
    }

    private var daysOfData: Int {
        guard let onboarded = store.profile?.onboardingCompletedAt else { return 0 }
        let calendar = store.clock.calendar
        let installDay = calendar.startOfDay(for: onboarded)
        let today = calendar.startOfDay(for: store.clock.now())
        return max(0, calendar.dateComponents([.day], from: installDay, to: today).day ?? 0)
    }

    // MARK: - Headline stack

    /// Three-row stack: big-number projection, baseline footnote line,
    /// signed delta. Day 0 hides the big-number (no projection yet).
    @ViewBuilder
    private var headlineStack: some View {
        VStack(alignment: .leading, spacing: DesignTokens.Spacing.sm) {
            if dayState != .day0,
               let baseline = store.profile?.baselineHealthspanYears {
                let projection = currentProjection(baseline: baseline)
                ViewThatFits(in: .horizontal) {
                    Text(formatHealthspan(projection))
                        .font(.system(size: 52, weight: .semibold, design: .rounded))
                    Text(formatHealthspan(projection))
                        .font(.system(size: 36, weight: .semibold, design: .rounded))
                    Text(formatHealthspan(projection))
                        .font(.system(size: 28, weight: .semibold, design: .rounded))
                }
                .accessibilityIdentifier("future.headline.projection")

                Text("you started at \(formatHealthspan(baseline))")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)

                signedDelta(projection: projection, baseline: baseline)

                if dayState != .day0 && dayState != .coldLaunch1to3 {
                    Text(store.toneMode.futureHeadlineSubtext)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                        .padding(.top, DesignTokens.Spacing.xs)
                }
            } else if let baseline = store.profile?.baselineHealthspanYears {
                // Day 0 — baseline-only headline.
                Text(formatHealthspan(baseline))
                    .font(.system(size: 36, weight: .semibold, design: .rounded))
                    .accessibilityIdentifier("future.headline.baseline")
                Text("Your starting baseline")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
            }
        }
    }

    @ViewBuilder
    private func signedDelta(projection: Double, baseline: Double) -> some View {
        let delta = projection - baseline
        if abs(delta) >= 0.05 {  // suppress display when delta rounds to zero
            let sign = delta >= 0 ? "+" : "−"
            let magnitude = formatHealthspan(abs(delta))
            let verb = delta >= 0 ? "earned" : "lost"
            Text("\(sign)\(magnitude) \(verb) since you started")
                .font(.subheadline)
                .foregroundStyle(.secondary)
                .accessibilityIdentifier("future.headline.delta")
        }
    }

    // MARK: - Day-specific content

    @ViewBuilder
    private var daySpecificContent: some View {
        switch dayState {
        case .day0:
            Text(store.toneMode.futureDay0Line)
                .font(.body)
                .foregroundStyle(.primary)
                .accessibilityIdentifier("future.day0.line")

        case .coldLaunch1to3:
            Text(store.toneMode.futureColdLaunchLine)
                .font(.body)
                .foregroundStyle(.primary)
                .accessibilityIdentifier("future.coldLaunch.line")

        case .warmingUp4to13:
            // Phase 3 will land the chart; Phase 4 will land the slider.
            // For Phase 2 we surface the N-aware transparency line
            // (pool-with-discrete-N — read from ReflectionPrompts).
            Text(ReflectionPrompts.futureWarmingUpTransparency(
                daysOfData: daysOfData,
                tone: store.toneMode
            ))
            .font(.body)
            .foregroundStyle(.primary)
            .accessibilityIdentifier("future.warmingUp.line")

        case .full14plus:
            // Phase 3 will land the chart here. Phase 2 placeholder:
            // surface a transparent "chart coming" line so the day-state
            // machine is testable. The DEBUG/RELEASE tab gate keeps
            // this out of TestFlight.
            Text("Trajectory chart lands in Phase 3.")
                .font(.body)
                .foregroundStyle(.secondary)
                .accessibilityIdentifier("future.full.placeholder")
        }
    }

    // MARK: - Helpers

    /// Computed projection: baseline + sum-of-dimension-deltas, clamped.
    /// Phase 2 placeholder returns baseline as-is (no engine yet).
    /// Phase 3 wires `HealthspanEngine.currentProjection(...)`.
    private func currentProjection(baseline: Double) -> Double {
        baseline
    }

    /// Format a healthspan-years Double as "Xy Ym" via
    /// DateComponentsFormatter. Per the cross-screen time-unit
    /// convention (plan §Phase 4): Future tab = years+months.
    private func formatHealthspan(_ years: Double) -> String {
        let totalMonths = Int((years * 12).rounded())
        let y = totalMonths / 12
        let m = totalMonths % 12
        if m == 0 { return "\(y) years" }
        return "\(y) years, \(m) months"
    }

    enum DayState {
        case day0
        case coldLaunch1to3
        case warmingUp4to13
        case full14plus
    }
}
