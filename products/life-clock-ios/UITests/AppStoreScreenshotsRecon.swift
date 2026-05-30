import XCTest

/// Captures the six App Store listing screenshots specified in
/// `docs/products/life-clock/APP_STORE_ASO.md` § First screenshots.
///
/// Outputs PNGs to `/tmp/lifeclock-appstore-screenshots/` with names that
/// map directly to the upload order in the ASC version page:
///
///   01-see-your-life-clock.png        — Today, full headline + drivers
///   02-earn-time-with-habits.png      — Today, plan + check-in chunk
///   03-apple-health-updates.png       — Profile → Apple Health row
///   04-find-whats-costing-time.png    — History weekly card
///   05-daily-longevity-quests.png     — Today, plan card focused
///   06-track-healthspan-trend.png     — Future tab trajectory
///
/// The launch environment seeds a Day-7 Pro user on a balanced day so the
/// Life Clock reads positive and the History shows real cards rather than
/// the day-1 empty state. The 2026-05-15 fixed date sits mid-month so the
/// monthly logging banner has content.
///
/// Run on iPhone 17 Pro Max + iPad Pro 13-inch (M5). Outside that, file the
/// captures under `screenshots/submission-v1/<device>/`.
final class AppStoreScreenshotsRecon: XCTestCase {
    private let outDir = "/tmp/lifeclock-appstore-screenshots"
    private let fixedDate = "2026-05-15T18:00:00Z"

    override func setUpWithError() throws {
        continueAfterFailure = true
        try? FileManager.default.createDirectory(
            atPath: outDir, withIntermediateDirectories: true
        )
    }

    func testCapture01SeeYourLifeClock() {
        let app = launch(initialTab: "today")
        dismissWrapUpIfPresent(app)
        let headline = app.descendants(matching: .any)
            .matching(identifier: "today.headline").firstMatch
        _ = headline.waitForExistence(timeout: 10)
        usleep(800_000)
        capture("01-see-your-life-clock", app: app)
    }

    func testCapture02EarnTimeWithHabits() {
        let app = launch(initialTab: "today")
        dismissWrapUpIfPresent(app)
        let headline = app.descendants(matching: .any)
            .matching(identifier: "today.headline").firstMatch
        _ = headline.waitForExistence(timeout: 10)
        usleep(400_000)
        app.swipeUp()
        usleep(400_000)
        capture("02-earn-time-with-habits", app: app)
    }

    func testCapture03AppleHealthUpdates() {
        let app = launch(initialTab: "profile")
        dismissWrapUpIfPresent(app)
        usleep(800_000)
        capture("03-apple-health-updates", app: app)
    }

    func testCapture04FindWhatsCostingTime() {
        let app = launch(initialTab: "history")
        dismissWrapUpIfPresent(app)
        usleep(800_000)
        capture("04-find-whats-costing-time", app: app)
    }

    func testCapture05DailyLongevityQuests() {
        let app = launch(initialTab: "today")
        dismissWrapUpIfPresent(app)
        let headline = app.descendants(matching: .any)
            .matching(identifier: "today.headline").firstMatch
        _ = headline.waitForExistence(timeout: 10)
        // Pro user is the default in the test fixture, so the Plan card's
        // header chip reads "Edit" with the `today.planEdit` accessibility
        // identifier (free users see a "Custom" lock chip instead). Open
        // the Plan Editor sheet — the closest surface in v1 to the
        // "daily longevity quests" frame from APP_STORE_ASO.md.
        let edit = app.descendants(matching: .any)
            .matching(identifier: "today.planEdit").firstMatch
        if edit.waitForExistence(timeout: 5) {
            edit.tap()
            let sheet = app.descendants(matching: .any)
                .matching(identifier: "planEditor.screen").firstMatch
            _ = sheet.waitForExistence(timeout: 5)
            usleep(600_000)
        } else {
            // Fallback: just scroll past the hero. Better than nothing.
            app.swipeUp()
            usleep(200_000)
            app.swipeUp()
            usleep(400_000)
        }
        capture("05-daily-longevity-quests", app: app)
    }

    func testCapture06TrackHealthspanTrend() {
        let app = launch(initialTab: "future", extraEnvironment: [
            "LIFECLOCK_JUMP_TO": "futureFull",
            "LIFECLOCK_SEED_SNAPSHOTS": "30",
        ])
        dismissWrapUpIfPresent(app)
        usleep(1_500_000)
        capture("06-track-healthspan-trend", app: app)
    }

    // MARK: - sheet handling

    /// The `WrapUpCoordinator` auto-presents yesterday's wrap-up on every
    /// cold launch when a streak is seeded. Dismiss it before capturing
    /// any tab background. Idempotent — does nothing if the sheet isn't
    /// up.
    private func dismissWrapUpIfPresent(_ app: XCUIApplication) {
        let cta = app.descendants(matching: .any)
            .matching(identifier: "wrapup.dismissCTA").firstMatch
        if cta.waitForExistence(timeout: 2) {
            cta.tap()
            usleep(600_000)
        }
    }

    // MARK: - helpers

    private func launch(initialTab: String,
                        extraEnvironment: [String: String] = [:]) -> XCUIApplication {
        let app = XCUIApplication()
        app.launchEnvironment["LIFECLOCK_UI_TEST"] = "1"
        app.launchEnvironment["LIFECLOCK_UI_TEST_SCENARIO"] = "onboarded"
        app.launchEnvironment["LIFECLOCK_USE_MOCK_HEALTH"] = "1"
        app.launchEnvironment["LIFECLOCK_HEALTH_AUTH"] = "authorized"
        app.launchEnvironment["LIFECLOCK_HEALTH_PROFILE"] = "baseline"
        // 21 days lands in the .full14plus Future-tab state and gives
        // History meaningful weekly cards.
        app.launchEnvironment["LIFECLOCK_SEED_STREAK"] = "21"
        app.launchEnvironment["LIFECLOCK_SEED_QUESTS_COMPLETED"] = "1"
        app.launchEnvironment["LIFECLOCK_SEED_DAYS_SINCE_INSTALL"] = "30"
        app.launchEnvironment["LIFECLOCK_FIXED_DATE"] = fixedDate
        app.launchEnvironment["LIFECLOCK_INITIAL_TAB"] = initialTab
        // Default coach tone — the App Store listing should reflect the
        // tone users land in by default, not the firmDirect variant.
        // Simulator defaults to Pro; we want Pro because that's the
        // marketing-target audience and the History/Future tabs render
        // their full content.
        for (key, value) in extraEnvironment {
            app.launchEnvironment[key] = value
        }
        app.launch()
        return app
    }

    private func capture(_ name: String, app: XCUIApplication) {
        let png = XCUIScreen.main.screenshot().pngRepresentation
        try? png.write(to: URL(fileURLWithPath: "\(outDir)/\(name).png"))
        // Also attach for the .xcresult bundle so the captures are visible
        // in Xcode's test report.
        let attachment = XCTAttachment(image: XCUIScreen.main.screenshot().image)
        attachment.name = name
        attachment.lifetime = .keepAlways
        add(attachment)
    }
}
