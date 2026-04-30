import Foundation
import SwiftData

/// Centralizes launch-time overrides used by UI tests and simulator audits.
/// This keeps deterministic state setup out of individual views.
struct LifeClockLaunchConfiguration {
    enum Scenario: String {
        case onboarding
        case onboarded
    }

    let isUITest: Bool
    let scenario: Scenario
    let useMockHealth: Bool
    let mockHealthAuthorized: Bool
    let clock: EngineClock

    static var current: LifeClockLaunchConfiguration {
        let env = ProcessInfo.processInfo.environment
        let isUITest = env["LIFECLOCK_UI_TEST"] == "1"
        let scenario = Scenario(rawValue: env["LIFECLOCK_UI_TEST_SCENARIO"] ?? "") ?? .onboarding
        let useMockHealth = env["LIFECLOCK_USE_MOCK_HEALTH"] == "1" || isUITest
        let mockHealthAuthorized = env["LIFECLOCK_UI_TEST_AUTHORIZED"] == "1"
        let clock: EngineClock
        if isUITest {
            clock = .fixed(Date(timeIntervalSince1970: 1_800_000_000))
        } else {
            clock = .live
        }

        return LifeClockLaunchConfiguration(
            isUITest: isUITest,
            scenario: scenario,
            useMockHealth: useMockHealth,
            mockHealthAuthorized: mockHealthAuthorized,
            clock: clock
        )
    }

    var useInMemoryStore: Bool { isUITest }

    @MainActor
    func makeHealthService() -> HealthKitServiceProtocol {
        if useMockHealth {
            return MockHealthKitService(preAuthorized: mockHealthAuthorized)
        }
        return HealthKitConfiguration.service()
    }

    func seedInitialStateIfNeeded(in context: ModelContext) {
        guard scenario == .onboarded else { return }

        let descriptor = FetchDescriptor<UserProfile>()
        if let existingProfiles = try? context.fetch(descriptor), !existingProfiles.isEmpty {
            return
        }

        let profile = UserProfile(
            birthDate: Date(timeIntervalSince1970: 631_152_000),
            biologicalSex: "female",
            toneMode: ToneMode.coach.rawValue
        )
        profile.sleepGoalHours = 7.5
        profile.strengthFrequencyPerWeek = 2
        profile.dietQualityBaseline = "okay"
        profile.onboardingCompletedAt = clock.now()
        profile.disclaimerAcceptedAt = clock.now()
        context.insert(profile)
        try? context.save()
    }
}
