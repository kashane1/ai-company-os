import XCTest

/// Throwaway recon driver for the simulator-driven-polish run on the
/// History `longAbsenceCard` (the welcome-back surface that replaces
/// the Yesterday card after a stretch with no usable data).
///
/// Seeds a returning user with `LIFECLOCK_SEED_LAST_LOG_DAYS_AGO=35`
/// so the most recent HabitLog + DailyHealthSnapshot land 35 days
/// before `LIFECLOCK_FIXED_DATE=2026-05-09`. The user has 5 contiguous
/// days of logs in late March / early April; nothing for May. This is
/// the worst-case 35-day return.
///
/// Captures three surfaces per tone — Today (with the wake animation
/// settled and the monthly-logging banner suppressed because no May
/// log exists), History (where the longAbsenceCard sits where the
/// Yesterday card would normally), and a confirmation that no
/// WrapUpSheet auto-presents on cold launch.
///
/// Outputs to /tmp/lifeclock-polish/long-absence/<slug>.{png,ax.txt}.
/// Not part of CI — delete at session end.
final class LongAbsenceCaptureRecon: XCTestCase {
    private let outDir = "/tmp/lifeclock-polish/long-absence"

    override func setUpWithError() throws {
        continueAfterFailure = true
        try? FileManager.default.createDirectory(
            atPath: outDir, withIntermediateDirectories: true
        )
    }

    func testGentle()     { run(tone: "gentle") }
    func testCoach()      { run(tone: "coach") }
    func testFirmDirect() { run(tone: "firm_direct") }

    private func run(tone: String) {
        let app = XCUIApplication()
        app.launchEnvironment["LIFECLOCK_UI_TEST"] = "1"
        app.launchEnvironment["LIFECLOCK_UI_TEST_SCENARIO"] = "onboarded"
        app.launchEnvironment["LIFECLOCK_USE_MOCK_HEALTH"] = "1"
        app.launchEnvironment["LIFECLOCK_HEALTH_AUTH"] = "authorized"
        app.launchEnvironment["LIFECLOCK_FIXED_DATE"] = "2026-05-09T12:00:00Z"
        app.launchEnvironment["LIFECLOCK_SEED_STREAK"] = "5"
        app.launchEnvironment["LIFECLOCK_SEED_LAST_LOG_DAYS_AGO"] = "35"
        app.launchEnvironment["LIFECLOCK_SEED_TONE"] = tone
        app.launch()

        // Settle wake animation + first refresh.
        usleep(1_500_000)

        // Capture Today first — note the absence of the monthly-logging
        // banner (no May logs yet) and verify no wrap-up sheet is up.
        capture("today-\(tone)", app: app)

        // Confirm no wrap-up sheet auto-presented (suppression check).
        let yesterdaySheet = app.descendants(matching: .any)
            .matching(identifier: "wrapup.sheet.yesterday").firstMatch
        let weeklySheet = app.descendants(matching: .any)
            .matching(identifier: "wrapup.sheet.weekly").firstMatch
        XCTAssertFalse(yesterdaySheet.exists, "yesterday wrap-up must suppress on 35-day return (\(tone))")
        XCTAssertFalse(weeklySheet.exists, "weekly wrap-up must suppress on 35-day return (\(tone))")

        // Tap History tab and capture the longAbsenceCard.
        app.tabBars.buttons["History"].tap()
        let card = app.descendants(matching: .any)
            .matching(identifier: "history.longAbsence").firstMatch
        let cardAppeared = card.waitForExistence(timeout: 6)
        if !cardAppeared {
            capture("history-\(tone)-MISSING-CARD", app: app)
            XCTFail("history.longAbsence card did not render (\(tone))")
            return
        }
        usleep(400_000)
        capture("history-\(tone)", app: app)
    }

    private func capture(_ name: String, app: XCUIApplication) {
        let png = XCUIScreen.main.screenshot().pngRepresentation
        try? png.write(to: URL(fileURLWithPath: "\(outDir)/\(name).png"))
        let ax = app.debugDescription
        try? ax.write(
            toFile: "\(outDir)/\(name).ax.txt",
            atomically: true, encoding: .utf8
        )
    }
}
