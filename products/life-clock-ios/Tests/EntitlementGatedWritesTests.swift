import XCTest
@testable import LifeClock

/// Defensive contract — all three Pro-only writers (`applyOverride`,
/// `revertOverride`, `selectPlanQuest`) on `LifeClockStore` MUST throw
/// `OverrideService.OverrideError.notEntitled` when the injected
/// `EntitlementProviding` reports `isPro == false`.
///
/// `OverrideSheet` and `PlanEditorSheet` rely on this throw to surface
/// tone-aware copy / no-op safely. The Pro-disabled UI walk in
/// `ProTouchpointsRecon` confirms the screens are not reachable from a
/// Free user's normal navigation, so this suite exists to lock the
/// last-line-of-defense behavior in case those gates ever regress.
@MainActor
final class EntitlementGatedWritesTests: XCTestCase {
    private let fixedDate = Date(timeIntervalSince1970: 1_800_000_000)

    private final class FreeEntitlements: EntitlementProviding {
        var isPro: Bool { false }
    }

    private func makeStore() throws -> LifeClockStore {
        let container = try LifeClockContainer.make(inMemory: true)
        let store = LifeClockStore(
            healthService: MockHealthKitService(seed: 1),
            modelContext: container.mainContext,
            engineClock: .fixed(fixedDate)
        )
        store.entitlements = FreeEntitlements()
        return store
    }

    func testApplyOverrideThrowsNotEntitledForFreeUser() throws {
        let store = try makeStore()
        XCTAssertThrowsError(
            try store.applyOverride(field: .stepCount, value: 8_000, on: fixedDate)
        ) { error in
            XCTAssertEqual(
                error as? OverrideService.OverrideError,
                .notEntitled,
                "applyOverride must reject Free users with .notEntitled"
            )
        }
    }

    func testRevertOverrideThrowsNotEntitledForFreeUser() throws {
        let store = try makeStore()
        XCTAssertThrowsError(
            try store.revertOverride(field: .stepCount, on: fixedDate)
        ) { error in
            XCTAssertEqual(
                error as? OverrideService.OverrideError,
                .notEntitled,
                "revertOverride must reject Free users with .notEntitled"
            )
        }
    }

    func testSelectPlanQuestThrowsNotEntitledForFreeUser() throws {
        let store = try makeStore()
        XCTAssertThrowsError(
            try store.selectPlanQuest(slug: "any-slug", in: .movement)
        ) { error in
            XCTAssertEqual(
                error as? OverrideService.OverrideError,
                .notEntitled,
                "selectPlanQuest must reject Free users with .notEntitled"
            )
        }
    }

    /// Belt-and-braces: the unwired default (entitlements == nil) is Free,
    /// so all three writers must also throw before any caller wires up a
    /// SubscriptionStore. Catches the regression where a forgotten
    /// `entitlements = ...` would silently grant Pro by inverting the
    /// guard.
    func testWritersThrowWhenNoEntitlementSourceWired() throws {
        let container = try LifeClockContainer.make(inMemory: true)
        let store = LifeClockStore(
            healthService: MockHealthKitService(seed: 1),
            modelContext: container.mainContext,
            engineClock: .fixed(fixedDate)
        )
        // Intentionally do NOT set store.entitlements.
        XCTAssertThrowsError(try store.applyOverride(field: .stepCount, value: 1, on: fixedDate))
        XCTAssertThrowsError(try store.revertOverride(field: .stepCount, on: fixedDate))
        XCTAssertThrowsError(try store.selectPlanQuest(slug: "x", in: .movement))
    }
}
