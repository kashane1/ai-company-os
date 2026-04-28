import XCTest
@testable import LifeClock

@MainActor
final class LifeClockStoreTests: XCTestCase {
    private let fixedDate = Date(timeIntervalSince1970: 1_800_000_000)

    private func makeStore(seed: UInt64 = 42) -> LifeClockStore {
        LifeClockStore(
            healthService: MockHealthKitService(seed: seed),
            engineClock: .fixed(fixedDate)
        )
    }

    func testBootstrapPopulatesEstimateAndQuests() async {
        let store = makeStore()
        await store.bootstrap()

        XCTAssertNotNil(store.profile)
        XCTAssertNotNil(store.todayEstimate)
        XCTAssertGreaterThanOrEqual(store.todayQuests.count, 1)
        XCTAssertLessThanOrEqual(store.todayQuests.count, 3)
    }

    func testQuestCompletionAddsLedgerEntryStampedAtPinnedClock() async {
        let store = makeStore(seed: 7)
        await store.bootstrap()
        let initialLedger = store.ledger.count
        guard let first = store.todayQuests.first else {
            XCTFail("expected at least one quest")
            return
        }
        store.toggleQuestCompletion(first)
        XCTAssertEqual(first.completedAt, fixedDate, "completedAt should use the injected clock, not Date()")
        XCTAssertEqual(store.ledger.count, initialLedger + 1)
    }
}
