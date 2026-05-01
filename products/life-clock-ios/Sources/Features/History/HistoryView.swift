import SwiftUI

/// Replaces `WeeklyReportView` as the long-term home for reflection.
/// Layout:
///
/// - Yesterday card (when a persisted snapshot exists)
/// - This week's net + drivers (free shows net only; Pro sees drivers + lever)
/// - Daily history list:
///     * Free: last 7 days unblurred; days 8-90 rendered with real
///       scaffolding behind a `.ultraThinMaterial` blur with a paywall CTA.
///     * Pro: full 90-day list, each row tappable → `DayDetailView`.
///       Triggers a lazy 90-day historical HK import on first visit so
///       the list isn't empty for new Pro upgrades.
struct HistoryView: View {
    @Environment(LifeClockStore.self) private var store
    @Environment(SubscriptionStore.self) private var subscriptions
    @State private var paywallPresented: Bool = false

    private static let freeRowLimit = 7

    var body: some View {
        NavigationStack {
            ScrollView {
                // LazyVStack defers materialization of off-screen rows. With
                // 90 history rows this matters: VStack would build all 90
                // up front including their backgrounds + chevrons.
                LazyVStack(alignment: .leading, spacing: DesignTokens.Spacing.lg) {
                    yesterdaySection
                    weeklySection
                    dailyHistorySection
                }
                .padding(DesignTokens.Spacing.lg)
                .readableColumn()
            }
            .navigationTitle("History")
            .navigationDestination(for: DayDetailRoute.self) { route in
                DayDetailView(dayStart: route.dayStart)
            }
            .sheet(isPresented: $paywallPresented) {
                PaywallSheet()
            }
            .onAppear {
                // Pro: kick off a one-time 90-day backfill so drilldown
                // rows aren't empty right after upgrade. Idempotent.
                if subscriptions.isPro {
                    store.historicalImporter.startIfNeeded()
                }
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
        } else if hasOlderSnapshots {
            // No qualifying yesterday data, but the user does have history
            // — they were away. Show a supportive "welcome back" card
            // instead of leaving the top of History blank.
            longAbsenceCard
        }
    }

    /// True iff at least one persisted snapshot exists older than yesterday.
    /// Used to distinguish "first install" (suppress everything) from
    /// "returning user after an absence" (show the welcome-back card).
    private var hasOlderSnapshots: Bool {
        store.recentSnapshots(limit: 3).count >= 2
    }

    private var longAbsenceCard: some View {
        VStack(alignment: .leading, spacing: DesignTokens.Spacing.xs) {
            Text(store.toneMode.historyLongAbsenceHeading)
                .font(.headline)
            Text(store.toneMode.historyLongAbsenceBody)
                .font(.callout)
                .foregroundStyle(.secondary)
        }
        .padding(DesignTokens.Spacing.md)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(
            DesignTokens.Palette.elevated,
            in: RoundedRectangle(cornerRadius: DesignTokens.Radius.md)
        )
    }

    // MARK: - Weekly card (preserves WeeklyReportView semantics)

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

    // MARK: - Daily history list

    @ViewBuilder
    private var dailyHistorySection: some View {
        let snapshots = store.recentSnapshots(limit: HistoricalImportCoordinator.importWindowDays)
        if !snapshots.isEmpty {
            VStack(alignment: .leading, spacing: DesignTokens.Spacing.sm) {
                Text("Past days")
                    .font(.headline)
                ForEach(Array(snapshots.enumerated()), id: \.element.date) { (index, snapshot) in
                    dayRow(snapshot, index: index)
                }
                if !subscriptions.isPro && snapshots.count > Self.freeRowLimit {
                    historyPaywallTeaser
                }
                if subscriptions.isPro {
                    importStatusBanner
                }
            }
        }
    }

    @ViewBuilder
    private func dayRow(_ snapshot: DailyHealthSnapshot, index: Int) -> some View {
        let isLocked = !subscriptions.isPro && index >= Self.freeRowLimit
        let row = DayHistoryRow(
            snapshot: snapshot,
            isLocked: isLocked,
            onTap: {
                if isLocked {
                    paywallPresented = true
                }
            }
        )
        if subscriptions.isPro {
            NavigationLink(value: DayDetailRoute(dayStart: snapshot.date)) {
                row
            }
            .buttonStyle(.plain)
        } else {
            row
        }
    }

    @ViewBuilder
    private var importStatusBanner: some View {
        switch store.historicalImporter.status {
        case .importing(let completed, let total):
            HStack {
                ProgressView(value: Double(completed), total: Double(total))
                Text("\(completed)/\(total)")
                    .font(.caption)
                    .foregroundStyle(.secondary)
                Button("Cancel") { store.historicalImporter.cancel() }
                    .buttonStyle(.borderless)
                    .controlSize(.small)
            }
            .padding(DesignTokens.Spacing.xs)
        case .finished, .idle, .cancelled, .failed:
            EmptyView()
        }
    }

    private var historyPaywallTeaser: some View {
        VStack(alignment: .leading, spacing: DesignTokens.Spacing.sm) {
            Text("See the last 90 days")
                .font(.headline)
            Text("Pro unlocks the full daily history and lets you adjust HealthKit values that don't reflect what really happened.")
                .font(.callout)
                .foregroundStyle(.secondary)
            Button {
                paywallPresented = true
            } label: {
                Text("See full history")
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

    // MARK: - Weekly cards

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

/// Single past-day row. Shows date + summary, blurs values when locked.
private struct DayHistoryRow: View {
    let snapshot: DailyHealthSnapshot
    let isLocked: Bool
    let onTap: () -> Void

    private var dateLabel: String {
        let formatter = DateFormatter()
        formatter.dateFormat = "EEE, MMM d"
        return formatter.string(from: snapshot.date)
    }

    private var summary: String {
        var parts: [String] = []
        if let steps = snapshot.stepCount { parts.append("\(steps) steps") }
        if let sleep = snapshot.sleepHours { parts.append(String(format: "%.1fh sleep", sleep)) }
        if parts.isEmpty { return "No data" }
        return parts.joined(separator: " · ")
    }

    var body: some View {
        Button(action: onTap) {
            HStack {
                VStack(alignment: .leading, spacing: 2) {
                    Text(dateLabel)
                        .font(.subheadline)
                    Text(summary)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
                Spacer()
                if snapshot.hasOverrides {
                    Image(systemName: "pencil.circle.fill")
                        .foregroundStyle(.secondary)
                        .font(.caption)
                }
                if isLocked {
                    Image(systemName: "lock.fill")
                        .foregroundStyle(.secondary)
                        .font(.caption)
                } else {
                    Image(systemName: "chevron.right")
                        .foregroundStyle(.secondary)
                        .font(.caption)
                }
            }
            .padding(.vertical, DesignTokens.Spacing.xs)
            .padding(.horizontal, DesignTokens.Spacing.sm)
            .background(
                DesignTokens.Palette.elevated.opacity(0.5),
                in: RoundedRectangle(cornerRadius: DesignTokens.Radius.sm)
            )
        }
        .buttonStyle(.plain)
        // Opacity + lock chip rather than blur. Blur (even one
        // ultraThinMaterial overlay) costs ~3-5ms/frame on iPhone 12 and
        // accumulates with row count. Opacity is free on the GPU and
        // reads as locked thanks to the lock icon already in the row.
        .opacity(isLocked ? 0.35 : 1.0)
    }
}

private struct DayDetailRoute: Hashable {
    let dayStart: Date
}
