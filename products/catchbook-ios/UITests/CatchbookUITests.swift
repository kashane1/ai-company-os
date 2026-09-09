import XCTest

final class CatchbookUITests: XCTestCase {
    private var app: XCUIApplication!

    override func setUpWithError() throws {
        continueAfterFailure = false
        app = XCUIApplication()
        app.launchEnvironment["CATCHBOOK_UI_TEST"] = "1"
    }

    func testEmptyLogbookCanStartOfflineTripAndSaveCatch() {
        app.launch()

        XCTAssertTrue(app.navigationBars["Home"].waitForExistence(timeout: 8))
        XCTAssertTrue(app.staticTexts["Ready when you are"].exists)

        app.buttons["home.startTrip"].tap()

        XCTAssertTrue(app.navigationBars["Start Trip"].waitForExistence(timeout: 5))
        let offlineCopy = app.staticTexts.matching(
            NSPredicate(format: "label CONTAINS %@", "Trip start still works offline")
        ).firstMatch
        XCTAssertTrue(offlineCopy.exists)

        app.buttons["startTrip.button"].tap()

        XCTAssertTrue(app.navigationBars["Current Trip"].waitForExistence(timeout: 5))

        let species = app.textFields["Species"]
        XCTAssertTrue(species.waitForExistence(timeout: 3))
        species.tap()
        species.typeText("Trout")
        app.buttons["quickCatch.saveButton"].tap()

        let catchCount = app.descendants(matching: .any)
            .matching(identifier: "trip.catchCount").firstMatch
        for _ in 0..<4 where !catchCount.exists {
            app.swipeDown()
        }
        XCTAssertTrue(catchCount.waitForExistence(timeout: 5))
        XCTAssertEqual(catchCount.value as? String, "1")
    }

    func testEmptyHomePrimaryActionRemainsUsableAtLargestDynamicType() {
        app.launchArguments += [
            "-UIPreferredContentSizeCategoryName",
            "UICTContentSizeCategoryAccessibilityXXXL",
        ]
        app.launch()

        let startTrip = app.buttons["home.startTrip"]
        XCTAssertTrue(startTrip.waitForExistence(timeout: 8))
        if !startTrip.isHittable {
            app.swipeUp()
        }
        XCTAssertTrue(startTrip.isHittable)
        XCTAssertTrue(app.tabBars.buttons["Home"].isHittable)
        XCTAssertTrue(app.tabBars.buttons["More"].isHittable)
    }
}
