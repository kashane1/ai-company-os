#if DEBUG
import SwiftUI

/// Research-only mockup for vision.md Open Question #7 — "Is there a *kind*
/// streak that survives a missed day without shame?"
///
/// Renders the current behavior plus three candidate treatments side-by-side
/// over a 10-day journey where day 4 and day 8 are missed. NONE of these
/// shipped — they exist so the operator can pick a direction. Reachable only
/// when launched with `LIFECLOCK_RESEARCH=kind-streak`.
struct KindStreakResearchView: View {
    /// Optional section selector. Set via `LIFECLOCK_RESEARCH_SECTION=baseline|a|b|c|all`.
    /// Lets each section render full-screen for clean per-option screenshots
    /// without scrolling. Default `all` shows the full document.
    private let section: String = ProcessInfo.processInfo.environment["LIFECLOCK_RESEARCH_SECTION"] ?? "all"

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: DesignTokens.Spacing.lg) {
                if section == "all" {
                    header
                    journeyHeader
                }

                if section == "all" || section == "baseline" {
                    sectionView(
                        title: "Baseline — current app",
                        blurb: "loggingDays goes to 0 if the gap exceeds 24h. Banner just disappears. No grace, no shame, no recognition of return.",
                        rows: BaselineRow.journey,
                        cell: { BaselineCell(row: $0) }
                    )
                }

                if section == "all" || section == "a" {
                    sectionView(
                        title: "Option A — No streak at all",
                        blurb: "Remove the streak banner entirely. Replace with a rolling \"X of last 7 days logged\" line on History only. Maximally anti-shame; loses the daily retention pull.",
                        rows: OptionARow.journey,
                        cell: { OptionACell(row: $0) }
                    )
                }

                if section == "all" || section == "b" {
                    sectionView(
                        title: "Option B — Rest-day grace",
                        blurb: "Streak survives ONE missed day per rolling 7 days, consumed silently as a built-in rest day. After a skip the banner reads \"{N}-day streak · 1 rest day used\". Two skips inside 7 days resets — but the reset copy is gentle.",
                        rows: OptionBRow.journey,
                        cell: { OptionBCell(row: $0) }
                    )
                }

                if section == "all" || section == "c" {
                    sectionView(
                        title: "Option C — Rolling rhythm",
                        blurb: "Replace the cumulative streak with a rolling \"{N} of last 7 days\" rhythm. A skip drops the count by 1 but the thread doesn't reset. Reads as a habit cadence rather than a fragile chain.",
                        rows: OptionCRow.journey,
                        cell: { OptionCCell(row: $0) }
                    )
                }

                if section == "all" {
                    summary
                }
            }
            .padding(DesignTokens.Spacing.lg)
            .frame(maxWidth: .infinity, alignment: .leading)
        }
        .background(DesignTokens.Palette.surface.ignoresSafeArea())
        .accessibilityIdentifier("research.kindStreak")
    }

    @ViewBuilder
    private func sectionView<Row, Cell: View>(
        title: String,
        blurb: String,
        rows: [Row],
        cell: @escaping (Row) -> Cell
    ) -> some View {
        section(title: title, blurb: blurb, rows: rows, cell: cell)
    }

    private var header: some View {
        VStack(alignment: .leading, spacing: DesignTokens.Spacing.xs) {
            Text("Research · Kind streak")
                .font(.caption.smallCaps())
                .foregroundStyle(.secondary)
            Text("vision.md Open Question #7")
                .font(.title2.bold())
            Text("Three treatments for surviving a missed day without shame.")
                .font(.callout)
                .foregroundStyle(.secondary)
        }
    }

    private var journeyHeader: some View {
        VStack(alignment: .leading, spacing: DesignTokens.Spacing.xs) {
            Text("Simulated journey")
                .font(.headline)
            Text("10 days. Day 4 and day 8 are missed (no diet log, app not opened).")
                .font(.footnote)
                .foregroundStyle(.secondary)
            JourneyDotsView()
        }
    }

    @ViewBuilder
    private func section<Row, Cell: View>(
        title: String,
        blurb: String,
        rows: [Row],
        @ViewBuilder cell: @escaping (Row) -> Cell
    ) -> some View {
        VStack(alignment: .leading, spacing: DesignTokens.Spacing.sm) {
            Text(title).font(.title3.bold())
            Text(blurb)
                .font(.footnote)
                .foregroundStyle(.secondary)
                .fixedSize(horizontal: false, vertical: true)
            VStack(spacing: DesignTokens.Spacing.sm) {
                ForEach(Array(rows.enumerated()), id: \.offset) { _, row in
                    cell(row)
                }
            }
        }
    }

    private var summary: some View {
        VStack(alignment: .leading, spacing: DesignTokens.Spacing.xs) {
            Text("Tradeoffs")
                .font(.headline)
            Group {
                Text("• A: kindest, weakest retention.")
                Text("• B: closest to a classic streak — adds a recoverable mechanic, still has a hard reset on the second miss.")
                Text("• C: replaces \"streak\" with a rhythm — no reset, no shame, but loses the dopamine of a rising number.")
            }
            .font(.footnote)
            .foregroundStyle(.secondary)
        }
        .padding(.top, DesignTokens.Spacing.md)
    }
}

// MARK: - Journey strip

private struct JourneyDotsView: View {
    var body: some View {
        HStack(spacing: 6) {
            ForEach(1...10, id: \.self) { day in
                let missed = (day == 4 || day == 8)
                VStack(spacing: 2) {
                    Circle()
                        .fill(missed ? Color.secondary.opacity(0.25) : DesignTokens.Palette.positive)
                        .frame(width: 14, height: 14)
                        .overlay(
                            Circle().stroke(missed ? Color.secondary : Color.clear, style: StrokeStyle(lineWidth: 1, dash: [2, 2]))
                        )
                    Text("\(day)").font(.caption2).foregroundStyle(.secondary)
                }
            }
        }
    }
}

// MARK: - Baseline (current app)

private struct BaselineRow {
    let day: Int
    let label: String
    let banner: BaselineBanner

    enum BaselineBanner {
        case streak(loggingDays: Int, goodDays: Int)
        case hidden
        case longAbsence
    }

    static let journey: [BaselineRow] = [
        .init(day: 3, label: "Day 3 — banner appears for first time", banner: .streak(loggingDays: 3, goodDays: 2)),
        .init(day: 5, label: "Day 5 — returning after missed day 4", banner: .hidden),
        .init(day: 7, label: "Day 7 — streak rebuilt to 3", banner: .streak(loggingDays: 3, goodDays: 3)),
        .init(day: 9, label: "Day 9 — returning after missed day 8", banner: .hidden),
        .init(day: 10, label: "Day 10 — only 2 days back", banner: .streak(loggingDays: 2, goodDays: 2))
    ]
}

private struct BaselineCell: View {
    let row: BaselineRow
    var body: some View {
        DayBlock(label: row.label) {
            switch row.banner {
            case .streak(let logging, let good):
                CurrentStreakBanner(loggingDays: logging, goodDays: good)
            case .hidden:
                EmptyBanner(text: "(no streak banner — current code zeros below 2 days)")
            case .longAbsence:
                LongAbsenceBanner()
            }
        }
    }
}

private struct CurrentStreakBanner: View {
    let loggingDays: Int
    let goodDays: Int
    var body: some View {
        HStack(spacing: DesignTokens.Spacing.sm) {
            Image(systemName: "flame.fill").foregroundStyle(.orange)
            VStack(alignment: .leading, spacing: 2) {
                Text("\(loggingDays)-day diet log streak").font(.callout.bold())
                if goodDays >= 2 {
                    Text("\(goodDays) of those great or okay")
                        .font(.caption).foregroundStyle(.secondary)
                } else {
                    Text("Logging is the win — quality follows.")
                        .font(.caption).foregroundStyle(.secondary)
                }
            }
            Spacer()
        }
        .padding(DesignTokens.Spacing.md)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(DesignTokens.Palette.elevated, in: RoundedRectangle(cornerRadius: DesignTokens.Radius.md))
    }
}

// MARK: - Option A — No streak

private struct OptionARow {
    let day: Int
    let label: String
    let weekly: Int

    static let journey: [OptionARow] = [
        .init(day: 3, label: "Day 3", weekly: 3),
        .init(day: 5, label: "Day 5 — after missed day 4", weekly: 4),
        .init(day: 9, label: "Day 9 — after missed day 8", weekly: 6),
        .init(day: 10, label: "Day 10", weekly: 7)
    ]
}

private struct OptionACell: View {
    let row: OptionARow
    var body: some View {
        DayBlock(label: row.label) {
            VStack(alignment: .leading, spacing: 4) {
                HStack {
                    Image(systemName: "checkmark.circle").foregroundStyle(DesignTokens.Palette.positive)
                    Text("\(row.weekly) of last 7 days logged").font(.callout)
                    Spacer()
                }
                Text("Surfaces in History only. Today screen is silent on streaks.")
                    .font(.caption2).foregroundStyle(.secondary)
            }
            .padding(DesignTokens.Spacing.md)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(DesignTokens.Palette.elevated, in: RoundedRectangle(cornerRadius: DesignTokens.Radius.md))
        }
    }
}

// MARK: - Option B — Rest-day grace

private struct OptionBRow {
    let day: Int
    let label: String
    let banner: OptionBBanner

    enum OptionBBanner {
        case streak(days: Int, restUsed: Bool)
        case freshStart(reason: String)
    }

    static let journey: [OptionBRow] = [
        .init(day: 3, label: "Day 3", banner: .streak(days: 3, restUsed: false)),
        .init(day: 5, label: "Day 5 — returning after missed day 4 (rest day consumed)", banner: .streak(days: 4, restUsed: true)),
        .init(day: 7, label: "Day 7", banner: .streak(days: 6, restUsed: true)),
        .init(day: 9, label: "Day 9 — returning after missed day 8 (second skip → fresh start)", banner: .freshStart(reason: "Fresh start. Day 1 of the next run.")),
        .init(day: 10, label: "Day 10", banner: .streak(days: 2, restUsed: false))
    ]
}

private struct OptionBCell: View {
    let row: OptionBRow
    var body: some View {
        DayBlock(label: row.label) {
            switch row.banner {
            case .streak(let days, let restUsed):
                HStack(spacing: DesignTokens.Spacing.sm) {
                    Image(systemName: "flame.fill").foregroundStyle(.orange)
                    VStack(alignment: .leading, spacing: 2) {
                        Text("\(days)-day streak").font(.callout.bold())
                        Text(restUsed ? "1 rest day used this week" : "Logging is the win — quality follows.")
                            .font(.caption).foregroundStyle(.secondary)
                    }
                    Spacer()
                    if restUsed {
                        Image(systemName: "moon.zzz.fill")
                            .foregroundStyle(.purple.opacity(0.7))
                            .accessibilityLabel("rest day used")
                    }
                }
                .padding(DesignTokens.Spacing.md)
                .frame(maxWidth: .infinity, alignment: .leading)
                .background(DesignTokens.Palette.elevated, in: RoundedRectangle(cornerRadius: DesignTokens.Radius.md))
            case .freshStart(let reason):
                HStack(spacing: DesignTokens.Spacing.sm) {
                    Image(systemName: "sun.horizon.fill").foregroundStyle(DesignTokens.Palette.positive)
                    VStack(alignment: .leading, spacing: 2) {
                        Text("Fresh start").font(.callout.bold())
                        Text(reason).font(.caption).foregroundStyle(.secondary)
                    }
                    Spacer()
                }
                .padding(DesignTokens.Spacing.md)
                .frame(maxWidth: .infinity, alignment: .leading)
                .background(DesignTokens.Palette.elevated, in: RoundedRectangle(cornerRadius: DesignTokens.Radius.md))
            }
        }
    }
}

// MARK: - Option C — Rolling rhythm

private struct OptionCRow {
    let day: Int
    let label: String
    let count: Int
    let total: Int = 7

    static let journey: [OptionCRow] = [
        .init(day: 3, label: "Day 3", count: 3),
        .init(day: 5, label: "Day 5 — after missed day 4", count: 4),
        .init(day: 7, label: "Day 7", count: 6),
        .init(day: 9, label: "Day 9 — after missed day 8", count: 6),
        .init(day: 10, label: "Day 10", count: 7)
    ]
}

private struct OptionCCell: View {
    let row: OptionCRow
    var body: some View {
        DayBlock(label: row.label) {
            HStack(spacing: DesignTokens.Spacing.md) {
                RhythmRingView(count: row.count, total: row.total)
                    .frame(width: 44, height: 44)
                VStack(alignment: .leading, spacing: 2) {
                    Text("\(row.count) of last 7 days").font(.callout.bold())
                    Text("Your weekly rhythm. No reset — just the rolling window.")
                        .font(.caption).foregroundStyle(.secondary)
                }
                Spacer()
            }
            .padding(DesignTokens.Spacing.md)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(DesignTokens.Palette.elevated, in: RoundedRectangle(cornerRadius: DesignTokens.Radius.md))
        }
    }
}

private struct RhythmRingView: View {
    let count: Int
    let total: Int
    var body: some View {
        ZStack {
            Circle()
                .stroke(DesignTokens.Palette.muted.opacity(0.2), lineWidth: 5)
            Circle()
                .trim(from: 0, to: CGFloat(count) / CGFloat(max(total, 1)))
                .stroke(DesignTokens.Palette.positive, style: StrokeStyle(lineWidth: 5, lineCap: .round))
                .rotationEffect(.degrees(-90))
            Text("\(count)/\(total)").font(.caption2.bold())
        }
    }
}

// MARK: - Shared cell scaffolding

private struct DayBlock<Content: View>: View {
    let label: String
    @ViewBuilder var content: () -> Content
    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            Text(label).font(.caption.smallCaps()).foregroundStyle(.secondary)
            content()
        }
    }
}

private struct EmptyBanner: View {
    let text: String
    var body: some View {
        Text(text)
            .font(.caption).italic().foregroundStyle(.secondary)
            .padding(.vertical, DesignTokens.Spacing.sm)
            .padding(.horizontal, DesignTokens.Spacing.md)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(
                RoundedRectangle(cornerRadius: DesignTokens.Radius.md)
                    .stroke(DesignTokens.Palette.muted.opacity(0.3), style: StrokeStyle(lineWidth: 1, dash: [4, 3]))
            )
    }
}

private struct LongAbsenceBanner: View {
    var body: some View {
        VStack(alignment: .leading, spacing: 2) {
            Text("Welcome back").font(.headline)
            Text("Time has kept moving. So can you.").font(.callout).foregroundStyle(.secondary)
        }
        .padding(DesignTokens.Spacing.md)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(DesignTokens.Palette.elevated, in: RoundedRectangle(cornerRadius: DesignTokens.Radius.md))
    }
}
#endif
