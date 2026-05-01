import SwiftUI

/// Replaces `WeeklyReportView` as the long-term home for reflection: shows
/// the most recent Yesterday Wrap-Up summary card at the top (when a recent
/// snapshot exists) followed by the existing weekly report content.
///
/// The richer 90-day archive, day-detail drilldown, override editor, and
/// Pro/free blur affordances called for in the History plan are deferred
/// to a follow-up PR; this view ships the minimum surface that makes the
/// renamed tab coherent on its own.
struct HistoryView: View {
    @Environment(LifeClockStore.self) private var store
    @Environment(SubscriptionStore.self) private var subscriptions
    @State private var paywallPresented: Bool = false

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: DesignTokens.Spacing.lg) {
                    yesterdaySection
                    weeklySection
                }
                .padding(DesignTokens.Spacing.lg)
                .readableColumn()
            }
            .navigationTitle("History")
            .sheet(isPresented: $paywallPresented) {
                PaywallSheet()
            }
        }
    }

    // MARK: - Yesterday card

    @ViewBuilder
    private var yesterdaySection: some View {
        if let yesterdayDelta = store.yesterdayDeltaMinutes {
            VStack(alignment: .leading, spacing: DesignTokens.Spacing.xs) {
                Text(store.toneMode.yesterdayWrapUpHeading)
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
                Text(TimeDeltaFormatter.format(minutes: yesterdayDelta))
                    .font(.system(size: 36, weight: .semibold, design: .rounded))
                    .foregroundStyle(yesterdayDelta >= 0
                        ? DesignTokens.Palette.positive
                        : DesignTokens.Palette.negative)
            }
            .padding(DesignTokens.Spacing.md)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(
                DesignTokens.Palette.elevated,
                in: RoundedRectangle(cornerRadius: DesignTokens.Radius.md)
            )
        }
    }

    // MARK: - Weekly card (preserves existing WeeklyReportView semantics)

    @ViewBuilder
    private var weeklySection: some View {
        if let report = store.weekly {
            netCard(report)
            if subscriptions.isPro {
                driversCard(report)
                leverCard(report)
            } else {
                paywallTeaser
            }
        } else {
            Text(store.toneMode.weeklyEmptyState)
                .foregroundStyle(.secondary)
        }
    }

    private var paywallTeaser: some View {
        VStack(alignment: .leading, spacing: DesignTokens.Spacing.sm) {
            Text("See what shaped this week")
                .font(.headline)
            Text("Pro unlocks the full weekly breakdown, your strongest supportive trend, and the next habit to focus on.")
                .font(.callout)
                .foregroundStyle(.secondary)
            Button {
                paywallPresented = true
            } label: {
                Text("See full week")
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, DesignTokens.Spacing.xs)
            }
            .buttonStyle(.borderedProminent)
        }
        .padding(DesignTokens.Spacing.md)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(
            DesignTokens.Palette.elevated,
            in: RoundedRectangle(cornerRadius: DesignTokens.Radius.md)
        )
    }

    private func netCard(_ report: WeeklyReport) -> some View {
        VStack(alignment: .leading, spacing: DesignTokens.Spacing.xs) {
            Text("Net this week").font(.subheadline).foregroundStyle(.secondary)
            Text(TimeDeltaFormatter.format(minutes: report.netTimeDeltaMinutes))
                .font(.system(size: 40, weight: .semibold, design: .rounded))
                .foregroundStyle(report.netTimeDeltaMinutes >= 0
                    ? DesignTokens.Palette.positive
                    : DesignTokens.Palette.negative)
            if let confidence = Confidence(rawValue: report.confidenceRaw) {
                ConfidenceBadge(confidence: confidence)
            }
        }
        .padding(DesignTokens.Spacing.md)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(
            DesignTokens.Palette.elevated,
            in: RoundedRectangle(cornerRadius: DesignTokens.Radius.md)
        )
    }

    private func driversCard(_ report: WeeklyReport) -> some View {
        VStack(alignment: .leading, spacing: DesignTokens.Spacing.sm) {
            Text("What shaped the week")
                .font(.headline)
            row(label: "Top positive", value: report.topPositiveDriver, color: DesignTokens.Palette.positive)
            row(label: "Top drag", value: report.topNegativeDriver, color: DesignTokens.Palette.negative)
        }
        .padding(DesignTokens.Spacing.md)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(
            DesignTokens.Palette.elevated,
            in: RoundedRectangle(cornerRadius: DesignTokens.Radius.md)
        )
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
        .background(
            DesignTokens.Palette.elevated,
            in: RoundedRectangle(cornerRadius: DesignTokens.Radius.md)
        )
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
