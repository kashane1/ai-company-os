import Foundation

/// Service boundary for HealthKit access.
///
/// v1 ships only `MockHealthKitService`. The live implementation lands with a
/// follow-up plan that adds the HealthKit entitlement and progressive
/// authorization flow. This protocol exists so the rest of the app can be
/// written against a stable shape today.
protocol HealthKitServiceProtocol {
    var isAuthorizationKnown: Bool { get }

    /// Returns the daily snapshot for the given date, or nil if no data is
    /// available. Treat nil as "missing data" — never as "denied".
    func dailySnapshot(for date: Date) async -> DailyHealthSnapshot?

    /// Returns up to `count` snapshots ending at `endDate`, oldest first.
    func recentSnapshots(endingAt endDate: Date, count: Int) async -> [DailyHealthSnapshot]
}
