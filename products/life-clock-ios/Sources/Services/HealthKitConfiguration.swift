import Foundation

/// Picks between `LiveHealthKitService` (production) and `MockHealthKitService`
/// (tests, dev simulators without seeded Health data).
///
/// Override at launch with `LIFECLOCK_USE_MOCK_HEALTH=1` in the scheme's
/// environment variables to force mock data even on a debug build that
/// otherwise wires the live service.
enum HealthKitConfiguration {
    @MainActor
    static func service() -> HealthKitServiceProtocol {
        if ProcessInfo.processInfo.environment["LIFECLOCK_USE_MOCK_HEALTH"] == "1" {
            return MockHealthKitService()
        }
        #if targetEnvironment(simulator)
        // Simulator without env override → use mock by default. Real
        // HKHealthStore on the simulator works only if the user has manually
        // seeded Health.app, which is rare in dev.
        return MockHealthKitService()
        #else
        return LiveHealthKitService()
        #endif
    }
}
