import Foundation

/// Deterministic mock backed by a seeded RNG. Same seed → same data.
final class MockHealthKitService: HealthKitServiceProtocol {
    let isAuthorizationKnown: Bool = false

    private let seed: UInt64
    private let calendar: Calendar

    init(seed: UInt64 = 42, calendar: Calendar = .lifeClockUTC) {
        self.seed = seed
        self.calendar = calendar
    }

    func dailySnapshot(for date: Date) async -> DailyHealthSnapshot? {
        let dayStart = calendar.startOfDay(for: date)
        var rng = MockHealthKitService.seededGenerator(seed: seed, day: dayStart)
        let snapshot = DailyHealthSnapshot(date: dayStart)
        snapshot.stepCount = 3_500 + Int(rng.uniform() * 9_500)
        snapshot.exerciseMinutes = Int(rng.uniform() * 60)
        snapshot.activeEnergyKcal = 200 + rng.uniform() * 600
        snapshot.workoutsCount = rng.uniform() > 0.7 ? 1 : 0
        snapshot.sleepHours = 6.0 + rng.uniform() * 2.5
        snapshot.sleepConsistencyScore = rng.uniform()
        snapshot.restingHeartRate = 55 + Int(rng.uniform() * 25)
        snapshot.heartRateAvg = 70 + Int(rng.uniform() * 20)
        snapshot.distanceMeters = Double(snapshot.stepCount ?? 0) * 0.78
        snapshot.sourceCompleteness = 0.8 // sample data is mostly complete
        return snapshot
    }

    func recentSnapshots(endingAt endDate: Date, count: Int) async -> [DailyHealthSnapshot] {
        var results: [DailyHealthSnapshot] = []
        for offset in stride(from: count - 1, through: 0, by: -1) {
            guard
                let day = calendar.date(byAdding: .day, value: -offset, to: endDate),
                let snapshot = await dailySnapshot(for: day)
            else { continue }
            results.append(snapshot)
        }
        return results
    }

    private static func seededGenerator(seed: UInt64, day: Date) -> SmallRNG {
        let dayKey = UInt64(bitPattern: Int64(day.timeIntervalSince1970))
        return SmallRNG(seed: seed ^ dayKey)
    }
}

extension Calendar {
    /// Calendar pinned to UTC. Used by mock service for stable, timezone-free
    /// fixture generation. Production code should use `EngineClock.live.calendar`.
    static let lifeClockUTC: Calendar = {
        var cal = Calendar(identifier: .gregorian)
        cal.timeZone = TimeZone(identifier: "UTC")!
        return cal
    }()
}

/// Internal SplitMix64-based RNG. Duplicated from EngineClock so this service
/// has no engine-layer dependency.
private struct SmallRNG {
    var state: UInt64
    init(seed: UInt64) { self.state = seed == 0 ? 0xDEADBEEF : seed }

    mutating func next() -> UInt64 {
        state = state &+ 0x9E3779B97F4A7C15
        var z = state
        z = (z ^ (z >> 30)) &* 0xBF58476D1CE4E5B9
        z = (z ^ (z >> 27)) &* 0x94D049BB133111EB
        return z ^ (z >> 31)
    }

    mutating func uniform() -> Double {
        Double(next() >> 11) / Double(UInt64(1) << 53)
    }
}
