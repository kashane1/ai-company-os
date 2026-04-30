import SwiftUI

struct WeeklyReportView: View {
    @Environment(LifeClockStore.self) private var store
    @Environment(SubscriptionStore.self) private var subscriptions
    @State private var paywallPresented: Bool = false

    // TODO(trend-vs-prior-week): once the user has ≥2 completed weeks of
    // persisted snapshots, render a "vs last week" delta inside the
    // netCard. Implementation outline:
    //   1. Add `LifeClockStore.previousWeekly: WeeklyReport?` populated by
    //      `clockEngine.calculateWeeklyTrend(snapshots: previous7,
    //      habits: previous7Habits, profile: profile)` where previous7 is
    //      `recentSnapshots(endingAt: 7-days-before-now, count: 7)`.
    //   2. In netCard, if previousWeekly is non-nil, show
    //      `report.netTimeDeltaMinutes - previousWeekly.netTimeDeltaMinutes`
    //      formatted via TimeDeltaFormatter as "vs last week" subtitle.
    //   3. Add a deterministic test that seeds two distinct weeks via
    //      MockHealthKitService(seed: ...) and asserts the comparison.
    // Deliberately not implemented yet — needs ≥2 weeks of real data to be
    // meaningful, and the audit explicitly defers this until TestFlight
    // beta produces it. Tracked in PHASE_STATUS.md "Gaps still open".

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: DesignTokens.Spacing.lg) {
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
                .padding(DesignTokens.Spacing.lg)
                .readableColumn()
            }
            .navigationTitle(store.toneMode.weeklyTitle)
            .sheet(isPresented: $paywallPresented) {
                PaywallSheet()
            }
        }
    }

    /// Free users see the net delta — the emotional hook stays free per
    /// MONETIZATION.md ("clock is the activation hook, weekly report is the
    /// retention hook"). Drivers + lever sit behind Pro.
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
        .background(DesignTokens.Palette.elevated, in: RoundedRectangle(cornerRadius: DesignTokens.Radius.md))
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
            Text("What shaped the week")
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
