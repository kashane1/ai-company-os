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
            forceSafetyNet: forceSafetyNet
        )
        #else
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
            forceSafetyNet: false
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
        guard scenario == .onboarded else { return }
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
        let onboardedAt: Date = {
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
