import XCTest
@testable import LifeClock

/// Phase 3 of the quest-pool affinity engine
/// (docs/plans/2026-05-08-feat-quest-pool-phase-3-engines-plan.md).
///
/// Need-weight is "what the user's body is telling us today" — driven
/// by HealthKit baselines + onboarding. HK trumps onboarding self-report
/// on disagreement (master plan D7). These tests pin the threshold
/// bands so a refactor cannot silently re-band users.
final class NeedWeightEngineTests: XCTestCase {
    private let day1 = Date(timeIntervalSince1970: 1_800_000_000)
    private let birthDate = Date(timeIntervalSince1970: 631_152_000)

    private func makeProfile(
        sleepGoalHours: Double = 7.5,
        dietQualityBaseline: String = "okay",
        alcoholFrequency: String = "rare",
        cardioMinsPerWeek: Int = 0
    ) -> UserProfile {
        let p = UserProfile(birthDate: birthDate)
        p.sleepGoalHours = sleepGoalHours
        p.dietQualityBaseline = dietQualityBaseline
        p.alcoholFrequency = alcoholFrequency
        p.cardioMinsPerWeek = cardioMinsPerWeek
        return p
    }

    private func snapshot(stepCount: Int? = nil, sleepHours: Double? = nil, daysAgo: Int = 0) -> DailyHealthSnapshot {
        let date = Calendar.current.date(byAdding: .day, value: -daysAgo, to: day1)!
        let s = DailyHealthSnapshot(date: date)
        s.stepCount = stepCount
        s.sleepHours = sleepHours
        return s
    }

    // MARK: - Activity bands (HK steps p50)

    func testActivityNeedHighWhenStepsP50Below5k() {
        let snapshots = (0..<10).map { snapshot(stepCount: 3_000, daysAgo: $0) }
        let p = makeProfile()
        XCTAssertEqual(NeedWeightEngine.activityNeedWeight(profile: p, snapshots: snapshots), 0.9)
    }

    func testActivityNeedMediumWhenStepsP50Between5kAnd8k() {
        let snapshots = (0..<10).map { snapshot(stepCount: 6_000, daysAgo: $0) }
        let p = makeProfile()
        XCTAssertEqual(NeedWeightEngine.activityNeedWeight(profile: p, snapshots: snapshots), 0.6)
    }

    func testActivityNeedLowWhenStepsP50Above8k() {
        let snapshots = (0..<10).map { snapshot(stepCount: 12_000, daysAgo: $0) }
        let p = makeProfile()
        XCTAssertEqual(NeedWeightEngine.activityNeedWeight(profile: p, snapshots: snapshots), 0.3)
    }

    // MARK: - Sleep bands (HK sleep p50)

    func testSleepNeedHighWhenSleepP50Below6_5h() {
        let snapshots = (0..<10).map { snapshot(sleepHours: 5.5, daysAgo: $0) }
        let p = makeProfile()
        XCTAssertEqual(NeedWeightEngine.sleepNeedWeight(profile: p, snapshots: snapshots), 0.9)
    }

    func testSleepNeedMediumWhenSleepP50Between6_5And7_5h() {
        let snapshots = (0..<10).map { snapshot(sleepHours: 7.0, daysAgo: $0) }
        let p = makeProfile()
        XCTAssertEqual(NeedWeightEngine.sleepNeedWeight(profile: p, snapshots: snapshots), 0.6)
    }

    func testSleepNeedLowWhenSleepP50AtOrAbove7_5h() {
        let snapshots = (0..<10).map { snapshot(sleepHours: 8.0, daysAgo: $0) }
        let p = makeProfile()
        XCTAssertEqual(NeedWeightEngine.sleepNeedWeight(profile: p, snapshots: snapshots), 0.3)
    }

    // MARK: - HK trumps onboarding (master plan D7)

    func testHKHighStepsTrumpsHighCardioGoal() {
        // User self-reported 200 cardio min/week (> 150 threshold) but
        // HK shows steps p50 = 12k (low need band). HK wins → activity
        // need stays low regardless of self-report.
        let snapshots = (0..<10).map { snapshot(stepCount: 12_000, daysAgo: $0) }
        let p = makeProfile(cardioMinsPerWeek: 200)
        XCTAssertEqual(NeedWeightEngine.activityNeedWeight(profile: p, snapshots: snapshots), 0.3)
    }

    func testHKLowStepsTrumpsHighCardioGoalSelfReport() {
        // Reverse: user said "200 cardio min/week" but HK shows 2,400 steps
        // p50. HK wins → activity need is high.
        let snapshots = (0..<10).map { snapshot(stepCount: 2_400, daysAgo: $0) }
        let p = makeProfile(cardioMinsPerWeek: 200)
        XCTAssertEqual(NeedWeightEngine.activityNeedWeight(profile: p, snapshots: snapshots), 0.9)
    }

    // MARK: - Insufficient HK data fallback

    func testActivityFallsBackToOnboardingWhenHKThin() {
        // Only 3 days of HK data — below the 5-day minimum. Engine
        // falls back to cardioMinsPerWeek bands.
        let snapshots = (0..<3).map { snapshot(stepCount: 12_000, daysAgo: $0) }
        let p = makeProfile(cardioMinsPerWeek: 0)
        // 0 cardio mins → high activity need
        XCTAssertEqual(NeedWeightEngine.activityNeedWeight(profile: p, snapshots: snapshots), 0.9)
    }

    func testSleepFallsBackToSleepGoalHoursWhenHKThin() {
        let snapshots: [DailyHealthSnapshot] = []
        let p = makeProfile(sleepGoalHours: 6.0)
        // sleepGoalHours < 6.5 → high sleep need
        XCTAssertEqual(NeedWeightEngine.sleepNeedWeight(profile: p, snapshots: snapshots), 0.9)
    }

    // MARK: - Diet (no HK)

    func testDietNeedFromBaseline_rough() {
        let p = makeProfile(dietQualityBaseline: "rough")
        XCTAssertEqual(NeedWeightEngine.dietNeedWeight(profile: p), 0.9)
    }

    func testDietNeedFromBaseline_okay() {
        let p = makeProfile(dietQualityBaseline: "okay")
        XCTAssertEqual(NeedWeightEngine.dietNeedWeight(profile: p), 0.6)
    }

    func testDietNeedFromBaseline_great() {
        let p = makeProfile(dietQualityBaseline: "great")
        XCTAssertEqual(NeedWeightEngine.dietNeedWeight(profile: p), 0.3)
    }

    func testDietHeavyAlcoholOverridesToHigh() {
        let p = makeProfile(dietQualityBaseline: "great", alcoholFrequency: "heavy")
        // dietQualityBaseline says low (0.3), but heavy alcohol forces high (0.9).
        XCTAssertEqual(NeedWeightEngine.dietNeedWeight(profile: p), 0.9)
    }

    // MARK: - End-to-end compute

    func testComputeReturnsAllThreeGenres() {
        let snapshots = (0..<10).map { snapshot(stepCount: 6_000, sleepHours: 7.0, daysAgo: $0) }
        let p = makeProfile(dietQualityBaseline: "okay")
        let result = NeedWeightEngine.compute(profile: p, recentSnapshots: snapshots)
        XCTAssertNotNil(result[.activity])
        XCTAssertNotNil(result[.sleep])
        XCTAssertNotNil(result[.diet])
    }
}
