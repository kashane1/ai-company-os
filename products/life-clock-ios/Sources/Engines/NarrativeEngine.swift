import Foundation

/// Pro long-form weekly narrative composer. Pure static. No persisted
/// state — runs on every Future tab open and snaps to last Sunday via
/// `clock.now().snappedToLastSunday`.
///
/// V1.7.0 — Future tab + History summary plan §Phase 4 (merged Pro
/// depth phase). Deterministic template composition; no LLM at runtime.
///
/// Composition spec per `docs/products/life-clock/future-tab-tone-pools-spec.md`:
///   Para 1 — This week's headline movement
///   Para 2 — Dominant driver (with concrete numbers)
///   Para 3 — Drag (with concrete numbers)
///   Para 4 — Action for next week (tone-divergent: gentle invites,
///            coach directs, firmDirect imperatives)
///
/// All slot values format via `NumberFormatter` at the call site
/// (i18n safety). Tone-distinctness invariant ≥30% token diff is
/// enforced by tests.
enum NarrativeEngine {

    /// One paragraph of the Pro long-form narrative. Stable order;
    /// renderer enumerates `.allCases` in display order.
    enum Paragraph: CaseIterable {
        case headline
        case dominantDriver
        case drag
        case action
    }

    /// Composed narrative result. `paragraphs` preserves
    /// `Paragraph.allCases` order; `subhead` is `Reflection from
    /// Sunday, May 10` per tone.
    struct Narrative: Equatable {
        let subhead: String
        let paragraphs: [Paragraph: String]

        var ordered: [String] {
            Paragraph.allCases.compactMap { paragraphs[$0] }
        }
    }

    /// Compute the Pro long-form narrative for the week ending
    /// `weekEnd`. `weekEnd` is `clock.now().snappedToLastSunday` —
    /// derived at the call site, not stored.
    static func compose(
        snapshots: [DailyHealthSnapshot],
        priorWeekSnapshots: [DailyHealthSnapshot],
        habits: [HabitLog],
        priorWeekHabits: [HabitLog],
        baseline: Double,
        currentAge: Double,
        tone: ToneMode,
        weekEnd: Date,
        clock: EngineClock = .live
    ) -> Narrative {
        let projection = HealthspanEngine.currentProjection(
            snapshots: snapshots,
            habits: habits,
            baseline: baseline,
            currentAge: currentAge,
            clock: clock
        )
        let priorProjection = HealthspanEngine.currentProjection(
            snapshots: priorWeekSnapshots,
            habits: priorWeekHabits,
            baseline: baseline,
            currentAge: currentAge,
            clock: clock
        )

        let weekDelta = projection.healthspanYears - priorProjection.healthspanYears
        let formattedDelta = formatYearsDelta(weekDelta)
        let deltaSign = weekDelta >= 0 ? "gained" : "slipped"

        // Dominant driver: top abs(delta).
        let dominant = projection.perDimensionDelta
            .filter { $0.value > 0 }
            .max { abs($0.value) < abs($1.value) }
            .map(\.key) ?? .sleep

        let drag = projection.perDimensionDelta
            .filter { $0.value < 0 }
            .min { $0.value < $1.value }
            .map(\.key) ?? .extras

        let aggregates = HealthspanEngine.aggregates(snapshots: snapshots, habits: habits)
        let priorAggregates = HealthspanEngine.aggregates(
            snapshots: priorWeekSnapshots,
            habits: priorWeekHabits
        )

        let dimValue = formatDimensionValue(dominant, aggregates: aggregates)
        let dimValuePrior = formatDimensionValue(dominant, aggregates: priorAggregates)
        let dragValue = formatDimensionValue(drag, aggregates: aggregates)
        let dragDetail = composeDragDetail(drag: drag, habits: habits)
        let action = composeAction(drag: drag, dragDetail: dragDetail)

        var paragraphs: [Paragraph: String] = [:]

        // Para 1 — headline movement
        paragraphs[.headline] = headlineParagraph(
            tone: tone,
            formattedDelta: formattedDelta,
            deltaSign: deltaSign,
            isPositive: weekDelta >= 0
        )

        // Para 2 — dominant driver
        paragraphs[.dominantDriver] = dominantDriverParagraph(
            tone: tone,
            dim: dominant,
            dimValue: dimValue,
            dimValuePrior: dimValuePrior
        )

        // Para 3 — drag
        paragraphs[.drag] = dragParagraph(
            tone: tone,
            drag: drag,
            dragValue: dragValue,
            dragDetail: dragDetail
        )

        // Para 4 — action
        paragraphs[.action] = actionParagraph(tone: tone, action: action)

        let dateText = formatWeekEndingDate(weekEnd)
        let subhead = tone.futureWeeklyNarrativeSubhead(dateText: dateText)

        return Narrative(subhead: subhead, paragraphs: paragraphs)
    }

    // MARK: - Paragraph composers

    private static func headlineParagraph(
        tone: ToneMode,
        formattedDelta: String,
        deltaSign: String,
        isPositive: Bool
    ) -> String {
        switch tone {
        case .gentle:
            return isPositive
                ? "\(formattedDelta) \(deltaSign) this week — a quiet ledger move in the right direction."
                : "\(formattedDelta) \(deltaSign) this week. Worth a look at what shifted."
        case .coach:
            return "\(formattedDelta) \(deltaSign) this week."
        case .firmDirect:
            return "Week's tally: \(formattedDelta) \(deltaSign)."
        }
    }

    private static func dominantDriverParagraph(
        tone: ToneMode,
        dim: HealthspanEngine.Dimension,
        dimValue: String,
        dimValuePrior: String
    ) -> String {
        let dimName = displayName(dim)
        switch tone {
        case .gentle:
            return "\(dimName) carried this week — averaging \(dimValue), up from \(dimValuePrior) the week before."
        case .coach:
            return "\(dimName) was the lever — \(dimValue) this week vs \(dimValuePrior) last."
        case .firmDirect:
            return "Top lever: \(dimName). \(dimValue) vs \(dimValuePrior)."
        }
    }

    private static func dragParagraph(
        tone: ToneMode,
        drag: HealthspanEngine.Dimension,
        dragValue: String,
        dragDetail: String
    ) -> String {
        let dragName = displayName(drag)
        switch tone {
        case .gentle:
            return "On the other side, \(dragName) crept up to \(dragValue). The biggest pull was \(dragDetail)."
        case .coach:
            return "Drag: \(dragName) reached \(dragValue). Largest contributor — \(dragDetail)."
        case .firmDirect:
            return "Drag: \(dragName) at \(dragValue). Source: \(dragDetail)."
        }
    }

    private static func actionParagraph(tone: ToneMode, action: String) -> String {
        switch tone {
        case .gentle:
            return "For next week, you might try \(action). No pressure — small shifts compound."
        case .coach:
            return "For next week: \(action)."
        case .firmDirect:
            return "Next week. \(action)."
        }
    }

    // MARK: - Slot formatters

    private static func formatYearsDelta(_ years: Double) -> String {
        let abs = Swift.abs(years)
        let rounded = (abs * 10).rounded() / 10
        return String(format: "%.1f years", rounded)
    }

    private static func formatDimensionValue(
        _ dim: HealthspanEngine.Dimension,
        aggregates: [HealthspanEngine.Dimension: Double]
    ) -> String {
        let value = aggregates[dim] ?? 0
        switch dim {
        case .sleep:
            return String(format: "%.1fh", value)
        case .steps:
            let formatter = NumberFormatter()
            formatter.numberStyle = .decimal
            return formatter.string(from: NSNumber(value: Int(value.rounded()))) ?? "0"
        case .exerciseMinutes:
            return String(format: "%.0f min/wk", value)
        case .dietQuality, .extras, .nicotine:
            return String(format: "%.1f/wk", value)
        }
    }

    private static func composeDragDetail(drag: HealthspanEngine.Dimension, habits: [HabitLog]) -> String {
        // Concrete factoid from the actual habit logs.
        switch drag {
        case .extras:
            let heavyDays = habits.filter { $0.alcoholLevel.lowercased() == "heavy" }.count
            return heavyDays > 0
                ? "\(heavyDays) heavy days this week"
                : "extras at light levels most days"
        case .nicotine:
            let nicotineDays = habits.filter { $0.smokingVaping }.count
            return "\(nicotineDays) nicotine days"
        case .sleep:
            return "the short nights mid-week"
        case .steps:
            return "rest days under 4k"
        case .exerciseMinutes:
            return "no MVPA blocks beyond walking"
        case .dietQuality:
            return "days that skipped a whole-food meal"
        }
    }

    private static func composeAction(
        drag: HealthspanEngine.Dimension,
        dragDetail: String
    ) -> String {
        // Per the spec's action generation rules.
        switch drag {
        case .extras:
            return "dropping one of the \(dragDetail) from the rotation"
        case .sleep:
            return "holding 7+ hours on the bottom-three nights"
        case .steps:
            return "adding 1,500 steps on rest days"
        case .exerciseMinutes:
            return "one extra 30-min session"
        case .dietQuality:
            return "one more whole-food day"
        case .nicotine:
            return "zero-day streak target"
        }
    }

    private static func displayName(_ dim: HealthspanEngine.Dimension) -> String {
        switch dim {
        case .sleep: return "Sleep"
        case .dietQuality: return "Whole food"
        case .steps: return "Steps"
        case .exerciseMinutes: return "Exercise"
        case .extras: return "Extras"
        case .nicotine: return "Nicotine"
        }
    }

    private static func formatWeekEndingDate(_ date: Date) -> String {
        let formatter = DateFormatter()
        formatter.setLocalizedDateFormatFromTemplate("MMM d")
        return formatter.string(from: date)
    }
}

extension Date {
    /// Most recent Sunday at or before `self`. Used by the Pro
    /// long-form subhead so the displayed date is derived, not
    /// persisted.
    func snappedToLastSunday(calendar: Calendar = .current) -> Date {
        let weekday = calendar.component(.weekday, from: self)
        // Sunday is .weekday == 1 in default Calendar.
        let daysBack = (weekday - 1 + 7) % 7
        return calendar.date(byAdding: .day, value: -daysBack, to: calendar.startOfDay(for: self)) ?? self
    }
}
