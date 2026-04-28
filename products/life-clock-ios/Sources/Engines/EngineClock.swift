import Foundation

/// Injected source of time, calendar, timezone, and randomness for engines.
///
/// Engines never call `Date()`, `Date.now`, `Calendar.current`, `TimeZone.current`,
/// or `Int.random(in:)` directly. They take an `EngineClock` and read everything
/// from it. This lets tests pin time and seed RNG; it also makes engines portable
/// across timezones (CI runs UTC; user devices don't).
struct EngineClock {
    var now: () -> Date
    var calendar: Calendar
    var random: () -> Double // returns value in [0, 1)

    static let live: EngineClock = {
        var cal = Calendar(identifier: .gregorian)
        cal.timeZone = TimeZone.current
        return EngineClock(
            now: { Date() },
            calendar: cal,
            random: { Double.random(in: 0..<1) }
        )
    }()

    static func fixed(_ date: Date, seed: UInt64 = 42) -> EngineClock {
        var cal = Calendar(identifier: .gregorian)
        cal.timeZone = TimeZone(identifier: "UTC")!
        var generator = SplitMix64(seed: seed)
        return EngineClock(
            now: { date },
            calendar: cal,
            random: {
                let raw = generator.next()
                return Double(raw >> 11) / Double(UInt64(1) << 53)
            }
        )
    }
}

/// Tiny seeded PRNG — SplitMix64. Plenty random for quest selection / variance.
private struct SplitMix64 {
    var state: UInt64

    init(seed: UInt64) { self.state = seed }

    mutating func next() -> UInt64 {
        state = state &+ 0x9E3779B97F4A7C15
        var z = state
        z = (z ^ (z >> 30)) &* 0xBF58476D1CE4E5B9
        z = (z ^ (z >> 27)) &* 0x94D049BB133111EB
        return z ^ (z >> 31)
    }
}
