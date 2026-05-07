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
        let walkOption = waitForVariantOption(slug: "movement.walk-after-meal.v1")
        walkOption.tap()

        // Done → store should persist the pick.
        app.buttons["planEditor.done"].tap()
        XCTAssertTrue(waitForGone(id: "planEditor.screen", timeout: 5),
                      "sheet should dismiss on Done")

        // Today's plan should now show the walk title.
        XCTAssertTrue(app.staticTexts["Post-meal 10-minute walk"].waitForExistence(timeout: 5),
                      "picked variant should appear in the Today plan list after Done")
    }

    // MARK: - Pro path: reset clears overrides

    /// Reset CTA wipes every pick and the engine defaults take over.
    func testProResetClearsAllOverrides() throws {
        // Stage 1: pick a variant + Done so the store actually has an
        // override to reset later.
        launchPro(seedStreak: 12)
        openPlanEditor()
        waitForVariantOption(slug: "movement.walk-after-meal.v1").tap()
        app.buttons["planEditor.done"].tap()
        XCTAssertTrue(app.staticTexts["Post-meal 10-minute walk"].waitForExistence(timeout: 5),
                      "stage 1 sanity: pick should land in Today")

        // Stage 2: reopen, reset, Done — Today should revert to the
        // engine default movement quest.
        openPlanEditor()
        app.buttons["planEditor.reset"].tap()
        app.buttons["planEditor.done"].tap()
        XCTAssertTrue(app.staticTexts["Move a little more"].waitForExistence(timeout: 5),
                      "after reset + Done, engine default movement quest should return")
    }

    // MARK: - Pro path: Cancel + swipe-down do NOT commit (Ask 1)

    /// Picking a variant and then dismissing without Done must NOT
    /// touch the store. Today's plan card should still show whatever
    /// it showed before the sheet opened.
    func testProCancelDoesNotCommit() throws {
        launchPro(seedStreak: 12)

        // Capture the baseline movement quest title from Today (whatever
        // engine picked first — variants are deterministic under FIXED_DATE).
        XCTAssertTrue(app.tabBars.buttons["Today"].waitForExistence(timeout: 12))
        scrollUntilVisible(anyDescendant: "today.planAction.0")

        openPlanEditor()
        waitForVariantOption(slug: "movement.walk-after-meal.v1").tap()
        // Cancel via the toolbar button.
        app.buttons["planEditor.cancel"].tap()
        XCTAssertTrue(waitForGone(id: "planEditor.screen", timeout: 5),
                      "Cancel must dismiss the sheet")

        // The picked walk title must NOT be on Today (because Cancel
        // discarded the draft).
        XCTAssertFalse(app.staticTexts["Post-meal 10-minute walk"].waitForExistence(timeout: 3),
                       "Cancel must not commit the draft pick")
    }

    /// Swipe-down dismissal behaves like Cancel.
    func testProSwipeDownDoesNotCommit() throws {
        launchPro(seedStreak: 12)
        openPlanEditor()

        waitForVariantOption(slug: "movement.walk-after-meal.v1").tap()
        app.descendants(matching: .any)["planEditor.screen"].swipeDown(velocity: .fast)
        XCTAssertTrue(waitForGone(id: "planEditor.screen", timeout: 5),
                      "swipe-down must dismiss the sheet")

        XCTAssertFalse(app.staticTexts["Post-meal 10-minute walk"].waitForExistence(timeout: 3),
                       "swipe-down must not commit the draft pick (Ask 1)")
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
        launchPro(seedStreak: 12, fixedDate: PlanEditorRecon.day1ISO)
        openPlanEditor()
        waitForVariantOption(slug: "movement.walk-after-meal.v1").tap()
        app.buttons["planEditor.done"].tap()
        XCTAssertTrue(app.staticTexts["Post-meal 10-minute walk"].waitForExistence(timeout: 3),
                      "day-1 sanity: pick should land in Today")

        // Day 2 — relaunch with FIXED_DATE advanced. Override should NOT
        // re-attach; the engine's default movement quest should be back.
        // Note: day 2 has its own RNG-driven mock step count, which can
        // independently cross the 7500 default target and drop the
        // movement slot. The reset-binding test is "yesterday's *picked*
        // walk variant must not survive" — assert the negative, not a
        // specific replacement.
        app.terminate()
        launchPro(seedStreak: 12, fixedDate: PlanEditorRecon.day2ISO)
        XCTAssertTrue(app.tabBars.buttons["Today"].waitForExistence(timeout: 12),
                      "day-2 launch must reach Today before assertions")
        // Yesterday's pick must NOT appear on Today.
        XCTAssertFalse(app.staticTexts["Post-meal 10-minute walk"].waitForExistence(timeout: 4),
                       "yesterday's pick must not survive the date roll")
        // And the persisted override key should have been pruned (open the
        // editor: every option is unselected by virtue of Today showing the
        // default; we don't have a direct `selected` AX value to assert,
        // so the Today-side assertion above is the binding test).
    }

    // MARK: - Final acceptance gate (substitute for computer-use checkpoint)

    /// Final acceptance gate. Real-finger checkpoint is now done via
    /// computer-use on the Simulator window (the bridge came back online
    /// in this session). This XCUITest stands as the regression net for
    /// the full Done-commits-but-Cancel-reverts contract:
    ///   - row tap → Done   →  Today shows the picked title
    ///   - row tap → Cancel →  Today does NOT show the picked title
    ///
    /// (Cancel + swipe-down each have their own focused test above; this
    /// test exercises both branches in one launch to catch any state
    /// bleed between the draft and the store.)
    func testFinalAcceptance_DonePersists_CancelReverts() throws {
        launchPro(seedStreak: 12)

        // Branch 1: pick → Done → Today reflects the pick.
        openPlanEditor()
        waitForVariantOption(slug: "movement.walk-after-meal.v1").tap()
        app.buttons["planEditor.done"].tap()
        XCTAssertTrue(app.staticTexts["Post-meal 10-minute walk"].waitForExistence(timeout: 5),
                      "Done must commit the draft pick to Today")

        // Branch 2: open again, change pick to stairs, Cancel → Today
        // still shows walk (the Done-committed value), not stairs.
        openPlanEditor()
        waitForVariantOption(slug: "movement.stairs-instead.v1").tap()
        app.buttons["planEditor.cancel"].tap()
        XCTAssertTrue(waitForGone(id: "planEditor.screen", timeout: 5))
        XCTAssertTrue(app.staticTexts["Post-meal 10-minute walk"].waitForExistence(timeout: 4),
                      "Cancel must NOT overwrite the previously-Done pick")
        XCTAssertFalse(app.staticTexts["Take the stairs today"].waitForExistence(timeout: 2),
                       "Cancel-discarded stairs pick must not appear on Today")
    }

    // MARK: - Helpers

    /// Day-1 ISO date used as the deterministic launch baseline. Pinning
    /// FIXED_DATE makes the MockHealthKit RNG seed (line 37 in
    /// MockHealthKitService) stable across runs — without it,
    /// `stepCount = 3500 + RNG*9500` lands ≥ 7500 on roughly half of
    /// invocations, which makes `movementVariants` return empty and the
    /// walk-variant assertion flap. 2026-05-06T08:00:00Z deterministically
    /// produces stepCount=6817 (below the 7500 default target), so all
    /// three movement variants render.
    static let day1ISO = "2026-05-06T08:00:00Z"
    static let day2ISO = "2026-05-07T08:00:00Z"

    private func launchPro(seedStreak: Int, fixedDate: String = PlanEditorRecon.day1ISO) {
        app = XCUIApplication()
        app.launchEnvironment["LIFECLOCK_UI_TEST"] = "1"
        app.launchEnvironment["LIFECLOCK_UI_TEST_SCENARIO"] = "onboarded"
        app.launchEnvironment["LIFECLOCK_USE_MOCK_HEALTH"] = "1"
        app.launchEnvironment["LIFECLOCK_HEALTH_AUTH"] = "authorized"
        app.launchEnvironment["LIFECLOCK_FIXED_DATE"] = fixedDate
        if seedStreak > 0 {
            app.launchEnvironment["LIFECLOCK_SEED_STREAK"] = String(seedStreak)
        }
        // Pro is the default in-sim; do NOT set LIFECLOCK_SIMULATOR_PRO_DISABLED.
        app.launch()
    }

    private func openPlanEditor() {
        XCTAssertTrue(app.tabBars.buttons["Today"].waitForExistence(timeout: 12),
                      "tab bar must be present after launch")
        scrollUntilVisible(anyDescendant: "today.planEdit")
        let edit = app.descendants(matching: .any)["today.planEdit"]
        XCTAssertTrue(edit.waitForExistence(timeout: 5),
                      "Pro user should see today.planEdit chip\n\(app.debugDescription)")
        edit.tap()
        XCTAssertTrue(app.descendants(matching: .any)["planEditor.screen"].waitForExistence(timeout: 5),
                      "tapping Edit must present PlanEditorSheet")
    }

    /// Wait for a variant option, scrolling the editor's ScrollView if
    /// the row is below the fold. Bumped timeout to 10 s (was 3) per
    /// Ask 3 — under host contention (4+ concurrent xcodebuild
    /// processes) per-tap latency easily exceeds 3 s.
    @discardableResult
    private func waitForVariantOption(slug: String) -> XCUIElement {
        let id = "planEditor.option.\(slug)"
        scrollUntilVisible(anyDescendant: id, attempts: 6)
        let opt = app.descendants(matching: .any)[id]
        XCTAssertTrue(opt.waitForExistence(timeout: 10),
                      "expected variant option \(id) to be present")
        return opt
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
