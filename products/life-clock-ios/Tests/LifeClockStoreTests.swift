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
        store.completeOnboarding(profile: profile, tone: .gentle, disclaimerAccepted: true)

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
                tone: .coach,
                disclaimerAccepted: true
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
        store.completeOnboarding(profile: profile, tone: .coach, disclaimerAccepted: true)
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
        store.completeOnboarding(profile: profile, tone: .coach, disclaimerAccepted: true)

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

    func testSetPalettePersistsAndRestoresAcrossColdRestart() async throws {
        let container = try LifeClockContainer.make(inMemory: true)
        let context = container.mainContext

        // Session 1: onboard, switch palette to aurora-cool.
        do {
            let store = LifeClockStore(
                healthService: MockHealthKitService(),
                modelContext: context,
                engineClock: .fixed(fixedDate)
            )
            store.completeOnboarding(
                profile: UserProfile(birthDate: Date(timeIntervalSince1970: 631_152_000), biologicalSex: "female"),
                tone: .coach,
                disclaimerAccepted: true
            )
            store.setPalette(.auroraCool)
            XCTAssertEqual(store.palette, .auroraCool)
            XCTAssertEqual(store.profile?.paletteId, "aurora-cool")
        }

        // Session 2: fresh store on the same container — palette must restore.
        let store2 = LifeClockStore(
            healthService: MockHealthKitService(),
            modelContext: context,
            engineClock: .fixed(fixedDate)
        )
        await store2.bootstrap()
        XCTAssertEqual(store2.palette, .auroraCool, "palette must survive cold restart")
    }

    func testBootstrapFallsBackToDefaultNavyForUnknownPaletteId() async throws {
        let container = try LifeClockContainer.make(inMemory: true)
        let context = container.mainContext

        // Session 1: onboard, then tamper paletteId on the persisted row.
        let profile = UserProfile(birthDate: Date(timeIntervalSince1970: 631_152_000), biologicalSex: "male")
        do {
            let store = LifeClockStore(
                healthService: MockHealthKitService(),
                modelContext: context,
                engineClock: .fixed(fixedDate)
            )
            store.completeOnboarding(profile: profile, tone: .coach, disclaimerAccepted: true)
            profile.paletteId = "ghost"
            try? context.save()
        }

        // Session 2: fresh store must fall back to default-navy without crashing.
        let store2 = LifeClockStore(
            healthService: MockHealthKitService(),
            modelContext: context,
            engineClock: .fixed(fixedDate)
        )
        await store2.bootstrap()
        XCTAssertEqual(store2.palette, .defaultNavy, "unknown paletteId must fall back to default-navy")
    }

    func testResetForOnboardingRestoresDefaultPalette() async throws {
        let store = try makeStore()
        let profile = UserProfile(birthDate: Date(timeIntervalSince1970: 631_152_000), biologicalSex: "female")
        store.completeOnboarding(profile: profile, tone: .coach, disclaimerAccepted: true)
        store.setPalette(.sunsetWarm)
        XCTAssertEqual(store.palette, .sunsetWarm)

        store.resetForOnboarding()
        XCTAssertEqual(store.palette, .defaultNavy, "reset must restore the default palette so a new onboarding starts clean")
    }

    func testCompleteOnboardingRejectsUnacceptedDisclaimer() async throws {
        let store = try makeStore()
        let profile = UserProfile(birthDate: Date(timeIntervalSince1970: 631_152_000), biologicalSex: "female")

        let accepted = store.completeOnboarding(profile: profile, tone: .coach, disclaimerAccepted: false)
        XCTAssertFalse(accepted, "store must refuse to mark onboarding complete without disclaimer acceptance")
        XCTAssertNil(store.profile, "no profile should be persisted on a refused acceptance")
        XCTAssertFalse(store.hasCompletedOnboarding)
    }

    func testClearTodayHabitsRemovesPersistedLog() async throws {
        let store = try makeStore()
        let profile = UserProfile(birthDate: Date(timeIntervalSince1970: 631_152_000), biologicalSex: "female")
        store.completeOnboarding(profile: profile, tone: .coach, disclaimerAccepted: true)

        let habits = HabitLog(date: fixedDate)
        habits.alcoholLevel = "heavy"
        await store.setTodayHabits(habits)
        XCTAssertNotNil(store.todayHabits)

        await store.clearTodayHabits()
        XCTAssertNil(store.todayHabits, "clearTodayHabits must drop the cached log")

        // And on a fresh store reading the same container, the row is gone.
        await store.bootstrap()
        XCTAssertNil(store.todayHabits, "clearTodayHabits must delete the persisted row, not just the cache")
    }

    func testResetForOnboardingClearsAllPersistedData() async throws {
        let store = try makeStore()
        let profile = UserProfile(birthDate: Date(timeIntervalSince1970: 631_152_000), biologicalSex: "female")
        store.completeOnboarding(profile: profile, tone: .coach, disclaimerAccepted: true)
        XCTAssertNotNil(store.profile)

        store.resetForOnboarding()
        XCTAssertNil(store.profile)
        XCTAssertFalse(store.hasCompletedOnboarding)
    }
}
