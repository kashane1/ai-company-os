import XCTest

/// Throwaway recon driver for the simulator-driven-polish run on the
/// monthly-logging banner (Today screen). Drives the app at multiple
/// `LIFECLOCK_FIXED_DATE` values that land on different milestone
/// thresholds in May 2026 (31 days → quarter=day 8, half=day 16,
/// threeQuarter=day 24), plus a non-milestone late-install day (20),
/// a calendar rollover into June, and the three tones on a single
/// milestone day so copy can be eyeballed in voice.
///
/// Outputs to /tmp/lifeclock-monthly/<slug>.{png,ax.txt}. Not part of
/// CI — delete at session end.
final class MonthlyBannerCaptureRecon: XCTestCase {
    private let outDir = "/tmp/lifeclock-monthly"

    override func setUpWithError() throws {
        continueAfterFailure = true
        try? FileManager.default.createDirectory(
            atPath: outDir, withIntermediateDirectories: true
        )
    }

    func testCaptureStartCoach()         { run(slug: "01-start-coach",         date: "2026-05-01T12:00:00Z", streak: 1,  tone: "coach") }
    func testCaptureQuarterCoach()       { run(slug: "02-quarter-coach",       date: "2026-05-08T12:00:00Z", streak: 5,  tone: "coach") }
    func testCaptureHalfCoach()          { run(slug: "03-half-coach",          date: "2026-05-16T12:00:00Z", streak: 10, tone: "coach") }
    func testCaptureThreeQuarterCoach()  { run(slug: "04-threequarter-coach",  date: "2026-05-24T12:00:00Z", streak: 15, tone: "coach") }
    func testCaptureNeutralLateInstall() { run(slug: "05-neutral-day20-coach", date: "2026-05-20T12:00:00Z", streak: 1,  tone: "coach") }
    func testCaptureHalfGentle()         { run(slug: "06-half-gentle",         date: "2026-05-16T12:00:00Z", streak: 10, tone: "gentle") }
    func testCaptureHalfFirmDirect()     { run(slug: "07-half-firmdirect",     date: "2026-05-16T12:00:00Z", streak: 10, tone: "firm_direct") }
    func testCaptureRolloverJune1()      { run(slug: "08-rollover-jun1-coach", date: "2026-06-01T12:00:00Z", streak: 1,  tone: "coach") }

    private func run(slug: String, date: String, streak: Int, tone: String) {
        let app = XCUIApplication()
        app.launchEnvironment["LIFECLOCK_UI_TEST"] = "1"
        app.launchEnvironment["LIFECLOCK_UI_TEST_SCENARIO"] = "onboarded"
        app.launchEnvironment["LIFECLOCK_USE_MOCK_HEALTH"] = "1"
        app.launchEnvironment["LIFECLOCK_HEALTH_AUTH"] = "authorized"
        app.launchEnvironment["LIFECLOCK_FIXED_DATE"] = date
        app.launchEnvironment["LIFECLOCK_SEED_STREAK"] = "\(streak)"
        app.launchEnvironment["LIFECLOCK_SEED_TONE"] = tone
        app.launch()

        // Wait for Today and the banner to render.
        let banner = app.descendants(matching: .any)
            .matching(identifier: "today.monthlyLogging").firstMatch
        let exists = banner.waitForExistence(timeout: 10)
        if !exists {
            // Capture full screen so we can see why.
            capture("\(slug)-no-banner", app: app)
            return
        }

        // Settle briefly so any on-appear animation completes.
        usleep(600_000)
        capture(slug, app: app)
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
