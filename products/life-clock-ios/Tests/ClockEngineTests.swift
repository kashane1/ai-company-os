import XCTest
@testable import LifeClock

final class ClockEngineTests: XCTestCase {
    private let fixedDate = Date(timeIntervalSince1970: 1_800_000_000) // 2027-01-15
    private let birthDate = Date(timeIntervalSince1970: 631_152_000)   // 1990-01-01

    private func makeEngine() -> ClockEngine {
        ClockEngine(clock: .fixed(fixedDate))
    }

    // MARK: - Determinism

    func testBaselineIsDeterministic() {
        let engine = makeEngine()
        let profile = UserProfile(birthDate: birthDate, biologicalSex: "male")
        let a = engine.calculateBaseline(profile: profile)
        let b = engine.calculateBaseline(profile: profile)
        XCTAssertEqual(a.projectedAgeYears, b.projectedAgeYears, accuracy: 0.0001)
        XCTAssertEqual(a.healthspanScore, b.healthspanScore, accuracy: 0.0001)
    }

    // MARK: - Population anchors

    func testFemaleBaselineHigherThanMaleByCDCMargin() {
        let engine = makeEngine()
        let male = UserProfile(birthDate: birthDate, biologicalSex: "male")
        let female = UserProfile(birthDate: birthDate, biologicalSex: "female")
        let m = engine.calculateBaseline(profile: male)
        let f = engine.calculateBaseline(profile: female)
        // CDC anchors: 76.5 male / 81.4 female. Difference is ~4.9 years.
        XCTAssertGreaterThan(f.projectedAgeYears - m.projectedAgeYears, 4.0)
        XCTAssertLessThan(f.projectedAgeYears - m.projectedAgeYears, 6.0)
    }

    func testHeavySmokerBaselineLowerThanNonSmoker() {
        let engine = makeEngine()
        let nonSmoker = UserProfile(birthDate: birthDate, biologicalSex: "male")
        let smoker = UserProfile(birthDate: birthDate, biologicalSex: "male")
        smoker.smokingStatus = "heavy"
        let nonResult = engine.calculateBaseline(profile: nonSmoker)
        let smokerResult = engine.calculateBaseline(profile: smoker)
        XCTAssertLessThan(smokerResult.projectedAgeYears, nonResult.projectedAgeYears)
    }

    // MARK: - Daily delta

    func testGoodDayProducesPositiveDelta() {
        let engine = makeEngine()
        let profile = UserProfile(birthDate: birthDate, biologicalSex: "female")
        let snapshot = DailyHealthSnapshot(date: fixedDate)
        snapshot.stepCount = 11_000
        snapshot.exerciseMinutes = 35
        snapshot.sleepHours = 7.8
        snapshot.sourceCompleteness = 0.8

        let result = engine.calculateDailyDelta(snapshot: snapshot, habits: nil, profile: profile)
        XCTAssertGreaterThan(result.deltaMinutes, 0)
        XCTAssertEqual(result.confidence, .high)
        XCTAssertFalse(result.drivers.isEmpty)
    }

    func testBadDayProducesNegativeDelta() {
        let engine = makeEngine()
        let profile = UserProfile(birthDate: birthDate, biologicalSex: "female")
        let snapshot = DailyHealthSnapshot(date: fixedDate)
        snapshot.stepCount = 1_500
        snapshot.exerciseMinutes = 0
        snapshot.sleepHours = 4.5
        snapshot.sourceCompleteness = 0.6

        let habits = HabitLog(date: fixedDate)
        habits.alcoholLevel = "heavy"
        habits.smokingVaping = true

        let result = engine.calculateDailyDelta(snapshot: snapshot, habits: habits, profile: profile)
        XCTAssertLessThan(result.deltaMinutes, 0)
    }

    func testMissingDataDoesNotCrashOrPenalize() {
        let engine = makeEngine()
        let profile = UserProfile(birthDate: birthDate, biologicalSex: "unspecified")
        let empty = DailyHealthSnapshot(date: fixedDate) // all nil
        empty.sourceCompleteness = 0.0

        let result = engine.calculateDailyDelta(snapshot: empty, habits: nil, profile: profile)
        XCTAssertEqual(result.deltaMinutes, 0)
        XCTAssertEqual(result.confidence, .low)
        XCTAssertTrue(result.drivers.isEmpty)
    }

    // MARK: - Weekly trend smoothing

    func testWeeklyTrendDampensSingleBadDay() {
        let engine = makeEngine()
        let profile = UserProfile(birthDate: birthDate, biologicalSex: "female")
        let cal = Calendar.lifeClockUTC

        var snapshots: [DailyHealthSnapshot] = []
        for offset in 0..<7 {
            let day = cal.date(byAdding: .day, value: -offset, to: fixedDate)!
            let s = DailyHealthSnapshot(date: cal.startOfDay(for: day))
            // 6 good days, 1 bad
            if offset == 3 {
                s.stepCount = 1_500
                s.sleepHours = 4.0
            } else {
                s.stepCount = 9_000
                s.exerciseMinutes = 25
                s.sleepHours = 7.6
            }
            s.sourceCompleteness = 0.8
            snapshots.append(s)
        }

        let report = engine.calculateWeeklyTrend(snapshots: snapshots, habits: [], profile: profile)
        // 6 good days should outweigh 1 bad day.
        XCTAssertGreaterThan(report.netTimeDeltaMinutes, 0)
        XCTAssertEqual(report.confidenceRaw, Confidence.high.rawValue)
    }

    // Regression: LifeClockStore.refreshFromHealthKit() previously passed
    // habits: [] to calculateWeeklyTrend, so habit-driven adjustments
    // (smoking-vaping penalty, strength training credit, etc.) silently
    // dropped out of the weekly net. This test pins the engine: feeding
    // habits with strong negative signals must produce a strictly lower
    // weekly net than feeding []. If this test fails, somebody re-introduced
    // habits: [] in the store call site.
    func testWeeklyTrendIncorporatesHabits() {
        let engine = makeEngine()
        let profile = UserProfile(birthDate: birthDate, biologicalSex: "male")
        let cal = Calendar.lifeClockUTC

        var snapshots: [DailyHealthSnapshot] = []
        var habits: [HabitLog] = []
        for offset in 0..<7 {
            let day = cal.startOfDay(for: cal.date(byAdding: .day, value: -offset, to: fixedDate)!)
            let s = DailyHealthSnapshot(date: day)
            s.stepCount = 9_000
            s.exerciseMinutes = 25
            s.sleepHours = 7.5
            s.sourceCompleteness = 0.8
            snapshots.append(s)

            let h = HabitLog(date: day)
            h.smokingVaping = true
            h.alcoholLevel = "heavy"
            h.dietQuality = "poor"
            habits.append(h)
        }

        let withoutHabits = engine.calculateWeeklyTrend(snapshots: snapshots, habits: [], profile: profile)
        let withHabits = engine.calculateWeeklyTrend(snapshots: snapshots, habits: habits, profile: profile)
        XCTAssertLessThan(
            withHabits.netTimeDeltaMinutes,
            withoutHabits.netTimeDeltaMinutes,
            "Heavy-smoking + heavy-alcohol + poor-diet habits must lower the weekly net vs. no habits"
        )
    }

    // MARK: - Diet rhythm composite (V1.2.0)

    /// With only `dietQuality` set and the new fields at their V1.2.0
    /// defaults (`right` / `unknown`), the diet driver must equal the
    /// pre-V1.2.0 single-axis behavior. Regression guard for existing
    /// user flows.
    func testDietLegacyBehaviorWhenOnlyQualitySet() {
        let engine = makeEngine()
        let profile = UserProfile(birthDate: birthDate, biologicalSex: "female")
        let snapshot = DailyHealthSnapshot(date: fixedDate)

        let great = HabitLog(date: fixedDate)
        great.dietQuality = "great"
        let greatResult = engine.calculateDailyDelta(snapshot: snapshot, habits: great, profile: profile)
        let greatDriver = greatResult.drivers.first { $0.driverType == "diet" }
        XCTAssertEqual(greatDriver?.deltaMinutes, 12)

        let rough = HabitLog(date: fixedDate)
        rough.dietQuality = "rough"
        let roughResult = engine.calculateDailyDelta(snapshot: snapshot, habits: rough, profile: profile)
        let roughDriver = roughResult.drivers.first { $0.driverType == "diet" }
        XCTAssertEqual(roughDriver?.deltaMinutes, -10)

        let okay = HabitLog(date: fixedDate)
        okay.dietQuality = "okay"
        let okayResult = engine.calculateDailyDelta(snapshot: snapshot, habits: okay, profile: profile)
        XCTAssertNil(
            okayResult.drivers.first { $0.driverType == "diet" },
            "All-default diet inputs must produce no ledger entry"
        )
    }

    /// `quality=okay` + `rhythm=skipBinge` legitimately produces a non-zero
    /// composite (-5). The pre-V1.2.0 line-468 short-circuit dropped any
    /// "okay" entry; under the composite, it must surface — and at low
    /// confidence (only rhythm contributing).
    func testDietRhythmContributesWhenQualityIsOkay() {
        let engine = makeEngine()
        let profile = UserProfile(birthDate: birthDate, biologicalSex: "female")
        let snapshot = DailyHealthSnapshot(date: fixedDate)

        let habits = HabitLog(date: fixedDate)
        habits.dietQuality = "okay"
        habits.dietAmountRhythm = "skipBinge"

        let result = engine.calculateDailyDelta(snapshot: snapshot, habits: habits, profile: profile)
        let dietDriver = result.drivers.first { $0.driverType == "diet" }
        XCTAssertEqual(dietDriver?.deltaMinutes, -5)
        XCTAssertEqual(dietDriver?.confidenceRaw, Confidence.low.rawValue)
    }

    /// Symmetric to the rhythm test: `quality=okay` + `anchor=yes` produces
    /// `+3` at low confidence (only anchor contributing).
    func testDietAnchorContributesWhenQualityIsOkay() {
        let engine = makeEngine()
        let profile = UserProfile(birthDate: birthDate, biologicalSex: "female")
        let snapshot = DailyHealthSnapshot(date: fixedDate)

        let habits = HabitLog(date: fixedDate)
        habits.dietQuality = "okay"
        habits.wholeFoodMeal = "yes"

        let result = engine.calculateDailyDelta(snapshot: snapshot, habits: habits, profile: profile)
        let dietDriver = result.drivers.first { $0.driverType == "diet" }
        XCTAssertEqual(dietDriver?.deltaMinutes, 3)
        XCTAssertEqual(dietDriver?.confidenceRaw, Confidence.low.rawValue)
    }

    /// All three inputs at their V1.2.0 defaults must produce no ledger
    /// entry — the "missing data never penalizes" rule.
    func testDietAllDefaultsReturnsNil() {
        let engine = makeEngine()
        let profile = UserProfile(birthDate: birthDate, biologicalSex: "female")
        let snapshot = DailyHealthSnapshot(date: fixedDate)

        let habits = HabitLog(date: fixedDate)
        // dietQuality="okay", dietAmountRhythm="right", wholeFoodMeal="unknown"
        // are all property-level defaults — leave them.

        let result = engine.calculateDailyDelta(snapshot: snapshot, habits: habits, profile: profile)
        XCTAssertNil(
            result.drivers.first { $0.driverType == "diet" },
            "Default-only HabitLog must produce no diet ledger entry"
        )
    }
}
