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
}
