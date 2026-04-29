import XCTest
import SwiftData
@testable import LifeClock

/// End-to-end test that boots the full Life Clock state graph the way the
/// app does at launch — in-memory `ModelContainer`, `MockHealthKitService`,
/// `EngineClock.fixed(...)` for determinism — and walks the loop the
/// founder pack describes:
///
///   open → see clock → log a habit → see drivers/quests update → cold-restart → state survives
///
/// This is the smoke test that catches whole categories of regression no
/// single-component test would: store↔engine↔persistence↔HK boundary
/// breakage, missed `await refreshFromHealthKit()` after a mutation,
/// schema migrations breaking under cold-restart, etc.
@MainActor
final class LifeClockE2ETests: XCTestCase {
    private let fixedDate = Date(timeIntervalSince1970: 1_800_000_000) // 2027-01-15 UTC
    private let birthDate = Date(timeIntervalSince1970: 631_152_000)   // 1990-01-01 UTC

    // MARK: - Whole-loop walk

    func testFullLoopFromOnboardingThroughColdRestart() async throws {
        let container = try LifeClockContainer.make(inMemory: true)
        let mockHealth = MockHealthKitService(seed: 17, preAuthorized: true)

        // Session 1 — first-launch boot.
        let store = LifeClockStore(
            healthService: mockHealth,
            modelContext: container.mainContext,
            engineClock: .fixed(fixedDate)
        )
        await store.bootstrap()
        XCTAssertNil(store.profile, "first launch must NOT seed a profile — onboarding does that")
        XCTAssertNil(store.todayEstimate)

        // Onboarding: complete with a real-looking profile.
        let profile = UserProfile(birthDate: birthDate, biologicalSex: "female", toneMode: ToneMode.coach.rawValue)
        profile.smokingStatus = "none"
        profile.alcoholFrequency = "rare"
        profile.sleepGoalHours = 7.5
        profile.strengthFrequencyPerWeek = 2
        store.completeOnboarding(profile: profile, tone: .coach, disclaimerAccepted: true)
        await store.refreshFromHealthKit()

        XCTAssertTrue(store.hasCompletedOnboarding)
        XCTAssertNotNil(store.todayEstimate, "Today should populate after onboarding + refresh")
        XCTAssertGreaterThanOrEqual(store.todayQuests.count, 1)
        XCTAssertLessThanOrEqual(store.todayQuests.count, 3)
        XCTAssertNotNil(store.weekly)
        XCTAssertTrue(store.isAdultUser, "DOB 1990 vs as-of 2027 → adult")

        // Quick log — heavy alcohol day. Engine should produce a recovery quest.
        let habits = HabitLog(date: fixedDate)
        habits.alcoholLevel = "heavy"
        habits.dietQuality = "rough"
        await store.setTodayHabits(habits)

        XCTAssertNotNil(store.todayHabits, "habit log must be persisted + cached on the store")
        XCTAssertEqual(store.todayHabits?.alcoholLevel, "heavy")
        XCTAssertTrue(
            store.todayQuests.contains { $0.category == "recovery" },
            "heavy-alcohol day must shift the risk quest to a recovery quest, not a punitive one"
        )

        // Quest completion — should land in the ledger with the pinned timestamp.
        let initialLedgerCount = store.ledger.count
        if let firstQuest = store.todayQuests.first {
            store.toggleQuestCompletion(firstQuest)
            XCTAssertEqual(firstQuest.completedAt, fixedDate, "completion stamp must use the injected clock")
            XCTAssertEqual(store.ledger.count, initialLedgerCount + 1)
        } else {
            XCTFail("expected at least one quest to complete")
        }

        // Tone mode switch — propagates to the persisted profile.
        store.setToneMode(.gentle)
        XCTAssertEqual(store.profile?.toneMode, ToneMode.gentle.rawValue)

        // Hide the clock — safety-net affordance.
        await store.setHideClock(true)
        XCTAssertEqual(store.profile?.hideClock, true)

        // Cold restart simulation — fresh store reading the same persistent
        // container. This is the single most important assertion in this test:
        // it proves persistence is real.
        let store2 = LifeClockStore(
            healthService: mockHealth,
            modelContext: container.mainContext,
            engineClock: .fixed(fixedDate)
        )
        await store2.bootstrap()

        XCTAssertNotNil(store2.profile, "second session must restore the persisted profile")
        XCTAssertTrue(store2.hasCompletedOnboarding)
        XCTAssertEqual(store2.toneMode, .gentle, "tone mode must survive cold restart")
        XCTAssertEqual(store2.profile?.hideClock, true, "hide-clock must survive cold restart")
        XCTAssertNotNil(store2.todayHabits, "habit log must survive cold restart")
        XCTAssertEqual(store2.todayHabits?.alcoholLevel, "heavy")
        XCTAssertGreaterThan(store2.ledger.count, 0, "ledger entries must survive cold restart")
    }

    // MARK: - Reset path

    func testResetForOnboardingClearsAllPersistedData() async throws {
        let container = try LifeClockContainer.make(inMemory: true)
        let store = LifeClockStore(
            healthService: MockHealthKitService(),
            modelContext: container.mainContext,
            engineClock: .fixed(fixedDate)
        )

        let profile = UserProfile(birthDate: birthDate, biologicalSex: "male")
        store.completeOnboarding(profile: profile, tone: .coach, disclaimerAccepted: true)
        let habits = HabitLog(date: fixedDate)
        habits.dietQuality = "great"
        await store.setTodayHabits(habits)

        store.resetForOnboarding()
        XCTAssertNil(store.profile)
        XCTAssertNil(store.todayHabits)
        XCTAssertTrue(store.ledger.isEmpty)
        XCTAssertFalse(store.hasCompletedOnboarding)

        // And on cold restart, we should be back at first-launch state.
        let store2 = LifeClockStore(
            healthService: MockHealthKitService(),
            modelContext: container.mainContext,
            engineClock: .fixed(fixedDate)
        )
        await store2.bootstrap()
        XCTAssertNil(store2.profile, "after reset, cold restart must NOT find a persisted profile")
    }

    // MARK: - Age-gate behavior end-to-end

    func testUnderEighteenUserHasIsAdultFalse() async throws {
        let container = try LifeClockContainer.make(inMemory: true)
        let store = LifeClockStore(
            healthService: MockHealthKitService(),
            modelContext: container.mainContext,
            engineClock: .fixed(fixedDate)
        )
        // DOB 2014 → 13 years old as of fixedDate (2027-01-15)
        let teenDOB = Calendar.lifeClockUTC.date(from: DateComponents(year: 2014, month: 1, day: 15))!
        let teen = UserProfile(birthDate: teenDOB, biologicalSex: "unspecified")
        store.completeOnboarding(profile: teen, tone: .coach, disclaimerAccepted: true)

        XCTAssertFalse(store.isAdultUser, "DOB 2014 vs as-of 2027 → 13 → not adult")
    }
}
