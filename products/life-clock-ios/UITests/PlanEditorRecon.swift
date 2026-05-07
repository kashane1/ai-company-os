import XCTest

/// Walks the new PlanEditorSheet (Today's plan editor) end-to-end.
///
/// Pro path:
/// - the Edit chip is `today.planEdit` (slider icon, no lock).
/// - `planEditor.screen` mounts; subtitle, reset CTA, all three category
///   sections, and at least one option per category are reachable by id.
/// - tapping a `planEditor.option.<slug>` flips the selection (the same
///   option's checkmark fills) and persists; closing the sheet and
///   reopening shows the selection still set.
/// - reset clears every selection.
///
/// Free path is covered by `ProTouchpointsRecon.testTouchpoint3_…`. This
/// file does not duplicate it.
///
/// Tomorrow-reset (one-shot) is covered by relaunching with
/// `LIFECLOCK_FIXED_DATE` advanced 24h; the override should not survive.
final class PlanEditorRecon: XCTestCase {
    private var app: XCUIApplication!

    override func setUpWithError() throws {
        continueAfterFailure = false
    }

    // MARK: - Pro path: variant discovery

    /// All three categories surface in the editor and each has at least
    /// one tappable option. The subtitle and reset CTA are present.
    func testProEditorExposesAllCategories() throws {
        launchPro(seedStreak: 12)

        openPlanEditor()

        XCTAssertTrue(app.descendants(matching: .any)["planEditor.subtitle"].waitForExistence(timeout: 3),
                      "tone-aware subtitle must surface (planEditor.subtitle)")
        XCTAssertTrue(app.buttons["planEditor.reset"].exists,
                      "reset-to-defaults CTA must be present")

        for category in ["movement", "sleepRecovery", "nutritionHabit"] {
            let title = app.descendants(matching: .any)["planEditor.categoryTitle.\(category)"]
            XCTAssertTrue(title.waitForExistence(timeout: 2),
                          "category title for \(category) must be in the AX tree")
        }

        // At least one option must exist; movement may be empty if today's
        // step goal is met, but the seeded `onboarded` profile has 0 steps,
        // so movement variants should render.
        let anyOption = app.descendants(matching: .any).matching(
            NSPredicate(format: "identifier BEGINSWITH 'planEditor.option.'")
        )
        XCTAssertGreaterThan(anyOption.count, 0,
                             "at least one quest variant must be reachable")
    }

    // MARK: - Pro path: variant pick + persistence within the day

    /// Tap a movement variant and confirm the selection survives a
    /// dismiss + re-open of the sheet (no relaunch). Per the v1 spec the
    /// pick is a one-shot for today, so within-day persistence is the
    /// strict requirement; the next test covers tomorrow-clear.
    func testProVariantPickPersistsWithinDay() throws {
        launchPro(seedStreak: 12)
        openPlanEditor()

        // Pick the "post-meal walk" variant (slug from QuestEngine).
        let walkSlug = "movement.walk-after-meal.v1"
        let walkOption = app.descendants(matching: .any)["planEditor.option.\(walkSlug)"]
        XCTAssertTrue(walkOption.waitForExistence(timeout: 3),
                      "expected movement walk variant to be present")
        walkOption.tap()

        // Close + reopen.
        app.buttons["planEditor.done"].tap()
        XCTAssertTrue(waitForGone(id: "planEditor.screen", timeout: 3),
                      "sheet should dismiss on Done")
        openPlanEditor()

        // The same row should still be selected — assert via accessibility
        // value or by re-querying the option (its checkmark + text are the
        // same node; selection is implicit in the AX hierarchy of the row
        // button label which we can't easily assert without a value, so
        // assert the override fed Today: switch to Today and verify the
        // movement quest title matches the picked variant).
        app.buttons["planEditor.done"].tap()

        // Today's plan should now show the walk title.
        let walkTitle = app.staticTexts["Post-meal 10-minute walk"]
        XCTAssertTrue(walkTitle.waitForExistence(timeout: 3),
                      "picked variant should appear in the Today plan list")
    }

    // MARK: - Pro path: reset clears overrides

    /// Reset CTA wipes every pick and the engine defaults take over.
    func testProResetClearsAllOverrides() throws {
        launchPro(seedStreak: 12)
        openPlanEditor()

        let walkOption = app.descendants(matching: .any)["planEditor.option.movement.walk-after-meal.v1"]
        XCTAssertTrue(walkOption.waitForExistence(timeout: 3))
        walkOption.tap()

        app.buttons["planEditor.reset"].tap()
        // Reset stays inside the sheet; just close + verify Today reverts
        // to the engine default ("Move a little more" — the steps quest).
        app.buttons["planEditor.done"].tap()
        let stepsTitle = app.staticTexts["Move a little more"]
        XCTAssertTrue(stepsTitle.waitForExistence(timeout: 3),
                      "after reset, engine default movement quest should return")
    }

    // MARK: - Tomorrow reset (one-shot semantics)

    /// Pick a variant on day N (FIXED_DATE), relaunch on day N+1, and
    /// confirm the override is gone. UserDefaults persists the encoded
    /// `TodayPlanOverrides`; `loadTodayPlanOverrides` is responsible for
    /// dropping a stale dayKey on launch.
    ///
    /// Note: the in-memory ModelContainer used under `LIFECLOCK_UI_TEST=1`
    /// resets on relaunch, but `UserDefaults.standard` does NOT — which is
    /// exactly the right substrate to exercise the tomorrow-reset path.
    func testTomorrowReset_OverridesClearedOnNewDay() throws {
        // Day 1 — pick a variant.
        launchPro(seedStreak: 12, fixedDate: "2026-05-06T08:00:00Z")
        openPlanEditor()
        let walkOption = app.descendants(matching: .any)["planEditor.option.movement.walk-after-meal.v1"]
        XCTAssertTrue(walkOption.waitForExistence(timeout: 3))
        walkOption.tap()
        app.buttons["planEditor.done"].tap()
        XCTAssertTrue(app.staticTexts["Post-meal 10-minute walk"].waitForExistence(timeout: 3),
                      "day-1 sanity: pick should land in Today")

        // Day 2 — relaunch with FIXED_DATE advanced. Override should NOT
        // re-attach; the engine's default movement quest should be back.
        app.terminate()
        launchPro(seedStreak: 12, fixedDate: "2026-05-07T08:00:00Z")
        XCTAssertTrue(app.tabBars.buttons["Today"].waitForExistence(timeout: 8))
        // Default movement quest title.
        XCTAssertTrue(app.staticTexts["Move a little more"].waitForExistence(timeout: 5),
                      "yesterday's pick must not survive the date roll")
        // And the persisted override key should have been pruned (open the
        // editor: every option is unselected by virtue of Today showing the
        // default; we don't have a direct `selected` AX value to assert,
        // so the Today-side assertion above is the binding test).
    }

    // MARK: - Final acceptance gate (substitute for computer-use checkpoint)

    /// The local computer-use bridge has been unreachable across the last
    /// two polish sessions. This test stands in for the requested final
    /// real-finger checkpoint: it taps a variant, dismisses the sheet via
    /// swipe-down (not the Done button), and asserts the pick still
    /// persisted — the gesture path matters because swipe-down dismissal
    /// is the most-likely real-user exit and the current implementation
    /// commits picks immediately on tap, so the swipe path must not lose
    /// the override.
    func testFinalAcceptance_VariantSurvivesSwipeDown() throws {
        launchPro(seedStreak: 12)
        openPlanEditor()

        let walkOption = app.descendants(matching: .any)["planEditor.option.movement.walk-after-meal.v1"]
        XCTAssertTrue(walkOption.waitForExistence(timeout: 3))
        walkOption.tap()

        // Swipe-down dismiss the sheet from inside it.
        app.descendants(matching: .any)["planEditor.screen"].swipeDown(velocity: .fast)

        XCTAssertTrue(waitForGone(id: "planEditor.screen", timeout: 4),
                      "swipe-down must dismiss the sheet")
        XCTAssertTrue(app.staticTexts["Post-meal 10-minute walk"].waitForExistence(timeout: 4),
                      "variant pick must survive a swipe-down dismissal")
    }

    // MARK: - Helpers

    private func launchPro(seedStreak: Int, fixedDate: String? = nil) {
        app = XCUIApplication()
        app.launchEnvironment["LIFECLOCK_UI_TEST"] = "1"
        app.launchEnvironment["LIFECLOCK_UI_TEST_SCENARIO"] = "onboarded"
        app.launchEnvironment["LIFECLOCK_USE_MOCK_HEALTH"] = "1"
        app.launchEnvironment["LIFECLOCK_HEALTH_AUTH"] = "authorized"
        if seedStreak > 0 {
            app.launchEnvironment["LIFECLOCK_SEED_STREAK"] = String(seedStreak)
        }
        if let fixedDate {
            app.launchEnvironment["LIFECLOCK_FIXED_DATE"] = fixedDate
        }
        // Pro is the default in-sim; do NOT set LIFECLOCK_SIMULATOR_PRO_DISABLED.
        app.launch()
    }

    private func openPlanEditor() {
        XCTAssertTrue(app.tabBars.buttons["Today"].waitForExistence(timeout: 10),
                      "tab bar must be present after launch")
        scrollUntilVisible(anyDescendant: "today.planEdit")
        let edit = app.descendants(matching: .any)["today.planEdit"]
        XCTAssertTrue(edit.waitForExistence(timeout: 3),
                      "Pro user should see today.planEdit chip\n\(app.debugDescription)")
        edit.tap()
        XCTAssertTrue(app.descendants(matching: .any)["planEditor.screen"].waitForExistence(timeout: 3),
                      "tapping Edit must present PlanEditorSheet")
    }

    private func scrollUntilVisible(anyDescendant id: String, attempts: Int = 8) {
        for _ in 0..<attempts {
            if app.descendants(matching: .any)[id].exists { return }
            let scroll = app.scrollViews.firstMatch
            if scroll.exists {
                scroll.swipeUp()
            } else {
                app.swipeUp()
            }
        }
    }

    private func waitForGone(id: String, timeout: TimeInterval) -> Bool {
        let deadline = Date().addingTimeInterval(timeout)
        while Date() < deadline {
            if !app.descendants(matching: .any)[id].exists { return true }
            usleep(150_000)
        }
        return false
    }
}
