import Foundation

/// Replaces the rolling-streak model with a calendar-month "kind streak":
/// the metric is N distinct days logged in the current calendar month.
/// Resolves vision.md Open Question #7 (option D, 2026-05-06): missed
/// days never break the chain — only the calendar resets, on the 1st of
/// each month.
///
/// `daysLogged` — distinct days in the *current* month with a non-`unknown`
/// diet log (`great`, `okay`, or `rough`). Honest "rough" logs count.
///
/// `milestone` — fires at start-of-month (day 1), 25%, 50%, and 75% of
/// the month elapsed. Triggered by `dayOfMonth / daysInMonth`, not by
/// `daysLogged`, so the cadence is steady regardless of how many days
/// the user actually logged. The milestone is *persistent for the day*
/// — the same fixed-date launch will always return the same milestone.
struct MonthlyLogging: Equatable {
    var daysLogged: Int
    var dayOfMonth: Int
    var daysInMonth: Int
    var monthName: String
    var milestone: Milestone?

    enum Milestone: String, Equatable {
        case start
        case quarter
        case half
        case threeQuarter
    }

    static let zero = MonthlyLogging(
        daysLogged: 0,
        dayOfMonth: 0,
        daysInMonth: 0,
        monthName: "",
        milestone: nil
    )
}

/// Pure, testable monthly-logging math. Takes calendar + as-of date +
/// habits; returns `MonthlyLogging`. No `Date()` calls, no mutation.
struct MonthlyLoggingCalculator {
    let calendar: Calendar

    func compute(habits: [HabitLog], asOf: Date) -> MonthlyLogging {
        let dayOfMonth = calendar.component(.day, from: asOf)
        let daysInMonth = calendar.range(of: .day, in: .month, for: asOf)?.count ?? 0

        guard let monthInterval = calendar.dateInterval(of: .month, for: asOf) else {
            return .zero
        }

        // Distinct day-keys logged inside the current month.
        var loggedDayKeys: Set<Date> = []
        for log in habits where isLogged(log) {
            let dayStart = calendar.startOfDay(for: log.date)
            if monthInterval.contains(dayStart) {
                loggedDayKeys.insert(dayStart)
            }
        }

        // English month name. The banner copy ("Halfway through {Month}…")
        // is English-only, so the month must be too — overriding the
        // system locale here keeps `{Month}` like "May" instead of an
        // ICU symbol like "M05" that test runners sometimes return.
        let formatter = DateFormatter()
        formatter.calendar = calendar
        formatter.locale = Locale(identifier: "en_US")
        formatter.dateFormat = "LLLL"
        let monthName = formatter.string(from: asOf)

        return MonthlyLogging(
            daysLogged: loggedDayKeys.count,
            dayOfMonth: dayOfMonth,
            daysInMonth: daysInMonth,
            monthName: monthName,
            milestone: milestone(dayOfMonth: dayOfMonth, daysInMonth: daysInMonth)
        )
    }

    /// First day of the month the threshold is *reached or crossed*. Bands are
    /// non-overlapping: day 1 is `.start`, the first day at ≥25% but <50% is
    /// `.quarter`, etc. Each milestone day shows the copy for the entire
    /// calendar day per the operator's "persistent" decision (2026-05-06).
    private func milestone(dayOfMonth: Int, daysInMonth: Int) -> MonthlyLogging.Milestone? {
        guard daysInMonth > 0, dayOfMonth >= 1 else { return nil }
        if dayOfMonth == 1 { return .start }
        let ratio = Double(dayOfMonth) / Double(daysInMonth)
        // Compute the first day of each band — the day on which `ratio`
        // first crosses the threshold. Use ceiling so a 30-day month
        // hits 25% on day 8 (8/30 = 0.267) but not on day 7 (0.233).
        let quarterDay = firstDay(crossing: 0.25, daysInMonth: daysInMonth)
        let halfDay = firstDay(crossing: 0.50, daysInMonth: daysInMonth)
        let threeQuarterDay = firstDay(crossing: 0.75, daysInMonth: daysInMonth)
        if dayOfMonth == quarterDay { return .quarter }
        if dayOfMonth == halfDay { return .half }
        if dayOfMonth == threeQuarterDay { return .threeQuarter }
        // ratio mentioned to satisfy the compiler in case future bands use it.
        _ = ratio
        return nil
    }

    private func firstDay(crossing threshold: Double, daysInMonth: Int) -> Int {
        // Smallest d such that d / daysInMonth >= threshold.
        let raw = ceil(threshold * Double(daysInMonth))
        let day = max(2, Int(raw)) // day 1 is reserved for .start
        return min(day, daysInMonth)
    }

    private func isLogged(_ log: HabitLog?) -> Bool {
        guard let log else { return false }
        let q = log.dietQuality.lowercased()
        return q == "great" || q == "okay" || q == "rough"
    }
}
