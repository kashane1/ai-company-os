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
    @State private var paywallScrollTarget: PaywallSheet.Section? = nil
    @State private var paywallPresented: Bool = false

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
            .sheet(isPresented: $paywallPresented) {
                PaywallSheet(scrollTo: paywallScrollTarget)
            }
            .onAppear {
                TelemetryRecorder.shared.emit(.futureTabViewed)
            }
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

                Text(store.toneMode.futureBaselineFootnote(formatted: formatHealthspan(baseline)))
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
                // Day-0 only — intentionally tone-neutral. No projection or
                // delta exists yet, so this is a structural label, not
                // narration. Routing through ToneMode here would invent
                // urgency (firmDirect) or presume momentum (coach) before
                // the model has data to defend either. See
                // docs/products/life-clock/polish-2026-05-11-future-tab-v1.7.0-audit-followup.md
                // catch #2.
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
            Text(store.toneMode.futureSignedDelta(
                sign: sign,
                magnitude: magnitude,
                positive: delta >= 0
            ))
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
            Text(ReflectionPrompts.futureWarmingUpTransparency(
                daysOfData: daysOfData,
                tone: store.toneMode
            ))
            .font(.body)
            .foregroundStyle(.primary)
            .accessibilityIdentifier("future.warmingUp.line")
            if let baseline = store.profile?.baselineHealthspanYears {
                let projection = healthspanProjection(baseline: baseline)
                TrajectoryChart(
                    points: trajectoryPoints(baseline: baseline),
                    baseline: baseline,
                    clampState: projection.clamped,
                    isScrubbing: store.isProjectionScrubbing
                )
                FreeNarrativeLine(
                    perDimensionDelta: projection.perDimensionDelta,
                    aggregates: resolvedAggregatesForNarrative(),
                    tone: store.toneMode
                )
                sliderSection(baseline: baseline)
            }

        case .full14plus:
            if let baseline = store.profile?.baselineHealthspanYears {
                let projection = healthspanProjection(baseline: baseline)
                TrajectoryChart(
                    points: trajectoryPoints(baseline: baseline),
                    baseline: baseline,
                    clampState: projection.clamped,
                    isScrubbing: store.isProjectionScrubbing
                )
                FreeNarrativeLine(
                    perDimensionDelta: projection.perDimensionDelta,
                    aggregates: resolvedAggregatesForNarrative(),
                    tone: store.toneMode
                )
                sliderSection(baseline: baseline)
                if subscriptions.isPro {
                    longFormNarrativeSection(baseline: baseline)
                }
            }
        }
    }

    /// Resolved per-dim aggregates for the free narrative line. Reuses
    /// the scrub-start cache when active so the threshold descriptor
    /// updates smoothly during slider movement without re-aggregating
    /// the 14-day window on every `onChange`.
    private func resolvedAggregatesForNarrative() -> [HealthspanEngine.Dimension: Double] {
        let base = store.cachedBaselineAggregates
            ?? HealthspanEngine.aggregates(
                snapshots: store.recentSnapshots(limit: 14),
                habits: recentHabits()
            )
        return HealthspanEngine.resolvedAggregates(
            baseAggregates: base,
            overrides: store.sliderOverrides
        )
    }

    @ViewBuilder
    private func sliderSection(baseline: Double) -> some View {
        let aggregates = HealthspanEngine.aggregates(
            snapshots: store.recentSnapshots(limit: 14),
            habits: store.recentHabits(limit: 14)
        )
        WhatIfSlider(
            baseAggregates: aggregates,
            isPro: subscriptions.isPro,
            store: store,
            onLockedTap: {
                paywallScrollTarget = .whatIfSimulator
                paywallPresented = true
                TelemetryRecorder.shared.emit(.futureProPaywallPresented)
            }
        )
    }

    @ViewBuilder
    private func longFormNarrativeSection(baseline: Double) -> some View {
        let now = store.clock.now()
        let cal = store.clock.calendar
        // `weekEnd` is the most recent Sunday — the same date used in
        // the narrative subhead ("Reflection from Sunday, May 10").
        // "This week" is the 7 days ending at `weekEnd`; "prior week"
        // is the 7 days before that. The store's 14-day window covers
        // both buckets exactly.
        let weekEnd = now.snappedToLastSunday(calendar: cal)
        let weekStart = cal.date(byAdding: .day, value: -7, to: weekEnd) ?? weekEnd
        let priorWeekStart = cal.date(byAdding: .day, value: -14, to: weekEnd) ?? weekEnd
        let allSnaps = store.recentSnapshots(limit: 14)
        let allHabits = store.recentHabits(limit: 14)
        let thisWeekSnaps = allSnaps.filter { $0.date >= weekStart && $0.date < weekEnd }
        let priorWeekSnaps = allSnaps.filter { $0.date >= priorWeekStart && $0.date < weekStart }
        let thisWeekHabits = allHabits.filter { $0.date >= weekStart && $0.date < weekEnd }
        let priorWeekHabits = allHabits.filter { $0.date >= priorWeekStart && $0.date < weekStart }
        let currentAge = Double(AgeGate.ageInYears(
            birthDate: store.profile?.birthDate ?? Date.distantPast,
            asOf: now,
            calendar: cal
        ))
        let narrative = NarrativeEngine.compose(
            snapshots: thisWeekSnaps,
            priorWeekSnapshots: priorWeekSnaps,
            habits: thisWeekHabits,
            priorWeekHabits: priorWeekHabits,
            baseline: baseline,
            currentAge: currentAge,
            tone: store.toneMode,
            weekEnd: weekEnd,
            clock: store.clock
        )
        LongFormNarrative(narrative: narrative)
    }

    // MARK: - Helpers

    /// Live computed projection from raw HK snapshots + habits, with
    /// slider overrides applied when present.
    /// Recomputed every render — cheap for in-memory 14-day windows.
    private func healthspanProjection(baseline: Double) -> HealthspanEngine.Projection {
        // V1.7.0: LIFECLOCK_JUMP_TO=futureCapReached/futureFloorReached
        // forces the clamp state for agent-native fixture parity.
        // (Realistic v1 coefficients top out below cap; without this
        // override an agent can't land on the cap-reached UI for
        // snapshot testing.)
        if let forced = LifeClockLaunchConfiguration.current.effectiveForcedClampState {
            let cap = baseline + 14
            let floor = max(Double(AgeGate.ageInYears(
                birthDate: store.profile?.birthDate ?? Date.distantPast,
                asOf: store.clock.now(),
                calendar: store.clock.calendar
            )) + 1, 0)
            switch forced {
            case .cappedAt:
                return HealthspanEngine.Projection(
                    healthspanYears: cap,
                    confidence: 1.0,
                    perDimensionDelta: [:],
                    clamped: .cappedAt(cap)
                )
            case .flooredAt:
                return HealthspanEngine.Projection(
                    healthspanYears: floor,
                    confidence: 1.0,
                    perDimensionDelta: [:],
                    clamped: .flooredAt(floor)
                )
            case .nearCap, .none:
                break
            }
        }
        let snapshots = store.recentSnapshots(limit: 14)
        let habits = recentHabits()
        let currentAge = Double(AgeGate.ageInYears(
            birthDate: store.profile?.birthDate ?? Date.distantPast,
            asOf: store.clock.now(),
            calendar: store.clock.calendar
        ))
        if store.sliderOverrides.isEmpty {
            return HealthspanEngine.currentProjection(
                snapshots: snapshots,
                habits: habits,
                baseline: baseline,
                currentAge: currentAge,
                clock: store.clock
            )
        }
        // Reuse the scrub-start memoized aggregates when available
        // (avoids re-computing the 14-day rolling values on every
        // onChange tick during an active scrub). Falls back to a
        // live aggregate when no scrub is in flight.
        let aggregates = store.cachedBaselineAggregates
            ?? HealthspanEngine.aggregates(snapshots: snapshots, habits: habits)
        return HealthspanEngine.projectWith(
            baseAggregates: aggregates,
            overrides: store.sliderOverrides,
            baseline: baseline,
            currentAge: currentAge,
            confidence: HealthspanEngine.sampleDensity(snapshots: snapshots, habits: habits)
        )
    }

    /// Numeric projection in years for the headline.
    private func currentProjection(baseline: Double) -> Double {
        guard dayState != .day0, dayState != .coldLaunch1to3 else {
            return baseline
        }
        return healthspanProjection(baseline: baseline).healthspanYears
    }

    /// Build the 30-point trajectory for the chart.
    ///
    /// Passes the current slider overrides + memoized scrub-start
    /// aggregates so the chart's current/future points stay in lockstep
    /// with the headline projection during a Pro slider scrub.
    private func trajectoryPoints(baseline: Double) -> [TrajectoryPoint] {
        let snapshots = store.recentSnapshots(limit: 14)
        let habits = recentHabits()
        let currentAge = Double(AgeGate.ageInYears(
            birthDate: store.profile?.birthDate ?? Date.distantPast,
            asOf: store.clock.now(),
            calendar: store.clock.calendar
        ))
        return HealthspanEngine.weeklyTrajectory(
            snapshots: snapshots,
            habits: habits,
            baseline: baseline,
            currentAge: currentAge,
            overrides: store.sliderOverrides,
            baseAggregates: store.cachedBaselineAggregates,
            clock: store.clock
        )
    }

    private func recentHabits() -> [HabitLog] {
        store.recentHabits(limit: 14)
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
