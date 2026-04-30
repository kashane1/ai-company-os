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

    let isUITest: Bool
    let scenario: Scenario
    let useMockHealth: Bool
    let healthAuth: HealthAuth
    let forcePaywall: Bool
    let seedStreak: Int
    let seedQuestsCompleted: Int
    let clock: EngineClock

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
        let seedStreak = max(0, Int(env["LIFECLOCK_SEED_STREAK"] ?? "") ?? 0)
        let seedQuestsCompleted = max(0, Int(env["LIFECLOCK_SEED_QUESTS_COMPLETED"] ?? "") ?? 0)

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
            clock: clock
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
            clock: .live
        )
        #endif
    }

    var useInMemoryStore: Bool { isUITest }

    @MainActor
    func makeHealthService() -> HealthKitServiceProtocol {
        guard useMockHealth else { return HealthKitConfiguration.service() }
        switch healthAuth {
        case .authorized:
            return MockHealthKitService(preAuthorized: true)
        case .denied:
            // Simulates denial: marked as "asked" so the UI doesn't keep prompting,
            // but returns no data. Matches the protocol stance that authorizationKnown
            // never claims to know whether grant succeeded — empty snapshots are the signal.
            return MockHealthKitService(simulateNoData: true, preAuthorized: true)
        case .notDetermined:
            return MockHealthKitService(preAuthorized: false)
        }
    }

    func seedInitialStateIfNeeded(in context: ModelContext) {
        guard scenario == .onboarded else { return }
        let descriptor = FetchDescriptor<UserProfile>()
        if let existing = try? context.fetch(descriptor), !existing.isEmpty { return }

        let now = clock.now()
        let calendar = clock.calendar
        let profile = UserProfile(
            birthDate: Date(timeIntervalSince1970: 631_152_000),
            biologicalSex: "female",
            toneMode: ToneMode.coach.rawValue
        )
        profile.sleepGoalHours = 7.5
        profile.strengthFrequencyPerWeek = 2
        profile.dietQualityBaseline = "okay"
        profile.onboardingCompletedAt = now
        profile.disclaimerAcceptedAt = now
        context.insert(profile)

        // Seed N days of diet-logged HabitLog entries to drive the streak banner.
        if seedStreak > 0 {
            for offset in 0..<seedStreak {
                guard let day = calendar.date(byAdding: .day, value: -offset, to: now) else { continue }
                let dayStart = calendar.startOfDay(for: day)
                let log = HabitLog(date: dayStart)
                log.dietQuality = "okay"
                log.alcoholLevel = "none"
                log.smokingVaping = false
                log.stressLevel = "medium"
                log.strengthTraining = false
                context.insert(log)
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
