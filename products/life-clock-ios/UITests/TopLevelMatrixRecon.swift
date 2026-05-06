import XCTest

/// Recon driver for the accessibility-and-color polish session
/// (`polish-2026-05-06-accessibility-color-matrix`). Walks the four
/// post-onboarding top-level surfaces — Today, History, Profile, and the
/// QuickLog sheet — and dumps PNG + AX-tree per (color-scheme × text-size)
/// configuration to /tmp/lifeclock-polish/<scheme>-<size>/.
///
/// Configuration is process-scoped (Dynamic Type can't change mid-process
/// reliably), so we drive it from outside via launch arguments. Each test
/// method is one of the four matrix cells; the test runner can launch them
/// in parallel or sequentially.
///
/// Throwaway: not part of CI. Intended to be deleted at session end.
final class TopLevelMatrixRecon: XCTestCase {
    private var app: XCUIApplication!

    /// Each cell of the matrix. Light/default is the existing baseline; the
    /// other three exercise the color/Dynamic-Type configuration space.
    private struct Cell {
        let scheme: String      // "light" | "dark"
        let size: String        // "default" | "axxl"
        var slug: String { "\(scheme)-\(size)" }
        var contentSizeCategory: String {
            size == "axxl"
                ? "UICTContentSizeCategoryAccessibilityXXL"
                : "UICTContentSizeCategoryL"
        }
    }

    func testLightDefault() throws { try walk(Cell(scheme: "light", size: "default")) }
    func testLightAXXL()    throws { try walk(Cell(scheme: "light", size: "axxl")) }
    func testDarkDefault()  throws { try walk(Cell(scheme: "dark",  size: "default")) }
    func testDarkAXXL()     throws { try walk(Cell(scheme: "dark",  size: "axxl")) }

    private func walk(_ cell: Cell) throws {
        let outDir = "/tmp/lifeclock-polish/\(cell.slug)"
        try? FileManager.default.removeItem(atPath: outDir)
        try? FileManager.default.createDirectory(
            atPath: outDir, withIntermediateDirectories: true
        )

        app = XCUIApplication()
        app.launchEnvironment["LIFECLOCK_UI_TEST"] = "1"
        app.launchEnvironment["LIFECLOCK_UI_TEST_SCENARIO"] = "onboarded"
        app.launchEnvironment["LIFECLOCK_USE_MOCK_HEALTH"] = "1"
        app.launchEnvironment["LIFECLOCK_HEALTH_AUTH"] = "authorized"
        app.launchEnvironment["LIFECLOCK_SEED_STREAK"] = "5"
        app.launchEnvironment["LIFECLOCK_SEED_QUESTS_COMPLETED"] = "2"
        app.launchEnvironment["LIFECLOCK_FORCE_COLOR_SCHEME"] = cell.scheme
        app.launchArguments += [
            "-UIPreferredContentSizeCategoryName", cell.contentSizeCategory,
        ]
        app.launch()

        // 01 Today (default tab)
        XCTAssertTrue(
            app.tabBars.buttons["Today"].waitForExistence(timeout: 10),
            "Today tab never appeared (\(cell.slug))"
        )
        // Settle wake animation (1.0s budget) before capture.
        sleep(2)
        capture(outDir, "01-today")

        // 02 History tab
        app.tabBars.buttons["History"].tap()
        sleep(1)
        capture(outDir, "02-history")

        // 03 Profile tab — heavier render (Form + badges + body metrics
        // + daily reminder). Settle longer so the AX-tree query and
        // screenshot don't race the first layout pass.
        app.tabBars.buttons["Profile"].tap()
        sleep(3)
        XCTAssertTrue(
            app.staticTexts["Profile"].waitForExistence(timeout: 6),
            "Profile nav title never appeared (\(cell.slug))"
        )
        capture(outDir, "03-profile")

        // 04 QuickLog sheet — open from Today's toolbar Check-In button.
        // Re-tap Today; one settle for the wake animation; then present.
        app.tabBars.buttons["Today"].tap()
        sleep(2)
        let checkIn = app.buttons["today.checkInToolbar"]
        guard checkIn.waitForExistence(timeout: 4), checkIn.isHittable else {
            // Don't fail the whole cell — capture diagnostic and move on.
            capture(outDir, "04-quickLog-MISSING")
            return
        }
        checkIn.tap()
        _ = app.otherElements["checkIn.screen"].waitForExistence(timeout: 6)
        sleep(2)
        capture(outDir, "04-quickLog")
    }

    private func capture(_ outDir: String, _ name: String) {
        let png = XCUIScreen.main.screenshot().pngRepresentation
        try? png.write(to: URL(fileURLWithPath: "\(outDir)/\(name).png"))
        let ax = app.debugDescription
        try? ax.write(
            toFile: "\(outDir)/\(name).ax.txt",
            atomically: true, encoding: .utf8
        )
    }
}
