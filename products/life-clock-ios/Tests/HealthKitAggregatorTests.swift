import XCTest
@testable import LifeClock

final class HealthKitAggregatorTests: XCTestCase {
    private let date = Date(timeIntervalSince1970: 1_800_000_000)

    func testAllInputsProduceFullCompleteness() {
        let snap = HealthKitAggregator.aggregate(
            date: date,
            stepCount: 9_000,
            exerciseMinutes: 35,
            activeEnergyKcal: 420,
            workoutsCount: 1,
            sleepHours: 7.5,
            restingHeartRate: 60,
            heartRateAvg: 72,
            weightKg: 78,
            vo2Max: 42
        )
        XCTAssertEqual(snap.stepCount, 9_000)
        XCTAssertEqual(snap.exerciseMinutes, 35)
        XCTAssertEqual(snap.activeEnergyKcal, 420)
        XCTAssertEqual(snap.workoutsCount, 1)
        XCTAssertEqual(snap.sleepHours, 7.5)
        XCTAssertEqual(snap.restingHeartRate, 60)
        XCTAssertEqual(snap.sourceCompleteness, 1.0, accuracy: 0.0001)
        XCTAssertEqual(snap.distanceMeters ?? 0, 9_000 * 0.78, accuracy: 0.5)
    }

    func testMissingFieldsLowerCompleteness() {
        let snap = HealthKitAggregator.aggregate(
            date: date,
            stepCount: 8_000,
            exerciseMinutes: nil,
            activeEnergyKcal: nil,
            workoutsCount: nil,
            sleepHours: nil,
            restingHeartRate: nil,
            heartRateAvg: nil,
            weightKg: nil,
            vo2Max: nil
        )
        XCTAssertEqual(snap.stepCount, 8_000)
        XCTAssertNil(snap.exerciseMinutes)
        XCTAssertNil(snap.sleepHours)
        // Only steps present out of {steps, exercise, sleep, restingHR, weight} → 0.2
        XCTAssertEqual(snap.sourceCompleteness, 0.2, accuracy: 0.0001)
    }

    func testAllNilProducesZeroCompleteness() {
        let snap = HealthKitAggregator.aggregate(
            date: date,
            stepCount: nil,
            exerciseMinutes: nil,
            activeEnergyKcal: nil,
            workoutsCount: nil,
            sleepHours: nil,
            restingHeartRate: nil,
            heartRateAvg: nil,
            weightKg: nil,
            vo2Max: nil
        )
        XCTAssertEqual(snap.sourceCompleteness, 0.0)
        XCTAssertNil(snap.stepCount)
        XCTAssertNil(snap.distanceMeters)
    }

    func testCompletenessIsBoundedAtOne() {
        // No way to exceed 1.0 — defensive check on `min(1.0, score)`.
        let score = HealthKitAggregator.computeCompleteness(
            stepCount: 1, exerciseMinutes: 1, sleepHours: 1, restingHeartRate: 1, weightKg: 1
        )
        XCTAssertEqual(score, 1.0)
    }

    func testDoubleRoundsToInt() {
        let snap = HealthKitAggregator.aggregate(
            date: date,
            stepCount: 8_999.7,
            exerciseMinutes: 19.4,
            activeEnergyKcal: 100,
            workoutsCount: 0,
            sleepHours: 6.5,
            restingHeartRate: 59.6,
            heartRateAvg: 71.2,
            weightKg: 80,
            vo2Max: 40
        )
        XCTAssertEqual(snap.stepCount, 9_000)        // .7 rounds up
        XCTAssertEqual(snap.exerciseMinutes, 19)     // .4 rounds down
        XCTAssertEqual(snap.restingHeartRate, 60)    // .6 rounds up
        XCTAssertEqual(snap.heartRateAvg, 71)        // .2 rounds down
    }
}

final class MockHealthKitServiceAuthorizationTests: XCTestCase {
    func testRequestAuthorizationFlipsFlag() async throws {
        let service = MockHealthKitService(preAuthorize: false)
        XCTAssertFalse(service.authorizationKnown(for: .core))
        try await service.requestAuthorization(for: .core)
        XCTAssertTrue(service.authorizationKnown(for: .core))
    }

    func testSimulateNoDataReturnsNilSnapshot() async {
        let service = MockHealthKitService(simulateNoData: true)
        let snap = await service.dailySnapshot(for: Date(timeIntervalSince1970: 1_800_000_000))
        XCTAssertNil(snap)
    }
}
