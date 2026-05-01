import Foundation

/// Injected source of time and calendar for engines and the store.
///
/// Engines and the store never call `Date()`, `Date.now`, `Calendar.current`,
/// or `TimeZone.current` directly. They take an `EngineClock` and read
/// everything from it. Tests pin time via `.fixed(_:)`; the store uses the
/// same instance so quest-completion timestamps are deterministic too.
struct EngineClock {
    var now: () -> Date
    var calendar: Calendar

    static let live: EngineClock = {
        var cal = Calendar(identifier: .gregorian)
        cal.timeZone = TimeZone.current
        return EngineClock(now: { Date() }, calendar: cal)
    }()

    static func fixed(_ date: Date) -> EngineClock {
        var cal = Calendar(identifier: .gregorian)
        cal.timeZone = TimeZone(identifier: "UTC")!
        return EngineClock(now: { date }, calendar: cal)
    }

    /// `yyyy-MM-dd` in this clock's calendar/timezone. Stable across DST and
    /// dateline boundaries because we render the calendar's components rather
    /// than diff Dates. Use for keys that need to compare two moments by
    /// "logical day" (e.g. wrap-up shown? snapshot persisted?).
    func dayKey(_ date: Date) -> String {
        let components = calendar.dateComponents([.year, .month, .day], from: date)
        return String(
            format: "%04d-%02d-%02d",
            components.year ?? 0,
            components.month ?? 0,
            components.day ?? 0
        )
    }
}
