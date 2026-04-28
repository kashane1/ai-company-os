import XCTest
@testable import LifeClock

@MainActor
final class LifeClockStoreTests: XCTestCase {
    func testBootstrapPopulatesEstimateAndQuests() async {
        let store = LifeClockStore(
            healthService: MockHealthKitService(seed: 42),
            engineClock: .fixed(Date(timeIntervalSince1970: 1_800_000_000), seed: 42)
        )
        await store.bootstrap()

        XCTAssertNotNil(store.profile, "bootstrap should seed a sample profile when none exists")
        XCTAssertNotNil(store.todayEstimate, "today estimate should be computed at bootstrap")
        XCTAssertGreaterThanOrEqual(store.todayQuests.count, 1)
        XCTAssertLessThanOrEqual(store.todayQuests.count, 3)
    }

    func testToneModeChangePropagatesToProfile() async {
        let store = LifeClockStore(
            healthService: MockHealthKitService(seed: 1),
            engineClock: .fixed(Date(timeIntervalSince1970: 1_800_000_000), seed: 1)
        )
        await store.bootstrap()
        store.setToneMode(.gentle)
        XCTAssertEqual(store.toneMode, .gentle)
        XCTAssertEqual(store.profile?.toneMode, ToneMode.gentle.rawValue)
    }

    func testQuestCompletionAddsLedgerEntry() async {
        let store = LifeClockStore(
            healthService: MockHealthKitService(seed: 7),
            engineClock: .fixed(Date(timeIntervalSince1970: 1_800_000_000), seed: 7)
        )
        await store.bootstrap()
        let initialLedger = store.ledger.count
        guard let first = store.todayQuests.first else {
            XCTFail("expected at least one quest")
            return
        }
        store.toggleQuestCompletion(first)
        XCTAssertNotNil(first.completedAt)
        XCTAssertEqual(store.ledger.count, initialLedger + 1)
    }
}
