import SwiftUI

struct TodayView: View {
    @Environment(LifeClockStore.self) private var store
    @State private var quickLogPresented: Bool = false
    @State private var reflectionPresented: Bool = false

    var body: some View {
        NavigationStack {
            ScrollView {
                // 2026-05-01 IA refactor: Today is the daily ritual surface
                // (score → why → plan → reflection → check-in). Order is
                // deliberate; do not reshuffle without revisiting the
                // brainstorm in docs/plans/2026-05-01-refactor-life-clock-
                // tab-consolidation-plan.md.
                VStack(alignment: .leading, spacing: DesignTokens.Spacing.lg) {
                    headline
                    clockCard
                    if let moment = store.supportMoment {
                        supportMomentCard(moment)
                    }
                    driversCard
                    questsCard
                    ReflectionCard(onTap: { reflectionPresented = true })
                    quickLogCard
                    dietStreakBanner
                }
                .padding(DesignTokens.Spacing.lg)
                .readableColumn()
            }
            .navigationTitle(store.toneMode.todayHeadline)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button {
                        quickLogPresented = true
                    } label: {
                        Label("Check in", systemImage: "square.and.pencil")
                    }
                    .accessibilityIdentifier("today.checkInToolbar")
                }
            }
            .sheet(isPresented: $quickLogPresented) {
                QuickLogSheet()
            }
            .sheet(isPresented: $reflectionPresented) {
                let prompt = ReflectionPrompts.prompt(
                    for: store.clock.now(),
                    calendar: store.clock.calendar
                )
                ReflectionSheet(
                    prompt: prompt,
                    onDismiss: { reflectionPresented = false }
                )
            }
        }
    }

    private var quickLogCard: some View {
        Button {
            quickLogPresented = true
        } label: {
            HStack {
                Image(systemName: "square.and.pencil")
                VStack(alignment: .leading) {
                    Text(store.todayHabits == nil ? "Save today's check-in" : "Update today's check-in")
                        .font(.callout.bold())
                    Text("Fuel, extras, recovery, strength, nicotine. About 30 seconds.")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
                Spacer()
                Image(systemName: "chevron.right").foregroundStyle(.secondary)
            }
            .padding(DesignTokens.Spacing.md)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(DesignTokens.Palette.elevated, in: RoundedRectangle(cornerRadius: DesignTokens.Radius.md))
        }
        .buttonStyle(.plain)
        .accessibilityIdentifier("today.checkInCard")
    }

    private var headline: some View {
        Group {
            if let estimate = store.todayEstimate {
                let delta = estimate.dailyTimeDeltaMinutes
                let prefix = delta >= 0 ? store.toneMode.deltaPositivePrefix : store.toneMode.deltaNegativePrefix
                VStack(alignment: .leading, spacing: DesignTokens.Spacing.xs) {
                    Text("\(prefix) today")
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                    Text(TimeDeltaFormatter.format(minutes: delta))
                        .font(.system(size: 44, weight: .semibold, design: .rounded))
                        .foregroundStyle(delta >= 0 ? DesignTokens.Palette.positive : DesignTokens.Palette.negative)
                    if let confidence = Confidence(rawValue: estimate.confidenceRaw) {
                        ConfidenceBadge(confidence: confidence)
                    }
                }
            } else {
                Text("Loading…").foregroundStyle(.secondary)
            }
        }
        .accessibilityIdentifier("today.headline")
    }

    private func supportMomentCard(_ moment: SupportMoment) -> some View {
        SupportMomentCard(
            moment: moment,
            dismissAction: store.dismissSupportMoment
        )
        .accessibilityIdentifier("today.supportMoment")
    }

    /// "Projected healthspan + anchor date" card. Hidden entirely when
    /// `profile.hideClock` is true — replaced by the headline-only path
    /// (the "+X min today" delta still renders above). Resolves Q5 and is
    /// the centerpiece of the safety-net offering.
    @ViewBuilder
    private var clockCard: some View {
        if store.profile?.hideClock == true {
            EmptyView()
        } else {
            VStack(alignment: .leading, spacing: DesignTokens.Spacing.sm) {
                Text("Projected healthspan")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
                Text(store.todayEstimate.map { TimeDeltaFormatter.format(years: $0.projectedAgeYears) } ?? "—")
                    .font(.title.bold())
                if let projected = store.todayEstimate?.projectedDate {
                    Text("Reference date: \(projected.formatted(.dateTime.year().month().day()))")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            }
            .padding(DesignTokens.Spacing.md)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(DesignTokens.Palette.elevated, in: RoundedRectangle(cornerRadius: DesignTokens.Radius.md))
            .accessibilityIdentifier("today.healthspan")
        }
    }

    private var driversCard: some View {
        VStack(alignment: .leading, spacing: DesignTokens.Spacing.sm) {
            Text("Why it changed")
                .font(.headline)
            if store.todayDrivers.isEmpty {
                Text("No health data yet. Connect Apple Health or save a daily check-in to start seeing patterns.")
                    .font(.callout)
                    .foregroundStyle(.secondary)
            } else {
                Text(interpretationLine)
                    .font(.callout)
                    .foregroundStyle(.secondary)
                    .accessibilityIdentifier("today.drivers.interpretation")
                ForEach(Array(store.todayDrivers.prefix(3).enumerated()), id: \.element.id) { index, driver in
                    HStack {
                        Text(driver.title).lineLimit(1)
                        Spacer()
                        Text(TimeDeltaFormatter.format(minutes: driver.deltaMinutes))
                            .foregroundStyle(driver.deltaMinutes >= 0 ? DesignTokens.Palette.positive : DesignTokens.Palette.negative)
                    }
                    .font(.callout)
                    .accessibilityIdentifier("today.driver.\(driver.driverType)")
                    .accessibilityValue(TimeDeltaFormatter.format(minutes: driver.deltaMinutes))
                }
                if let dietHint = dietContextLine {
                    Text(dietHint)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            }
        }
        .padding(DesignTokens.Spacing.md)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(DesignTokens.Palette.elevated, in: RoundedRectangle(cornerRadius: DesignTokens.Radius.md))
        .accessibilityIdentifier("today.drivers")
    }

    /// One-line plain-language interpretation that frames the headline
    /// delta. Sits below "Why it changed" and above the driver list. Reads
    /// the headline delta sign + the top driver title (a primitive — keeps
    /// `ToneMode` SwiftData-free per its `import Foundation`-only boundary).
    private var interpretationLine: String {
        guard let estimate = store.todayEstimate else {
            return store.toneMode.todayInterpretationPreData()
        }
        let topTitle = store.todayDrivers.first?.title
        return estimate.dailyTimeDeltaMinutes >= 0
            ? store.toneMode.todayInterpretationPositive(driverTitle: topTitle)
            : store.toneMode.todayInterpretationNegative(driverTitle: topTitle)
    }

    /// A small streak chip when the user is on a diet-logging run. Only
    /// renders at >=2 days — a "1-day streak" isn't a streak yet. The
    /// good-day count appears as a secondary label when nonzero, which keeps
    /// honest "rough" logs from feeling punitive (logging streak still grows).
    @ViewBuilder
    private var dietStreakBanner: some View {
        let streaks = store.dietStreaks
        if streaks.loggingDays >= 2 {
            HStack(spacing: DesignTokens.Spacing.sm) {
                Image(systemName: "flame.fill")
                    .foregroundStyle(.orange)
                VStack(alignment: .leading, spacing: 2) {
                    Text("\(streaks.loggingDays)-day diet log streak")
                        .font(.callout.bold())
                    if streaks.goodDays >= 2 {
                        Text("\(streaks.goodDays) of those great or okay")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    } else {
                        Text("Logging is the win — quality follows.")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                }
                Spacer()
            }
            .padding(DesignTokens.Spacing.md)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(DesignTokens.Palette.elevated, in: RoundedRectangle(cornerRadius: DesignTokens.Radius.md))
            .accessibilityIdentifier("today.dietStreak")
            .accessibilityValue("\(streaks.loggingDays) days")
        } else {
            EmptyView()
        }
    }

    /// One soft, plain-language line about today's diet impact when relevant.
    /// Only fires when diet is actually a top driver — avoids "you ate badly"
    /// nagging on days the user didn't log.
    private var dietContextLine: String? {
        let dietDriver = store.todayDrivers.first { $0.driverType == "diet" }
        guard let dietDriver else { return nil }
        if dietDriver.deltaMinutes > 0 {
            return "Your meals supported today's progress."
        }
        return "A rough food day is feedback, not failure. One better meal can help tomorrow feel steadier."
    }

    private var questsCard: some View {
        VStack(alignment: .leading, spacing: DesignTokens.Spacing.sm) {
            Text("Today's Plan")
                .font(.headline)
            Text("One small thing to notice or do.")
                .font(.caption)
                .foregroundStyle(.secondary)
            ForEach(Array(store.todayQuests.enumerated()), id: \.element.id) { index, quest in
                Button {
                    store.toggleQuestCompletion(quest)
                } label: {
                    HStack(alignment: .top, spacing: DesignTokens.Spacing.sm) {
                        Image(systemName: quest.completedAt == nil ? "circle" : "checkmark.circle.fill")
                            .foregroundStyle(quest.completedAt == nil ? .secondary : DesignTokens.Palette.positive)
                        VStack(alignment: .leading, spacing: DesignTokens.Spacing.xs) {
                            Text(quest.title).font(.callout.bold())
                            Text(quest.detail).font(.caption).foregroundStyle(.secondary)
                        }
                    }
                }
                .buttonStyle(.plain)
                .accessibilityIdentifier("today.planAction.\(index)")
                // Carries the completion state into the a11y tree so
                // UITests can assert the toggle actually flipped, not
                // just that the button still exists. Tests read this
                // via XCUIElement.value.
                .accessibilityValue(quest.completedAt == nil ? "incomplete" : "complete")
            }
        }
        .padding(DesignTokens.Spacing.md)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(DesignTokens.Palette.elevated, in: RoundedRectangle(cornerRadius: DesignTokens.Radius.md))
        .accessibilityIdentifier("today.plan")
    }
}
