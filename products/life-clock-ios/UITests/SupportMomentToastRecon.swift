import XCTest

/// Recon driver for the SupportMoment-toast lighting polish session
/// (`polish-2026-05-15-supportmoment-toast-lighting`). Drives the toast
/// to present, then captures the screen — toast plus the
/// `.sectionCard()` Today cards behind it — in light and dark so the
/// shared lighting convention (`.cardLighting()`) can be eyeballed
/// against the surrounding cards.
///
/// The toast is emitted by `emit(.checkInSaved)` on the QuickLog/
/// Check-In save path. Its entry point (`today.checkInToolbar`) is
/// always visible at the top of Today, so this path is fully
/// deterministic and needs no scrolling (the Today ScrollView's plan
/// card sits below the fold and the ScrollView does not respond to
/// gesture drags in the XCUITest harness). After the sheet dismisses
/// the toast presents over the Today cards (headline, mascot, "Why it
/// changed" — all `.sectionCard()` surfaces), which is exactly the
/// lighting comparison the success criterion asks for.
///
/// The toast auto-dismisses after 3.5s, so we capture rapidly across
/// the visible window once it presents.
///
/// Throwaway: not part of CI. Intended to be deleted once the polish
/// session's PR-time review is complete.
final class SupportMomentToastRecon: XCTestCase {
    private var app: XCUIApplication!

    func testToastLight() throws { try drive(scheme: "light") }
    func testToastDark() throws { try drive(scheme: "dark") }

    private func drive(scheme: String) throws {
        let outDir = "/tmp/lifeclock-toast/\(scheme)"
        try? FileManager.default.removeItem(atPath: outDir)
        try? FileManager.default.createDirectory(
            atPath: outDir, withIntermediateDirectories: true
        )

        app = XCUIApplication()
        app.launchEnvironment["LIFECLOCK_UI_TEST"] = "1"
        app.launchEnvironment["LIFECLOCK_UI_TEST_SCENARIO"] = "onboarded"
        app.launchEnvironment["LIFECLOCK_USE_MOCK_HEALTH"] = "1"
        app.launchEnvironment["LIFECLOCK_HEALTH_AUTH"] = "authorized"
        app.launchEnvironment["LIFECLOCK_SEED_TONE"] = "coach"
        app.launchEnvironment["LIFECLOCK_SEED_STREAK"] = "5"
        app.launchEnvironment["LIFECLOCK_SEED_QUESTS_COMPLETED"] = "2"
        app.launchEnvironment["LIFECLOCK_FORCE_COLOR_SCHEME"] = scheme
        app.launch()

        XCTAssertTrue(
            app.tabBars.buttons["Today"].waitForExistence(timeout: 10),
            "Today tab never appeared (\(scheme))"
        )
        // Mirror the proven TopLevelMatrixRecon QuickLog sequence: settle
        // the wake animation, re-tap Today, settle again, then open the
        // Check-In sheet via the toolbar button.
        sleep(2)
        app.tabBars.buttons["Today"].tap()
        sleep(2)

        let checkInToolbar = app.buttons["today.checkInToolbar"]
        guard checkInToolbar.waitForExistence(timeout: 4), checkInToolbar.isHittable else {
            capture(outDir, "00-toolbar-missing")
            XCTFail("today.checkInToolbar not hittable (\(scheme))")
            return
        }
        checkInToolbar.tap()
        _ = app.otherElements["checkIn.screen"].waitForExistence(timeout: 6)
        sleep(2)
        capture(outDir, "00-after-toolbar-tap")

        let save = app.buttons["checkIn.save"]
        if !save.waitForExistence(timeout: 6) {
            let ax = app.debugDescription
            try? ax.write(
                toFile: "\(outDir)/00-no-save.ax.txt",
                atomically: true, encoding: .utf8
            )
            XCTFail("checkIn.save never appeared (\(scheme))")
            return
        }
        save.tap()

        // Sheet dismisses, then the toast presents as an
        // `.overlay(alignment:.top)` over Today (3.5s auto-dismiss).
        // Capture rapidly across the visible window so at least one
        // frame lands while it is fully on screen and the spring
        // (response 0.42) has settled.
        usleep(900_000)
        capture(outDir, "01-toast-over-today")
        usleep(450_000)
        capture(outDir, "02-toast-settled")
        usleep(600_000)
        capture(outDir, "03-toast-late")
        let toast = app.descendants(matching: .any)["today.supportMoment"]
        if !toast.exists {
            let ax = app.debugDescription
            try? ax.write(
                toFile: "\(outDir)/04-toast-missing.ax.txt",
                atomically: true, encoding: .utf8
            )
        }
    }

    private func capture(_ outDir: String, _ name: String) {
        let png = XCUIScreen.main.screenshot().pngRepresentation
        try? png.write(to: URL(fileURLWithPath: "\(outDir)/\(name).png"))
    }
}
