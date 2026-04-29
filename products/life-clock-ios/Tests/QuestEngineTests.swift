import XCTest
@testable import LifeClock

final class QuestEngineTests: XCTestCase {
    private let fixedDate = Date(timeIntervalSince1970: 1_800_000_000)
    private let birthDate = Date(timeIntervalSince1970: 631_152_000)

    private func makeEngine() -> QuestEngine {
        QuestEngine(clock: .fixed(fixedDate))
    }

    private func makeProfile() -> UserProfile {
        UserProfile(birthDate: birthDate, biologicalSex: "female")
    }

    // MARK: - Quest count invariant

    func testReturnsBetweenOneAndThreeQuests() {
        let engine = makeEngine()
        let profile = makeProfile()
        let quests = engine.generateDailyQuests(profile: profile, snapshot: nil, habits: nil)
        XCTAssertGreaterThanOrEqual(quests.count, 1)
        XCTAssertLessThanOrEqual(quests.count, 3)
    }

    // MARK: - Determinism

    func testSameInputsProduceSameQuests() {
        let engine = makeEngine()
        let profile = makeProfile()
        let a = engine.generateDailyQuests(profile: profile, snapshot: nil, habits: nil)
        let b = engine.generateDailyQuests(profile: profile, snapshot: nil, habits: nil)
        XCTAssertEqual(a.map(\.title), b.map(\.title))
    }

    // MARK: - Missing data fallback

    func testNoSnapshotProducesManualLogFriendlyQuests() {
        let engine = makeEngine()
        let profile = makeProfile()
        let quests = engine.generateDailyQuests(profile: profile, snapshot: nil, habits: nil)
        // No HealthKit data ⇒ a movement quest still appears, but its detail
        // copy doesn't reference a step number the user hasn't seen.
        let movement = quests.first { $0.category == "movement" }
        XCTAssertNotNil(movement)
        if let movement {
            XCTAssertFalse(movement.detail.contains("Get to"))
        }
    }

    // MARK: - Adaptation to logged habits

    func testHeavyAlcoholDayShiftsRiskQuestToRecovery() {
        let engine = makeEngine()
        let profile = makeProfile()
        let habits = HabitLog(date: fixedDate)
        habits.alcoholLevel = "heavy"

        let quests = engine.generateDailyQuests(profile: profile, snapshot: nil, habits: habits)
        let recovery = quests.first { $0.category == "recovery" }
        XCTAssertNotNil(recovery, "Heavy-alcohol day should produce a recovery quest, not a punitive one")
    }

    func testCompletedStepGoalSkipsMovementQuest() {
        let engine = makeEngine()
        let profile = makeProfile()
        let snapshot = DailyHealthSnapshot(date: fixedDate)
        snapshot.stepCount = 12_000
        snapshot.sleepHours = 7.5
        snapshot.sourceCompleteness = 0.8

        let quests = engine.generateDailyQuests(profile: profile, snapshot: snapshot, habits: nil)
        XCTAssertNil(quests.first { $0.category == "movement" })
        XCTAssertGreaterThanOrEqual(quests.count, 1)
    }

    // MARK: - No medical recommendations

    func testNoQuestRecommendsMedicationOrSupplements() {
        let engine = makeEngine()
        let profile = makeProfile()
        let quests = engine.generateDailyQuests(profile: profile, snapshot: nil, habits: nil)
        let blacklist = ["medication", "supplement", "prescribe", "diagnose", "cure"]
        for quest in quests {
            let combined = (quest.title + " " + quest.detail).lowercased()
            for term in blacklist {
                XCTAssertFalse(combined.contains(term), "Quest copy must never mention '\(term)': \(combined)")
            }
        }
    }
}
