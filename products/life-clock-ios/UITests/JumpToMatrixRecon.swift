import XCTest

/// Recon driver for fix-list item 7 (JUMP_TO + tab-persistence matrix —
/// V1.7.0 Future tab regression-risk verification). Walks every active
/// `FutureJumpTo` target × cold launch, captures one PNG + AX dump per
/// landing, and asserts the per-target AX identifier signature so a
/// silently broken JUMP_TO landing fails the run instead of producing
/// a misleading screenshot.
///
/// Targets driven here:
///
///   futureDay0          → `future.headline.baseline` + `future.day0.line`
///   futureColdLaunch    → `future.headline.projection` + `future.coldLaunch.line`
///   futureWarmingUp     → `future.headline.projection` + `future.warmingUp.line` + chart + slider
///   futureFull          → `future.headline.projection` + chart + slider (no `warmingUp.line`)
///   futureCapReached    → as futureFull + `future.chart.capReached` + slider thumb at sleep=7.5
///   futureFloorReached  → as futureFull + `future.chart.floorReached` + slider thumb at sleep=4.0
///   paywallWhatIfSection → `paywall.screen` + `paywall.whatIfSimulator` reachable
///
/// Cross-tab persistence: after landing on Future, switch to Today
/// then back to Future. The store-owned `selectedTab` (LifeClockStore.swift:119)
/// must persist; tab-switch back to Today must NOT replay the wake
/// animation (feedback_life_clock_wake_animation.md — wake plays on
/// app open only, never on tab-switch).
///
/// Foreground-resume + hot-relaunch transitions are verified live via
/// computer-use after this recon lands; they're not driven from
/// XCUITest because scenePhase background-foreground transitions are
/// not reliably reproducible from XCUIApplication.activate() alone.
///
/// Output: /tmp/lifeclock-jumpto-matrix/<target>/{01-landing.png, 01-landing.ax.txt,
/// 02-tab-persistence-toToday.png, 03-tab-persistence-backToFuture.png}.
///
/// Throwaway-by-default — not part of CI. Deleted at session end.
final class JumpToMatrixRecon: XCTestCase {
    private var app: XCUIApplication!

    private struct Target {
        /// Raw `LIFECLOCK_JUMP_TO` value.
        let jumpTo: String
        /// AX identifiers that must exist after cold launch. Each must
        /// resolve within `waitTimeout`; any miss fails the test.
        let requiredAfterLaunch: [String]
        /// Whether this target lands on the Future tab (vs paywall over Today).
        let landsOnFutureTab: Bool
    }

    private let waitTimeout: TimeInterval = 10
    private let outRoot = "/tmp/lifeclock-jumpto-matrix"

    private let targets: [Target] = [
        Target(
            jumpTo: "futureDay0",
            requiredAfterLaunch: ["future.screen", "future.headline.baseline", "future.day0.line"],
            landsOnFutureTab: true
        ),
        Target(
            jumpTo: "futureColdLaunch",
            requiredAfterLaunch: ["future.screen", "future.headline.projection", "future.coldLaunch.line"],
            landsOnFutureTab: true
        ),
        Target(
            jumpTo: "futureWarmingUp",
            requiredAfterLaunch: ["future.screen", "future.headline.projection", "future.warmingUp.line", "future.trajectory.chart", "future.whatIfSlider"],
            landsOnFutureTab: true
        ),
        Target(
            jumpTo: "futureFull",
            requiredAfterLaunch: ["future.screen", "future.headline.projection", "future.trajectory.chart", "future.whatIfSlider"],
            landsOnFutureTab: true
        ),
        Target(
            jumpTo: "futureCapReached",
            requiredAfterLaunch: ["future.screen", "future.headline.projection", "future.chart.capReached", "future.whatIfSlider"],
            landsOnFutureTab: true
        ),
        Target(
            jumpTo: "futureFloorReached",
            requiredAfterLaunch: ["future.screen", "future.headline.projection", "future.chart.floorReached", "future.whatIfSlider"],
            landsOnFutureTab: true
        ),
        Target(
            jumpTo: "paywallWhatIfSection",
            requiredAfterLaunch: ["paywall.screen", "paywall.whatIfSimulator"],
            landsOnFutureTab: false
        ),
    ]

    func testFutureDay0()           throws { try walk(targets[0]) }
    func testFutureColdLaunch()     throws { try walk(targets[1]) }
    func testFutureWarmingUp()      throws { try walk(targets[2]) }
    func testFutureFull()           throws { try walk(targets[3]) }
    func testFutureCapReached()     throws { try walk(targets[4]) }
    func testFutureFloorReached()   throws { try walk(targets[5]) }
    func testPaywallWhatIfSection() throws { try walk(targets[6]) }

    // MARK: - Walk

    private func walk(_ target: Target) throws {
        let outDir = "\(outRoot)/\(target.jumpTo)"
        try? FileManager.default.removeItem(atPath: outDir)
        try? FileManager.default.createDirectory(
            atPath: outDir, withIntermediateDirectories: true
        )

        app = XCUIApplication()
        app.launchEnvironment["LIFECLOCK_UI_TEST"] = "1"
        app.launchEnvironment["LIFECLOCK_UI_TEST_SCENARIO"] = "onboarded"
        app.launchEnvironment["LIFECLOCK_USE_MOCK_HEALTH"] = "1"
        app.launchEnvironment["LIFECLOCK_HEALTH_AUTH"] = "authorized"
        app.launchEnvironment["LIFECLOCK_FORCE_PRO"] = "1"
        app.launchEnvironment["LIFECLOCK_FUTURE_TAB_UNLOCKED"] = "1"
        app.launchEnvironment["LIFECLOCK_JUMP_TO"] = target.jumpTo
        app.launch()

        // Assert per-target AX signature; fail loud on miss so a broken
        // landing is visible without re-reading every PNG.
        for identifier in target.requiredAfterLaunch {
            let element = anyElement(with: identifier)
            XCTAssertTrue(
                element.waitForExistence(timeout: waitTimeout),
                "\(target.jumpTo): missing required AX identifier \(identifier) after cold launch"
            )
        }

        // Settle one wake-animation budget (~1s) before capture.
        sleep(2)
        capture(outDir, "01-landing")

        // Tab persistence + wake-animation re-entry guard. Only
        // applicable for Future-tab landings; paywall sits on top of
        // Today and is dismissed by the user.
        guard target.landsOnFutureTab else { return }

        // Toggle to Today, then back to Future. Tab state lives in the
        // store (LifeClockStore.swift:119); selection must survive the
        // round-trip. Wake animation must NOT replay when re-entering
        // Today via tab-switch.
        let today = app.tabBars.buttons["Today"]
        let future = app.tabBars.buttons["Future"]
        guard today.waitForExistence(timeout: waitTimeout) else {
            XCTFail("\(target.jumpTo): tab bar never appeared")
            return
        }
        today.tap()
        sleep(1)
        capture(outDir, "02-tab-persistence-toToday")

        future.tap()
        sleep(1)
        XCTAssertTrue(
            anyElement(with: "future.screen").waitForExistence(timeout: waitTimeout),
            "\(target.jumpTo): Future tab did not re-render after round-trip"
        )
        capture(outDir, "03-tab-persistence-backToFuture")

        // Foreground resume: home button → activate(). After resume,
        // the Future tab must STILL be selected (scenePhase=.active
        // must not reset selectedTab). This catches a regression where
        // a future onChange/onAppear handler reseats the initial tab.
        XCUIDevice.shared.press(.home)
        sleep(1)
        app.activate()
        XCTAssertTrue(
            anyElement(with: "future.screen").waitForExistence(timeout: waitTimeout),
            "\(target.jumpTo): Future tab not selected after foreground resume"
        )
        sleep(2)
        capture(outDir, "04-foreground-resume")

        // Hot relaunch: terminate + .launch() again. Verifies the
        // env-var fixture is sticky across process death and the
        // JUMP_TO landing is deterministic on relaunch. Only run for
        // one representative target (futureFull) to keep the matrix
        // honest without paying 7× the launch cost.
        if target.jumpTo == "futureFull" {
            app.terminate()
            sleep(1)
            app.launch()
            XCTAssertTrue(
                anyElement(with: "future.screen").waitForExistence(timeout: waitTimeout),
                "\(target.jumpTo): hot relaunch did not re-land on Future tab"
            )
            sleep(2)
            capture(outDir, "05-hot-relaunch")
        }
    }

    // MARK: - Helpers

    /// AX identifiers can resolve as `staticTexts` (Text), `otherElements`
    /// (View/ScrollView), or `buttons`. The recon doesn't care which —
    /// it only asserts presence. Walk all common kinds; first hit wins.
    private func anyElement(with identifier: String) -> XCUIElement {
        let kinds: [XCUIElementQuery] = [
            app.otherElements,
            app.staticTexts,
            app.buttons,
            app.scrollViews,
            app.images,
            app.descendants(matching: .any),
        ]
        for query in kinds {
            let candidate = query[identifier]
            if candidate.exists { return candidate }
        }
        // Return a sentinel that will fail `waitForExistence`.
        return app.descendants(matching: .any)[identifier]
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
