import Charts
import SwiftData
import SwiftUI

struct FishingStatsView: View {
    @Query(sort: \Trip.startAt, order: .reverse) private var trips: [Trip]
    @Query(sort: \CatchRecord.caughtAt, order: .reverse) private var catches: [CatchRecord]
    @Query(sort: \PersonalBest.updatedAt, order: .reverse) private var personalBests: [PersonalBest]

    private var stats: FishingStats {
        FishingStatsLogic.build(
            trips: trips,
            catches: catches,
            personalBests: personalBests
        )
    }

    var body: some View {
        Group {
            if stats.hasAnyData {
                ScrollView {
                    VStack(alignment: .leading, spacing: Spacing.xl) {
                        headlineSection(headline: stats.headline)
                        highlightsSection(activity: stats.activity)
                        monthlySection(months: stats.monthly)
                        topListSection(title: "Top Species", icon: "fish", entries: stats.species)
                        topListSection(title: "Top Lures & Baits", icon: "lasso.and.sparkles", entries: stats.lures)
                        topListSection(title: "Top Spots", icon: "mappin.and.ellipse", entries: stats.spots)
                        dispositionSection(disposition: stats.disposition)
                        timeOfDaySection(entries: stats.timeOfDay)
                    }
                    .padding(.horizontal)
                    .padding(.vertical, Spacing.lg)
                }
                .background(Color(.systemGroupedBackground))
            } else {
                emptyState
            }
        }
        .navigationTitle("Fishing Stats")
        .navigationBarTitleDisplayMode(.inline)
    }

    // MARK: - Sections

    @ViewBuilder
    private func headlineSection(headline: FishingStatsHeadline) -> some View {
        VStack(alignment: .leading, spacing: Spacing.sm) {
            StatsSectionHeader(title: "Overview")

            LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible())], spacing: Spacing.md) {
                StatTile(value: "\(headline.totalTrips)", label: "Trips", icon: "water.waves")
                StatTile(value: "\(headline.totalCatches)", label: "Catches", icon: "fish")
                StatTile(
                    value: formatDecimal(headline.catchesPerTrip, fractionDigits: 1),
                    label: "Avg per trip",
                    icon: "chart.bar.fill"
                )
                StatTile(
                    value: formatHours(headline.totalHoursFished),
                    label: "Hours fished",
                    icon: "clock"
                )
                StatTile(
                    value: "\(headline.skunkedTrips)",
                    label: headline.totalTrips > 0
                        ? "Skunked (\(Int((headline.skunkRate * 100).rounded()))%)"
                        : "Skunked",
                    icon: "face.dashed"
                )
                StatTile(
                    value: "\(headline.personalBestCount)",
                    label: headline.personalBestCount == 1 ? "Personal best" : "Personal bests",
                    icon: "trophy.fill"
                )
            }
        }
    }

    @ViewBuilder
    private func highlightsSection(activity: FishingStatsActivity) -> some View {
        VStack(alignment: .leading, spacing: Spacing.sm) {
            StatsSectionHeader(title: "Highlights")

            VStack(spacing: Spacing.md) {
                if let biggest = activity.biggestByWeight {
                    HighlightRow(
                        icon: "scalemass.fill",
                        title: "Heaviest",
                        primary: "\(formatDecimal(biggest.value, fractionDigits: 2)) kg",
                        secondary: biggest.species,
                        footer: AppFormatters.tripDate.string(from: biggest.caughtAt)
                    )
                }
                if let longest = activity.longestByLength {
                    HighlightRow(
                        icon: "ruler",
                        title: "Longest",
                        primary: "\(formatDecimal(longest.value, fractionDigits: 1)) cm",
                        secondary: longest.species,
                        footer: AppFormatters.tripDate.string(from: longest.caughtAt)
                    )
                }
                if activity.distinctSpecies > 0 {
                    HighlightRow(
                        icon: "chart.pie.fill",
                        title: "Distinct species",
                        primary: "\(activity.distinctSpecies)",
                        secondary: activity.distinctSpecies == 1 ? "species logged" : "species logged",
                        footer: nil
                    )
                }
                if let firstTripAt = activity.firstTripAt {
                    HighlightRow(
                        icon: "sparkles",
                        title: "First trip logged",
                        primary: AppFormatters.tripDate.string(from: firstTripAt),
                        secondary: nil,
                        footer: activity.lastTripAt.map { "Latest \(AppFormatters.tripDate.string(from: $0))" }
                    )
                }
            }
            .appCard(prominent: true)
        }
    }

    @ViewBuilder
    private func monthlySection(months: [FishingStatsMonthEntry]) -> some View {
        let hasData = months.contains(where: { $0.tripCount > 0 || $0.catchCount > 0 })
        if hasData {
            VStack(alignment: .leading, spacing: Spacing.sm) {
                StatsSectionHeader(title: "Last 12 Months")

                Chart {
                    ForEach(months) { month in
                        BarMark(
                            x: .value("Month", month.label),
                            y: .value("Catches", month.catchCount)
                        )
                        .foregroundStyle(Color.appAccent)
                        .annotation(position: .top) {
                            if month.catchCount > 0 {
                                Text("\(month.catchCount)")
                                    .font(.caption2.monospacedDigit())
                                    .foregroundStyle(.secondary)
                            }
                        }
                    }
                }
                .chartYAxis {
                    AxisMarks(position: .leading)
                }
                .frame(height: 180)
                .appCard(prominent: true)

                HStack {
                    Text("Catches per month")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                    Spacer()
                    Text("\(months.reduce(0) { $0 + $1.tripCount }) trips")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            }
        }
    }

    @ViewBuilder
    private func topListSection(title: String, icon: String, entries: [FishingStatsEntry]) -> some View {
        if !entries.isEmpty {
            let maxCount = entries.map(\.count).max() ?? 1
            VStack(alignment: .leading, spacing: Spacing.sm) {
                StatsSectionHeader(title: title, icon: icon)

                VStack(spacing: Spacing.sm) {
                    ForEach(entries) { entry in
                        TopEntryRow(entry: entry, maxCount: maxCount)
                    }
                }
                .appCard(prominent: true)
            }
        }
    }

    @ViewBuilder
    private func dispositionSection(disposition: FishingStatsDisposition) -> some View {
        if disposition.total > 0 {
            VStack(alignment: .leading, spacing: Spacing.sm) {
                StatsSectionHeader(title: "Disposition")

                VStack(alignment: .leading, spacing: Spacing.sm) {
                    DispositionBar(disposition: disposition)
                    DispositionLegendRow(color: .appAccent, label: "Released", count: disposition.released, total: disposition.total)
                    DispositionLegendRow(color: .appWarning, label: "Kept", count: disposition.kept, total: disposition.total)
                    if disposition.unknown > 0 {
                        DispositionLegendRow(
                            color: .secondary.opacity(0.5),
                            label: "Not recorded",
                            count: disposition.unknown,
                            total: disposition.total
                        )
                    }
                }
                .appCard(prominent: true)
            }
        }
    }

    @ViewBuilder
    private func timeOfDaySection(entries: [FishingStatsEntry]) -> some View {
        if !entries.isEmpty {
            VStack(alignment: .leading, spacing: Spacing.sm) {
                StatsSectionHeader(title: "Time of Day", icon: "sun.max.fill")

                Chart {
                    ForEach(entries) { entry in
                        BarMark(
                            x: .value("Window", entry.label),
                            y: .value("Catches", entry.count)
                        )
                        .foregroundStyle(Color.appAccent.gradient)
                    }
                }
                .frame(height: 160)
                .appCard(prominent: true)
            }
        }
    }

    @ViewBuilder
    private var emptyState: some View {
        VStack(spacing: Spacing.lg) {
            Image(systemName: "chart.bar.xaxis")
                .font(.system(size: 48))
                .foregroundStyle(.secondary)
            Text("No stats yet")
                .font(.title3.weight(.semibold))
            Text("Log a trip and a few catches to see your fishing stats appear here.")
                .font(.subheadline)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
                .padding(.horizontal, Spacing.xl)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .padding()
        .background(Color(.systemGroupedBackground))
    }

    // MARK: - Formatters

    private func formatDecimal(_ value: Double, fractionDigits: Int) -> String {
        let formatter = NumberFormatter()
        formatter.numberStyle = .decimal
        formatter.minimumFractionDigits = 0
        formatter.maximumFractionDigits = fractionDigits
        return formatter.string(from: NSNumber(value: value)) ?? "0"
    }

    private func formatHours(_ hours: Double) -> String {
        if hours < 1 {
            let minutes = Int((hours * 60).rounded())
            return "\(minutes)m"
        }
        return formatDecimal(hours, fractionDigits: 1) + "h"
    }
}

// MARK: - Building blocks

private struct StatsSectionHeader: View {
    let title: String
    var icon: String? = nil

    var body: some View {
        HStack(spacing: Spacing.xs) {
            if let icon {
                Image(systemName: icon)
                    .foregroundStyle(.appAccent)
                    .font(.footnote.weight(.semibold))
            }
            Text(title)
                .font(.footnote.weight(.semibold))
                .foregroundStyle(.secondary)
                .textCase(.uppercase)
        }
    }
}

private struct StatTile: View {
    let value: String
    let label: String
    let icon: String

    var body: some View {
        VStack(alignment: .leading, spacing: Spacing.xs) {
            Image(systemName: icon)
                .font(.footnote)
                .foregroundStyle(.appAccent)
            Text(value)
                .font(.title2.weight(.bold).monospacedDigit())
                .lineLimit(1)
                .minimumScaleFactor(0.6)
            Text(label)
                .font(.caption)
                .foregroundStyle(.secondary)
                .lineLimit(2)
                .fixedSize(horizontal: false, vertical: true)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(Spacing.md)
        .background(.background, in: RoundedRectangle(cornerRadius: 12, style: .continuous))
    }
}

private struct HighlightRow: View {
    let icon: String
    let title: String
    let primary: String
    let secondary: String?
    let footer: String?

    var body: some View {
        HStack(alignment: .top, spacing: Spacing.md) {
            Image(systemName: icon)
                .font(.title3)
                .foregroundStyle(.appAccent)
                .frame(width: 28)
            VStack(alignment: .leading, spacing: 2) {
                Text(title)
                    .font(.caption)
                    .foregroundStyle(.secondary)
                Text(primary)
                    .font(.headline.monospacedDigit())
                if let secondary {
                    Text(secondary)
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                }
                if let footer {
                    Text(footer)
                        .font(.caption)
                        .foregroundStyle(.tertiary)
                }
            }
            Spacer(minLength: 0)
        }
    }
}

private struct TopEntryRow: View {
    let entry: FishingStatsEntry
    let maxCount: Int

    private var fraction: CGFloat {
        guard maxCount > 0 else { return 0 }
        return CGFloat(entry.count) / CGFloat(maxCount)
    }

    var body: some View {
        VStack(alignment: .leading, spacing: Spacing.xxs) {
            HStack {
                Text(entry.label)
                    .font(.subheadline.weight(.medium))
                    .lineLimit(1)
                Spacer()
                Text("\(entry.count)")
                    .font(.subheadline.monospacedDigit())
                    .foregroundStyle(.secondary)
            }
            GeometryReader { proxy in
                ZStack(alignment: .leading) {
                    Capsule()
                        .fill(Color.appAccent.opacity(0.15))
                    Capsule()
                        .fill(Color.appAccent)
                        .frame(width: max(6, proxy.size.width * fraction))
                }
            }
            .frame(height: 6)
        }
    }
}

private struct DispositionBar: View {
    let disposition: FishingStatsDisposition

    var body: some View {
        GeometryReader { proxy in
            let total = max(disposition.total, 1)
            let released = proxy.size.width * CGFloat(disposition.released) / CGFloat(total)
            let kept = proxy.size.width * CGFloat(disposition.kept) / CGFloat(total)
            HStack(spacing: 0) {
                Rectangle().fill(Color.appAccent).frame(width: released)
                Rectangle().fill(Color.appWarning).frame(width: kept)
                Rectangle().fill(Color.secondary.opacity(0.25))
            }
            .clipShape(Capsule())
        }
        .frame(height: 12)
    }
}

private struct DispositionLegendRow: View {
    let color: Color
    let label: String
    let count: Int
    let total: Int

    private var percentText: String {
        guard total > 0 else { return "0%" }
        let pct = Int((Double(count) / Double(total) * 100).rounded())
        return "\(pct)%"
    }

    var body: some View {
        HStack(spacing: Spacing.sm) {
            Circle().fill(color).frame(width: 10, height: 10)
            Text(label)
                .font(.subheadline)
            Spacer()
            Text("\(count) · \(percentText)")
                .font(.subheadline.monospacedDigit())
                .foregroundStyle(.secondary)
        }
    }
}
