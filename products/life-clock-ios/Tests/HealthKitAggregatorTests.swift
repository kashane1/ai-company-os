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
            sleepHours: 7.5,
            restingHeartRate: 60,
            weightKg: 78
        )
        XCTAssertEqual(snap.stepCount, 9_000)
        XCTAssertEqual(snap.exerciseMinutes, 35)
        XCTAssertEqual(snap.activeEnergyKcal, 420)
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
            sleepHours: nil,
            restingHeartRate: nil,
            weightKg: nil
        )
        XCTAssertEqual(snap.stepCount, 8_000)
        XCTAssertNil(snap.exerciseMinutes)
        XCTAssertNil(snap.sleepHours)
        // Only steps present out of {steps, exercise, activeEnergyKcal,
        // sleep, restingHR, weight} → 1/6
        XCTAssertEqual(snap.sourceCompleteness, 1.0 / 6.0, accuracy: 0.0001)
    }

    func testAllNilProducesZeroCompleteness() {
        let snap = HealthKitAggregator.aggregate(
            date: date,
            stepCount: nil,
            exerciseMinutes: nil,
            activeEnergyKcal: nil,
            sleepHours: nil,
            restingHeartRate: nil,
            weightKg: nil
        )
        XCTAssertEqual(snap.sourceCompleteness, 0.0)
        XCTAssertNil(snap.stepCount)
        XCTAssertNil(snap.distanceMeters)
    }

    func testCompletenessIsBoundedAtOne() {
        let score = HealthKitAggregator.computeCompleteness(
            stepCount: 1,
            exerciseMinutes: 1,
            activeEnergyKcal: 1,
            sleepHours: 1,
            restingHeartRate: 1,
            weightKg: 1
        )
        XCTAssertEqual(score, 1.0, accuracy: 0.0001)
    }

    func testCompletenessIncludesActiveEnergy() {
        // Regression: previously activeEnergyKcal didn't count toward
        // completeness, so a day with ONLY active energy data scored 0
        // and was silently dropped by the import filter. Pin it.
        let onlyEnergy = HealthKitAggregator.computeCompleteness(
            stepCount: nil,
            exerciseMinutes: nil,
            activeEnergyKcal: 350,
            sleepHours: nil,
            restingHeartRate: nil,
            weightKg: nil
        )
        XCTAssertGreaterThan(onlyEnergy, 0,
                             "Active-energy-only days must not be filtered out as empty")
    }

    func testDoubleRoundsToInt() {
        let snap = HealthKitAggregator.aggregate(
            date: date,
            stepCount: 8_999.7,
            exerciseMinutes: 19.4,
            activeEnergyKcal: 100,
            sleepHours: 6.5,
            restingHeartRate: 59.6,
            weightKg: 80
        )
        XCTAssertEqual(snap.stepCount, 9_000)        // .7 rounds up
        XCTAssertEqual(snap.exerciseMinutes, 19)     // .4 rounds down
        XCTAssertEqual(snap.restingHeartRate, 60)    // .6 rounds up
    }
}

final class MockHealthKitServiceAuthorizationTests: XCTestCase {
    @MainActor
    func testRequestAuthorizationFlipsFlag() async throws {
        let service = MockHealthKitService(preAuthorized: false)
        XCTAssertFalse(service.authorizationKnown)
        try await service.requestAuthorization()
        XCTAssertTrue(service.authorizationKnown)
    }

    @MainActor
    func testSimulateNoDataReturnsNilSnapshot() async {
        let service = MockHealthKitService(simulateNoData: true)
        let snap = await service.dailySnapshot(for: Date(timeIntervalSince1970: 1_800_000_000))
        XCTAssertNil(snap)
    }
}
