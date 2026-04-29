import SwiftUI

struct TodayView: View {
    @Environment(LifeClockStore.self) private var store
    @State private var quickLogPresented: Bool = false

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: DesignTokens.Spacing.lg) {
                    headline
                    dietStreakBanner
                    clockCard
                    driversCard
                    quickLogCard
                    questsCard
                    DisclaimerBanner()
                }
                .padding(DesignTokens.Spacing.lg)
            }
            .navigationTitle(store.toneMode.todayHeadline)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button {
                        quickLogPresented = true
                    } label: {
                        Label("Quick log", systemImage: "square.and.pencil")
                    }
                }
            }
            .sheet(isPresented: $quickLogPresented) {
                QuickLogSheet()
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
                    Text(store.todayHabits == nil ? "Log today's habits" : "Update today's habits")
                        .font(.callout.bold())
                    Text("Alcohol, smoking, diet, stress, strength — 30 seconds.")
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
                    Text("Anchor date: \(projected.formatted(.dateTime.year().month().day()))")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            }
            .padding(DesignTokens.Spacing.md)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(DesignTokens.Palette.elevated, in: RoundedRectangle(cornerRadius: DesignTokens.Radius.md))
        }
    }

    private var driversCard: some View {
        VStack(alignment: .leading, spacing: DesignTokens.Spacing.sm) {
            Text("What moved your clock today")
                .font(.headline)
            if store.todayDrivers.isEmpty {
                Text("No data yet — check back tomorrow.")
                    .font(.callout)
                    .foregroundStyle(.secondary)
            } else {
                ForEach(store.todayDrivers.prefix(3), id: \.id) { driver in
                    HStack {
                        Text(driver.title).lineLimit(1)
                        Spacer()
                        Text(TimeDeltaFormatter.format(minutes: driver.deltaMinutes))
                            .foregroundStyle(driver.deltaMinutes >= 0 ? DesignTokens.Palette.positive : DesignTokens.Palette.negative)
                    }
                    .font(.callout)
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
            return "Your meals helped your clock today."
        }
        return "A rough food day is feedback, not failure. One better meal can move tomorrow back."
    }

    private var questsCard: some View {
        VStack(alignment: .leading, spacing: DesignTokens.Spacing.sm) {
            Text("Today's quests")
                .font(.headline)
            ForEach(store.todayQuests, id: \.id) { quest in
                HStack(alignment: .top) {
                    Image(systemName: quest.completedAt == nil ? "circle" : "checkmark.circle.fill")
                        .foregroundStyle(quest.completedAt == nil ? .secondary : DesignTokens.Palette.positive)
                    VStack(alignment: .leading) {
                        Text(quest.title).font(.callout.bold())
                        Text(quest.detail).font(.caption).foregroundStyle(.secondary)
                    }
                }
                .contentShape(Rectangle())
                .onTapGesture { store.toggleQuestCompletion(quest) }
            }
        }
        .padding(DesignTokens.Spacing.md)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(DesignTokens.Palette.elevated, in: RoundedRectangle(cornerRadius: DesignTokens.Radius.md))
    }
}
