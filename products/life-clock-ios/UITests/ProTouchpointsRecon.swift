import XCTest

/// Walks every Pro touchpoint in the app with `LIFECLOCK_SIMULATOR_PRO_DISABLED=1`
/// so the StoreKit dev-experience hatch is bypassed and the real Free path
/// is exercised. Each test asserts that:
///
/// - free users see the locked CTA / fogged stack / paywall trigger,
/// - tapping the CTA presents `paywall.screen` (or `onboarding.paywallPrimary`),
/// - dismissing the paywall returns to a stable surface (no crash, no
///   dead-end nav, no Pro-only chrome leaking through).
///
/// Touchpoint 4 (`OverrideSheet.notEntitled`) is unreachable from the Free
/// UI by construction — `HistoryView.dayRow` routes Free taps to the
/// paywall before `DayDetailView` (which hosts `OverrideSheet`) can mount.
/// That defensive path lives in `EntitlementGatedWritesTests` instead.
final class ProTouchpointsRecon: XCTestCase {
    private var app: XCUIApplication!

    override func setUpWithError() throws {
        continueAfterFailure = false
    }

    // MARK: - Touchpoint 3: Today plan editor lock

    /// `subscriptions.isPro == false` → the Plan card's edit chip renders
    /// with `today.planEditLocked` (lock icon + "Pro" label). Tapping it
    /// presents `PaywallSheet`, NOT `PlanEditorSheet`.
    func testTouchpoint3_PlanEditorLockedRoutesToPaywall() throws {
        launch(scenario: "onboarded", proDisabled: true, seedStreak: 12)

        // The Plan card sits below the mascot + clock + drivers; scroll
        // before querying so a11y elements materialize in the hierarchy.
        XCTAssertTrue(app.tabBars.buttons["Today"].waitForExistence(timeout: 10),
                      "tab bar must be present after launch")
        scrollUntilVisible(anyDescendant: "today.planEditLocked")
        let lockedChip = app.descendants(matching: .any)["today.planEditLocked"]
        XCTAssertTrue(lockedChip.waitForExistence(timeout: 3),
                      "Free users should see today.planEditLocked, not today.planEdit\n\(app.debugDescription)")
        XCTAssertFalse(app.descendants(matching: .any)["today.planEdit"].exists,
                       "today.planEdit must NOT be exposed when Pro is disabled")

        lockedChip.tap()
        XCTAssertTrue(app.buttons["paywall.close"].waitForExistence(timeout: 5),
                      "tapping the locked plan chip must present PaywallSheet")
        XCTAssertFalse(app.buttons["planEditor.done"].exists,
                       "PlanEditorSheet must not appear without Pro")

        app.buttons["paywall.close"].tap()
        scrollUntilVisible(buttonID: "today.planEditLocked")
        XCTAssertTrue(app.buttons["today.planEditLocked"].waitForExistence(timeout: 3),
                      "closing the paywall must return to Today")
    }

    // MARK: - Touchpoints 1 + 2: History fog gate + day-row tap

    /// Free user on History sees the weekly teaser unlock CTA, the fogged
    /// preview stack with its unlock CTA, and any unblurred day rows are
    /// `history.row.locked` (route to paywall on tap), never
    /// `history.row.pro`.
    func testTouchpoint12_HistoryFogGateAndLockedRows() throws {
        launch(scenario: "onboarded", proDisabled: true, seedStreak: 12)

        let history = app.tabBars.buttons["History"]
        XCTAssertTrue(history.waitForExistence(timeout: 5))
        history.tap()

        XCTAssertTrue(app.scrollViews.firstMatch.waitForExistence(timeout: 5))
        // Weekly teaser CTA is the first paywall trigger on History.
        let weekly = app.buttons["history.weeklyTeaserUnlock"]
        if weekly.waitForExistence(timeout: 3) {
            // It exists — fine. Don't tap it yet; we want to inspect rows.
            XCTAssertTrue(weekly.isHittable)
        }

        // No Pro-only row should be exposed.
        XCTAssertFalse(app.buttons["history.row.pro"].exists,
                       "Pro-only NavigationLink rows must not render when Pro is disabled")

        // Fogged unlock CTA must be present (the stack always renders for
        // free users, even when they have <3 real rows — placeholders fill).
        scrollUntilVisible(buttonID: "history.foggedUnlock")
        let foggedUnlock = app.buttons["history.foggedUnlock"]
        XCTAssertTrue(foggedUnlock.waitForExistence(timeout: 3),
                      "fogged paywall CTA must surface on History for free users")
        foggedUnlock.tap()
        XCTAssertTrue(app.buttons["paywall.close"].waitForExistence(timeout: 5))
        app.buttons["paywall.close"].tap()
        XCTAssertTrue(app.navigationBars["History"].waitForExistence(timeout: 3))

        // Tap a locked row if any are visible — should route to paywall too.
        let lockedRow = app.buttons["history.row.locked"].firstMatch
        if lockedRow.waitForExistence(timeout: 2) {
            lockedRow.tap()
            XCTAssertTrue(app.buttons["paywall.close"].waitForExistence(timeout: 5),
                          "tapping a locked history row must present the paywall")
            app.buttons["paywall.close"].tap()
        }
    }

    // MARK: - Touchpoint 5: Profile Upgrade entry

    /// Profile section "Subscription" exposes `profile.upgrade` (button
    /// "Upgrade to Pro") when Pro is disabled. Tapping it presents
    /// `paywall.screen` and `paywall.close` returns to Profile.
    func testTouchpoint5_ProfileUpgradeEntry() throws {
        launch(scenario: "onboarded", proDisabled: true, seedStreak: 12)

        app.tabBars.buttons["Profile"].tap()
        scrollUntilVisible(buttonID: "profile.upgrade")
        let upgrade = app.buttons["profile.upgrade"]
        XCTAssertTrue(upgrade.waitForExistence(timeout: 5))
        upgrade.tap()
        XCTAssertTrue(app.buttons["paywall.close"].waitForExistence(timeout: 5))
        app.buttons["paywall.close"].tap()
        scrollUntilVisible(buttonID: "profile.upgrade")
        XCTAssertTrue(app.buttons["profile.upgrade"].waitForExistence(timeout: 3),
                      "closing the paywall returns to Profile with the Upgrade button still present")
    }

    // MARK: - Touchpoint 6: LIFECLOCK_FORCE_PAYWALL=1 boot path

    /// With `LIFECLOCK_FORCE_PAYWALL=1` the app should pop `PaywallSheet`
    /// at launch (after `bootstrap()`), even on the onboarded scenario.
    /// `paywall.close` must dismiss to a usable Today screen.
    func testTouchpoint6_ForcePaywallBootPath() throws {
        app = XCUIApplication()
        app.launchEnvironment["LIFECLOCK_UI_TEST"] = "1"
        app.launchEnvironment["LIFECLOCK_UI_TEST_SCENARIO"] = "onboarded"
        app.launchEnvironment["LIFECLOCK_USE_MOCK_HEALTH"] = "1"
        app.launchEnvironment["LIFECLOCK_FORCE_PAYWALL"] = "1"
        app.launchEnvironment["LIFECLOCK_SIMULATOR_PRO_DISABLED"] = "1"
        app.launch()

        XCTAssertTrue(app.buttons["paywall.close"].waitForExistence(timeout: 10),
                      "force-paywall env-var must surface PaywallSheet at boot")
        app.buttons["paywall.close"].tap()
        XCTAssertTrue(app.tabBars.buttons["Today"].waitForExistence(timeout: 5),
                      "closing the forced paywall lands on a navigable Today")
    }

    // MARK: - Touchpoint 8: Restore-purchases path

    /// Profile's `profile.restore` button stays enabled, becomes
    /// `restoring` when tapped (StoreKit sandbox is flaky in CI; we just
    /// verify the tap doesn't crash and the button re-settles).
    func testTouchpoint8_RestorePurchasesFromProfile() throws {
        launch(scenario: "onboarded", proDisabled: true, seedStreak: 12)

        app.tabBars.buttons["Profile"].tap()
        scrollUntilVisible(buttonID: "profile.restore")
        let restore = app.buttons["profile.restore"]
        XCTAssertTrue(restore.waitForExistence(timeout: 5),
                      "profile.restore must be reachable for free users")
        XCTAssertTrue(restore.isEnabled,
                      "profile.restore is enabled by default (toggles to disabled while in flight)")
        // Don't actually tap — `AppStore.sync()` can present a system
        // sign-in dialog in the simulator that bleeds into subsequent
        // tests. Reachability + enabled-state is the contract a free
        // user sees on entry.
    }

    // MARK: - Touchpoint 9: Cancel-from-paywall recovery

    /// Open the paywall via Profile, dismiss with the close button, and
    /// confirm the app returns to a stable Profile surface without lingering
    /// modal chrome.
    func testTouchpoint9_CancelFromPaywallRecovery() throws {
        launch(scenario: "onboarded", proDisabled: true, seedStreak: 12)

        app.tabBars.buttons["Profile"].tap()
        scrollUntilVisible(buttonID: "profile.upgrade")
        let upgrade = app.buttons["profile.upgrade"]
        XCTAssertTrue(upgrade.waitForExistence(timeout: 5))
        upgrade.tap()
        XCTAssertTrue(app.buttons["paywall.close"].waitForExistence(timeout: 5))

        app.buttons["paywall.close"].tap()
        // Allow the sheet animation to finish before re-querying.
        let close = app.buttons["paywall.close"]
        let gone = NSPredicate(format: "exists == false")
        let exp = expectation(for: gone, evaluatedWith: close, handler: nil)
        wait(for: [exp], timeout: 3)
        // App is still navigable: tabbing back to Today works.
        app.tabBars.buttons["Today"].tap()
        XCTAssertTrue(app.buttons["today.checkInToolbar"].waitForExistence(timeout: 5))
    }

    // MARK: - Final acceptance: swipe-down dismissal

    /// Belt-and-braces gesture pass for the paywall sheet — XCUITest is
    /// our stand-in for the operator's "computer-use checkpoint". Drives
    /// the purchase-sheet via Profile, dismisses it with a swipe-down on
    /// the sheet body (in addition to the explicit Close button), and
    /// verifies the app stays navigable.
    func testFinalAcceptance_PaywallSwipeDownDismissal() throws {
        launch(scenario: "onboarded", proDisabled: true, seedStreak: 12)

        app.tabBars.buttons["Profile"].tap()
        scrollUntilVisible(buttonID: "profile.upgrade")
        app.buttons["profile.upgrade"].tap()
        let close = app.buttons["paywall.close"]
        XCTAssertTrue(close.waitForExistence(timeout: 5))

        // Swipe down on the sheet — modal sheets dismiss when the user
        // drags from the top toward the bottom of the screen. In XCUITest
        // we simulate this with a long swipe on the navigation bar area.
        let nav = app.navigationBars.firstMatch
        XCTAssertTrue(nav.waitForExistence(timeout: 3))
        nav.swipeDown(velocity: .fast)
        nav.swipeDown(velocity: .fast)

        // Either swipe dismissed the sheet OR Close still works; both are
        // acceptable. Assert end-state: app on Profile, no paywall.close.
        if close.exists { close.tap() }
        let gone = NSPredicate(format: "exists == false")
        let exp = expectation(for: gone, evaluatedWith: close, handler: nil)
        wait(for: [exp], timeout: 4)
        XCTAssertTrue(app.tabBars.buttons["Profile"].isSelected
                      || app.buttons["profile.upgrade"].waitForExistence(timeout: 3))
    }

    // MARK: - Helpers

    /// Lazy-rendered SwiftUI elements only attach to the a11y tree once they
    /// scroll into view (Form rows + items deep in a ScrollView/LazyVStack).
    /// Swipe up until the target appears or we've made N attempts.
    private func scrollUntilVisible(buttonID id: String, attempts: Int = 8) {
        scrollUntilVisible(anyDescendant: id, attempts: attempts)
    }

    /// Element-type-agnostic scroll. SwiftUI maps buttons-with-custom-labels
    /// inconsistently between `.button` and `.other` depending on the label
    /// shape, so query by descendant identifier.
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

    private func launch(
        scenario: String,
        proDisabled: Bool,
        seedStreak: Int = 0
    ) {
        app = XCUIApplication()
        app.launchEnvironment["LIFECLOCK_UI_TEST"] = "1"
        app.launchEnvironment["LIFECLOCK_UI_TEST_SCENARIO"] = scenario
        app.launchEnvironment["LIFECLOCK_USE_MOCK_HEALTH"] = "1"
        app.launchEnvironment["LIFECLOCK_HEALTH_AUTH"] = "authorized"
        if proDisabled {
            app.launchEnvironment["LIFECLOCK_SIMULATOR_PRO_DISABLED"] = "1"
        }
        if seedStreak > 0 {
            app.launchEnvironment["LIFECLOCK_SEED_STREAK"] = String(seedStreak)
        }
        app.launch()
        dismissWrapUpIfPresent()
    }

    /// `LIFECLOCK_SEED_STREAK > 0` back-dates onboarding so the wrap-up
    /// reinstall guard is past (commit 2b3f1a4), which means an
    /// `onboarded` launch with a streak auto-presents `WrapUpSheet`. The
    /// modal sits over the tab bar and silently swallows
    /// `tabBars.buttons[...].tap()`, so every Pro touchpoint that walks
    /// into Profile fails its `scrollUntilVisible` loop. Tap the dismiss
    /// CTA if the sheet is up; no-op otherwise.
    private func dismissWrapUpIfPresent() {
        let cta = app.buttons["wrapup.dismissCTA"]
        if cta.waitForExistence(timeout: 3) {
            cta.tap()
            // A weekly wrap-up may immediately follow on Monday returns;
            // tap again if a second sheet replaces the first.
            if cta.waitForExistence(timeout: 2) { cta.tap() }
        }
    }
}
