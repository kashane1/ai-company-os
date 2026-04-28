import SwiftUI

struct WeeklyReportView: View {
    @Environment(LifeClockStore.self) private var store

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: DesignTokens.Spacing.lg) {
                    if let report = store.weekly {
                        netCard(report)
                        driversCard(report)
                        leverCard(report)
                    } else {
                        Text("Weekly report will appear after a week of data.")
                            .foregroundStyle(.secondary)
                    }
                    DisclaimerBanner()
                }
                .padding(DesignTokens.Spacing.lg)
            }
            .navigationTitle("Weekly")
        }
    }

    private func netCard(_ report: WeeklyReport) -> some View {
        VStack(alignment: .leading, spacing: DesignTokens.Spacing.xs) {
            Text("Net this week").font(.subheadline).foregroundStyle(.secondary)
            Text(TimeDeltaFormatter.format(minutes: report.netTimeDeltaMinutes))
                .font(.system(size: 40, weight: .semibold, design: .rounded))
                .foregroundStyle(report.netTimeDeltaMinutes >= 0 ? DesignTokens.Palette.positive : DesignTokens.Palette.negative)
            if let confidence = Confidence(rawValue: report.confidenceRaw) {
                ConfidenceBadge(confidence: confidence)
            }
        }
        .padding(DesignTokens.Spacing.md)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(DesignTokens.Palette.elevated, in: RoundedRectangle(cornerRadius: DesignTokens.Radius.md))
    }

    private func driversCard(_ report: WeeklyReport) -> some View {
        VStack(alignment: .leading, spacing: DesignTokens.Spacing.sm) {
            Text("What moved the clock")
                .font(.headline)
            row(label: "Top positive", value: report.topPositiveDriver, color: DesignTokens.Palette.positive)
            row(label: "Top drag", value: report.topNegativeDriver, color: DesignTokens.Palette.negative)
        }
        .padding(DesignTokens.Spacing.md)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(DesignTokens.Palette.elevated, in: RoundedRectangle(cornerRadius: DesignTokens.Radius.md))
    }

    private func leverCard(_ report: WeeklyReport) -> some View {
        VStack(alignment: .leading, spacing: DesignTokens.Spacing.xs) {
            Text("Next best lever")
                .font(.subheadline)
                .foregroundStyle(.secondary)
            Text(report.nextBestLever.capitalized)
                .font(.title3.bold())
            Text("Small, repeatable wins compound. Don't try to fix everything.")
                .font(.caption)
                .foregroundStyle(.secondary)
        }
        .padding(DesignTokens.Spacing.md)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(DesignTokens.Palette.elevated, in: RoundedRectangle(cornerRadius: DesignTokens.Radius.md))
    }

    private func row(label: String, value: String, color: Color) -> some View {
        HStack {
            Text(label).foregroundStyle(.secondary)
            Spacer()
            Text(value.capitalized).foregroundStyle(color)
        }
        .font(.callout)
    }
}
