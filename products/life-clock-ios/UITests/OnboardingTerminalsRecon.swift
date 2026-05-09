import XCTest

/// Recon driver for the 2026-05-09 polish session — sweeps the three
/// terminal-tier onboarding screens (`recoveryPreview`, `healthKitAuth`,
/// `paywallPrimary`) across the (palette × color-scheme × Dynamic Type)
/// configuration space the 2026-05-06 matrix audit deferred.
///
/// 12 cells (3 palettes × 2 schemes × 2 sizes) × 3 screens = 36 captures.
/// Output lands at /tmp/lifeclock-polish/onboarding-terminals/<slug>/.
///
/// Each cell launches once per palette/scheme/size combination, jumps
/// straight to `recoveryPreview` via `LIFECLOCK_JUMP_TO`, captures, taps
/// Continue, captures `healthKitAuth`, taps "Not now" (the soft-skip,
/// which doesn't trigger a system permission dialog), then captures
/// `paywallPrimary`. Configuration is process-scoped (Dynamic Type and
/// the palette override both bind at app launch), so the matrix is
/// driven by external launch arguments rather than mid-process flips.
///
/// Throwaway: not part of CI. Intended to be deleted at session end
/// alongside `TopLevelMatrixRecon.swift`.
final class OnboardingTerminalsRecon: XCTestCase {
    private var app: XCUIApplication!

    private struct Cell {
        let palette: String      // "default-navy" | "aurora-cool" | "sunset-warm"
        let scheme: String       // "light" | "dark"
        let size: String         // "default" | "axxl"
        var slug: String { "\(palette)-\(scheme)-\(size)" }
        var contentSizeCategory: String {
            size == "axxl"
                ? "UICTContentSizeCategoryAccessibilityXXL"
                : "UICTContentSizeCategoryL"
        }
    }

    func testNavyLightDefault()    throws { try walk(Cell(palette: "default-navy", scheme: "light", size: "default")) }
    func testNavyLightAXXL()       throws { try walk(Cell(palette: "default-navy", scheme: "light", size: "axxl")) }
    func testNavyDarkDefault()     throws { try walk(Cell(palette: "default-navy", scheme: "dark",  size: "default")) }
    func testNavyDarkAXXL()        throws { try walk(Cell(palette: "default-navy", scheme: "dark",  size: "axxl")) }
    func testAuroraLightDefault()  throws { try walk(Cell(palette: "aurora-cool", scheme: "light", size: "default")) }
    func testAuroraLightAXXL()     throws { try walk(Cell(palette: "aurora-cool", scheme: "light", size: "axxl")) }
    func testAuroraDarkDefault()   throws { try walk(Cell(palette: "aurora-cool", scheme: "dark",  size: "default")) }
    func testAuroraDarkAXXL()      throws { try walk(Cell(palette: "aurora-cool", scheme: "dark",  size: "axxl")) }
    func testSunsetLightDefault()  throws { try walk(Cell(palette: "sunset-warm", scheme: "light", size: "default")) }
    func testSunsetLightAXXL()     throws { try walk(Cell(palette: "sunset-warm", scheme: "light", size: "axxl")) }
    func testSunsetDarkDefault()   throws { try walk(Cell(palette: "sunset-warm", scheme: "dark",  size: "default")) }
    func testSunsetDarkAXXL()      throws { try walk(Cell(palette: "sunset-warm", scheme: "dark",  size: "axxl")) }

    private func walk(_ cell: Cell) throws {
        let outDir = "/tmp/lifeclock-polish/onboarding-terminals/\(cell.slug)"
        try? FileManager.default.removeItem(atPath: outDir)
        try? FileManager.default.createDirectory(
            atPath: outDir, withIntermediateDirectories: true
        )

        app = XCUIApplication()
        app.launchEnvironment["LIFECLOCK_UI_TEST"] = "1"
        // `onboarding` keeps OnboardingCoordinator as the root; combined
        // with `JUMP_TO` the path opens directly on the named terminal
        // screen with a pre-populated draft (heavy lifestyle answers
        // → non-zero recovery yearsBack).
        app.launchEnvironment["LIFECLOCK_UI_TEST_SCENARIO"] = "onboarding"
        app.launchEnvironment["LIFECLOCK_USE_MOCK_HEALTH"] = "1"
        // `authorized` makes `requestHealthAuthorization()` short-circuit
        // through the mock — no system permission dialog interrupts the
        // capture sequence on the healthKitAuth → paywallPrimary tap.
        app.launchEnvironment["LIFECLOCK_HEALTH_AUTH"] = "authorized"
        app.launchEnvironment["LIFECLOCK_JUMP_TO"] = "recoveryPreview"
        app.launchEnvironment["LIFECLOCK_FORCE_PALETTE"] = cell.palette
        app.launchEnvironment["LIFECLOCK_FORCE_COLOR_SCHEME"] = cell.scheme
        app.launchArguments += [
            "-UIPreferredContentSizeCategoryName", cell.contentSizeCategory,
        ]
        app.launch()

        // 01 RecoveryPreview — wait for the screen root, then settle
        // the cycling-phrase animation before capture so AX-tree state
        // and pixel state agree.
        XCTAssertTrue(
            app.otherElements["onboarding.recoveryPreview"].waitForExistence(timeout: 10),
            "recoveryPreview never appeared (\(cell.slug))"
        )
        sleep(2)
        capture(outDir, "01-recoveryPreview")

        // 02 HealthKitAuth — Continue advances the path; the scaffold
        // root id flips to `onboarding.healthKitAuth`.
        let continueButton = app.buttons["onboarding.continue"]
        guard continueButton.waitForExistence(timeout: 4), continueButton.isHittable else {
            capture(outDir, "02-healthKitAuth-MISSING-continue")
            return
        }
        continueButton.tap()
        XCTAssertTrue(
            app.otherElements["onboarding.healthKitAuth"].waitForExistence(timeout: 6),
            "healthKitAuth never appeared (\(cell.slug))"
        )
        // axxl re-layouts the secondary "Not now" caption block; one
        // settle so the Dynamic-Type pass has stabilized before capture.
        sleep(1)
        capture(outDir, "02-healthKitAuth")

        // 03 PaywallPrimary — soft-skip path so the system HK prompt
        // never appears regardless of mock-auth gating.
        let skipButton = app.buttons["onboarding.healthKitAuth.skip"]
        guard skipButton.waitForExistence(timeout: 4), skipButton.isHittable else {
            capture(outDir, "03-paywallPrimary-MISSING-skip")
            return
        }
        skipButton.tap()
        XCTAssertTrue(
            app.otherElements["onboarding.paywallPrimary"].waitForExistence(timeout: 6),
            "paywallPrimary never appeared (\(cell.slug))"
        )
        sleep(1)
        capture(outDir, "03-paywallPrimary")
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
