import XCTest
import SwiftData
@testable import LifeClock

@MainActor
final class OverrideServiceTests: XCTestCase {
    private var container: ModelContainer!
    private var context: ModelContext!
    private var service: OverrideService!
    private let dayStart = Date(timeIntervalSince1970: 1_768_521_600)
    private let recomputedAt = Date(timeIntervalSince1970: 1_768_530_000)

    override func setUp() async throws {
        try await super.setUp()
        container = try LifeClockContainer.make(inMemory: true)
        context = container.mainContext
        service = OverrideService(modelContext: context)
        seedSnapshot()
    }

    private func seedSnapshot(stepCount: Int = 8000, sleepHours: Double = 7.5) {
        let snapshot = DailyHealthSnapshot(date: dayStart)
        snapshot.stepCount = stepCount
        snapshot.sleepHours = sleepHours
        snapshot.exerciseMinutes = 30
        snapshot.activeEnergyKcal = 400
        context.insert(snapshot)
        try? context.save()
    }

    private func snapshot() -> DailyHealthSnapshot {
        let descriptor = FetchDescriptor<DailyHealthSnapshot>()
        return try! context.fetch(descriptor).first!
    }

    // MARK: - Apply

    func testApplyOverrideStoresValueAndCapturesOriginal() throws {
        try service.applyOverride(
            field: .stepCount, value: 12_000, on: dayStart, recomputedAt: recomputedAt
        )
        let s = snapshot()
        XCTAssertEqual(s.effectiveValue(for: .stepCount), 12_000)
        XCTAssertEqual(s.originalHealthKitValue(for: .stepCount), 8_000)
        XCTAssertTrue(s.isOverridden(.stepCount))
        XCTAssertEqual(s.lastRecomputedAt, recomputedAt)
    }

    func testApplyOverrideIsWriteOnceForOriginal() throws {
        // First override captures original = 8000.
        try service.applyOverride(
            field: .stepCount, value: 12_000, on: dayStart, recomputedAt: recomputedAt
        )
        // Second override updates the override but does NOT overwrite the
        // captured original (so revert still restores the truly original).
        try service.applyOverride(
            field: .stepCount, value: 9_000, on: dayStart, recomputedAt: recomputedAt
        )
        let s = snapshot()
        XCTAssertEqual(s.effectiveValue(for: .stepCount), 9_000)
        XCTAssertEqual(s.originalHealthKitValue(for: .stepCount), 8_000,
                       "Original must be captured at first override, never on subsequent edits")
    }

    func testApplyOverrideRejectsOutOfRangeValue() {
        XCTAssertThrowsError(
            try service.applyOverride(
                field: .stepCount, value: 200_000, on: dayStart, recomputedAt: recomputedAt
            )
        ) { error in
            XCTAssertEqual(error as? OverrideService.OverrideError, .invalidValue)
        }
        let s = snapshot()
        XCTAssertFalse(s.isOverridden(.stepCount))
    }

    func testApplyOverrideRejectsNegativeValue() {
        XCTAssertThrowsError(
            try service.applyOverride(
                field: .sleepHours, value: -1, on: dayStart, recomputedAt: recomputedAt
            )
        ) { error in
            XCTAssertEqual(error as? OverrideService.OverrideError, .invalidValue)
        }
    }

    func testApplyOverrideThrowsForMissingSnapshot() {
        let other = Date(timeIntervalSince1970: 1_700_000_000)
        XCTAssertThrowsError(
            try service.applyOverride(
                field: .stepCount, value: 1_000, on: other, recomputedAt: recomputedAt
            )
        ) { error in
            XCTAssertEqual(error as? OverrideService.OverrideError, .snapshotMissing)
        }
    }

    // MARK: - Revert

    func testRevertRestoresOriginalAndClearsOverride() throws {
        try service.applyOverride(
            field: .stepCount, value: 12_000, on: dayStart, recomputedAt: recomputedAt
        )
        try service.revertOverride(field: .stepCount, on: dayStart, recomputedAt: recomputedAt)
        let s = snapshot()
        XCTAssertEqual(s.stepCount, 8_000, "Raw HK field must be restored to captured original")
        XCTAssertFalse(s.isOverridden(.stepCount))
        XCTAssertNil(s.originalHealthKitValue(for: .stepCount),
                     "Captured original must be cleared after revert so a future override starts fresh")
    }

    func testRevertWithoutOverrideIsNoOp() throws {
        // No override exists → revert is a soft no-op (no throw, no mutation).
        try service.revertOverride(field: .stepCount, on: dayStart, recomputedAt: recomputedAt)
        let s = snapshot()
        XCTAssertEqual(s.stepCount, 8_000)
        XCTAssertFalse(s.isOverridden(.stepCount))
    }

    // MARK: - Multi-field

    func testOverridesAreIndependentPerField() throws {
        try service.applyOverride(field: .stepCount, value: 12_000, on: dayStart, recomputedAt: recomputedAt)
        try service.applyOverride(field: .sleepHours, value: 8.5, on: dayStart, recomputedAt: recomputedAt)
        let s = snapshot()
        XCTAssertEqual(s.effectiveValue(for: .stepCount), 12_000)
        XCTAssertEqual(s.effectiveValue(for: .sleepHours), 8.5)
        XCTAssertEqual(s.effectiveValue(for: .exerciseMinutes), 30, "Untouched field falls through to raw HK value")
    }

    // MARK: - Engine effect

    func testApplyOverrideWritesThroughToRawFieldSoEngineSeesIt() throws {
        // CRITICAL: ClockEngine reads snapshot.stepCount / sleepHours
        // directly. Applying an override MUST update the raw field in
        // addition to overridesData, otherwise the score never reflects
        // user corrections.
        try service.applyOverride(
            field: .stepCount, value: 12_000, on: dayStart, recomputedAt: recomputedAt
        )
        let s = snapshot()
        XCTAssertEqual(s.stepCount, 12_000,
                       "Raw field must mirror override so engine reads see the corrected value")
        XCTAssertEqual(s.originalHealthKitValue(for: .stepCount), 8_000,
                       "Original HK value preserved separately for revert")
    }

    func testRevertRestoresEngineVisibleValue() throws {
        try service.applyOverride(
            field: .sleepHours, value: 9.0, on: dayStart, recomputedAt: recomputedAt
        )
        XCTAssertEqual(snapshot().sleepHours, 9.0)
        try service.revertOverride(field: .sleepHours, on: dayStart, recomputedAt: recomputedAt)
        XCTAssertEqual(snapshot().sleepHours, 7.5,
                       "Revert restores the raw field to the captured original — engine sees pre-override value again")
    }

    /// Pins the data-integrity reviewer's verified-but-untested behavior:
    /// after revert, the captured original is cleared, so a subsequent
    /// `applyOverride` re-captures from the current raw value rather than
    /// holding onto a stale original.
    func testReEditAfterRevertReCapturesOriginal() throws {
        // 1. First override: captures original = 8000.
        try service.applyOverride(
            field: .stepCount, value: 12_000, on: dayStart, recomputedAt: recomputedAt
        )
        XCTAssertEqual(snapshot().originalHealthKitValue(for: .stepCount), 8_000)

        // 2. Revert: clears override + captured original; raw restored.
        try service.revertOverride(field: .stepCount, on: dayStart, recomputedAt: recomputedAt)
        XCTAssertNil(snapshot().originalHealthKitValue(for: .stepCount),
                     "Revert must clear the captured original so future edits re-capture")
        XCTAssertEqual(snapshot().stepCount, 8_000)

        // 3. Apply a new override: re-captures original from current raw.
        try service.applyOverride(
            field: .stepCount, value: 9_000, on: dayStart, recomputedAt: recomputedAt
        )
        XCTAssertEqual(snapshot().effectiveValue(for: .stepCount), 9_000)
        XCTAssertEqual(snapshot().originalHealthKitValue(for: .stepCount), 8_000,
                       "Original must be re-captured fresh from current raw, not held over from before revert")

        // 4. Revert again: raw back to 8000.
        try service.revertOverride(field: .stepCount, on: dayStart, recomputedAt: recomputedAt)
        XCTAssertEqual(snapshot().stepCount, 8_000)
    }
}
