import XCTest
@testable import LifeClock

/// V1.7.0 — Future tab + History summary plan §Phase 2/4.
///
/// `LifeClockLaunchConfiguration` carries a growing matrix of env-var
/// fixture knobs (initialTab, JUMP_TO, slider seeds, paywall force,
/// telemetry capture). The `effective*` derived properties compose
/// these orthogonal knobs into a single resolved fixture state. Each
/// derivation is dirt-simple in isolation but has *combinatorial*
/// reachability — these tests pin the contract so a future JUMP_TO
/// addition doesn't silently change the resolved tab or paywall flow.
///
/// Covers the audit follow-up's `effectiveSliderOverrideSeeds`
/// (new 2026-05-11 — JUMP_TO cap/floor lands with slider thumbs at
/// extremes that justify the headline clamp).
final class LifeClockLaunchConfigurationTests: XCTestCase {

    // MARK: - Test-only factory

    /// Mirrors the RELEASE-branch defaults from `LifeClockLaunchConfiguration.current`.
    /// Caller overrides only the field(s) under test.
    private func config(
        scenario: LifeClockLaunchConfiguration.Scenario = .onboarding,
        forcePaywall: Bool = false,
        initialTab: AppTab = .today,
        futureJumpTo: LifeClockLaunchConfiguration.FutureJumpTo? = nil,
        seedDaysSinceInstall: Int? = nil
    ) -> LifeClockLaunchConfiguration {
        LifeClockLaunchConfiguration(
            isUITest: false,
            scenario: scenario,
            useMockHealth: false,
            healthAuth: .notDetermined,
            forcePaywall: forcePaywall,
            seedStreak: 0,
            seedQuestsCompleted: 0,
            clock: .live,
            forceColorScheme: nil,
            forcePalette: nil,
            seedTone: nil,
            healthProfile: .baseline,
            seedBadDayToday: false,
            seedLastLogDaysAgo: 0,
            initialTab: initialTab,
            forceSafetyNet: false,
            forceQuickLog: false,
            futureTabUnlocked: true,
            futureJumpTo: futureJumpTo,
            seedDaysSinceInstall: seedDaysSinceInstall,
            seedBaselineAdjustment: nil,
            seedSliderOverridesJSON: nil,
            seedSnapshots: nil,
            telemetryCapturePath: nil
        )
    }

    // MARK: - effectiveInitialTab

    func testJumpToFutureFamilyImpliesFutureTab() {
        for jumpTo: LifeClockLaunchConfiguration.FutureJumpTo in [
            .futureDay0, .futureColdLaunch, .futureWarmingUp,
            .futureFull, .futureCapReached, .futureFloorReached
        ] {
            let c = config(initialTab: .today, futureJumpTo: jumpTo)
            XCTAssertEqual(c.effectiveInitialTab, .future,
                           "JUMP_TO=\(jumpTo) must imply the Future tab")
        }
    }

    func testInitialTabExplicitWinsWhenNoJumpTo() {
        let c = config(initialTab: .profile, futureJumpTo: nil)
        XCTAssertEqual(c.effectiveInitialTab, .profile,
                       "no JUMP_TO ⇒ explicit initialTab passes through")
    }

    func testPaywallJumpToDoesNotImplyFutureTab() {
        // paywallWhatIfSection should auto-present the paywall but not
        // change which tab renders behind it.
        let c = config(initialTab: .profile, futureJumpTo: .paywallWhatIfSection)
        XCTAssertEqual(c.effectiveInitialTab, .profile)
    }

    // MARK: - effectiveSeedDaysSinceInstall

    func testJumpToFutureDay0PresetsZeroDays() {
        XCTAssertEqual(config(futureJumpTo: .futureDay0).effectiveSeedDaysSinceInstall, 0)
    }

    func testJumpToFutureFullPresetsThirtyDays() {
        XCTAssertEqual(config(futureJumpTo: .futureFull).effectiveSeedDaysSinceInstall, 30)
        XCTAssertEqual(config(futureJumpTo: .futureCapReached).effectiveSeedDaysSinceInstall, 30,
                       "cap/floor variants must also seed full14plus")
        XCTAssertEqual(config(futureJumpTo: .futureFloorReached).effectiveSeedDaysSinceInstall, 30)
    }

    func testExplicitSeedOverridesJumpToPreset() {
        let c = config(futureJumpTo: .futureFull, seedDaysSinceInstall: 5)
        XCTAssertEqual(c.effectiveSeedDaysSinceInstall, 5,
                       "explicit env var must win over JUMP_TO default")
    }

    // MARK: - effectiveForcePaywall + scroll target

    func testForcePaywallTrueWhenLegacyEnvSet() {
        let c = config(forcePaywall: true)
        XCTAssertTrue(c.effectiveForcePaywall)
        XCTAssertNil(c.effectivePaywallScrollTarget)
    }

    func testForcePaywallTrueAndScrollsWhenJumpToPaywallSection() {
        let c = config(futureJumpTo: .paywallWhatIfSection)
        XCTAssertTrue(c.effectiveForcePaywall)
        XCTAssertEqual(c.effectivePaywallScrollTarget, .whatIfSimulator)
    }

    // MARK: - effectiveForcedClampState

    func testForcedClampStateNilForNonClampJumpTos() {
        XCTAssertNil(config(futureJumpTo: nil).effectiveForcedClampState)
        XCTAssertNil(config(futureJumpTo: .futureFull).effectiveForcedClampState)
        XCTAssertNil(config(futureJumpTo: .futureDay0).effectiveForcedClampState)
    }

    func testForcedClampStateCapAndFloor() {
        if case .cappedAt = config(futureJumpTo: .futureCapReached).effectiveForcedClampState {
            // expected
        } else {
            XCTFail("futureCapReached must yield .cappedAt")
        }
        if case .flooredAt = config(futureJumpTo: .futureFloorReached).effectiveForcedClampState {
            // expected
        } else {
            XCTFail("futureFloorReached must yield .flooredAt")
        }
    }

    // MARK: - effectiveSliderOverrideSeeds (audit follow-up)

    func testSliderOverrideSeedsNilForNonClampJumpTos() {
        XCTAssertNil(config(futureJumpTo: nil).effectiveSliderOverrideSeeds)
        XCTAssertNil(config(futureJumpTo: .futureFull).effectiveSliderOverrideSeeds)
    }

    func testSliderOverrideSeedsForCapPositionThumbsAtMaxBenefit() {
        guard let seeds = config(futureJumpTo: .futureCapReached).effectiveSliderOverrideSeeds else {
            return XCTFail("expected non-nil seeds for futureCapReached")
        }
        XCTAssertEqual(seeds[.sleep], 7.5,
                       "sleep thumb must land at the U-curve optimum")
        XCTAssertEqual(seeds[.steps], 12_000,
                       "steps must exceed the 10k plateau")
        XCTAssertEqual(seeds[.exerciseMinutes], 400,
                       "exercise must exceed the 300 min/wk saturation")
        XCTAssertEqual(seeds[.nicotine], 0,
                       "nicotine must be zero so smoking dominance does not apply")
        XCTAssertEqual(seeds[.extras], 0)
    }

    func testSliderOverrideSeedsForFloorPositionThumbsAtMaxDrag() {
        guard let seeds = config(futureJumpTo: .futureFloorReached).effectiveSliderOverrideSeeds else {
            return XCTFail("expected non-nil seeds for futureFloorReached")
        }
        XCTAssertEqual(seeds[.nicotine], 7,
                       "nicotine > 0 is required to dominate the projection toward the floor")
        XCTAssertEqual(seeds[.extras], 7,
                       "extras saturated at the maximum-drag frequency")
        XCTAssertEqual(seeds[.steps], 1_000,
                       "steps below the 4k drag threshold")
    }
}
