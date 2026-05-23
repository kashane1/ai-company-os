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
        // Today is default; wait for headline so we know recompute settled.
        let headline = app.descendants(matching: .any)
            .matching(identifier: "today.headline").firstMatch
        _ = headline.waitForExistence(timeout: 10)
        usleep(800_000)
        capture("01-see-your-life-clock", app: app)
    }

    func testCapture02EarnTimeWithHabits() {
        let app = launch(initialTab: "today")
        let headline = app.descendants(matching: .any)
            .matching(identifier: "today.headline").firstMatch
        _ = headline.waitForExistence(timeout: 10)
        usleep(400_000)
        // Scroll to plan + check-in chunk
        app.swipeUp()
        usleep(400_000)
        capture("02-earn-time-with-habits", app: app)
    }

    func testCapture03AppleHealthUpdates() {
        let app = launch(initialTab: "profile")
        usleep(800_000)
        capture("03-apple-health-updates", app: app)
    }

    func testCapture04FindWhatsCostingTime() {
        let app = launch(initialTab: "history")
        usleep(800_000)
        capture("04-find-whats-costing-time", app: app)
    }

    func testCapture05DailyLongevityQuests() {
        let app = launch(initialTab: "today")
        let headline = app.descendants(matching: .any)
            .matching(identifier: "today.headline").firstMatch
        _ = headline.waitForExistence(timeout: 10)
        // Scroll past hero into plan card
        app.swipeUp()
        usleep(200_000)
        app.swipeUp()
        usleep(400_000)
        capture("05-daily-longevity-quests", app: app)
    }

    func testCapture06TrackHealthspanTrend() {
        let app = launch(initialTab: "future")
        usleep(1_000_000)
        capture("06-track-healthspan-trend", app: app)
    }

    // MARK: - helpers

    private func launch(initialTab: String) -> XCUIApplication {
        let app = XCUIApplication()
        app.launchEnvironment["LIFECLOCK_UI_TEST"] = "1"
        app.launchEnvironment["LIFECLOCK_UI_TEST_SCENARIO"] = "onboarded"
        app.launchEnvironment["LIFECLOCK_USE_MOCK_HEALTH"] = "1"
        app.launchEnvironment["LIFECLOCK_HEALTH_AUTH"] = "authorized"
        app.launchEnvironment["LIFECLOCK_HEALTH_PROFILE"] = "baseline"
        app.launchEnvironment["LIFECLOCK_SEED_STREAK"] = "7"
        app.launchEnvironment["LIFECLOCK_SEED_QUESTS_COMPLETED"] = "1"
        app.launchEnvironment["LIFECLOCK_FIXED_DATE"] = fixedDate
        // Default coach tone — the App Store listing should reflect the
        // tone users land in by default, not the firmDirect variant.
        app.launchEnvironment["LIFECLOCK_INITIAL_TAB"] = initialTab
        // The fixture surface defaults the simulator to Pro; we want Pro
        // because that's the marketing-target audience and the History/Future
        // tabs render their full content. (Set to "1" to flip to Free.)
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
