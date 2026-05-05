import Foundation

/// One-shot per-day overrides of the daily plan: each `QuestEngine.Category`
/// maps to a chosen quest slug. Reset at the next calendar day; never
/// persisted as a long-term preference (per the v1 product decision —
/// long-term preferences are a separate Settings concept).
struct TodayPlanOverrides: Codable, Equatable {
    /// `YYYY-MM-DD` of the day these picks belong to. When the in-memory
    /// dayKey doesn't match today, the picks are stale and ignored.
    var dayKey: String
    /// `QuestEngine.Category.rawValue` → quest slug.
    var picks: [String: String]

    static let empty = TodayPlanOverrides(dayKey: "", picks: [:])

    var isEmpty: Bool { picks.isEmpty }

    /// `YYYY-MM-DD` formatter shared between writers and the staleness check.
    static func dayKey(for date: Date, calendar: Calendar) -> String {
        let day = calendar.startOfDay(for: date)
        let comps = calendar.dateComponents([.year, .month, .day], from: day)
        return String(format: "%04d-%02d-%02d", comps.year ?? 0, comps.month ?? 0, comps.day ?? 0)
    }
}
