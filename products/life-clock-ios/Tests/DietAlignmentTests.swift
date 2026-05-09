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
    //
    // Phase 5b retired the legacy nutrition-variant pool. The behaviors
    // that previously lived here (no-log → log-your-diet, rough-diet
    // → repair, heavy-alcohol → recovery, no calorie/macro language)
    // are now properties of the authored diet pool, covered by:
    //   * `QuestPoolToneParityTests.testProductionPoolToneInvariants`
    //   * `QuestPoolTests.testProductionDietIntentGridIsFullyCovered`
    //   * `QuestPoolToneParityTests.testEveryDietSlugIsReachable`
    //
    // The ClockEngine ledger tests above remain — diet quality is still
    // a real driver in the daily delta math, independent of which quest
    // is surfaced.

    func testNutritionQuestsContainNoCalorieOrMacroLanguage() throws {
        let pool = try QuestPool.loadFromBundle(Bundle.main)
        let dietQuests = pool.quests(in: .diet)
        XCTAssertFalse(dietQuests.isEmpty, "Production diet pool expected non-empty")
        let blacklist = [
            "calorie", "calories", "kcal",
            "macro", "macros", "gram", "grams",
            "keto", "paleo", "vegan", "carnivore", "atkins",
            "fast for", "fasting window",
            "clean food", "bad food", "junk food",
            "lose weight", "weight loss",
            "diet plan",
        ]
        for quest in dietQuests {
            for tone in ToneMode.allCases {
                guard let copy = quest.copy[tone] else { continue }
                let combined = (copy.title + " " + copy.detail).lowercased()
                for term in blacklist {
                    XCTAssertFalse(
                        combined.contains(term),
                        "diet quest \(quest.slug) (\(tone.rawValue)) must never use '\(term)': \(combined)"
                    )
                }
            }
        }
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
