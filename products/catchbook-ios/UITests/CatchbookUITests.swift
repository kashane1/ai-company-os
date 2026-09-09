import XCTest

final class CatchbookUITests: XCTestCase {
    private var app: XCUIApplication!

    override func setUpWithError() throws {
        continueAfterFailure = false
        app = XCUIApplication()
        app.terminate()
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

    func testDeniedLocationAndUnavailableCameraStillAllowSavingCatch() {
        app.launchEnvironment["CATCHBOOK_UI_TEST_LOCATION_AUTHORIZATION"] = "denied"
        app.launchEnvironment["CATCHBOOK_UI_TEST_CAMERA_AVAILABILITY"] = "unavailable"
        app.launch()

        XCTAssertTrue(app.navigationBars["Home"].waitForExistence(timeout: 8))
        app.buttons["home.startTrip"].tap()

        let locationStatus = app.staticTexts["tripStart.locationStatus"]
        XCTAssertTrue(locationStatus.waitForExistence(timeout: 5))
        XCTAssertTrue(locationStatus.label.contains("Location is unavailable"))
        XCTAssertTrue(locationStatus.label.contains("still start a trip"))

        app.buttons["startTrip.button"].tap()
        XCTAssertTrue(app.navigationBars["Current Trip"].waitForExistence(timeout: 5))

        let catchCount = app.descendants(matching: .any)
            .matching(identifier: "trip.catchCount").firstMatch
        XCTAssertTrue(catchCount.waitForExistence(timeout: 5))
        XCTAssertEqual(catchCount.value as? String, "0")

        app.buttons["More details"].tap()
        let cameraStatus = app.staticTexts["quickCatch.cameraUnavailableStatus"]
        for _ in 0..<3 where !cameraStatus.exists {
            app.swipeUp()
        }
        XCTAssertTrue(cameraStatus.waitForExistence(timeout: 5))
        XCTAssertTrue(cameraStatus.label.contains("Camera is unavailable"))
        XCTAssertFalse(app.buttons["quickCatch.cameraButton"].isEnabled)
        XCTAssertTrue(app.buttons["quickCatch.photoLibraryButton"].exists)
        app.buttons["More details"].tap()

        let species = app.textFields["Species"]
        species.tap()
        species.typeText("Trout")
        app.swipeDown()
        XCTAssertFalse(app.keyboards.firstMatch.exists)

        let saveCatch = app.buttons["quickCatch.saveButton"]
        XCTAssertTrue(saveCatch.waitForExistence(timeout: 5))
        XCTAssertTrue(saveCatch.isHittable)
        saveCatch.tap()

        let savedCatchScreen = XCTAttachment(screenshot: app.screenshot())
        savedCatchScreen.name = "denied-location-camera-unavailable-save"
        savedCatchScreen.lifetime = .keepAlways
        add(savedCatchScreen)

        for _ in 0..<3 {
            app.swipeDown()
        }

        let updatedCatchCount = app.descendants(matching: .any)
            .matching(identifier: "trip.catchCount").firstMatch
        expectation(
            for: NSPredicate(format: "value == %@", "1"),
            evaluatedWith: updatedCatchCount
        )
        waitForExpectations(timeout: 5)
        XCTAssertEqual(updatedCatchCount.value as? String, "1")
    }
}
