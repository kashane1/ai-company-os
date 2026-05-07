import XCTest

/// Throwaway recon driver for the simulator-driven-polish vision audit on
/// the bad-day Today screen. Lands the user on a clearly-negative day
/// (`LIFECLOCK_HEALTH_PROFILE=poor` → ≈ -27 min from health drivers, plus
/// `LIFECLOCK_SEED_BAD_DAY=1` → -70 min from logged habits = ≈ -97 min)
/// across all three tones and captures Today + the Pro-gated PlanEditorSheet.
///
/// The fixed date sits mid-month so the monthlyLoggingBanner shows up with
/// 14 days logged this month — the brief asks us to confirm the banner
/// still reads kindly on a bad day.
///
/// Outputs to /tmp/lifeclock-bad-day/<slug>.{png,ax.txt}. Not part of CI —
/// session-scoped recon only.
final class BadDayCaptureRecon: XCTestCase {
    private let outDir = "/tmp/lifeclock-bad-day"
    private let fixedDate = "2026-05-15T18:00:00Z"

    override func setUpWithError() throws {
        continueAfterFailure = true
        try? FileManager.default.createDirectory(
            atPath: outDir, withIntermediateDirectories: true
        )
    }

    func testCaptureGentle()     { run(slug: "01-today-gentle",     tone: "gentle") }
    func testCaptureCoach()      { run(slug: "02-today-coach",      tone: "coach") }
    func testCaptureFirmDirect() { run(slug: "03-today-firmdirect", tone: "firm_direct") }

    func testCapturePlanEditorGentle()     { runPlanEditor(slug: "04-planeditor-gentle",     tone: "gentle") }
    func testCapturePlanEditorCoach()      { runPlanEditor(slug: "05-planeditor-coach",      tone: "coach") }
    func testCapturePlanEditorFirmDirect() { runPlanEditor(slug: "06-planeditor-firmdirect", tone: "firm_direct") }

    private func run(slug: String, tone: String) {
        let app = launch(tone: tone, forcePro: false)

        // Wait for headline so we know the recompute settled.
        let headline = app.descendants(matching: .any)
            .matching(identifier: "today.headline").firstMatch
        guard headline.waitForExistence(timeout: 10) else {
            capture("\(slug)-no-headline", app: app); return
        }
        usleep(800_000)
        capture("\(slug)-top", app: app)

        // Scroll down so the monthly banner + plan + check-in surfaces are
        // visible in the second capture. The plan card is the user's "do
        // something" path on a bad day; the brief explicitly wants us to
        // see it next to the negative headline.
        app.swipeUp()
        usleep(400_000)
        capture("\(slug)-bottom", app: app)
    }

    private func runPlanEditor(slug: String, tone: String) {
        let app = launch(tone: tone, forcePro: true)

        // Pro is forced -> the chip reads "Edit" with `today.planEdit` id.
        let edit = app.descendants(matching: .any)
            .matching(identifier: "today.planEdit").firstMatch
        guard edit.waitForExistence(timeout: 10) else {
            capture("\(slug)-no-edit-chip", app: app); return
        }
        edit.tap()

        let sheet = app.descendants(matching: .any)
            .matching(identifier: "planEditor.screen").firstMatch
        guard sheet.waitForExistence(timeout: 5) else {
            capture("\(slug)-no-sheet", app: app); return
        }
        usleep(400_000)
        capture(slug, app: app)
    }

    private func launch(tone: String, forcePro: Bool) -> XCUIApplication {
        let app = XCUIApplication()
        app.launchEnvironment["LIFECLOCK_UI_TEST"] = "1"
        app.launchEnvironment["LIFECLOCK_UI_TEST_SCENARIO"] = "onboarded"
        app.launchEnvironment["LIFECLOCK_USE_MOCK_HEALTH"] = "1"
        app.launchEnvironment["LIFECLOCK_HEALTH_AUTH"] = "authorized"
        app.launchEnvironment["LIFECLOCK_HEALTH_PROFILE"] = "poor"
        app.launchEnvironment["LIFECLOCK_SEED_BAD_DAY"] = "1"
        app.launchEnvironment["LIFECLOCK_FIXED_DATE"] = fixedDate
        app.launchEnvironment["LIFECLOCK_SEED_STREAK"] = "14"
        app.launchEnvironment["LIFECLOCK_SEED_TONE"] = tone
        if forcePro { app.launchEnvironment["LIFECLOCK_FORCE_PRO"] = "1" }
        app.launch()
        return app
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
