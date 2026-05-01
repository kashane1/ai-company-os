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
}
