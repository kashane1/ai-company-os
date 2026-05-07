import XCTest

/// Recon driver for the wrap-up sequencing polish session
/// (`polish-2026-05-06-wrapup-sequencing-foreground-cycles`).
///
/// Drives a returning-user (`onboarded` + 10-day streak) across distinct
/// `LIFECLOCK_FIXED_DATE` values to surface integration behaviors that the
/// `WrapUpCoordinatorTests` unit suite cannot reach:
///
/// - `testThursdayYesterdayOnly` — non-Monday return; only the yesterday
///   wrap-up should present.
/// - `testMondayYesterdayThenWeekly` — Monday return; yesterday wins on
///   first present, but does the weekly wrap-up sequence in once yesterday
///   is dismissed within the same launch?
/// - `testRepresentDoesNotFireSameSession` — `markWrapUpShown` discipline
///   under same-day re-bootstrap (no replay).
/// - `testBackgroundMidWrapUpKeepsSheet` — backgrounding mid-wrap-up does
///   not clobber the sheet on foreground; wake animation cannot dismiss it.
///
/// Throwaway: not part of CI. Goldens land at /tmp/lifeclock-polish/wrapup.
final class WrapUpSequenceRecon: XCTestCase {
    private let outDir = "/tmp/lifeclock-polish/wrapup"

    override func setUpWithError() throws {
        try? FileManager.default.removeItem(atPath: outDir)
        try? FileManager.default.createDirectory(
            atPath: outDir,
            withIntermediateDirectories: true
        )
        continueAfterFailure = false
    }

    private func makeApp(fixedDate: String, streak: Int = 10) -> XCUIApplication {
        let app = XCUIApplication()
        app.launchEnvironment = [
            "LIFECLOCK_UI_TEST": "1",
            "LIFECLOCK_USE_MOCK_HEALTH": "1",
            "LIFECLOCK_HEALTH_AUTH": "authorized",
            "LIFECLOCK_UI_TEST_SCENARIO": "onboarded",
            "LIFECLOCK_SEED_STREAK": String(streak),
            "LIFECLOCK_SEED_TONE": "coach",
            "LIFECLOCK_FIXED_DATE": fixedDate
        ]
        return app
    }

    private func snapshot(_ app: XCUIApplication, name: String) {
        let png = app.screenshot().pngRepresentation
        try? png.write(to: URL(fileURLWithPath: "\(outDir)/\(name).png"))
        let tree = app.debugDescription
        try? tree.write(
            toFile: "\(outDir)/\(name).ax.txt",
            atomically: true,
            encoding: .utf8
        )
    }

    // MARK: - (a) Thursday: yesterday only

    func testThursdayYesterdayOnly() {
        // 2026-04-30 is a Thursday (UTC). firstWeekday=Monday → no weekly.
        let app = makeApp(fixedDate: "2026-04-30T12:00:00Z")
        app.launch()

        let yesterday = app.otherElements["wrapup.sheet.yesterday"]
        XCTAssertTrue(
            yesterday.waitForExistence(timeout: 10),
            "expected yesterday wrap-up on Thursday return"
        )
        snapshot(app, name: "01-thursday-yesterday-presented")

        let weekly = app.otherElements["wrapup.sheet.weekly"]
        XCTAssertFalse(weekly.exists, "weekly must not present on Thursday")

        // Tap the in-sheet CTA, capture post-dismiss state.
        app.buttons["wrapup.dismissCTA"].firstMatch.tap()
        let dismissed = NSPredicate(format: "exists == false")
        expectation(for: dismissed, evaluatedWith: yesterday)
        waitForExpectations(timeout: 5)
        snapshot(app, name: "02-thursday-dismissed")
    }

    // MARK: - (b) Monday: yesterday + weekly sequencing

    func testMondayYesterdayThenWeekly() {
        // 2026-05-04 is a Monday (UTC). firstWeekday=Monday → weekly is due.
        let app = makeApp(fixedDate: "2026-05-04T12:00:00Z")
        app.launch()

        let yesterday = app.otherElements["wrapup.sheet.yesterday"]
        XCTAssertTrue(
            yesterday.waitForExistence(timeout: 10),
            "expected yesterday wrap-up to win first on Monday"
        )
        snapshot(app, name: "03-monday-yesterday-first")

        // Dismiss yesterday and watch for weekly to sequence in.
        app.buttons["wrapup.dismissCTA"].firstMatch.tap()
        let yesterdayGone = NSPredicate(format: "exists == false")
        expectation(for: yesterdayGone, evaluatedWith: yesterday)
        waitForExpectations(timeout: 5)
        snapshot(app, name: "04-monday-after-yesterday-dismiss")

        // Whether this passes encodes the bug-or-feature of this session:
        // the spec says "weekly is queued behind yesterday; never both at
        // once." The coordinator returns weekly on the next call, but
        // markWrapUpShown does not recompute, so we expect this to FAIL
        // until the fix lands. Capture the state either way.
        let weekly = app.otherElements["wrapup.sheet.weekly"]
        let appeared = weekly.waitForExistence(timeout: 5)
        snapshot(app, name: appeared ? "05-monday-weekly-sequenced" : "05-monday-weekly-MISSING")
        XCTAssertTrue(
            appeared,
            "weekly wrap-up must sequence in after yesterday dismissal on Monday"
        )

        // If we reach here, dismiss weekly cleanly. Re-query the dismiss
        // button each time — the sheet swap can leave a stale reference.
        let weeklyDismiss = app.buttons["wrapup.dismissCTA"].firstMatch
        XCTAssertTrue(
            weeklyDismiss.waitForExistence(timeout: 5),
            "weekly dismissCTA button must be hittable after sequencing"
        )
        weeklyDismiss.tap()
        let weeklyGone = NSPredicate(format: "exists == false")
        expectation(for: weeklyGone, evaluatedWith: weekly)
        waitForExpectations(timeout: 5)
        snapshot(app, name: "06-monday-after-weekly-dismiss")
    }

    // MARK: - (d) markWrapUpShown discipline — no re-present same session

    func testRepresentDoesNotFireSameSession() {
        let app = makeApp(fixedDate: "2026-04-30T12:00:00Z")
        app.launch()

        let yesterday = app.otherElements["wrapup.sheet.yesterday"]
        XCTAssertTrue(yesterday.waitForExistence(timeout: 10))
        app.buttons["wrapup.dismissCTA"].firstMatch.tap()
        let yesterdayGone = NSPredicate(format: "exists == false")
        expectation(for: yesterdayGone, evaluatedWith: yesterday)
        waitForExpectations(timeout: 5)

        // Force a foreground reconcile: deactivate then reactivate the app.
        XCUIDevice.shared.press(.home)
        sleep(2)
        app.activate()
        // Give bootstrap()/refreshFromHealthKit reconcile + 300s short-circuit
        // path a moment to settle. waitForExistence(false) gives us a real
        // wait instead of a stale snapshot read.
        let dontReturn = NSPredicate(format: "exists == false")
        let waited = expectation(for: dontReturn, evaluatedWith: yesterday)
        let result = XCTWaiter().wait(for: [waited], timeout: 8)
        snapshot(app, name: "07-no-represent-after-bg-fg")
        XCTAssertEqual(
            result,
            .completed,
            "yesterday wrap-up must not re-present after dismissal in same day"
        )
    }

    // MARK: - (c) Background mid-wrap-up

    func testBackgroundMidWrapUpKeepsSheet() {
        let app = makeApp(fixedDate: "2026-04-30T12:00:00Z")
        app.launch()

        let yesterday = app.otherElements["wrapup.sheet.yesterday"]
        XCTAssertTrue(yesterday.waitForExistence(timeout: 10))
        snapshot(app, name: "08-yesterday-before-bg")

        // Background and foreground without dismissing.
        XCUIDevice.shared.press(.home)
        sleep(1)
        app.activate()
        sleep(2)
        snapshot(app, name: "09-yesterday-after-bg-fg")

        XCTAssertTrue(
            yesterday.exists,
            "yesterday wrap-up sheet must survive a background/foreground cycle"
        )

        // Dismiss cleanly to leave state tidy.
        if app.buttons["wrapup.dismissCTA"].firstMatch.exists {
            app.buttons["wrapup.dismissCTA"].firstMatch.tap()
        }
    }
}
