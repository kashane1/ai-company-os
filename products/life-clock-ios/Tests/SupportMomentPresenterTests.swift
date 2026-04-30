import XCTest
@testable import LifeClock

/// Phase 2.B contract tests. The presenter is pure-value and side-effect-free,
/// so these tests run without a `ModelContainer` and are byte-precise on copy.
final class SupportMomentPresenterTests: XCTestCase {
    private let presenter = SupportMomentPresenter()

    func testOnboardingComplete() {
        let moment = presenter.moment(for: .onboardingComplete)
        XCTAssertEqual(moment?.title, "You're set.")
        XCTAssertEqual(moment?.tone, .calm)
    }

    func testQuestCompletedIsCelebrationWithReward() {
        let moment = presenter.moment(for: .questCompleted(rewardMinutes: 18))
        XCTAssertEqual(moment?.title, "Nice work.")
        XCTAssertEqual(moment?.tone, .celebration)
        XCTAssertTrue(moment?.detail.contains("Possible impact:") ?? false)
    }

    func testQuestUndoneIsCalm() {
        let moment = presenter.moment(for: .questUndone)
        XCTAssertEqual(moment?.title, "Action removed.")
        XCTAssertEqual(moment?.tone, .calm)
    }

    func testCheckInPositiveDeltaWinsOverStrengthAndPrior() {
        let moment = presenter.moment(for: .checkInSaved(
            deltaMinutes: 12,
            strengthLogged: true,
            hadPriorCheckIn: true
        ))
        XCTAssertEqual(moment?.title, "Nice work.")
        XCTAssertEqual(moment?.tone, .celebration)
        XCTAssertTrue(moment?.detail.contains("Your check-in moved today's progress") ?? false)
    }

    func testCheckInStrengthOnly() {
        let moment = presenter.moment(for: .checkInSaved(
            deltaMinutes: 0,
            strengthLogged: true,
            hadPriorCheckIn: false
        ))
        XCTAssertEqual(moment?.title, "Strength training logged.")
        XCTAssertEqual(moment?.tone, .celebration)
    }

    func testCheckInUpdatedAfterPriorButNoDeltaOrStrength() {
        let moment = presenter.moment(for: .checkInSaved(
            deltaMinutes: 0,
            strengthLogged: false,
            hadPriorCheckIn: true
        ))
        XCTAssertEqual(moment?.title, "Check-in updated.")
        XCTAssertEqual(moment?.tone, .calm)
    }

    func testCheckInSavedFirstTime() {
        let moment = presenter.moment(for: .checkInSaved(
            deltaMinutes: 0,
            strengthLogged: false,
            hadPriorCheckIn: false
        ))
        XCTAssertEqual(moment?.title, "Check-in saved.")
        XCTAssertEqual(moment?.tone, .calm)
    }

    func testResetReturnsNil() {
        XCTAssertNil(presenter.moment(for: .reset))
    }
}
