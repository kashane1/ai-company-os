import XCTest

/// PF-P5 — WrapUp clock-face lighting visual verification against the app
/// icon. Throwaway, session-scoped recon (NOT CI). Stands up the cold-launch
/// yesterday-wrap-up present-condition and captures the `ClockHandView`
/// render so it can be diffed against `Assets.xcassets/AppIcon.appiconset/`.
///
/// What it captures, per the PF-P5 brief:
///   * (a/b) light + dark, settled final-angle frame — world-fixed light
///     source upper-left + rim depth visible in both schemes.
///   * (c) a mid-reveal frame grabbed ~0.5s into the 1.4s sweep so the
///     hand is partially rotated — confirms the inverse-rotation shadow
///     stays world-fixed (does NOT rotate with the hand).
///   * (d) negative-delta path — bad yesterday habit log so the sweep is
///     counter-clockwise with the negative palette.
///
/// Fixed date 2026-04-30 is a Thursday (UTC); firstWeekday=Monday so only
/// the yesterday wrap-up presents (no weekly collision). Streak 7 +
/// days-since-install 8 puts the user past the reinstall guard with a
/// seeded snapshot for 2026-04-29 (yesterday).
///
/// Outputs to /tmp/lifeclock-wrapup-lighting/<slug>.{png,ax.txt}.
final class WrapUpLightingVerifyRecon: XCTestCase {
    private let outDir = "/tmp/lifeclock-wrapup-lighting"
    private let fixedDate = "2026-04-30T12:00:00Z"

    override func setUpWithError() throws {
        continueAfterFailure = true
        try? FileManager.default.createDirectory(
            atPath: outDir, withIntermediateDirectories: true
        )
    }

    func testLightSettled() { run(slug: "01-light", scheme: "light", badDay: false) }
    func testDarkSettled()  { run(slug: "02-dark",  scheme: "dark",  badDay: false) }

    /// Negative-delta path. `LIFECLOCK_HEALTH_PROFILE=poor` +
    /// `LIFECLOCK_SEED_BAD_DAY=1` drive the seeded day toward the negative
    /// palette; captured in both schemes.
    func testNegativeLight() { run(slug: "03-negative-light", scheme: "light", badDay: true) }
    func testNegativeDark()  { run(slug: "04-negative-dark",  scheme: "dark",  badDay: true) }

    private func run(slug: String, scheme: String, badDay: Bool) {
        let app = launch(scheme: scheme, badDay: badDay)

        let sheet = app.descendants(matching: .any)
            .matching(identifier: "wrapup.sheet.yesterday").firstMatch
        guard sheet.waitForExistence(timeout: 20) else {
            capture("\(slug)-NO-WRAPUP-DIAG", app: app)
            XCTFail("yesterday wrap-up did not present for \(slug)")
            return
        }

        // The sweep is 1.4s (yesterday). The existence check above can
        // resolve at variable points into the animation, so instead of a
        // single timed grab we burst-capture screenshots back-to-back the
        // instant the sheet exists. `XCUIScreen.screenshot()` is ~60-90ms,
        // so ~14 frames spans the 1.4s ease-out — at least one frame lands
        // with the hand clearly mid-rotation, which is the frame that
        // proves the inverse-rotation shadow stays world-fixed (drops
        // toward bottom-right regardless of the hand's angle).
        for frame in 0..<16 {
            let png = XCUIScreen.main.screenshot().pngRepresentation
            try? png.write(to: URL(
                fileURLWithPath: "\(outDir)/\(slug)-sweep\(String(format: "%02d", frame)).png"
            ))
        }

        // Final settled frame + AX tree.
        usleep(600_000)
        capture("\(slug)-settled", app: app)
    }

    private func launch(scheme: String, badDay: Bool) -> XCUIApplication {
        let app = XCUIApplication()
        app.launchEnvironment["LIFECLOCK_UI_TEST"] = "1"
        app.launchEnvironment["LIFECLOCK_UI_TEST_SCENARIO"] = "onboarded"
        app.launchEnvironment["LIFECLOCK_USE_MOCK_HEALTH"] = "1"
        app.launchEnvironment["LIFECLOCK_HEALTH_AUTH"] = "authorized"
        app.launchEnvironment["LIFECLOCK_SEED_STREAK"] = "7"
        app.launchEnvironment["LIFECLOCK_SEED_DAYS_SINCE_INSTALL"] = "8"
        app.launchEnvironment["LIFECLOCK_SEED_BASELINE_ADJUSTMENT"] = "0"
        app.launchEnvironment["LIFECLOCK_SEED_TONE"] = "coach"
        app.launchEnvironment["LIFECLOCK_FIXED_DATE"] = fixedDate
        app.launchEnvironment["LIFECLOCK_FORCE_COLOR_SCHEME"] = scheme
        if badDay {
            app.launchEnvironment["LIFECLOCK_SEED_BAD_DAY"] = "1"
            app.launchEnvironment["LIFECLOCK_HEALTH_PROFILE"] = "poor"
        }
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
