import XCTest
@testable import LifeClock

/// Tests for the diet-quality alignment pass.
///
/// Three principles under test:
///   1. Diet quality is a real, bounded driver in the daily delta.
///   2. Missing diet input never penalizes — never a negative ledger entry
///      from absence.
///   3. Nutrition quests surface coarse, encouraging copy with no calorie /
///      macro / named-diet vocabulary.
final class DietAlignmentTests: XCTestCase {
    private let fixedDate = Date(timeIntervalSince1970: 1_800_000_000)
    private let birthDate = Date(timeIntervalSince1970: 631_152_000)

    // MARK: - ClockEngine: daily delta

    func testGreatDietProducesSmallPositiveDeltaWithLedgerEntry() {
        let engine = ClockEngine(clock: .fixed(fixedDate))
        let profile = UserProfile(birthDate: birthDate, biologicalSex: "female")
        let snapshot = DailyHealthSnapshot(date: fixedDate)
        snapshot.sourceCompleteness = 0.4
        let habits = HabitLog(date: fixedDate)
        habits.dietQuality = "great"

        let result = engine.calculateDailyDelta(snapshot: snapshot, habits: habits, profile: profile)
        let dietDriver = result.drivers.first { $0.driverType == "diet" }
        XCTAssertNotNil(dietDriver, "great diet should produce a ledger entry")
        XCTAssertGreaterThan(dietDriver?.deltaMinutes ?? 0, 0)
        XCTAssertLessThanOrEqual(dietDriver?.deltaMinutes ?? 0, 15, "diet delta is bounded — single rough day must not swing the clock")
        XCTAssertEqual(dietDriver?.source, "manual", "diet entries are self-reported")
        XCTAssertEqual(dietDriver?.confidenceRaw, Confidence.medium.rawValue)
    }

    func testRoughDietProducesSmallNegativeDelta() {
        let engine = ClockEngine(clock: .fixed(fixedDate))
        let profile = UserProfile(birthDate: birthDate, biologicalSex: "female")
        let snapshot = DailyHealthSnapshot(date: fixedDate)
        snapshot.sourceCompleteness = 0.4
        let habits = HabitLog(date: fixedDate)
        habits.dietQuality = "rough"

        let result = engine.calculateDailyDelta(snapshot: snapshot, habits: habits, profile: profile)
        let dietDriver = result.drivers.first { $0.driverType == "diet" }
        XCTAssertNotNil(dietDriver)
        XCTAssertLessThan(dietDriver?.deltaMinutes ?? 0, 0)
        // Bounded — never more punitive than a heavy-alcohol day.
        XCTAssertGreaterThanOrEqual(dietDriver?.deltaMinutes ?? 0, -15)
    }

    func testMissingDietQualityDoesNotProduceNegativeEntry() {
        // Caller passes nil habits — no log at all.
        let engine = ClockEngine(clock: .fixed(fixedDate))
        let profile = UserProfile(birthDate: birthDate, biologicalSex: "female")
        let snapshot = DailyHealthSnapshot(date: fixedDate)
        snapshot.stepCount = 9_000
        snapshot.sourceCompleteness = 0.4

        let result = engine.calculateDailyDelta(snapshot: snapshot, habits: nil, profile: profile)
        XCTAssertNil(result.drivers.first { $0.driverType == "diet" }, "missing diet input must not generate a diet driver")
        XCTAssertGreaterThanOrEqual(result.deltaMinutes, 0, "movement-only day with no diet log shouldn't be penalized")
    }

    func testOkayDietIsNeutral() {
        let engine = ClockEngine(clock: .fixed(fixedDate))
        let profile = UserProfile(birthDate: birthDate, biologicalSex: "female")
        let snapshot = DailyHealthSnapshot(date: fixedDate)
        snapshot.sourceCompleteness = 0.4
        let habits = HabitLog(date: fixedDate)
        habits.dietQuality = "okay"

        let result = engine.calculateDailyDelta(snapshot: snapshot, habits: habits, profile: profile)
        XCTAssertNil(result.drivers.first { $0.driverType == "diet" }, "okay diet is neutral — no ledger noise")
    }

    // MARK: - ClockEngine: baseline factors diet quality

    func testGreatDietBaselineHigherThanRoughDietBaseline() {
        let engine = ClockEngine(clock: .fixed(fixedDate))
        let great = UserProfile(birthDate: birthDate, biologicalSex: "female")
        great.dietQualityBaseline = "great"
        let rough = UserProfile(birthDate: birthDate, biologicalSex: "female")
        rough.dietQualityBaseline = "rough"

        let g = engine.calculateBaseline(profile: great)
        let r = engine.calculateBaseline(profile: rough)
        XCTAssertGreaterThan(g.projectedAgeYears, r.projectedAgeYears)
        // Bounded baseline difference — not a clinical claim.
        XCTAssertLessThanOrEqual(g.projectedAgeYears - r.projectedAgeYears, 5.0)
    }

    // MARK: - QuestEngine: nutrition quests

    func testNoLogYieldsLogYourDietQuest() {
        let engine = QuestEngine(clock: .fixed(fixedDate))
        let profile = UserProfile(birthDate: birthDate, biologicalSex: "female")

        let quests = engine.generateDailyQuests(profile: profile, snapshot: nil, habits: nil)
        let nutritionQuest = quests.first { $0.category == "nutrition" }
        XCTAssertNotNil(nutritionQuest, "no habits logged should still produce a nutrition quest")
        XCTAssertTrue(
            nutritionQuest?.title.lowercased().contains("log your diet") ?? false,
            "the no-log path should nudge logging, not preach"
        )
    }

    func testRoughDietProducesGentleRepairQuest() {
        let engine = QuestEngine(clock: .fixed(fixedDate))
        let profile = UserProfile(birthDate: birthDate, biologicalSex: "female")
        let habits = HabitLog(date: fixedDate)
        habits.dietQuality = "rough"

        let quests = engine.generateDailyQuests(profile: profile, snapshot: nil, habits: habits)
        let repairQuest = quests.first { $0.category == "nutrition" }
        XCTAssertNotNil(repairQuest)
        let combined = (repairQuest?.title ?? "" + " " + (repairQuest?.detail ?? "")).lowercased()
        XCTAssertTrue(
            combined.contains("feedback") || combined.contains("better meal") || combined.contains("one"),
            "rough-diet quest should be encouraging, not punitive"
        )
    }

    func testNutritionQuestsContainNoCalorieOrMacroLanguage() {
        let engine = QuestEngine(clock: .fixed(fixedDate))
        let profile = UserProfile(birthDate: birthDate, biologicalSex: "female")
        let habits = HabitLog(date: fixedDate)
        habits.dietQuality = "great" // forces rotating quest path

        let quests = engine.generateDailyQuests(profile: profile, snapshot: nil, habits: habits)
        let blacklist = [
            "calorie", "calories", "kcal",
            "macro", "macros", "gram", "grams",
            "keto", "paleo", "vegan", "carnivore", "atkins",
            "fast for", "fasting window",
            "clean food", "bad food", "junk food",
            "lose weight", "weight loss",
            "diet plan",
        ]
        for quest in quests {
            let combined = (quest.title + " " + quest.detail).lowercased()
            for term in blacklist {
                XCTAssertFalse(
                    combined.contains(term),
                    "nutrition quest copy must never use '\(term)': \(combined)"
                )
            }
        }
    }

    func testHeavyAlcoholStillTakesPriorityOverNutrition() {
        let engine = QuestEngine(clock: .fixed(fixedDate))
        let profile = UserProfile(birthDate: birthDate, biologicalSex: "female")
        let habits = HabitLog(date: fixedDate)
        habits.alcoholLevel = "heavy"
        habits.dietQuality = "rough"

        let quests = engine.generateDailyQuests(profile: profile, snapshot: nil, habits: habits)
        XCTAssertNotNil(quests.first { $0.category == "recovery" }, "heavy-alcohol day takes priority — recovery quest, not nutrition")
        XCTAssertNil(quests.first { $0.category == "nutrition" }, "no nutrition quest when recovery is the right move")
    }

    func testNutritionQuestsAreDeterministicForSameDay() {
        let engine1 = QuestEngine(clock: .fixed(fixedDate))
        let engine2 = QuestEngine(clock: .fixed(fixedDate))
        let profile = UserProfile(birthDate: birthDate, biologicalSex: "female")
        let habits = HabitLog(date: fixedDate)
        habits.dietQuality = "great"

        let q1 = engine1.generateDailyQuests(profile: profile, snapshot: nil, habits: habits).map(\.title)
        let q2 = engine2.generateDailyQuests(profile: profile, snapshot: nil, habits: habits).map(\.title)
        XCTAssertEqual(q1, q2, "same day, same inputs → same quests (no Date()/random leakage)")
    }
}
