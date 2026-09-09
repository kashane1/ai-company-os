import XCTest

final class AfterPlansUITests: XCTestCase {
    private var app: XCUIApplication!

    override func setUpWithError() throws {
        continueAfterFailure = false
        app = XCUIApplication()
        app.launchEnvironment["AFTERPLANS_UI_TEST"] = "1"
        app.launchEnvironment["AFTERPLANS_BACKEND"] = "inMemory"
    }

    func testOnboardingCanCreateAnInviteOnlyPlanOffline() throws {
        app.launch()

        XCTAssertTrue(app.staticTexts["Keep the moment going."].waitForExistence(timeout: 8))
        for _ in 0..<5 {
            app.buttons["onboarding.intro.continue"].tap()
        }

        let firstName = app.textFields["onboarding.name.firstName"]
        XCTAssertTrue(firstName.waitForExistence(timeout: 5))
        firstName.tap()
        firstName.typeText("Sam")
        app.buttons["onboarding.name.continue"].tap()

        XCTAssertTrue(app.staticTexts["How visible should you be?"].waitForExistence(timeout: 5))
        app.buttons["onboarding.privacy.continue"].tap()

        XCTAssertTrue(app.staticTexts["What do you do — and where?"].waitForExistence(timeout: 5))
        app.buttons["onboarding.activity.continue"].tap()

        XCTAssertTrue(app.staticTexts["Did someone share a code?"].waitForExistence(timeout: 5))
        app.buttons["onboarding.inviteCode.skip"].tap()

        let createPlan = app.buttons["home.createPlan"]
        XCTAssertTrue(createPlan.waitForExistence(timeout: 5))
        createPlan.tap()

        XCTAssertTrue(app.navigationBars["Plan What's Next"].waitForExistence(timeout: 5))
        XCTAssertFalse(app.buttons["createPlan.publish"].isEnabled)

        let inviteOnly = app.buttons["createPlan.visibility.inviteOnly"]
        inviteOnly.tap()
        XCTAssertEqual(inviteOnly.value as? String, "selected")

        let title = app.textFields["createPlan.title"]
        app.swipeUp()
        XCTAssertTrue(title.waitForExistence(timeout: 5))
        title.tap()
        title.typeText("Tea after class")
        XCTAssertTrue(app.buttons["createPlan.publish"].isEnabled)
        app.buttons["createPlan.publish"].tap()

        XCTAssertFalse(app.navigationBars["Plan What's Next"].waitForExistence(timeout: 2))
        XCTAssertTrue(app.staticTexts["Tea after class"].waitForExistence(timeout: 5))
        let planVisibility = app.staticTexts["home.currentPlanVisibility"]
        XCTAssertTrue(planVisibility.waitForExistence(timeout: 5))
        XCTAssertEqual(planVisibility.label, "Invite only")
        let actionMessage = app.staticTexts["home.actionMessage"]
        XCTAssertTrue(actionMessage.waitForExistence(timeout: 5))
        XCTAssertTrue(actionMessage.label.contains("Your plan is live for"))
    }
}
