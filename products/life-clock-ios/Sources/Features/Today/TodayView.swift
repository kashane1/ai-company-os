import SwiftUI

struct TodayView: View {
    @Environment(LifeClockStore.self) private var store

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: DesignTokens.Spacing.lg) {
                    headline
                    clockCard
                    driversCard
                    questsCard
                    DisclaimerBanner()
                }
                .padding(DesignTokens.Spacing.lg)
            }
            .navigationTitle(store.toneMode.todayHeadline)
        }
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

    private var clockCard: some View {
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

    private var driversCard: some View {
        VStack(alignment: .leading, spacing: DesignTokens.Spacing.sm) {
            Text("Top drivers today")
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
            }
        }
        .padding(DesignTokens.Spacing.md)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(DesignTokens.Palette.elevated, in: RoundedRectangle(cornerRadius: DesignTokens.Radius.md))
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
