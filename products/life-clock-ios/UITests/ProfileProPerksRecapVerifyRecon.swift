import XCTest

/// PV-P4 visual verification of the Profile "Your Pro perks" recap that
/// Sprint E `8a56234` shipped at code level but no session had ever seen
/// on screen. NOT a behaviour change — a recon that captures the Profile
/// Subscription section in Pro and Free and asserts the shipped contract:
///
/// - Pro: section order is Pro·Active (`checkmark.seal.fill`) → Manage
///   subscription (`profile.manageSubscription`) → "Your Pro perks" recap
///   (`profile.proPerks`, the 5 `ProPerks.perks` titles) → Restore
///   (`profile.restore`). The recap renders the 5 titles element-for-
///   element from `ProPerks.perks` (same source `PaywallSheet.header`
///   consumes), so the two surfaces cannot drift.
/// - Free (`LIFECLOCK_SIMULATOR_PRO_DISABLED=1`): the recap is ABSENT and
///   the tone-aware Upgrade subline (`profile.upgrade`) shows instead.
///
/// Captures land under
/// `docs/products/life-clock/research/profile-properks-2026-05-16/`.
final class ProfileProPerksRecapVerifyRecon: XCTestCase {
    private let outDir =
        "/Users/simons/ai-company-os/.claude/worktrees/dazzling-roentgen-dfcc33/docs/products/life-clock/research/profile-properks-2026-05-16"

    /// Mirror of `ProPerks.perks` titles — the recap must render these
    /// element-for-element and in this order.
    private let expectedPerkTitles = [
        "Full daily history",
        "Weekly drivers + next-best lever",
        "Correction power",
        "Custom Today's Plan",
        "Deeper trend breakdown",
    ]

    override func setUpWithError() throws {
        continueAfterFailure = false
        try? FileManager.default.createDirectory(
            atPath: outDir, withIntermediateDirectories: true
        )
    }

    // MARK: - Pro state: recap present, quiet, ordered, element-for-element

    func testProState_PerksRecapPresentQuietOrdered() throws {
        let app = launch(proDisabled: false)

        app.tabBars.buttons["Profile"].tap()
        scrollUntilVisible(anyDescendant: "profile.proPerks", in: app)

        let recap = app.descendants(matching: .any)["profile.proPerks"]
        XCTAssertTrue(recap.waitForExistence(timeout: 5),
                      "Pro user must see the quiet profile.proPerks recap\n\(app.debugDescription)")

        // Order: Pro·Active row + Manage subscription must precede the
        // recap, and Restore must follow it (vertical y ordering in the
        // Subscription Form section).
        let manage = app.descendants(matching: .any)["profile.manageSubscription"]
        let restore = app.buttons["profile.restore"]
        XCTAssertTrue(manage.exists, "profile.manageSubscription must exist for Pro")
        XCTAssertTrue(restore.exists, "profile.restore must exist")
        XCTAssertLessThan(manage.frame.minY, recap.frame.minY,
                          "Manage subscription must sit ABOVE the perks recap")
        XCTAssertLessThan(recap.frame.maxY, restore.frame.maxY,
                          "Restore must sit BELOW the perks recap")

        // Pro·Active row — the checkmark.seal.fill + "Active" label.
        XCTAssertTrue(app.staticTexts["Active"].exists,
                      "Pro·Active row must render the Active label")

        // The recap is accessibilityElement(children: .combine) so the 5
        // perk titles fold into the element's combined label. Assert each
        // title is present, in order, in that label.
        let combined = recap.label
        var searchFrom = combined.startIndex
        for title in expectedPerkTitles {
            guard let range = combined.range(of: title, range: searchFrom..<combined.endIndex) else {
                XCTFail("perk title '\(title)' missing or out of order in recap label: \(combined)")
                return
            }
            searchFrom = range.upperBound
        }
        XCTAssertTrue(combined.contains("Your Pro perks"),
                      "recap must carry its quiet 'Your Pro perks' caption")

        capture("pro-subscription-section", app: app)
    }

    // MARK: - Free state: recap absent, tone-aware Upgrade subline present

    func testFreeState_PerksRecapAbsentUpgradeSublinePresent() throws {
        let app = launch(proDisabled: true)

        app.tabBars.buttons["Profile"].tap()
        scrollUntilVisible(anyDescendant: "profile.upgrade", in: app)

        XCTAssertTrue(app.descendants(matching: .any)["profile.upgrade"].waitForExistence(timeout: 5),
                      "Free user must see the profile.upgrade row\n\(app.debugDescription)")
        XCTAssertFalse(app.descendants(matching: .any)["profile.proPerks"].exists,
                       "profile.proPerks recap MUST be absent for Free users")
        XCTAssertFalse(app.descendants(matching: .any)["profile.manageSubscription"].exists,
                       "Manage subscription must NOT render for Free users")

        // Tone-aware Upgrade subline (default/coach tone copy).
        let coachSubline =
            "Full daily history, weekly drivers + next-best lever, and correction power."
        XCTAssertTrue(app.staticTexts[coachSubline].exists,
                      "tone-aware Upgrade subline must render under the Upgrade row")

        // The upgrade row attaches to the a11y tree slightly before it is
        // fully on-screen; nudge the Subscription section into frame for
        // the capture (best-effort — the assertions above already prove
        // the contract regardless of scroll position).
        scrollUntilVisible(anyDescendant: "profile.restore", in: app)
        capture("free-subscription-section", app: app)
    }

    // MARK: - Helpers

    private func scrollUntilVisible(anyDescendant id: String, in app: XCUIApplication, attempts: Int = 8) {
        for _ in 0..<attempts {
            if app.descendants(matching: .any)[id].exists { return }
            let scroll = app.scrollViews.firstMatch
            if scroll.exists { scroll.swipeUp() } else { app.swipeUp() }
        }
    }

    private func launch(proDisabled: Bool) -> XCUIApplication {
        let app = XCUIApplication()
        app.launchEnvironment["LIFECLOCK_UI_TEST"] = "1"
        app.launchEnvironment["LIFECLOCK_UI_TEST_SCENARIO"] = "onboarded"
        app.launchEnvironment["LIFECLOCK_INITIAL_TAB"] = "profile"
        app.launchEnvironment["LIFECLOCK_USE_MOCK_HEALTH"] = "1"
        app.launchEnvironment["LIFECLOCK_HEALTH_AUTH"] = "authorized"
        if proDisabled {
            app.launchEnvironment["LIFECLOCK_SIMULATOR_PRO_DISABLED"] = "1"
        }
        app.launch()
        // An onboarded launch with no seeded streak does not auto-present
        // the wrap-up, but guard anyway so a stray sheet can't swallow taps.
        let cta = app.buttons["wrapup.dismissCTA"]
        if cta.waitForExistence(timeout: 2) { cta.tap() }
        return app
    }

    private func capture(_ name: String, app: XCUIApplication) {
        let png = XCUIScreen.main.screenshot().pngRepresentation
        try? png.write(to: URL(fileURLWithPath: "\(outDir)/\(name).png"))
        try? app.debugDescription.write(
            toFile: "\(outDir)/\(name).ax.txt",
            atomically: true, encoding: .utf8
        )
    }
}
