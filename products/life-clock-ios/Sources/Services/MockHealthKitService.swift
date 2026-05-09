import Foundation

/// Deterministic mock backed by a seeded RNG. Same seed → same data.
///
/// Conforms to the live protocol shape so the rest of the app does not
/// branch on which implementation is wired. `requestAuthorization` is a
/// no-op that just flips the in-memory "asked" flag.
final class MockHealthKitService: HealthKitServiceProtocol {
    /// Shape of the simulated daily snapshots. `baseline` is the existing
    /// generous-mid mock used by every fixture before the bad-day audit.
    /// `poor` deliberately returns low-signal numbers (sub-2.5k steps, no
    /// exercise, <5h sleep, elevated RHR) so the simulator-driven-polish
    /// loop can audit how the app speaks on a clearly negative day without
    /// wiring real HealthKit. `empty` simulates a fully-authorized app that
    /// still has no useful Apple Health signal yet.
    enum HealthProfile: String {
        case baseline
        case poor
        case empty
    }

    let isHealthDataAvailable: Bool = true

    private let seed: UInt64
    private let calendar: Calendar
    private let simulateNoData: Bool
    private let healthProfile: HealthProfile
    private(set) var authorizationKnown: Bool

    init(
        seed: UInt64 = 42,
        calendar: Calendar = .lifeClockUTC,
        simulateNoData: Bool = false,
        preAuthorized: Bool = false,
        healthProfile: HealthProfile = .baseline
    ) {
        self.seed = seed
        self.calendar = calendar
        self.simulateNoData = simulateNoData
        self.healthProfile = healthProfile
        self.authorizationKnown = preAuthorized
    }

    func requestAuthorization() async throws {
        authorizationKnown = true
    }

    func dailySnapshot(for date: Date) async -> DailyHealthSnapshot? {
        guard authorizationKnown else { return nil }
        guard !simulateNoData else { return nil }
        let dayStart = calendar.startOfDay(for: date)
        var rng = MockHealthKitService.seededGenerator(seed: seed, day: dayStart)
        switch healthProfile {
        case .baseline:
            let snapshot = DailyHealthSnapshot(date: dayStart)
            snapshot.stepCount = 3_500 + Int(rng.uniform() * 9_500)
            snapshot.exerciseMinutes = Int(rng.uniform() * 60)
            snapshot.activeEnergyKcal = 200 + rng.uniform() * 600
            snapshot.sleepHours = 6.0 + rng.uniform() * 2.5
            snapshot.sleepConsistencyScore = rng.uniform()
            snapshot.restingHeartRate = 55 + Int(rng.uniform() * 25)
            snapshot.sourceCompleteness = 0.8
            snapshot.distanceMeters = Double(snapshot.stepCount ?? 0) * 0.78
            return snapshot
        case .poor:
            let snapshot = DailyHealthSnapshot(date: dayStart)
            // Deterministic low-signal day. Numbers chosen so the engine
            // produces a clearly-negative dailyTimeDeltaMinutes (movement
            // -12 for <2.5k steps, sleep -15 for <5h, no exercise entry)
            // before any habit penalties are layered on.
            snapshot.stepCount = 1_400 + Int(rng.uniform() * 600)
            snapshot.exerciseMinutes = 0
            snapshot.activeEnergyKcal = 120 + rng.uniform() * 80
            snapshot.sleepHours = 4.2 + rng.uniform() * 0.6
            snapshot.sleepConsistencyScore = 0.25 + rng.uniform() * 0.15
            snapshot.restingHeartRate = 76 + Int(rng.uniform() * 8)
            snapshot.sourceCompleteness = 0.7
            snapshot.distanceMeters = Double(snapshot.stepCount ?? 0) * 0.78
            return snapshot
        case .empty:
            return nil
        }
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
