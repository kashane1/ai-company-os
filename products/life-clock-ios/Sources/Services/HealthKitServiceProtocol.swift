import Foundation

/// Service boundary for HealthKit access.
///
/// Two implementations live under `Sources/Services/`:
///   - `LiveHealthKitService` — talks to `HKHealthStore`, used in production.
///   - `MockHealthKitService` — deterministic fixture data for tests and dev.
///
/// `HealthKitConfiguration.service()` chooses between them based on the env.
///
/// Authorization model: read denials are silent by Apple privacy design. We
/// track whether we *asked* (`authorizationKnown`) but never claim to know
/// whether the user denied. The Profile screen surfaces this honestly:
/// "Not configured" → "Available" / "No data" → never "Connected" / "Denied".
protocol HealthKitServiceProtocol {
    /// True iff `HKHealthStore.isHealthDataAvailable()` (always false on iPad
    /// pre-iPadOS 17, on Mac Catalyst, etc).
    var isHealthDataAvailable: Bool { get }

    /// Triggers the system authorization sheet. Idempotent — iOS will not
    /// re-prompt for already-decided types. Throws on platforms where
    /// HealthKit is unavailable, on entitlement misconfiguration, or on
    /// missing `Info.plist` usage strings — debuggable in TestFlight, not
    /// silently swallowed.
    func requestAuthorization() async throws

    /// True once `requestAuthorization()` has been called in any prior
    /// session. Persisted across launches via UserDefaults.
    var authorizationKnown: Bool { get }

    /// Daily snapshot for the given date, or nil if no data is available.
    /// Treat nil as "missing data" — never as "denied". Calling this without
    /// authorizationKnown is allowed; the underlying store returns empty
    /// results for unauthorized reads.
    func dailySnapshot(for date: Date) async -> DailyHealthSnapshot?

    /// Up to `count` snapshots ending at `endDate`, oldest first.
    func recentSnapshots(endingAt endDate: Date, count: Int) async -> [DailyHealthSnapshot]
}

enum HealthKitError: Error {
    case unavailable
}
