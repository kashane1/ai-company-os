import XCTest
@testable import LifeClock

/// Phase 2.B contract tests. The presenter is pure-value and side-effect-free,
/// so these tests run without a `ModelContainer` and are byte-precise on copy.
final class SupportMomentPresenterTests: XCTestCase {
    private let presenter = SupportMomentPresenter()

    func testOnboardingComplete() {
        let moment = presenter.moment(for: .onboardingComplete, tone: .coach)
        XCTAssertEqual(moment.title, "You're set.")
        XCTAssertEqual(moment.tone, .calm)
    }

    /// Quest completed under Coach tone uses the today-focused payoff
    /// line that matches what the user just saw on the persist-banked
    /// clock.
    func testQuestCompleted_CoachUsesTodayFocusedTonePayoff() {
        let moment = presenter.moment(for: .questCompleted(rewardMinutes: 18), tone: .coach)
        XCTAssertEqual(moment.title, "Nice work.")
        XCTAssertEqual(moment.tone, .celebration)
        XCTAssertEqual(moment.detail, "+18 min on the clock.")
    }

    /// Gentle tone variant of the same intent.
    func testQuestCompleted_GentleUsesTodayFocusedTonePayoff() {
        let moment = presenter.moment(for: .questCompleted(rewardMinutes: 18), tone: .gentle)
        XCTAssertEqual(moment.detail, "Your clock just moved +18 min.")
    }

    /// Firm/Direct tone variant.
    func testQuestCompleted_FirmDirectUsesTodayFocusedTonePayoff() {
        let moment = presenter.moment(for: .questCompleted(rewardMinutes: 18), tone: .firmDirect)
        XCTAssertEqual(moment.detail, "+18 min. On the clock.")
    }

    func testQuestUndoneIsCalm() {
        let moment = presenter.moment(for: .questUndone, tone: .coach)
        XCTAssertEqual(moment.title, "Action removed.")
        XCTAssertEqual(moment.tone, .calm)
    }

    func testCheckInPositiveDeltaWinsOverStrengthAndPrior() {
        let moment = presenter.moment(for: .checkInSaved(
            deltaMinutes: 12,
            strengthLogged: true,
            hadPriorCheckIn: true
        ), tone: .coach)
        XCTAssertEqual(moment.title, "Life Clock updated.")
        XCTAssertEqual(moment.tone, .celebration)
        XCTAssertTrue(moment.detail.contains("Today's signals moved your Life Clock"))
    }

    func testCheckInStrengthOnly() {
        let moment = presenter.moment(for: .checkInSaved(
            deltaMinutes: 0,
            strengthLogged: true,
            hadPriorCheckIn: false
        ), tone: .coach)
        XCTAssertEqual(moment.title, "Life Clock updated.")
        XCTAssertEqual(moment.tone, .celebration)
        XCTAssertEqual(moment.detail, "Strength is in for today. Small wins compound over time.")
    }

    func testCheckInUpdatedAfterPriorButNoDeltaOrStrength() {
        let moment = presenter.moment(for: .checkInSaved(
            deltaMinutes: 0,
            strengthLogged: false,
            hadPriorCheckIn: true
        ), tone: .coach)
        XCTAssertEqual(moment.title, "Life Clock updated.")
        XCTAssertEqual(moment.tone, .calm)
        XCTAssertEqual(moment.detail, "Your daily signals are in. This is feedback, not failure.")
    }

    func testCheckInSavedFirstTime() {
        let moment = presenter.moment(for: .checkInSaved(
            deltaMinutes: 0,
            strengthLogged: false,
            hadPriorCheckIn: false
        ), tone: .coach)
        XCTAssertEqual(moment.title, "Life Clock updated.")
        XCTAssertEqual(moment.tone, .calm)
        XCTAssertEqual(moment.detail, "Your daily signals are in. This is feedback, not failure.")
    }
}
