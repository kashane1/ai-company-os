import Foundation
import SwiftData

/// Centralizes launch-time overrides used by UI tests and simulator audits.
///
/// Two layers of fixture knobs:
///
/// 1. The legacy `Scenario` enum (`onboarding` / `onboarded`) controls
///    high-level onboarding state. Existing XCUITests use it.
///
/// 2. Orthogonal env-var probes (`forcePaywall`, `healthAuth`, `seedStreak`,
///    `seedQuestsCompleted`, `fixedDate`) compose freely so an agent or
///    auditor can land on any reachable UI state deterministically without
///    growing a combinatorial Scenario enum.
///
/// All env-var parsing is wrapped in `#if DEBUG`. Release builds always
/// return production defaults regardless of `ProcessInfo.environment`,
/// removing the fixture surface from the App Store binary entirely.
struct LifeClockLaunchConfiguration {
    enum Scenario: String {
        case onboarding
        case onboarded
    }

    /// Health authorization fixture state for the mock service.
    ///
    /// `authorized`: mock returns full snapshots; `authorizationKnown == true`.
    /// `denied`:     mock returns nil snapshots (no data); `authorizationKnown == true`.
    /// `notDetermined`: mock returns full snapshots; `authorizationKnown == false`
    ///                  until `requestAuthorization()` is called.
    enum HealthAuth: String {
        case authorized
        case denied
        case notDetermined
    }

    /// Test-only color-scheme override. When set, the root view binds
    /// `.preferredColorScheme(_:)` so polish/audit recon runs can capture
    /// each top-level screen in light AND dark without driving Settings.
    enum ColorScheme: String {
        case light
        case dark
    }

    /// `LIFECLOCK_JUMP_TO=<state>` fixture knob for the Future tab and
    /// related surfaces. Lets an XCUITest or recon driver land on a
    /// specific state without driving the full clock + onboarding chain.
    /// V1.7.0 (Future tab plan §Phase 2/4) — agent-native parity: any
    /// state the user can reach must also be reachable by fixture.
    enum FutureJumpTo: String {
        case futureDay0
        case futureColdLaunch
        case futureWarmingUp
        case futureFull
        case futureCapReached
        case futureFloorReached
        case paywallWhatIfSection
        case reinstallRecovery   // deferred to v1.1 implementation; reserved
        case rebaselineRitual    // deferred to v1.1 implementation; reserved
    }

    let isUITest: Bool
    let scenario: Scenario
    let useMockHealth: Bool
    let healthAuth: HealthAuth
    let forcePaywall: Bool
    let seedStreak: Int
    let seedQuestsCompleted: Int
    let clock: EngineClock
    let forceColorScheme: ColorScheme?
    /// `LIFECLOCK_FORCE_PALETTE=default-navy|aurora-cool|sunset-warm` overrides
    /// the active palette, applied as the final word so it sticks regardless
    /// of profile presence. Mirrors `forceColorScheme` for the
    /// 3-palette × 2-scheme × 2-size onboarding-terminals matrix.
    let forcePalette: LifeClockPalette?
    /// `LIFECLOCK_SEED_TONE=gentle|coach|firm_direct` overrides the seeded
    /// `UserProfile.toneMode` when scenario is `.onboarded`. Lets simulator
    /// audits screenshot each tone deterministically without driving Profile
    /// to flip the picker.
    let seedTone: ToneMode?
    /// `LIFECLOCK_HEALTH_PROFILE=baseline|poor|empty` shapes the mock
    /// service's daily snapshot. `poor` powers the bad-day polish recon;
    /// `empty` simulates a fully-authorized app with no useful Apple Health
    /// signal yet — see `MockHealthKitService.HealthProfile`.
    let healthProfile: MockHealthKitService.HealthProfile
    /// `LIFECLOCK_SEED_BAD_DAY=1` overrides today's seeded HabitLog with
    /// the all-bad combination (rough diet, heavy alcohol, smoking,
    /// skip/binge rhythm, no whole-food anchor, high stress, no strength).
    /// Composed with `LIFECLOCK_HEALTH_PROFILE=poor` it lands the user on
    /// a ≈ −90 minute Today screen for the three-tone vision audit.
    let seedBadDayToday: Bool
    /// `LIFECLOCK_SEED_LAST_LOG_DAYS_AGO=N` shifts the most recent seeded
    /// HabitLog + DailyHealthSnapshot N days into the past. Default 0
    /// (snapshots include today). Composes with `seedStreak`: with
    /// `seedStreak=5` and this set to 35, snapshots land at days
    /// −35…−39 from `now`, simulating a returning user after a long
    /// absence. Used by the long-absence-card polish recon.
    let seedLastLogDaysAgo: Int
    /// `LIFECLOCK_INITIAL_TAB=profile|history|today` lets a recon driver
    /// land directly on a non-Today tab without writing an XCUITest. Used
    /// by simulator-driven-polish runs that target Profile or History.
    let initialTab: AppTab
    /// `LIFECLOCK_FORCE_SAFETY_NET=1` auto-presents the SafetyNet sheet
    /// on Profile mount. Same pattern as `forcePaywall` — lets polish
    /// recon land directly on SafetyNet across the tone × scheme grid
    /// without depending on a cliclick tap into the List entry (iOS 26
    /// Simulator does not always deliver cliclick `c:` events to SwiftUI
    /// List buttons; observed during the 2026-05-11 SafetyNet drift
    /// audit). DEBUG-only.
    let forceSafetyNet: Bool
    /// `LIFECLOCK_FORCE_QUICK_LOG=1` auto-presents the Daily Check-In
    /// (`QuickLogSheet`) on Today mount. Same pattern as `forceSafetyNet`
    /// — lets polish recon capture the 3-tone × scheme × XXL grid without
    /// driving a cliclick tap on the Today toolbar. The toolbar Button
    /// itself is reachable via cliclick (verified during 2026-05-11
    /// SafetyNet polish: tab bar + standalone Buttons receive taps fine;
    /// only Buttons inside `Form`/`List` rows fail), but the forced-sheet
    /// pattern is deterministic and shaves iterations on the screenshot
    /// grid. DEBUG-only.
    let forceQuickLog: Bool

    // MARK: - V1.7.0 Future tab fixture knobs (2026-05-11)
    //
    // Plan §Phase 2/4 agent-native parity: a recon driver or XCUITest
    // must be able to land directly on every Future-tab state without
    // gestural drives. Knobs compose orthogonally with existing
    // `seedTone`, `forceColorScheme`, `forcePalette`, `clock` (FIXED_DATE).

    /// `LIFECLOCK_FUTURE_TAB_UNLOCKED=1|0` overrides the default release
    /// gate. DEBUG default `true` (tab visible); RELEASE default `false`
    /// until Phase 4 flips the default at code level. Phase 2 + Phase 3
    /// ship with the tab hidden in RELEASE.
    let futureTabUnlocked: Bool

    /// `LIFECLOCK_JUMP_TO=<FutureJumpTo>` lands the simulator on a
    /// named Future-tab state. Combined with `initialTab=future`,
    /// guarantees a deterministic first frame.
    let futureJumpTo: FutureJumpTo?

    /// `LIFECLOCK_SEED_DAYS_SINCE_INSTALL=N` shifts `onboardingCompletedAt`
    /// N days into the past relative to `clock.now()`. Lets a recon
    /// driver land on History summary day-1 / day-7+ states and on
    /// Future-tab day-state thresholds (1–3 / 4–13 / 14+).
    /// Composes with `seedStreak` — the streak is independent of the
    /// install anchor.
    let seedDaysSinceInstall: Int?

    /// `LIFECLOCK_SEED_BASELINE_ADJUSTMENT=<float>` seeds the V1.7.0
    /// anchor-dial state on an `onboarded` scenario by writing
    /// `personalAdjustmentYears` and `anchorAdjustedAt`. The store's
    /// `bootstrapV170Baseline()` then computes `baselineHealthspanYears`
    /// on first launch, unlocking surfaces gated on a captured baseline
    /// (Today trajectory peek, Future projections). Without this knob
    /// the `onboarded` scenario simulates a user who completed onboarding
    /// but has not yet anchored — useful for testing the pre-baseline
    /// edge case but not for Today-peek polish walks. Opt-in: nil leaves
    /// the anchor fields unset.
    let seedBaselineAdjustment: Double?

    /// `LIFECLOCK_SEED_SLIDER_OVERRIDES=<json>` provides deterministic
    /// `HealthspanEngine.projectWith(overrides:)` inputs so a test
    /// can render the cap/floor/near-cap states without gestural
    /// scrubbing. JSON shape: `{"sleep":7.5,"steps":12000,...}`.
    /// Parsed lazily by FutureView/WhatIfSlider; this property just
    /// carries the raw string.
    let seedSliderOverridesJSON: String?

    /// `LIFECLOCK_TELEMETRY_CAPTURE_PATH=/tmp/...json` enables an
    /// in-memory event ring buffer that's flushed to disk on app
    /// background. UITests assert event emission against the file
    /// contents. nil disables capture entirely (default).
    let telemetryCapturePath: String?

    // MARK: - JUMP_TO derived values

    /// Effective initial tab — `LIFECLOCK_JUMP_TO=future*|paywallWhatIfSection`
    /// implicitly selects the Future tab. Explicit `LIFECLOCK_INITIAL_TAB`
    /// still wins when JUMP_TO is unset.
    var effectiveInitialTab: AppTab {
        switch futureJumpTo {
        case .futureDay0, .futureColdLaunch, .futureWarmingUp, .futureFull,
             .futureCapReached, .futureFloorReached:
            return .future
        case .paywallWhatIfSection, .reinstallRecovery, .rebaselineRitual, .none:
            return initialTab
        }
    }

    /// Effective `seedDaysSinceInstall` — JUMP_TO=future* presets
    /// derived values when the explicit env var isn't set.
    /// futureDay0=0 / futureColdLaunch=2 / futureWarmingUp=8 /
    /// futureFull=30 (also used by cap/floor variants).
    var effectiveSeedDaysSinceInstall: Int? {
        if let explicit = seedDaysSinceInstall { return explicit }
        switch futureJumpTo {
        case .futureDay0: return 0
        case .futureColdLaunch: return 2
        case .futureWarmingUp: return 8
        case .futureFull, .futureCapReached, .futureFloorReached: return 30
        case .paywallWhatIfSection, .reinstallRecovery, .rebaselineRitual, .none: return nil
        }
    }

    /// Whether the paywall should auto-present on launch. JUMP_TO=
    /// `paywallWhatIfSection` triggers this (in addition to the
    /// legacy `LIFECLOCK_FORCE_PAYWALL=1` env var).
    var effectiveForcePaywall: Bool {
        forcePaywall || futureJumpTo == .paywallWhatIfSection
    }

    /// Scroll target for the auto-presented paywall, when applicable.
    /// `paywallWhatIfSection` → `.whatIfSimulator`; otherwise nil
    /// (lands at top).
    var effectivePaywallScrollTarget: PaywallSheet.Section? {
        switch futureJumpTo {
        case .paywallWhatIfSection: return .whatIfSimulator
        default: return nil
        }
    }

    /// Fixture-only forced projection clamp state. JUMP_TO=
    /// `futureCapReached` / `futureFloorReached` substitutes the
    /// engine's math so agents can land on the cap/floor UI without
    /// re-tuning the coefficients to actually reach the boundary.
    /// (Realistic v1 coefficients top out at baseline + ~9y, well
    /// under the +14y cap; this knob lets us snapshot the clamp UI
    /// regardless.) Returns nil for non-clamp JUMP_TO values.
    var effectiveForcedClampState: HealthspanEngine.Projection.ClampState? {
        switch futureJumpTo {
        case .futureCapReached: return .cappedAt(0)   // baseline filled in at consume site
        case .futureFloorReached: return .flooredAt(0)
        default: return nil
        }
    }

    /// Fixture-only slider seed positions. JUMP_TO=
    /// `futureCapReached` / `futureFloorReached` pre-positions the
    /// `WhatIfSlider` thumbs at the extreme that "justifies" the
    /// forced headline clamp — otherwise a recon screenshot captures a
    /// contradictory state ("cap reached" headline + default thumbs).
    /// Realistic v1 coefficients won't actually land on the engine's
    /// cap/floor from these values; the headline's `effectiveForcedClampState`
    /// shortcut substitutes the exact boundary value. Returns nil when
    /// no fixture is active.
    var effectiveSliderOverrideSeeds: [HealthspanEngine.Dimension: Double]? {
        switch futureJumpTo {
        case .futureCapReached:
            return [
                .sleep: 7.5,
                .dietQuality: 7,
                .steps: 12_000,
                .exerciseMinutes: 400,
                .extras: 0,
                .nicotine: 0,
            ]
        case .futureFloorReached:
            return [
                .sleep: 4,
                .dietQuality: 0,
                .steps: 1_000,
                .exerciseMinutes: 0,
                .extras: 7,
                .nicotine: 7,
            ]
        default:
            return nil
        }
    }

    static var current: LifeClockLaunchConfiguration {
        #if DEBUG
        let env = ProcessInfo.processInfo.environment
        let isUITest = env["LIFECLOCK_UI_TEST"] == "1"
        let scenario = Scenario(rawValue: env["LIFECLOCK_UI_TEST_SCENARIO"] ?? "") ?? .onboarding
        let useMockHealth = env["LIFECLOCK_USE_MOCK_HEALTH"] == "1" || isUITest

        // Health auth: legacy LIFECLOCK_UI_TEST_AUTHORIZED=1 maps to .authorized
        // for back-compat; new LIFECLOCK_HEALTH_AUTH=denied|authorized|notDetermined
        // takes precedence when present.
        let healthAuth: HealthAuth = {
            if let raw = env["LIFECLOCK_HEALTH_AUTH"], let parsed = HealthAuth(rawValue: raw) {
                return parsed
            }
            if env["LIFECLOCK_UI_TEST_AUTHORIZED"] == "1" { return .authorized }
            return .notDetermined
        }()

        let forcePaywall = env["LIFECLOCK_FORCE_PAYWALL"] == "1"
        let forceColorScheme = ColorScheme(rawValue: env["LIFECLOCK_FORCE_COLOR_SCHEME"] ?? "")
        let forcePalette = LifeClockPalette(rawValue: env["LIFECLOCK_FORCE_PALETTE"] ?? "")
        let seedStreak = max(0, Int(env["LIFECLOCK_SEED_STREAK"] ?? "") ?? 0)
        let seedQuestsCompleted = max(0, Int(env["LIFECLOCK_SEED_QUESTS_COMPLETED"] ?? "") ?? 0)
        let seedTone = ToneMode(rawValue: env["LIFECLOCK_SEED_TONE"] ?? "")
        let healthProfile = MockHealthKitService.HealthProfile(
            rawValue: env["LIFECLOCK_HEALTH_PROFILE"] ?? ""
        ) ?? .baseline
        let seedBadDayToday = env["LIFECLOCK_SEED_BAD_DAY"] == "1"
        let seedLastLogDaysAgo = max(0, Int(env["LIFECLOCK_SEED_LAST_LOG_DAYS_AGO"] ?? "") ?? 0)
        let initialTab = AppTab(rawValue: env["LIFECLOCK_INITIAL_TAB"] ?? "") ?? .today
        let forceSafetyNet = env["LIFECLOCK_FORCE_SAFETY_NET"] == "1"
        let forceQuickLog = env["LIFECLOCK_FORCE_QUICK_LOG"] == "1"
        // V1.7.0 Future tab knobs. DEBUG default `true` so simulator
        // recon can hit the tab without setting an env var. RELEASE
        // default `false` lives in the #else branch below.
        let futureTabUnlocked: Bool = {
            if let raw = env["LIFECLOCK_FUTURE_TAB_UNLOCKED"] {
                return raw == "1"
            }
            return true
        }()
        let futureJumpTo = FutureJumpTo(rawValue: env["LIFECLOCK_JUMP_TO"] ?? "")
        let seedDaysSinceInstall: Int? = {
            guard let raw = env["LIFECLOCK_SEED_DAYS_SINCE_INSTALL"] else { return nil }
            return Int(raw).map { max(0, $0) }
        }()
        let seedBaselineAdjustment: Double? = {
            guard let raw = env["LIFECLOCK_SEED_BASELINE_ADJUSTMENT"] else { return nil }
            return Double(raw)
        }()
        let seedSliderOverridesJSON = env["LIFECLOCK_SEED_SLIDER_OVERRIDES"]
        let telemetryCapturePath = env["LIFECLOCK_TELEMETRY_CAPTURE_PATH"]

        let clock: EngineClock = {
            if let iso = env["LIFECLOCK_FIXED_DATE"],
               let parsed = ISO8601DateFormatter.lifeClockISO.date(from: iso) {
                return .fixed(parsed)
            }
            if isUITest {
                return .fixed(Date(timeIntervalSince1970: 1_800_000_000))
            }
            return .live
        }()

        return LifeClockLaunchConfiguration(
            isUITest: isUITest,
            scenario: scenario,
            useMockHealth: useMockHealth,
            healthAuth: healthAuth,
            forcePaywall: forcePaywall,
            seedStreak: seedStreak,
            seedQuestsCompleted: seedQuestsCompleted,
            clock: clock,
            forceColorScheme: forceColorScheme,
            forcePalette: forcePalette,
            seedTone: seedTone,
            healthProfile: healthProfile,
            seedBadDayToday: seedBadDayToday,
            seedLastLogDaysAgo: seedLastLogDaysAgo,
            initialTab: initialTab,
            forceSafetyNet: forceSafetyNet,
            forceQuickLog: forceQuickLog,
            futureTabUnlocked: futureTabUnlocked,
            futureJumpTo: futureJumpTo,
            seedDaysSinceInstall: seedDaysSinceInstall,
            seedBaselineAdjustment: seedBaselineAdjustment,
            seedSliderOverridesJSON: seedSliderOverridesJSON,
            telemetryCapturePath: telemetryCapturePath
        )
        #else
        // RELEASE: V1.7.0 Phase 4 flips futureTabUnlocked to `true`.
        // The tab still hides when profile.onboardingCompletedAt == nil,
        // so fresh installs never see it before onboarding completes.
        return LifeClockLaunchConfiguration(
            isUITest: false,
            scenario: .onboarding,
            useMockHealth: false,
            healthAuth: .notDetermined,
            forcePaywall: false,
            seedStreak: 0,
            seedQuestsCompleted: 0,
            clock: .live,
            forceColorScheme: nil,
            forcePalette: nil,
            seedTone: nil,
            healthProfile: .baseline,
            seedBadDayToday: false,
            seedLastLogDaysAgo: 0,
            initialTab: .today,
            forceSafetyNet: false,
            forceQuickLog: false,
            futureTabUnlocked: true,
            futureJumpTo: nil,
            seedDaysSinceInstall: nil,
            seedBaselineAdjustment: nil,
            seedSliderOverridesJSON: nil,
            telemetryCapturePath: nil
        )
        #endif
    }

    var useInMemoryStore: Bool { isUITest }

    @MainActor
    func makeHealthService() -> HealthKitServiceProtocol {
        guard useMockHealth else { return HealthKitConfiguration.service() }
        switch healthAuth {
        case .authorized:
            return MockHealthKitService(preAuthorized: true, healthProfile: healthProfile)
        case .denied:
            // Simulates denial: marked as "asked" so the UI doesn't keep prompting,
            // but returns no data. Matches the protocol stance that authorizationKnown
            // never claims to know whether grant succeeded — empty snapshots are the signal.
            return MockHealthKitService(simulateNoData: true, preAuthorized: true)
        case .notDetermined:
            return MockHealthKitService(preAuthorized: false, healthProfile: healthProfile)
        }
    }

    func seedInitialStateIfNeeded(in context: ModelContext) {
        // V1.7.0: LIFECLOCK_JUMP_TO=future* implies the user must
        // already be onboarded (Future tab requires baseline). Seed
        // when EITHER an explicit onboarded scenario OR a JUMP_TO
        // that needs onboarded state is set.
        let needsOnboardedSeed = scenario == .onboarded
            || futureJumpTo != nil
            || effectiveSeedDaysSinceInstall != nil
        guard needsOnboardedSeed else { return }
        let descriptor = FetchDescriptor<UserProfile>()
        if let existing = try? context.fetch(descriptor), !existing.isEmpty { return }

        let now = clock.now()
        let calendar = clock.calendar
        // Back-date onboarding by `seedStreak + seedLastLogDaysAgo` days when
        // seeding a returning user. The wrap-up reinstall guard
        // (`today >= onboardedAt + 2`) and weekly recency window both need
        // real elapsed days; without this the wrap-up flow is unreachable
        // from a fresh seed. Min 2 days when streak ≥ 2 so any
        // returning-user fixture is past the guard. With
        // `seedLastLogDaysAgo` set, the user must have onboarded BEFORE the
        // earliest seeded snapshot — otherwise the longAbsenceCard's
        // `hasOlderSnapshots` predicate stays unreachable.
        //
        // V1.7.0: `LIFECLOCK_SEED_DAYS_SINCE_INSTALL=N` takes precedence
        // when set — used by the Future tab + History summary day-state
        // tests to land on Day 0 / Day 1–6 / Day 7+ / Day 14+ without
        // also seeding a streak.
        let onboardedAt: Date = {
            if let daysSince = effectiveSeedDaysSinceInstall {
                return calendar.date(byAdding: .day, value: -daysSince, to: now) ?? now
            }
            guard seedStreak > 0 else { return now }
            let daysBack = max(2, seedStreak + seedLastLogDaysAgo)
            return calendar.date(byAdding: .day, value: -daysBack, to: now) ?? now
        }()
        let profile = UserProfile(
            birthDate: Date(timeIntervalSince1970: 631_152_000),
            biologicalSex: "female",
            toneMode: (seedTone ?? .coach).rawValue
        )
        if let forcePalette {
            profile.paletteId = forcePalette.rawValue
        }
        profile.sleepGoalHours = 7.5
        profile.strengthFrequencyPerWeek = 2
        profile.dietQualityBaseline = "okay"
        profile.onboardingCompletedAt = onboardedAt
        profile.onboardingV2CompletedAt = onboardedAt
        profile.disclaimerAcceptedAt = onboardedAt
        if let adjustment = seedBaselineAdjustment {
            profile.personalAdjustmentYears = adjustment
            profile.anchorAdjustedAt = onboardedAt
        }
        context.insert(profile)

        // Seed N days of diet-logged HabitLog entries backward from `now`. With
        // a `LIFECLOCK_FIXED_DATE` inside the current month, this drives the
        // monthlyLoggingBanner — N becomes the count if all seeded days fall
        // in the same calendar month. Also seeds matching DailyHealthSnapshot
        // rows so wrap-up integration audits (yesterday + weekly) have real
        // data; without these rows the wrap-up flow is unreachable from a
        // fresh seed (`pendingYesterday` requires a snapshot with
        // `hasMinimumData == true`).
        if seedStreak > 0 {
            let todayStart = calendar.startOfDay(for: now)
            for offset in 0..<seedStreak {
                let totalOffset = offset + seedLastLogDaysAgo
                guard let day = calendar.date(byAdding: .day, value: -totalOffset, to: now) else { continue }
                let dayStart = calendar.startOfDay(for: day)
                let log = HabitLog(date: dayStart)
                if seedBadDayToday && dayStart == todayStart {
                    // Bad-day-today fixture for the simulator-driven-polish
                    // vision audit. Combined with `LIFECLOCK_HEALTH_PROFILE=poor`
                    // this produces a clearly-negative `dailyTimeDeltaMinutes`
                    // (≈ −90) without inventing new tone copy.
                    log.dietQuality = "rough"
                    log.alcoholLevel = "heavy"
                    log.smokingVaping = true
                    log.stressLevel = "high"
                    log.strengthTraining = false
                    log.dietAmountRhythm = "skipBinge"
                    log.wholeFoodMeal = "no"
                } else {
                    log.dietQuality = "okay"
                    log.alcoholLevel = "none"
                    log.smokingVaping = false
                    log.stressLevel = "medium"
                    log.strengthTraining = false
                }
                context.insert(log)

                let snapshot = DailyHealthSnapshot(date: dayStart)
                snapshot.stepCount = 8_400
                snapshot.distanceMeters = 6_400
                snapshot.exerciseMinutes = 32
                snapshot.activeEnergyKcal = 410
                snapshot.sleepHours = 7.4
                snapshot.sleepConsistencyScore = 0.78
                snapshot.restingHeartRate = 60
                snapshot.sourceCompleteness = 0.85
                snapshot.lastRecomputedAt = now
                context.insert(snapshot)

                let dayKey = DayKey.from(date: dayStart, calendar: calendar)
                let reflection = DailyReflection(
                    dayKey: dayKey,
                    prompt: "What stood out today?",
                    response: "A quiet moment after lunch."
                )
                context.insert(reflection)
            }

            // Seed WeeklyReport rows for the past 4 weeks so weekly wrap-ups
            // (Monday only) have rows to query. NOTE: production currently
            // never persists WeeklyReport — this is a fixture-only assist
            // until `LifeClockStore.refreshFromHealthKit` learns to upsert
            // them. Tracked in the wrap-up-sequencing session log.
            for weeksBack in 1...4 {
                guard let weekStart = calendar.date(
                    byAdding: .day,
                    value: -weeksBack * 7,
                    to: calendar.startOfDay(for: now)
                ) else { continue }
                guard let weekEnd = calendar.date(byAdding: .day, value: 6, to: weekStart) else { continue }
                let report = WeeklyReport(weekStart: weekStart, weekEnd: weekEnd)
                report.netTimeDeltaMinutes = 0
                context.insert(report)
            }
        }

        // Seed N completed quests for today. Slugs come from the live engine so
        // they survive applyPersistedCompletions matching.
        if seedQuestsCompleted > 0 {
            let dayStart = calendar.startOfDay(for: now)
            let todayLog = (try? context.fetch(
                FetchDescriptor<HabitLog>(predicate: #Predicate { $0.date == dayStart })
            ))?.first
            let questEngine = QuestEngine(clock: clock)
            let quests = questEngine.generateDailyQuests(
                profile: profile,
                snapshot: nil,
                habits: todayLog
            )
            for quest in quests.prefix(seedQuestsCompleted) {
                quest.completedAt = now
                context.insert(quest)
            }
        }

        try? context.save()
    }
}

private extension ISO8601DateFormatter {
    /// Pinned formatter for `LIFECLOCK_FIXED_DATE` — accepts `2026-04-30T00:00:00Z`.
    static let lifeClockISO: ISO8601DateFormatter = {
        let f = ISO8601DateFormatter()
        f.formatOptions = [.withInternetDateTime]
        return f
    }()
}
