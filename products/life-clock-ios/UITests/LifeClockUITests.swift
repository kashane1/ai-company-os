import XCTest

final class LifeClockUITests: XCTestCase {
    private var app: XCUIApplication!

    override func setUpWithError() throws {
        continueAfterFailure = false
    }

    func testOnboardingFlowLeadsIntoSupportiveTodayExperience() throws {
        launchApp(scenario: "onboarding")

        XCTAssertTrue(app.otherElements["onboarding.value"].waitForExistence(timeout: 5))
        app.buttons["onboarding.continue"].tap()

        XCTAssertTrue(app.otherElements["onboarding.safety"].waitForExistence(timeout: 5))
        app.switches["onboarding.disclaimerToggle"].tap()
        app.buttons["onboarding.continue"].tap()

        XCTAssertTrue(app.otherElements["onboarding.baseline"].waitForExistence(timeout: 5))
        app.buttons["onboarding.continue"].tap()

        XCTAssertTrue(app.otherElements["onboarding.tone"].waitForExistence(timeout: 5))
        app.buttons["onboarding.tone.coach"].tap()
        app.buttons["onboarding.continue"].tap()

        XCTAssertTrue(app.otherElements["onboarding.health"].waitForExistence(timeout: 5))
        app.buttons["onboarding.connectHealth"].tap()
        app.buttons["onboarding.continue"].tap()

        XCTAssertTrue(app.otherElements["onboarding.reveal"].waitForExistence(timeout: 5))
        app.buttons["onboarding.finish"].tap()

        XCTAssertTrue(app.navigationBars["Today's progress"].waitForExistence(timeout: 5))
        XCTAssertTrue(app.buttons["Plan"].exists)
        XCTAssertFalse(app.buttons["Quests"].exists)
        XCTAssertTrue(app.staticTexts["Save today's check-in"].exists)
    }

    func testDailyCheckInShowsSupportMomentAndNavigationStillWorks() throws {
        launchApp(scenario: "onboarded")

        XCTAssertTrue(app.buttons["today.checkInCard"].waitForExistence(timeout: 5))
        app.buttons["today.checkInCard"].tap()

        XCTAssertTrue(app.buttons["checkIn.save"].waitForExistence(timeout: 5))
        app.buttons["checkIn.save"].tap()

        XCTAssertTrue(app.staticTexts["Check-in saved."].waitForExistence(timeout: 5))
        XCTAssertTrue(app.staticTexts["Your daily check-in is saved."].waitForExistence(timeout: 5))

        app.buttons["Progress"].tap()
        XCTAssertTrue(app.navigationBars["Progress"].waitForExistence(timeout: 5))
    }

    func testPlanCompletionUpdatesMomentumAndProgressLog() throws {
        launchApp(scenario: "onboarded")

        app.buttons["Plan"].tap()
        XCTAssertTrue(app.navigationBars["Plan"].waitForExistence(timeout: 5))
        XCTAssertTrue(app.buttons["plan.complete.0"].waitForExistence(timeout: 5))
        app.buttons["plan.complete.0"].tap()

        app.buttons["Today"].tap()
        XCTAssertTrue(app.staticTexts["Nice work."].waitForExistence(timeout: 5))
        XCTAssertTrue(app.staticTexts.containing("1 of").firstMatch.waitForExistence(timeout: 5))

        app.buttons["Progress"].tap()
        XCTAssertTrue(app.navigationBars["Progress"].waitForExistence(timeout: 5))
        XCTAssertTrue(app.staticTexts.containing("Completed action:").firstMatch.waitForExistence(timeout: 5))
    }

    private func launchApp(scenario: String) {
        app = XCUIApplication()
        app.launchEnvironment["LIFECLOCK_UI_TEST"] = "1"
        app.launchEnvironment["LIFECLOCK_UI_TEST_SCENARIO"] = scenario
        app.launchEnvironment["LIFECLOCK_USE_MOCK_HEALTH"] = "1"
        app.launch()
    }
}

private extension XCUIElementQuery {
    func containing(_ substring: String) -> XCUIElementQuery {
        matching(NSPredicate(format: "label CONTAINS %@", substring))
    }
}
