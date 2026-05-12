import Foundation

/// In-memory result returned by `LifeClockStore.cumulativeDeltaSinceInstall()`.
/// Drives `InstallSummarySection`'s hero, narrative, and contributors
/// panel.
///
/// V1.7.0 (Future tab + History summary plan §Phase 1). The cumulative
/// walk runs from `max(profile.onboardingCompletedAt, now - 3.years)`
/// to yesterday (today excluded per the existing
/// `recentSnapshots(includingToday: false)` convention).
struct CumulativeSummary: Equatable {
    /// Signed sum of `dailyTimeDeltaMinutes` across the window.
    let totalDeltaMinutes: Int

    /// Start of the cache window. Equal to `onboardingCompletedAt`
    /// unless the user has been installed more than 3 years (rare in
    /// v1) — then the 3-year truncation applies and the view surfaces
    /// the "since {Year}" affordance instead of "since {Month Day}".
    let windowStart: Date

    /// Most recent date included in the cumulative walk (yesterday
    /// when the cache is fresh).
    let lastIncludedDate: Date

    /// Days of install: `days(windowStart..now)`. Drives the day-state
    /// machine in the view (Day 0 / 1–6 / 7+ reveal gates).
    let daysSinceInstall: Int

    /// Top-3 driver contributors (or fewer if `snapshotsWithData < 7`).
    /// Sorted by `abs(netDeltaMinutes)` desc.
    let topContributors: [CumulativeContributor]

    /// Number of snapshot+habit days that had usable signal (used for
    /// the Day 7+ "no signal yet" gate per the plan).
    let snapshotsWithData: Int

    /// True when the 3-year window truncation applies — i.e.
    /// `windowStart != onboardingCompletedAt`. Drives the "since
    /// {Year}" copy variant.
    let truncatedTo3Years: Bool
}

/// One row in the History summary section's top-3 contributors panel.
/// Encoded as JSON inside `CumulativeSummaryCache.topContributorsData`.
struct CumulativeContributor: Codable, Equatable, Hashable {
    /// Stable string keys matching `ClockEngine.calculateDailyDelta`'s
    /// `driverType` outputs. Phase 1 consumes raw strings to avoid
    /// coupling the History summary to the Phase 4 slider dimension
    /// enum (which doesn't exist yet). The view layer maps these to
    /// tone copy via the per-dimension switch in `InstallSummarySection`.
    enum Dimension: String, Codable {
        case sleep
        case movement     // steps / step-derived activity
        case exercise     // exercise minutes
        case diet
        case alcohol
        case smoking
        case strength
        case other
    }

    let dimension: Dimension
    let netDeltaMinutes: Int

    /// Count of days within the window where this driver appeared.
    /// Drives the rules-based narrative ("X of your top days came from…").
    let topDayCount: Int
}

extension CumulativeContributor.Dimension {
    /// Maps raw `TimeLedgerEntry.driverType` strings (set by
    /// `ClockEngine.calculateDailyDelta`) to the cumulative-summary
    /// dimension keys. Unknown strings fall to `.other`.
    init(driverString: String) {
        switch driverString.lowercased() {
        case "sleep": self = .sleep
        case "movement": self = .movement
        case "exercise": self = .exercise
        case "diet": self = .diet
        case "alcohol": self = .alcohol
        case "smoking": self = .smoking
        case "strength": self = .strength
        default: self = .other
        }
    }
}
