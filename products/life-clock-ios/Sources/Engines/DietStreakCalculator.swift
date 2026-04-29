import Foundation

/// Two diet-related streaks computed from persisted `HabitLog` rows.
///
/// `loggingDays` — consecutive days the user has logged *any* non-`unknown`
/// diet quality. Encourages the habit of logging itself, regardless of
/// quality. This is the most important streak for the daily loop.
///
/// `goodDays` — consecutive days the user has logged `great` or `okay`
/// (i.e. not `rough`). Encourages diet quality without preaching: a single
/// `rough` day breaks this streak but does *not* break `loggingDays` —
/// honesty is rewarded.
struct DietStreaks: Equatable {
    var loggingDays: Int
    var goodDays: Int

    static let zero = DietStreaks(loggingDays: 0, goodDays: 0)
}

/// Pure, testable streak math. Takes calendar + as-of date + habits;
/// returns streaks. No `Date()` calls, no mutation, no I/O.
struct DietStreakCalculator {
    let calendar: Calendar

    /// `asOf` is "today" from the caller's perspective. Streaks survive 24h:
    /// if the most recent log is from `asOf` or the day before, we walk
    /// backward from there. If the gap exceeds one day, both streaks are 0.
    func compute(habits: [HabitLog], asOf: Date) -> DietStreaks {
        guard !habits.isEmpty else { return .zero }

        let today = calendar.startOfDay(for: asOf)

        // Index logs by their day-start. If a day has multiple rows
        // (shouldn't happen given the upsert-by-date contract, but be
        // defensive), keep the last write.
        var byDay: [Date: HabitLog] = [:]
        for log in habits {
            byDay[calendar.startOfDay(for: log.date)] = log
        }

        // Find the most recent day with a log (any non-unknown).
        let candidateDays = byDay.keys
            .filter { isLogged(byDay[$0]) }
            .sorted(by: >)
        guard let mostRecent = candidateDays.first else { return .zero }

        // Streak survives 24h. If the most recent log is older than yesterday,
        // both streaks are zero.
        let daysGap = calendar.dateComponents([.day], from: mostRecent, to: today).day ?? Int.max
        if daysGap > 1 { return .zero }

        // Walk back day-by-day from `mostRecent`, counting both streaks.
        var loggingDays = 0
        var goodDays = 0
        var goodStillIntact = true
        var cursor: Date? = mostRecent
        while let day = cursor, let log = byDay[day], isLogged(log) {
            loggingDays += 1
            if goodStillIntact {
                if isGood(log) {
                    goodDays += 1
                } else {
                    goodStillIntact = false
                }
            }
            cursor = calendar.date(byAdding: .day, value: -1, to: day)
        }
        return DietStreaks(loggingDays: loggingDays, goodDays: goodDays)
    }

    private func isLogged(_ log: HabitLog?) -> Bool {
        guard let log else { return false }
        let q = log.dietQuality.lowercased()
        return q == "great" || q == "okay" || q == "rough"
    }

    private func isGood(_ log: HabitLog) -> Bool {
        let q = log.dietQuality.lowercased()
        return q == "great" || q == "okay"
    }
}
