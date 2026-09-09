import XCTest

final class LifeClockUITests: XCTestCase {
    private var app: XCUIApplication!

    override func setUpWithError() throws {
        continueAfterFailure = false
    }

    /// Walks the new ~33-screen reveal-onboarding flow far enough to prove
    /// the coordinator is wired up, the dot-grid renders, the dial is
    /// reachable, and the paywall surfaces. Stops short of completing
    /// purchase (sandbox StoreKit is flaky in CI per pre-existing
    /// SubscriptionStoreTests).
    ///
    /// Replaces the legacy 7-step UITest that was driving `onboarding.value`
    /// → `onboarding.safety` → … (the old screen IDs no longer exist now
    /// that LifeClockApp routes the empty-profile branch to
    /// `OnboardingCoordinator`).
    func testOnboardingV2FlowReachesPaywall() throws {
        launchApp(scenario: "onboarding")

        // ColdOpen auto-advances in about 1.2 seconds. XCUITest is attached
        // after that transition on modern simulators, so the stable contract
        // is the first actionable welcome screen rather than a transient view.
        XCTAssertTrue(app.otherElements["onboarding.welcome"].waitForExistence(timeout: 8))

        // welcome -> meetYourClock -> reactiveSlider -> goalPick.
        // appPreviews / visibilityFraming / personalizeIntro removed
        // 2026-05-05; their funnel rows roll up via
        // OnboardingScreen.deprecatedScreens.
        XCTAssertTrue(app.otherElements["onboarding.welcome"].waitForExistence(timeout: 5))
        app.buttons["onboarding.continue"].tap()

        XCTAssertTrue(app.otherElements["onboarding.meetYourClock"].waitForExistence(timeout: 5))
        app.buttons["onboarding.continue"].tap()

        XCTAssertTrue(app.otherElements["onboarding.reactiveSlider"].waitForExistence(timeout: 5))
        app.buttons["onboarding.continue"].tap()

        // Goal pick — must select before continue is enabled
        XCTAssertTrue(app.otherElements["onboarding.goalPick"].waitForExistence(timeout: 5))
        app.buttons["onboarding.goal.justCurious"].tap()
        app.buttons["onboarding.continue"].tap()

        // The selected voice and sticking point now precede baseline data.
        XCTAssertTrue(app.otherElements["onboarding.tone"].waitForExistence(timeout: 5))
        app.buttons["onboarding.tone.coach"].tap()
        app.buttons["onboarding.continue"].tap()

        XCTAssertTrue(app.otherElements["onboarding.habitFailureMode"].waitForExistence(timeout: 5))
        app.buttons["onboarding.habitFailureMode.forget"].tap()
        app.buttons["onboarding.continue"].tap()

        // Baseline DOB
        XCTAssertTrue(app.otherElements["onboarding.baselineDOB"].waitForExistence(timeout: 5))
        app.buttons["onboarding.continue"].tap()

        // Baseline sex
        XCTAssertTrue(app.otherElements["onboarding.baselineSex"].waitForExistence(timeout: 5))
        app.buttons["onboarding.baselineSex.unspecified"].tap()
        app.buttons["onboarding.continue"].tap()

        // Body comp — skip path (toggle stays off)
        XCTAssertTrue(app.otherElements["onboarding.bodyComp"].waitForExistence(timeout: 5))
        app.buttons["onboarding.continue"].tap()

        // Smoking
        XCTAssertTrue(app.otherElements["onboarding.smoking"].waitForExistence(timeout: 5))
        app.buttons["onboarding.smoking.none"].tap()
        app.buttons["onboarding.continue"].tap()

        // Alcohol
        XCTAssertTrue(app.otherElements["onboarding.alcohol"].waitForExistence(timeout: 5))
        app.buttons["onboarding.alcohol.rare"].tap()
        app.buttons["onboarding.continue"].tap()

        // Strength + cardio + sleep + diet — accept defaults
        XCTAssertTrue(app.otherElements["onboarding.strength"].waitForExistence(timeout: 5))
        app.buttons["onboarding.continue"].tap()
        XCTAssertTrue(app.otherElements["onboarding.cardio"].waitForExistence(timeout: 5))
        app.buttons["onboarding.continue"].tap()
        XCTAssertTrue(app.otherElements["onboarding.sleep"].waitForExistence(timeout: 5))
        app.buttons["onboarding.continue"].tap()
        XCTAssertTrue(app.otherElements["onboarding.diet"].waitForExistence(timeout: 5))
        app.buttons["onboarding.diet.okay"].tap()
        app.buttons["onboarding.continue"].tap()

        // Sensitive consent — take the skip path so we don't have to
        // simulate every parental / stress / loneliness input.
        XCTAssertTrue(element("onboarding.sensitiveConsent").waitForExistence(timeout: 5))
        app.buttons["onboarding.skipSensitive"].tap()

        // Prior attempts
        XCTAssertTrue(app.otherElements["onboarding.priorAttempts"].waitForExistence(timeout: 5))
        app.buttons["onboarding.priorAttempts.firstTime"].tap()
        app.buttons["onboarding.continue"].tap()

        // User guess, then the reveal sequence.
        XCTAssertTrue(app.otherElements["onboarding.leverGuess"].waitForExistence(timeout: 5))
        app.buttons["onboarding.leverGuess.sleep"].tap()
        app.buttons["onboarding.continue"].tap()

        // Analyzing — fake-progress timer (~4.5s) advances automatically.
        XCTAssertTrue(element("onboarding.analyzing").waitForExistence(timeout: 5))

        XCTAssertTrue(
            app.otherElements["onboarding.whatWeDontDo"].waitForExistence(timeout: 8),
            "analyzing should auto-advance to the trust statement"
        )
        app.buttons["onboarding.continue"].tap()

        // Archetype reveal
        XCTAssertTrue(
            app.otherElements["onboarding.archetypeReveal"].waitForExistence(timeout: 8),
            "the trust statement should advance to archetype reveal"
        )
        app.buttons["onboarding.continue"].tap()

        // Healthspan reveal replaced the retired dot-grid screens.
        XCTAssertTrue(app.otherElements["onboarding.healthspanReveal"].waitForExistence(timeout: 5))
        app.buttons["onboarding.continue"].tap()

        // Engine reveal + dial — the heart of the feature.
        XCTAssertTrue(element("onboarding.engineRevealAndDial").waitForExistence(timeout: 5))
        XCTAssertTrue(
            element("onboarding.dialYears").exists,
            "the running healthspan years label must be present"
        )
        XCTAssertTrue(
            element("onboarding.dial.slider").exists,
            "the ±5yr dial slider must be reachable"
        )
        app.buttons["onboarding.dial.confirm"].tap()
        // Confirmation alert — Anchor commits the one-time adjustment.
        let anchorButton = app.alerts.firstMatch.buttons["Anchor"]
        XCTAssertTrue(anchorButton.waitForExistence(timeout: 5))
        anchorButton.tap()

        // Recovery preview
        XCTAssertTrue(app.otherElements["onboarding.recoveryPreview"].waitForExistence(timeout: 5))
        app.buttons["onboarding.continue"].tap()

        // HealthKit auth — exercise the explicit offline-safe skip path.
        XCTAssertTrue(app.otherElements["onboarding.healthKitAuth"].waitForExistence(timeout: 5))
        app.buttons["onboarding.healthKitAuth.skip"].tap()

        // Receipt confirms the inputs before the conversion surface.
        XCTAssertTrue(app.otherElements["onboarding.receipt"].waitForExistence(timeout: 5))
        app.buttons["onboarding.continue"].tap()

        // Paywall — proves the conversion moment is reachable. We don't
        // attempt to purchase (sandbox StoreKit is flaky); we just verify
        // the surface and dismiss.
        XCTAssertTrue(
            app.otherElements["onboarding.paywallPrimary"].waitForExistence(timeout: 10),
            "must reach the single-tier paywall"
        )
        XCTAssertTrue(
            app.buttons["paywall.tier.annual"].exists,
            "annual tier toggle should be present with equal-prominence pricing"
        )
        XCTAssertTrue(app.buttons["paywall.close"].exists)

        // PV-P1: the onboarding-terminal paywall (100% of new users)
        // must enumerate the 5 ProPerks concretely beneath the
        // personalized headline/body, sourced verbatim from
        // `ProPerks.perks` (the single source of truth in lockstep with
        // MONETIZATION.md § Pro Annual). Asserts the perks block is
        // addressable and every perk *title* is present in the paywall
        // AX tree. The verbatim element-for-element match against the
        // source list is unit-tested in ProPerksTests (a UITest target
        // cannot import the app's `ProPerks` enum). `paywall.perks`
        // combines its children, so the titles surface as either an
        // element label or staticText depending on Dynamic Type.
        let perksBlock = element("paywall.perks")
        XCTAssertTrue(
            perksBlock.waitForExistence(timeout: 5),
            "paywall.perks enumeration block must be addressable on the onboarding-terminal paywall"
        )
        // Verbatim with ProPerks.perks (kept in lockstep by ProPerksTests).
        let expectedPerkTitles = [
            "Full daily history",
            "Weekly drivers + next-best lever",
            "Correction power",
            "Custom Today's Plan",
            "Deeper trend breakdown",
        ]
        let perksLabel = perksBlock.label
        for title in expectedPerkTitles {
            let presentOnScreen =
                perksLabel.contains(title)
                || app.staticTexts.containing(
                    NSPredicate(format: "label CONTAINS %@", title)
                ).firstMatch.exists
            XCTAssertTrue(
                presentOnScreen,
                "perk title '\(title)' must be enumerated on the onboarding-terminal paywall"
            )
        }
    }

    /// Original paywall agent-driveability test from Phase 2.C — still
    /// relevant for re-engagement (`PaywallSheet` from Profile / History
    /// locked rows). The new onboarding `PaywallPrimaryView` uses
    /// different identifiers (`paywall.purchase`) but `paywall.close`
    /// works on both surfaces.
    func testPaywallCloseIsAgentDriveable() throws {
        app = XCUIApplication()
        app.launchEnvironment["LIFECLOCK_UI_TEST"] = "1"
        app.launchEnvironment["LIFECLOCK_UI_TEST_SCENARIO"] = "onboarded"
        app.launchEnvironment["LIFECLOCK_USE_MOCK_HEALTH"] = "1"
        app.launchEnvironment["LIFECLOCK_FORCE_PAYWALL"] = "1"
        app.launch()

        let close = app.buttons["paywall.close"]
        XCTAssertTrue(close.waitForExistence(timeout: 8),
                      "paywall.close must exist so agents can audit the paywall surface")
        close.tap()
        let stillVisible = close.waitForExistence(timeout: 2)
        XCTAssertFalse(stillVisible, "paywall should dismiss after tapping paywall.close")
    }

    /// Post-onboarding navigation regression — verifies the existing
    /// `onboarded` scenario lands in the supportive Today experience
    /// once a profile has been seeded. The Progress-tab navigation that
    /// used to sit at the end of this test was removed in the 2026-05-01
    /// IA refactor (the Progress tab is gone).
    func testDailyCheckInShowsSupportMomentOnToday() throws {
        launchApp(scenario: "onboarded")

        XCTAssertTrue(app.buttons["today.checkInCard"].waitForExistence(timeout: 5))
        app.buttons["today.checkInCard"].tap()

        XCTAssertTrue(app.buttons["checkIn.save"].waitForExistence(timeout: 5))
        // The visible label follows the person's selected tone and whether
        // they have logged today; the accessibility identifier is the stable
        // contract for this action.
        app.buttons["checkIn.save"].tap()

        XCTAssertTrue(app.staticTexts["Life Clock updated."].waitForExistence(timeout: 5))
    }

    /// Verifies the current IA: Today, History, Future, and Profile remain
    /// reachable while the retired Plan / Progress / Quests destinations do
    /// not return as top-level tabs.
    func testTabBarContainsCurrentFourDestinations() throws {
        launchApp(scenario: "onboarded")
        XCTAssertTrue(app.buttons["today.checkInCard"].waitForExistence(timeout: 5),
                      "Today screen should be the default tab")
        XCTAssertFalse(app.buttons["Plan"].exists, "Plan tab should not exist post-refactor")
        XCTAssertFalse(app.buttons["Progress"].exists, "Progress tab should not exist post-refactor")
        XCTAssertFalse(app.buttons["Quests"].exists, "Quests tab should not exist post-refactor")
        XCTAssertTrue(app.buttons["History"].exists, "History tab should be present")
        XCTAssertTrue(app.buttons["Future"].exists, "Future tab should be present")
        XCTAssertTrue(app.buttons["Profile"].exists, "Profile tab should be present")
    }

    func testDeniedHealthStateUsesHonestSparseCopyAcrossSurfaces() throws {
        launchApp(
            scenario: "onboarded",
            extraEnvironment: [
                "LIFECLOCK_HEALTH_AUTH": "denied",
                "LIFECLOCK_HEALTH_PROFILE": "empty",
            ]
        )

        XCTAssertTrue(element("today.headlineSparse").waitForExistence(timeout: 5))
        XCTAssertTrue(
            app.staticTexts.containing("We can't currently see your Apple Health data").firstMatch.waitForExistence(timeout: 3),
            "Today should say we can't see Apple Health instead of implying a 0-step day"
        )

        app.tabBars.buttons["History"].tap()
        XCTAssertTrue(element("history.emptyState").waitForExistence(timeout: 5))
        XCTAssertTrue(
            app.staticTexts.containing("No recent Apple Health signal").firstMatch.waitForExistence(timeout: 3)
        )

        app.tabBars.buttons["Profile"].tap()
        XCTAssertTrue(app.buttons["profile.health.retry"].waitForExistence(timeout: 5))
        XCTAssertTrue(
            app.staticTexts.containing("We can't currently see steps, sleep, exercise, or resting heart rate").firstMatch.waitForExistence(timeout: 3)
        )
    }

    func testReturningUserWithoutCurrentHealthAccessKeepsHistoryButNotTodayPrecision() throws {
        launchApp(
            scenario: "onboarded",
            extraEnvironment: [
                "LIFECLOCK_HEALTH_AUTH": "denied",
                "LIFECLOCK_SEED_STREAK": "5",
                "LIFECLOCK_SEED_LAST_LOG_DAYS_AGO": "1",
                "LIFECLOCK_SEED_SNAPSHOTS": "5",
            ]
        )

        XCTAssertTrue(element("today.headlineSparse").waitForExistence(timeout: 5))
        XCTAssertTrue(
            app.staticTexts.containing("Earlier history is still here").firstMatch.waitForExistence(timeout: 3),
            "returning user path should acknowledge saved history without claiming a fresh minute estimate"
        )

        // Relaunch directly into History. The DEBUG fixture keeps this check
        // deterministic even when Simulator reports transient invalid tab-bar
        // hit points after an app relaunch.
        launchApp(
            scenario: "onboarded",
            extraEnvironment: [
                "LIFECLOCK_HEALTH_AUTH": "denied",
                "LIFECLOCK_SEED_STREAK": "5",
                "LIFECLOCK_SEED_LAST_LOG_DAYS_AGO": "1",
                "LIFECLOCK_SEED_SNAPSHOTS": "5",
                "LIFECLOCK_INITIAL_TAB": "history",
            ]
        )
        XCTAssertTrue(element("history.screen").waitForExistence(timeout: 5))
        let pastDays = app.staticTexts["Past days"]
        for _ in 0..<4 where !pastDays.exists {
            app.swipeUp()
        }
        XCTAssertTrue(pastDays.waitForExistence(timeout: 5))
        XCTAssertFalse(app.otherElements["history.emptyState"].exists,
                       "seeded returning user should still have historical rows")
    }

    /// Verifies the IA refactor keeps the Today's Plan section reachable
    /// directly on Today (the Plan tab no longer exists). Toggling a plan
    /// action goes through `store.toggleQuestCompletion`, mutates
    /// `Quest.completedAt`, and the row's `.accessibilityValue` flips from
    /// "incomplete" to "complete". Asserting on the value (not just the
    /// button's continued existence) catches the case where the button
    /// renders but the toggle no-ops.
    func testPlanCompletionFromTodayUpdatesQuestState() throws {
        launchApp(scenario: "onboarded")

        let row = app.buttons["today.planAction.0"]
        XCTAssertTrue(row.waitForExistence(timeout: 5))
        XCTAssertEqual(row.value as? String, "incomplete",
                       "fresh quest row should start incomplete")
        row.tap()

        // The toggle goes through the @MainActor store + ModelContext
        // save, then SwiftUI re-renders the row. Poll for the a11y
        // value flip rather than asserting immediately.
        let flipped = NSPredicate(format: "value == %@", "complete")
        let exp = expectation(for: flipped, evaluatedWith: row, handler: nil)
        wait(for: [exp], timeout: 3)
    }

    /// Verifies the new mascot hero on Today: the wrapper carries
    /// `today.mascot` and exposes the formatted minutes delta as its
    /// VoiceOver value. Locks the agent-facing contract for downstream
    /// scripted verification of "did today's check-in move the clock?"
    func testTodayMascotExposesFormattedDeltaValue() throws {
        launchApp(scenario: "onboarded")

        let mascot = app.otherElements["today.mascot"]
        XCTAssertTrue(mascot.waitForExistence(timeout: 5),
                      "today.mascot should appear when an estimate exists and hideClock is off")

        // The seeded `onboarded` scenario produces a deterministic
        // estimate via `LifeClockLaunchConfiguration`. We can't pin the
        // exact minute count without coupling to the seeded numbers, but
        // we can assert the value is a `TimeDeltaFormatter`-shaped string
        // ("+N min" / "-N min" / "+Nh Mm" / "0 min").
        let value = (mascot.value as? String) ?? ""
        let pattern = #"^[+-]?\d+(\s?(min|h(\s\d+m)?))?$"#
        let regex = try NSRegularExpression(pattern: pattern)
        let range = NSRange(value.startIndex..., in: value)
        XCTAssertNotNil(regex.firstMatch(in: value, options: [], range: range),
                        "mascot value should match TimeDeltaFormatter shape, got: \(value)")
    }

    private func element(_ identifier: String) -> XCUIElement {
        app.descendants(matching: .any).matching(identifier: identifier).firstMatch
    }

    private func launchApp(scenario: String) {
        app = XCUIApplication()
        app.launchEnvironment["LIFECLOCK_UI_TEST"] = "1"
        app.launchEnvironment["LIFECLOCK_UI_TEST_SCENARIO"] = scenario
        app.launchEnvironment["LIFECLOCK_USE_MOCK_HEALTH"] = "1"
        app.launch()
    }

    private func launchApp(scenario: String, extraEnvironment: [String: String]) {
        app = XCUIApplication()
        app.launchEnvironment["LIFECLOCK_UI_TEST"] = "1"
        app.launchEnvironment["LIFECLOCK_UI_TEST_SCENARIO"] = scenario
        app.launchEnvironment["LIFECLOCK_USE_MOCK_HEALTH"] = "1"
        for (key, value) in extraEnvironment {
            app.launchEnvironment[key] = value
        }
        app.launch()
    }
}

private extension XCUIElementQuery {
    func containing(_ substring: String) -> XCUIElementQuery {
        matching(NSPredicate(format: "label CONTAINS %@", substring))
    }
}
