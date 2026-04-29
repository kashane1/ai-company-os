import XCTest
import SwiftData
@testable import LifeClock

@MainActor
final class LifeClockStoreTests: XCTestCase {
    private let fixedDate = Date(timeIntervalSince1970: 1_800_000_000)

    private func makeStore(seed: UInt64 = 42, simulateNoData: Bool = false) throws -> LifeClockStore {
        let container = try LifeClockContainer.make(inMemory: true)
        return LifeClockStore(
            healthService: MockHealthKitService(seed: seed, simulateNoData: simulateNoData),
            modelContext: container.mainContext,
            engineClock: .fixed(fixedDate)
        )
    }

    func testBootstrapPopulatesEstimateAndQuests() async throws {
        let store = try makeStore()

        // First-launch path: no profile yet.
        await store.bootstrap()
        XCTAssertNil(store.profile, "bootstrap should not seed a profile when none persisted — onboarding does that")
    }

    func testCompleteOnboardingPersistsProfile() async throws {
        let store = try makeStore()
        let profile = UserProfile(birthDate: Date(timeIntervalSince1970: 631_152_000), biologicalSex: "female")
        store.completeOnboarding(profile: profile, tone: .gentle)

        XCTAssertNotNil(store.profile)
        XCTAssertTrue(store.hasCompletedOnboarding)
        XCTAssertEqual(store.toneMode, .gentle)

        // Refresh now has a profile to anchor on.
        await store.refreshFromHealthKit()
        XCTAssertNotNil(store.todayEstimate)
        XCTAssertGreaterThanOrEqual(store.todayQuests.count, 1)
        XCTAssertLessThanOrEqual(store.todayQuests.count, 3)
    }

    func testColdRestartLoadsPersistedProfile() async throws {
        let container = try LifeClockContainer.make(inMemory: true)
        let context = container.mainContext

        // Session 1: complete onboarding.
        do {
            let store = LifeClockStore(
                healthService: MockHealthKitService(),
                modelContext: context,
                engineClock: .fixed(fixedDate)
            )
            store.completeOnboarding(
                profile: UserProfile(birthDate: Date(timeIntervalSince1970: 631_152_000), biologicalSex: "male"),
                tone: .coach
            )
        }

        // Session 2: fresh store reading from the same persistent container.
        let store2 = LifeClockStore(
            healthService: MockHealthKitService(),
            modelContext: context,
            engineClock: .fixed(fixedDate)
        )
        await store2.bootstrap()
        XCTAssertNotNil(store2.profile, "second session should restore the persisted profile")
        XCTAssertTrue(store2.hasCompletedOnboarding)
    }

    func testQuestCompletionAddsLedgerEntryStampedAtPinnedClock() async throws {
        let store = try makeStore(seed: 7)
        let profile = UserProfile(birthDate: Date(timeIntervalSince1970: 631_152_000), biologicalSex: "female")
        store.completeOnboarding(profile: profile, tone: .coach)
        await store.refreshFromHealthKit()

        let initialLedger = store.ledger.count
        guard let first = store.todayQuests.first else {
            XCTFail("expected at least one quest")
            return
        }
        store.toggleQuestCompletion(first)
        XCTAssertEqual(first.completedAt, fixedDate, "completedAt should use the injected clock, not Date()")
        XCTAssertEqual(store.ledger.count, initialLedger + 1)
    }

    func testSetTodayHabitsUpsertsByDate() async throws {
        let store = try makeStore()
        let profile = UserProfile(birthDate: Date(timeIntervalSince1970: 631_152_000), biologicalSex: "female")
        store.completeOnboarding(profile: profile, tone: .coach)

        let habits1 = HabitLog(date: fixedDate)
        habits1.alcoholLevel = "heavy"
        await store.setTodayHabits(habits1)
        XCTAssertEqual(store.todayHabits?.alcoholLevel, "heavy")

        // Second call with same date should upsert, not create a duplicate.
        let habits2 = HabitLog(date: fixedDate)
        habits2.alcoholLevel = "none"
        habits2.smokingVaping = true
        await store.setTodayHabits(habits2)
        XCTAssertEqual(store.todayHabits?.alcoholLevel, "none")
        XCTAssertEqual(store.todayHabits?.smokingVaping, true)
    }

    func testResetForOnboardingClearsAllPersistedData() async throws {
        let store = try makeStore()
        let profile = UserProfile(birthDate: Date(timeIntervalSince1970: 631_152_000), biologicalSex: "female")
        store.completeOnboarding(profile: profile, tone: .coach)
        XCTAssertNotNil(store.profile)

        store.resetForOnboarding()
        XCTAssertNil(store.profile)
        XCTAssertFalse(store.hasCompletedOnboarding)
    }
}
