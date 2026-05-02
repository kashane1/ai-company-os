import XCTest
@testable import LifeClock

final class CompletionBadgeEngineTests: XCTestCase {
    func testCatalogContainsManyPossibleBadges() {
        let badges = CompletionBadgeEngine().badges(for: CompletionBadgeProgress())

        XCTAssertGreaterThanOrEqual(badges.count, 40)
        XCTAssertTrue(badges.contains { $0.category == .movement })
        XCTAssertTrue(badges.contains { $0.category == .sleep })
        XCTAssertTrue(badges.contains { $0.category == .nutrition })
        XCTAssertTrue(badges.contains { $0.category == .dailyPlan })
    }

    func testUnlocksTieredBadgesFromProgress() {
        let badges = CompletionBadgeEngine().badges(for: CompletionBadgeProgress(
            onboardedAt: Date(timeIntervalSince1970: 1_800_000_000),
            completedQuestCount: 25,
            completedQuestDays: 7,
            threeQuestDays: 1,
            checkInDays: 7,
            dietLoggingStreakDays: 3,
            supportiveDietDays: 7,
            greatDietDays: 1,
            lowRiskRecoveryDays: 7,
            strengthDays: 1,
            stepTargetDays: 7,
            tenThousandStepDays: 1,
            exerciseTargetDays: 7,
            sleepGoalDays: 7,
            positiveWeekCount: 1,
            dataRichDays: 7,
            healthConnected: true,
            reminderEnabled: true
        ))

        XCTAssertTrue(badges.first { $0.id == "plan.completed.25" }?.isUnlocked == true)
        XCTAssertTrue(badges.first { $0.id == "movement.steps7500.7" }?.isUnlocked == true)
        XCTAssertTrue(badges.first { $0.id == "sleep.goal.7" }?.isUnlocked == true)
        XCTAssertTrue(badges.first { $0.id == "plan.completed.50" }?.isUnlocked == false)
    }
}
