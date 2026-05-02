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

        // Phase 3.5 lead-ins
        XCTAssertTrue(
            app.otherElements["onboarding.coldOpen"].waitForExistence(timeout: 8),
            "first screen of the new flow"
        )
        // ColdOpen auto-advances or accepts a tap; tap to skip the 2s timer.
        app.otherElements["onboarding.coldOpen"].tap()

        XCTAssertTrue(app.otherElements["onboarding.appPreviews"].waitForExistence(timeout: 5))
        app.buttons["onboarding.continue"].tap()

        XCTAssertTrue(app.otherElements["onboarding.welcome"].waitForExistence(timeout: 5))
        app.buttons["onboarding.continue"].tap()

        XCTAssertTrue(app.otherElements["onboarding.meetYourClock"].waitForExistence(timeout: 5))
        app.buttons["onboarding.continue"].tap()

        XCTAssertTrue(app.otherElements["onboarding.reactiveSlider"].waitForExistence(timeout: 5))
        app.buttons["onboarding.continue"].tap()

        // Phase 4 personalize intro
        XCTAssertTrue(app.otherElements["onboarding.visibilityFraming"].waitForExistence(timeout: 5))
        app.buttons["onboarding.continue"].tap()

        XCTAssertTrue(app.otherElements["onboarding.personalizeIntro"].waitForExistence(timeout: 5))
        app.buttons["onboarding.continue"].tap()

        // Goal pick — must select before continue is enabled
        XCTAssertTrue(app.otherElements["onboarding.goalPick"].waitForExistence(timeout: 5))
        app.buttons["onboarding.goal.justCurious"].tap()
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
        XCTAssertTrue(app.otherElements["onboarding.sensitiveConsent"].waitForExistence(timeout: 5))
        app.buttons["onboarding.skipSensitive"].tap()

        // Tone
        XCTAssertTrue(app.otherElements["onboarding.tone"].waitForExistence(timeout: 5))
        app.buttons["onboarding.tone.coach"].tap()
        app.buttons["onboarding.continue"].tap()

        // Prior attempts
        XCTAssertTrue(app.otherElements["onboarding.priorAttempts"].waitForExistence(timeout: 5))
        app.buttons["onboarding.priorAttempts.firstTime"].tap()
        app.buttons["onboarding.continue"].tap()

        // Analyzing — fake-progress timer (~4.5s) advances automatically.
        XCTAssertTrue(app.otherElements["onboarding.analyzing"].waitForExistence(timeout: 5))

        // Archetype reveal
        XCTAssertTrue(
            app.otherElements["onboarding.archetypeReveal"].waitForExistence(timeout: 8),
            "analyzing should auto-advance to archetype reveal"
        )
        app.buttons["onboarding.continue"].tap()

        // .justCurious goal SKIPS bigNumberPenalty per coordinator's
        // shouldShowPenaltyScreen() — flow goes
        // concreteThisYear → lifeGridFull → lifeGridRemaining →
        // engineRevealAndDial directly.
        XCTAssertTrue(app.otherElements["onboarding.concreteThisYear"].waitForExistence(timeout: 5))
        app.buttons["onboarding.continue"].tap()
        XCTAssertTrue(app.otherElements["onboarding.lifeGridFull"].waitForExistence(timeout: 5))
        app.buttons["onboarding.continue"].tap()
        XCTAssertTrue(app.otherElements["onboarding.lifeGridRemaining"].waitForExistence(timeout: 5))
        app.buttons["onboarding.continue"].tap()

        // Engine reveal + dial — the heart of the feature.
        XCTAssertTrue(app.otherElements["onboarding.engineRevealAndDial"].waitForExistence(timeout: 5))
        XCTAssertTrue(
            app.otherElements["onboarding.dialYears"].exists,
            "the running healthspan years label must be present"
        )
        XCTAssertTrue(
            app.otherElements["onboarding.dial.slider"].exists,
            "the ±5yr dial slider must be reachable"
        )
        app.buttons["onboarding.dial.confirm"].tap()
        // Confirmation alert — Lock to commit.
        let lockButton = app.alerts.firstMatch.buttons["Lock"]
        XCTAssertTrue(lockButton.waitForExistence(timeout: 5))
        lockButton.tap()

        // Recovery preview
        XCTAssertTrue(app.otherElements["onboarding.recoveryPreview"].waitForExistence(timeout: 5))
        app.buttons["onboarding.continue"].tap()

        // HealthKit auth — first tap fires the request, second tap advances.
        XCTAssertTrue(app.otherElements["onboarding.healthKitAuth"].waitForExistence(timeout: 5))
        app.buttons["onboarding.continue"].tap()
        // System dialog handling is environment-specific; in CI we just
        // verify we eventually reach the paywall.

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
        XCTAssertTrue(app.buttons["Update Life Clock"].exists)
        app.buttons["checkIn.save"].tap()

        XCTAssertTrue(app.staticTexts["Life Clock updated."].waitForExistence(timeout: 5))
    }

    /// Verifies the 2026-05-01 IA refactor: tab bar is exactly Today,
    /// History, Profile. Plan / Progress / Quests are gone; their content
    /// lives inside Today (and History). Regression guard against
    /// accidentally re-adding a tab.
    func testTabBarHasOnlyThreeTabs() throws {
        launchApp(scenario: "onboarded")
        XCTAssertTrue(app.buttons["today.checkInCard"].waitForExistence(timeout: 5),
                      "Today screen should be the default tab")
        XCTAssertFalse(app.buttons["Plan"].exists, "Plan tab should not exist post-refactor")
        XCTAssertFalse(app.buttons["Progress"].exists, "Progress tab should not exist post-refactor")
        XCTAssertFalse(app.buttons["Quests"].exists, "Quests tab should not exist post-refactor")
        XCTAssertTrue(app.buttons["History"].exists, "History tab should be present")
        XCTAssertTrue(app.buttons["Profile"].exists, "Profile tab should be present")
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

    private func launchApp(scenario: String) {
        app = XCUIApplication()
        app.launchEnvironment["LIFECLOCK_UI_TEST"] = "1"
        app.launchEnvironment["LIFECLOCK_UI_TEST_SCENARIO"] = scenario
        app.launchEnvironment["LIFECLOCK_USE_MOCK_HEALTH"] = "1"
        app.launch()
    }
}

private extension XCUIElementQuery {
    func containing(_ substring: String) -> XCUIElementQuery {
        matching(NSPredicate(format: "label CONTAINS %@", substring))
    }
}
