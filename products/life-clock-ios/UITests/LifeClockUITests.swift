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
        XCTAssertTrue(app.buttons["Update Life Clock"].exists)
        app.buttons["checkIn.save"].tap()

        XCTAssertTrue(app.staticTexts["Life Clock updated."].waitForExistence(timeout: 5))
        XCTAssertTrue(app.staticTexts["Your daily signals are in."].waitForExistence(timeout: 5))

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

    /// Phase 2.C: paywall must be dismissible by an agent. Purchase
    /// (paywall.subscribe) is intentionally not exposed to XCUITest.
    func testPaywallCloseIsAgentDriveable() throws {
        app = XCUIApplication()
        app.launchEnvironment["LIFECLOCK_UI_TEST"] = "1"
        app.launchEnvironment["LIFECLOCK_UI_TEST_SCENARIO"] = "onboarded"
        app.launchEnvironment["LIFECLOCK_USE_MOCK_HEALTH"] = "1"
        app.launchEnvironment["LIFECLOCK_FORCE_PAYWALL"] = "1"
        app.launch()

        let close = app.buttons["paywall.close"]
        XCTAssertTrue(close.waitForExistence(timeout: 8),
                      "paywall.close must exist so agents can audit the paywall surface")
        close.tap()
        // Confirm sheet dismissed: paywall.close should no longer exist.
        let stillVisible = close.waitForExistence(timeout: 2)
        XCTAssertFalse(stillVisible, "paywall should dismiss after tapping paywall.close")
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
