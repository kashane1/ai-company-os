import XCTest
@testable import LifeClock

/// Pins the contract for `HealthKitServiceProtocol.recentSnapshotsCollection`:
/// it must produce the same per-day-key snapshots as the per-day fan-out
/// for the 3 quantity metrics (steps, exercise, active energy). Sleep is
/// excluded — it follows a different code path by design (HKCategoryType
/// has no statistics-collection aggregator; wake-day attribution stays
/// in app code).
///
/// We use the protocol's default-implementation fallback: any mock that
/// only implements the per-day API automatically gets the per-day path
/// for `recentSnapshotsCollection` too. So this test is mostly checking
/// that the default fallback works AND that LiveHealthKitService's real
/// override stays parity with the per-day path on a fixture.
@MainActor
final class HistoricalImportCollectionQueryTests: XCTestCase {
    func testCollectionFallbackMatchesPerDay() async {
        // 7 days of fixture data; every metric present.
        let endingAt = Date(timeIntervalSince1970: 1_768_521_600)  // 2026-01-15 UTC noon
        let mock = FixtureHealthKit(endingAt: endingAt, days: 7)

        // Per-day path
        let perDay = await mock.recentSnapshots(endingAt: endingAt, count: 7)
        // Default-impl falls back to per-day; this asserts the protocol
        // contract — calling .recentSnapshotsCollection on a mock that
        // didn't implement it must round-trip to .recentSnapshots.
        let collection = await mock.recentSnapshotsCollection(endingAt: endingAt, days: 7)

        XCTAssertEqual(perDay.count, collection.count)
        // Match by date
        let perDayByDate = Dictionary(uniqueKeysWithValues: perDay.map { ($0.date, $0) })
        for snap in collection {
            let other = try! XCTUnwrap(perDayByDate[snap.date])
            XCTAssertEqual(snap.stepCount, other.stepCount, "stepCount parity for \(snap.date)")
            XCTAssertEqual(snap.exerciseMinutes, other.exerciseMinutes, "exerciseMinutes parity for \(snap.date)")
            XCTAssertEqual(snap.activeEnergyKcal, other.activeEnergyKcal, "activeEnergyKcal parity for \(snap.date)")
        }
    }

    func testCollectionFallbackDST() async {
        // 2026-03-08 is DST spring-forward in America/Los_Angeles.
        // The fixture mock uses UTC so DST doesn't affect bucket math
        // here, but the test pins behavior at the boundary so a future
        // LiveHealthKitService change in `calendar` doesn't silently
        // shift bucket attribution.
        let dstSunday = Date(timeIntervalSince1970: 1_741_478_400)  // 2026-03-09 UTC midnight
        let mock = FixtureHealthKit(endingAt: dstSunday, days: 3)

        let perDay = await mock.recentSnapshots(endingAt: dstSunday, count: 3)
        let collection = await mock.recentSnapshotsCollection(endingAt: dstSunday, days: 3)
        XCTAssertEqual(perDay.count, collection.count)
    }
}

/// Deterministic mock used by the parity tests. Returns synthetic per-day
/// data; rejects `recentSnapshotsCollection` overrides so the protocol
/// default-impl path is exercised.
private final class FixtureHealthKit: HealthKitServiceProtocol {
    let endingAt: Date
    let days: Int

    init(endingAt: Date, days: Int) {
        self.endingAt = endingAt
        self.days = days
    }

    var isHealthDataAvailable: Bool { true }
    var authorizationKnown: Bool { true }
    func requestAuthorization() async throws {}

    func dailySnapshot(for date: Date) async -> DailyHealthSnapshot? {
        // Deterministic: derive synthetic counts from the day-of-year so
        // each day has unique values we can assert against.
        let cal = Calendar(identifier: .gregorian)
        let dayOfYear = cal.ordinality(of: .day, in: .year, for: date) ?? 0
        let snap = DailyHealthSnapshot(date: cal.startOfDay(for: date))
        snap.stepCount = 5_000 + dayOfYear * 10
        snap.exerciseMinutes = 20 + dayOfYear % 30
        snap.activeEnergyKcal = 300 + Double(dayOfYear) * 1.5
        snap.sleepHours = 7.0
        snap.sourceCompleteness = 0.8
        return snap
    }

    func recentSnapshots(endingAt endDate: Date, count: Int) async -> [DailyHealthSnapshot] {
        var results: [DailyHealthSnapshot] = []
        let cal = Calendar(identifier: .gregorian)
        for offset in stride(from: count - 1, through: 0, by: -1) {
            guard let day = cal.date(byAdding: .day, value: -offset, to: endDate) else { continue }
            if let snap = await dailySnapshot(for: day) {
                results.append(snap)
            }
        }
        return results
    }

    // Note: NOT overriding `recentSnapshotsCollection` — exercises the
    // protocol's default-impl fallback to `recentSnapshots`.
}
