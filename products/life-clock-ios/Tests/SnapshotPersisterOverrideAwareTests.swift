import XCTest
import SwiftData
@testable import LifeClock

/// Pins the override-aware merge in `LifeClockStore.persistSnapshot`:
/// when HK refresh delivers new values for a snapshot that has overrides,
/// overridden fields are preserved and only non-overridden fields take the
/// HK update.
///
/// We exercise the merge through `LifeClockStore.refreshFromHealthKit()`
/// rather than calling the private persister directly — this catches
/// regressions in the wiring between the HK fetch path and the override
/// gate at the integration boundary.
@MainActor
final class SnapshotPersisterOverrideAwareTests: XCTestCase {
    private var container: ModelContainer!
    private var context: ModelContext!
    private let dayStart = Date(timeIntervalSince1970: 1_768_521_600)

    override func setUp() async throws {
        try await super.setUp()
        container = try LifeClockContainer.make(inMemory: true)
        context = container.mainContext
    }

    private func makeStore(hkSteps: Int) -> LifeClockStore {
        let mock = ProvidedMockHealthKit()
        mock.snapshotProvider = { [dayStart] _ in
            let snap = DailyHealthSnapshot(date: dayStart)
            snap.stepCount = hkSteps
            snap.sleepHours = 7.0
            snap.exerciseMinutes = 30
            snap.activeEnergyKcal = 400
            snap.sourceCompleteness = 1.0
            return snap
        }
        let profile = UserProfile(birthDate: Date(timeIntervalSince1970: 0))
        context.insert(profile)
        try? context.save()

        let store = LifeClockStore(
            healthService: mock,
            modelContext: context,
            engineClock: .fixed(dayStart.addingTimeInterval(60))
        )
        store.profile = profile
        return store
    }

    func testHKRefreshSkipsOverriddenStepCount() async throws {
        // 1. Initial HK delivers 5000 steps.
        let store = makeStore(hkSteps: 5_000)
        await store.refreshFromHealthKit()

        // 2. User applies an override of 12_000. The override lives in
        // overridesData; raw stepCount stays at 5000 (the captured HK).
        try store.applyOverride(field: .stepCount, value: 12_000, on: dayStart)
        let descriptor = FetchDescriptor<DailyHealthSnapshot>()
        let afterOverride = try XCTUnwrap(try context.fetch(descriptor).first)
        XCTAssertEqual(afterOverride.effectiveValue(for: .stepCount), 12_000,
                       "Effective value reads through the override")
        XCTAssertEqual(afterOverride.stepCount, 5_000,
                       "Raw HK field is captured and unchanged by override")

        // 3. HK delivers a different value (e.g. 0 — phone left at home).
        // The override-aware persister must NOT overwrite the raw field,
        // because the effective view is what users see and the override
        // is meant to remain authoritative.
        let fresh = makeStore(hkSteps: 0)
        await fresh.refreshFromHealthKit(force: true)
        let final = try XCTUnwrap(try context.fetch(descriptor).first)
        XCTAssertEqual(final.effectiveValue(for: .stepCount), 12_000,
                       "User's override remains authoritative across HK refresh")
        XCTAssertEqual(final.stepCount, 5_000,
                       "Override-aware persister leaves raw stepCount alone (would be 0 without the gate)")
    }

    func testHKRefreshUpdatesNonOverriddenFields() async throws {
        let store = makeStore(hkSteps: 5_000)
        await store.refreshFromHealthKit()

        // Override only stepCount; sleepHours should still update from HK.
        try store.applyOverride(field: .stepCount, value: 12_000, on: dayStart)

        let mock = ProvidedMockHealthKit()
        mock.snapshotProvider = { [dayStart] _ in
            let snap = DailyHealthSnapshot(date: dayStart)
            snap.stepCount = 0
            snap.sleepHours = 9.0  // ← changed
            snap.exerciseMinutes = 30
            snap.activeEnergyKcal = 400
            snap.sourceCompleteness = 1.0
            return snap
        }
        let profile = try context.fetch(FetchDescriptor<UserProfile>()).first!
        let store2 = LifeClockStore(
            healthService: mock,
            modelContext: context,
            engineClock: .fixed(dayStart.addingTimeInterval(60))
        )
        store2.profile = profile
        await store2.refreshFromHealthKit(force: true)

        let final = try XCTUnwrap(
            try context.fetch(FetchDescriptor<DailyHealthSnapshot>()).first
        )
        XCTAssertEqual(final.effectiveValue(for: .stepCount), 12_000,
                       "Override preserved (effective value)")
        XCTAssertEqual(final.sleepHours, 9.0,
                       "Non-overridden field updated from HK")
    }
}

/// Test-only mock used by these integration tests. Production code uses
/// `LiveHealthKitService`. Kept here (not in main ProvidedMockHealthKit)
/// so other tests aren't affected by the snapshotProvider closure.
private final class ProvidedMockHealthKit: HealthKitServiceProtocol {
    var snapshotProvider: (@Sendable (Date) -> DailyHealthSnapshot?)?

    var isHealthDataAvailable: Bool { true }
    var authorizationKnown: Bool { true }

    func requestAuthorization() async throws {}

    func dailySnapshot(for date: Date) async -> DailyHealthSnapshot? {
        snapshotProvider?(date)
    }

    func recentSnapshots(endingAt endDate: Date, count: Int) async -> [DailyHealthSnapshot] {
        []
    }
}
