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

    private static let freeRowLimit = 3
    private static let foggedPreviewRowCount = 6

    var body: some View {
        NavigationStack {
            ScrollView {
                // LazyVStack defers materialization of off-screen rows. With
                // 90 history rows this matters: VStack would build all 90
                // up front including their backgrounds + chevrons.
                LazyVStack(alignment: .leading, spacing: DesignTokens.Spacing.lg) {
                    // V1.7.0: install-summary section sits at the top of
                    // History. Cumulative since-install ledger. Fully
                    // free. See Future tab + History summary plan §Phase 1.
                    InstallSummarySection()
                    yesterdaySection
                    weeklySection
                    dailyHistorySection
                }
                .padding(DesignTokens.Spacing.lg)
                .readableColumn()
            }
            .navigationTitle("History")
            .accessibilityIdentifier("history.screen")
            .navigationDestination(for: DayDetailRoute.self) { route in
                DayDetailView(dayStart: route.dayStart)
            }
            .sheet(isPresented: $paywallPresented) {
                PaywallSheet()
                    .environment(subscriptions)
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
                    .headingLighting()
            }
            .sectionCard()
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
                .headingLighting()
            Text(store.toneMode.historyLongAbsenceBody)
                .font(.callout)
                .foregroundStyle(.secondary)
        }
        .sectionCard()
        .accessibilityIdentifier("history.longAbsence")
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
                    .headingLighting()
                if subscriptions.isPro {
                    importStatusBanner
                    ForEach(snapshots, id: \.date) { snapshot in
                        dayRow(snapshot)
                    }
                } else {
                    let visible = Array(snapshots.prefix(Self.freeRowLimit))
                    ForEach(visible, id: \.date) { snapshot in
                        dayRow(snapshot)
                    }
                    foggedPaywallStack(behind: Array(snapshots.dropFirst(Self.freeRowLimit)))
                }
            }
        } else if subscriptions.isPro {
            // First-run Pro user with no persisted history yet — surface
            // the import progress so they know the empty list is temporary.
            VStack(alignment: .leading, spacing: DesignTokens.Spacing.sm) {
                Text("Past days")
                    .font(.headline)
                    .headingLighting()
                importStatusBanner
                historyEmptyStateCard
            }
        } else {
            VStack(alignment: .leading, spacing: DesignTokens.Spacing.sm) {
                Text("Past days")
                    .font(.headline)
                    .headingLighting()
                historyEmptyStateCard
            }
        }
    }

    @ViewBuilder
    private func dayRow(_ snapshot: DailyHealthSnapshot) -> some View {
        let content = DayHistoryRowContent(
            snapshot: snapshot,
            deltaMinutes: store.dailyDelta(for: snapshot),
            isLocked: false
        )
        if subscriptions.isPro {
            NavigationLink(value: DayDetailRoute(dayStart: snapshot.date)) {
                content
            }
            .buttonStyle(.plain)
            .accessibilityIdentifier("history.row.pro")
        } else {
            // Free users get a read-only summary. Tapping nudges toward
            // the upgrade since per-day detail/editing is Pro-only.
            Button {
                paywallPresented = true
            } label: {
                content
            }
            .buttonStyle(.plain)
            .accessibilityIdentifier("history.row.locked")
        }
    }

    @ViewBuilder
    private var importStatusBanner: some View {
        switch store.historicalImporter.status {
        case .importing(let completed, let total):
            VStack(alignment: .leading, spacing: DesignTokens.Spacing.xs) {
                Text("More history is importing now, please wait…")
                    .font(.subheadline)
                HStack {
                    ProgressView(value: Double(completed), total: Double(total))
                    Text("\(completed)/\(total)")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                    Button("Cancel") { store.historicalImporter.cancel() }
                        .buttonStyle(.borderless)
                        .controlSize(.small)
                }
            }
            .sectionCard()
        case .finished, .idle, .cancelled, .failed:
            EmptyView()
        }
    }

    /// Foggy preview shown to free users below their unlocked rows. Real
    /// snapshot data (or a placeholder when none exists) is rendered behind
    /// an `.ultraThinMaterial` blur with an enticing CTA on top so users
    /// can see there's a lot more here without reading a number.
    private func foggedPaywallStack(behind locked: [DailyHealthSnapshot]) -> some View {
        let placeholders = makePlaceholderSnapshots(
            count: max(Self.foggedPreviewRowCount - locked.count, 0)
        )
        let preview = Array((locked + placeholders).prefix(Self.foggedPreviewRowCount))

        return ZStack {
            VStack(spacing: DesignTokens.Spacing.sm) {
                ForEach(preview, id: \.date) { snapshot in
                    DayHistoryRowContent(
                        snapshot: snapshot,
                        deltaMinutes: store.dailyDelta(for: snapshot)
                            ?? placeholderDelta(for: snapshot.date),
                        isLocked: false
                    )
                }
            }
            .accessibilityHidden(true)
            .allowsHitTesting(false)
            .blur(radius: 10)
            .overlay(
                RoundedRectangle(cornerRadius: DesignTokens.Radius.md)
                    .fill(.ultraThinMaterial)
            )
            .clipShape(RoundedRectangle(cornerRadius: DesignTokens.Radius.md))

            VStack(spacing: DesignTokens.Spacing.sm) {
                // Pro-gate glyph per paywall-spec.md § Visual-signal vocabulary.
                Image(systemName: "lock.fill")
                    .font(.title2)
                    .foregroundStyle(.tint)
                    .opacity(0.5)
                Text("Import all your historical health data as a Pro member")
                    .font(.headline)
                    .multilineTextAlignment(.center)
                    .headingLighting()
                Text("See every past day, spot the trends that shape your Life Clock, and adjust the values HealthKit gets wrong.")
                    .font(.callout)
                    .foregroundStyle(.secondary)
                    .multilineTextAlignment(.center)
                Button {
                    paywallPresented = true
                } label: {
                    Text("Unlock full history")
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, DesignTokens.Spacing.xs)
                }
                .buttonStyle(.borderedProminent)
                .padding(.top, DesignTokens.Spacing.xs)
                .accessibilityIdentifier("history.foggedUnlock")
            }
            .padding(DesignTokens.Spacing.md)
        }
    }

    private var historyEmptyStateCard: some View {
        // Empty state per `premium-feel-backlog-2026-05-12-standard.md`
        // Prompt 4: card-shaped, icon + tone-aware body. The body copy
        // is multi-state (5 health-data states); the icon is constant.
        VStack(spacing: 10) {
            Image(systemName: "calendar.badge.clock")
                .font(.system(size: 28, weight: .regular))
                .foregroundStyle(.secondary)
            Text(historyEmptyStateBody)
                .font(.callout)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
                .fixedSize(horizontal: false, vertical: true)
        }
        .sectionCard()
        .accessibilityIdentifier("history.emptyState")
    }

    private var historyEmptyStateBody: String {
        let variant: ToneMode.HistoryEmptyHealthState
        switch store.healthDataState {
        case .unavailable: variant = .unavailable
        case .awaitingAuthorization: variant = .awaitingAuthorization
        case .historicalOnly: variant = .historicalOnly
        case .noRecentData: variant = .noRecentData
        case .availableToday: variant = .availableToday
        }
        return store.toneMode.historyEmptyStateBody(for: variant)
    }

    /// When the free user has no real locked rows yet (new install, only
    /// a few days of data), synthesize plausible-looking rows behind the
    /// fog so the section reads as "lots more data exists" rather than
    /// "an empty blurred box". Values are stable per-day so the blur
    /// doesn't shimmer between renders.
    private func makePlaceholderSnapshots(count: Int) -> [DailyHealthSnapshot] {
        guard count > 0 else { return [] }
        let cal = Calendar.current
        let base = cal.startOfDay(for: Date())
        return (1...count).compactMap { offset in
            guard let date = cal.date(
                byAdding: .day,
                value: -(Self.freeRowLimit + offset),
                to: base
            ) else { return nil }
            let snapshot = DailyHealthSnapshot(date: date)
            // Plausible mid-range mock values; deterministic per-offset.
            snapshot.stepCount = 6500 + (offset * 137) % 4000
            snapshot.sleepHours = 6.5 + Double((offset * 13) % 20) / 10.0
            return snapshot
        }
    }

    private func placeholderDelta(for date: Date) -> Int {
        // Deterministic, signed, modest values — enough to render the
        // colored hero text behind the fog without claiming real numbers.
        let day = Calendar.current.component(.day, from: date)
        let raw = ((day * 17) % 90) - 45
        return raw
    }

    // MARK: - Weekly cards

    private var paywallTeaser: some View {
        VStack(alignment: .leading, spacing: DesignTokens.Spacing.sm) {
            Text("See what shaped this week")
                .font(.headline)
                .headingLighting()
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
            .accessibilityIdentifier("history.weeklyTeaserUnlock")
        }
        .sectionCard()
    }

    private func netCard(_ report: WeeklyReport) -> some View {
        VStack(alignment: .leading, spacing: DesignTokens.Spacing.xs) {
            Text(store.toneMode.historyWeeklyNetLabel).font(.subheadline).foregroundStyle(.secondary)
            Text(TimeDeltaFormatter.format(minutes: report.netTimeDeltaMinutes))
                .font(.system(size: 40, weight: .semibold, design: .rounded))
                .foregroundStyle(report.netTimeDeltaMinutes >= 0
                    ? DesignTokens.Palette.positive
                    : DesignTokens.Palette.negative)
                .headingLighting()
            if let confidence = Confidence(rawValue: report.confidenceRaw) {
                ConfidenceBadge(confidence: confidence)
            }
        }
        .sectionCard()
    }

    private func driversCard(_ report: WeeklyReport) -> some View {
        VStack(alignment: .leading, spacing: DesignTokens.Spacing.sm) {
            Text(store.toneMode.historyWeeklyDriversHeading)
                .font(.headline)
                .headingLighting()
            row(
                label: "Top positive",
                value: report.topPositiveDriver,
                emptyPlaceholder: store.toneMode.historyTopPositiveEmpty,
                color: DesignTokens.Palette.positive
            )
            row(
                label: "Top drag",
                value: report.topNegativeDriver,
                emptyPlaceholder: store.toneMode.historyTopDragEmpty,
                color: DesignTokens.Palette.negative
            )
        }
        .sectionCard()
    }

    private func leverCard(_ report: WeeklyReport) -> some View {
        VStack(alignment: .leading, spacing: DesignTokens.Spacing.xs) {
            Text(store.toneMode.historyNextLeverHeading)
                .font(.subheadline)
                .foregroundStyle(.secondary)
            Text(report.nextBestLever.capitalized)
                .font(.title3.bold())
                .headingLighting()
            Text(store.toneMode.historyNextLeverCaption)
                .font(.caption)
                .foregroundStyle(.secondary)
        }
        .sectionCard()
    }

    private func row(
        label: String,
        value: String,
        emptyPlaceholder: String,
        color: Color
    ) -> some View {
        let trimmed = value.trimmingCharacters(in: .whitespaces)
        let isEmpty = trimmed.isEmpty || trimmed == "—" || trimmed == "-"
        return HStack {
            Text(label).foregroundStyle(.secondary)
            Spacer()
            if isEmpty {
                Text(emptyPlaceholder).foregroundStyle(.secondary)
            } else {
                Text(value.capitalized).foregroundStyle(color)
            }
        }
        .font(.callout)
    }
}

/// Single past-day row content. Wrap in a Button or NavigationLink at the
/// call site — nesting a Button inside a NavigationLink breaks taps.
private struct DayHistoryRowContent: View {
    let snapshot: DailyHealthSnapshot
    let deltaMinutes: Int?
    let isLocked: Bool

    private var dateLabel: String {
        let formatter = DateFormatter()
        formatter.dateFormat = "EEE, MMM d"
        return formatter.string(from: snapshot.date)
    }

    private var summary: String {
        var parts: [String] = []
        if let steps = snapshot.stepCount { parts.append("\(steps) steps") }
        if let sleep = snapshot.sleepHours { parts.append(String(format: "%.1fh sleep", sleep)) }
        if parts.isEmpty { return "No Apple Health data" }
        return parts.joined(separator: " · ")
    }

    var body: some View {
        HStack(spacing: DesignTokens.Spacing.sm) {
            VStack(alignment: .leading, spacing: 2) {
                Text(dateLabel)
                    .font(.subheadline)
                Text(summary)
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
            Spacer()
            if let deltaMinutes {
                Text(TimeDeltaFormatter.format(minutes: deltaMinutes))
                    .font(.system(size: 22, weight: .semibold, design: .rounded))
                    .foregroundStyle(deltaMinutes >= 0
                        ? DesignTokens.Palette.positive
                        : DesignTokens.Palette.negative)
                    .lineLimit(1)
            }
            if snapshot.hasOverrides {
                Image(systemName: "pencil.circle.fill")
                    .foregroundStyle(.secondary)
                    .font(.caption)
            }
            if isLocked {
                // Pro-gate glyph per paywall-spec.md § Visual-signal vocabulary.
                Image(systemName: "lock.fill")
                    .foregroundStyle(.tint)
                    .opacity(0.5)
                    .font(.caption)
            } else {
                Image(systemName: "chevron.right")
                    .foregroundStyle(.secondary)
                    .font(.caption)
            }
        }
        .contentShape(Rectangle())
        .padding(.vertical, DesignTokens.Spacing.xs)
        .padding(.horizontal, DesignTokens.Spacing.sm)
        .background(
            DesignTokens.Palette.elevated.opacity(0.5),
            in: RoundedRectangle(cornerRadius: DesignTokens.Radius.sm)
        )
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
