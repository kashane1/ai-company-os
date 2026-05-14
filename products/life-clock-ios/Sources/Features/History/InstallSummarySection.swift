import SwiftUI

/// Top-of-History install-summary section. Free for everyone.
///
/// V1.7.0 — Future tab + History summary plan §Phase 1. Cumulative
/// since-install ledger: hero number + rules-based narrative + top-3
/// contributors panel (Day 7+). All copy tone-conditional.
///
/// Day-state machine:
///   day0       — `Your ledger starts today. Check back tomorrow.`
///   day1to6    — hero + narrative; contributors panel hidden
///   day7Plus   — hero + narrative + top-3 contributors panel
///   noSignal   — Day 7+ but <3 days of HK/QuickLog data (HK denied
///                entire week typically); hero replaced with the
///                no-signal copy.
struct InstallSummarySection: View {
    @Environment(LifeClockStore.self) private var store

    var body: some View {
        if let summary = store.cumulativeDeltaSinceInstall() {
            content(for: summary)
                .onAppear {
                    TelemetryRecorder.shared.emit(.historySummaryViewed)
                }
        } else {
            EmptyView()
        }
    }

    @ViewBuilder
    private func content(for summary: CumulativeSummary) -> some View {
        VStack(alignment: .leading, spacing: DesignTokens.Spacing.sm) {
            switch dayState(for: summary) {
            case .day0:
                day0Hero
            case .day1to6:
                heroNumber(for: summary)
                narrativeLine(for: summary)
            case .day7PlusNoSignal:
                noSignalHero
            case .day7Plus:
                heroNumber(for: summary)
                narrativeLine(for: summary)
                contributorsPanel(for: summary)
            }
        }
        .sectionCard()
        .accessibilityElement(children: .contain)
        .accessibilityIdentifier("history.installSummary")
    }

    // MARK: - Day state

    private enum DayState {
        case day0
        case day1to6
        case day7PlusNoSignal
        case day7Plus
    }

    private func dayState(for summary: CumulativeSummary) -> DayState {
        if summary.daysSinceInstall == 0 { return .day0 }
        if summary.daysSinceInstall < 7 { return .day1to6 }
        if summary.snapshotsWithData < 3 { return .day7PlusNoSignal }
        return .day7Plus
    }

    // MARK: - Day 0

    private var day0Hero: some View {
        Text(store.toneMode.historySummaryDay0Hero)
            .font(.headline)
            .accessibilityIdentifier("history.installSummary.day0")
    }

    // MARK: - No signal yet

    private var noSignalHero: some View {
        Text(store.toneMode.historySummaryNoSignal)
            .font(.headline)
            .accessibilityIdentifier("history.installSummary.noSignal")
    }

    // MARK: - Hero number

    private func heroNumber(for summary: CumulativeSummary) -> some View {
        let formatted = formatDaysHours(summary.totalDeltaMinutes)
        let sign = summary.totalDeltaMinutes >= 0 ? "+" : "−"
        let anchor = anchorText(for: summary)
        let prefix = store.toneMode.historySummaryAnchorPrefix(
            positive: summary.totalDeltaMinutes >= 0
        )

        return VStack(alignment: .leading, spacing: DesignTokens.Spacing.xs) {
            ViewThatFits(in: .horizontal) {
                Text("\(sign)\(formatted)")
                    .font(.system(size: 36, weight: .semibold, design: .rounded))
                Text("\(sign)\(formatted)")
                    .font(.system(size: 28, weight: .semibold, design: .rounded))
                Text("\(sign)\(formatted)")
                    .font(.system(size: 22, weight: .semibold, design: .rounded))
            }
            // Same neutral foreground for ± per the plan / SpecFlow gap
            // #14. Tone copy carries valence.

            Text("\(prefix) \(anchor)")
                .font(.subheadline)
                .foregroundStyle(.secondary)
        }
        .accessibilityIdentifier("history.installSummary.hero")
    }

    private func anchorText(for summary: CumulativeSummary) -> String {
        // 3-year truncation affordance: when the cache window starts
        // later than the install date, surface the year rather than
        // a misleadingly recent "since Month Day".
        let formatter = DateFormatter()
        if summary.truncatedTo3Years {
            formatter.setLocalizedDateFormatFromTemplate("y")
            return formatter.string(from: summary.windowStart)
        }
        formatter.setLocalizedDateFormatFromTemplate("MMM d")
        return formatter.string(from: summary.windowStart)
    }

    /// Days + hours formatter. `+14d 6h` / `−3d 8h` / `+4h`. Per the
    /// cross-screen time-unit convention (plan §Phase 4): History
    /// summary uses days+hours for the medium horizon.
    private func formatDaysHours(_ minutes: Int) -> String {
        let abs = Swift.abs(minutes)
        let days = abs / (60 * 24)
        let hoursRemainder = (abs % (60 * 24)) / 60
        if days == 0 {
            if hoursRemainder == 0 {
                let mins = abs % 60
                return "\(mins)m"
            }
            return "\(hoursRemainder)h"
        }
        if hoursRemainder == 0 { return "\(days)d" }
        return "\(days)d \(hoursRemainder)h"
    }

    // MARK: - Narrative

    @ViewBuilder
    private func narrativeLine(for summary: CumulativeSummary) -> some View {
        if let line = composedNarrative(for: summary) {
            Text(line)
                .font(.body)
                .foregroundStyle(.secondary)
                .accessibilityIdentifier("history.installSummary.narrative")
        }
    }

    /// Rules-based one-line narrative referencing the strongest
    /// contributor. Returns nil when there's no contributor to cite.
    private func composedNarrative(for summary: CumulativeSummary) -> String? {
        guard let top = summary.topContributors.first else { return nil }
        let dimDisplay = displayName(top.dimension)
        let tone = store.toneMode
        let positiveLever = top.netDeltaMinutes >= 0
        switch tone {
        case .gentle:
            return positiveLever
                ? "\(dimDisplay) has been quietly carrying you across these days."
                : "\(dimDisplay) has been a quiet drag — the lever's there when you're ready."
        case .coach:
            return positiveLever
                ? "\(dimDisplay) is your strongest lever across this window."
                : "\(dimDisplay) is the drag pulling against you."
        case .firmDirect:
            return positiveLever
                ? "\(dimDisplay): top lever."
                : "\(dimDisplay): heaviest drag."
        }
    }

    // MARK: - Top-3 contributors

    @ViewBuilder
    private func contributorsPanel(for summary: CumulativeSummary) -> some View {
        if !summary.topContributors.isEmpty {
            Divider().padding(.vertical, DesignTokens.Spacing.xs)
            Text(store.toneMode.historyTopContributorsHeading)
                .font(.subheadline)
                .foregroundStyle(.secondary)
                .accessibilityIdentifier("history.installSummary.contributorsHeading")
            VStack(alignment: .leading, spacing: DesignTokens.Spacing.xs) {
                ForEach(Array(summary.topContributors.enumerated()), id: \.offset) { _, contributor in
                    contributorRow(contributor)
                }
            }
            .accessibilityIdentifier("history.installSummary.contributorsList")
        }
    }

    private func contributorRow(_ contributor: CumulativeContributor) -> some View {
        HStack {
            Text(displayName(contributor.dimension))
                .font(.subheadline)
            Spacer()
            Text(formatDaysHoursSigned(contributor.netDeltaMinutes))
                .font(.subheadline.monospacedDigit())
                .foregroundStyle(.secondary)
        }
    }

    /// Signed days+hours. `+12h` / `−1d 4h`. Always shows a sign so
    /// the panel is scannable.
    private func formatDaysHoursSigned(_ minutes: Int) -> String {
        let sign = minutes >= 0 ? "+" : "−"
        return "\(sign)\(formatDaysHours(minutes))"
    }

    private func displayName(_ dimension: CumulativeContributor.Dimension) -> String {
        switch dimension {
        case .sleep: return "Sleep"
        case .movement: return "Steps"
        case .exercise: return "Exercise"
        case .diet: return "Whole food"
        case .alcohol: return "Extras"
        case .smoking: return "Nicotine"
        case .strength: return "Strength"
        case .other: return "Other"
        }
    }
}
