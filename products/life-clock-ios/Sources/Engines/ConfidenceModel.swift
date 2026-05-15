import Foundation

enum Confidence: String, CaseIterable {
    case low
    case medium
    case high

    var label: String {
        switch self {
        case .low: return "Low"
        case .medium: return "Medium"
        case .high: return "High"
        }
    }
}

/// Data-quality scoring for the daily and weekly views.
///
/// Surfaced to the user as "Data quality" (see `ConfidenceBadge`). The
/// internal enum is still called `Confidence` because the schema field
/// `confidenceRaw` persists across versions and per-driver rows use the
/// same enum to mark source reliability (HealthKit = high, manual = medium).
///
/// The score blends two sides equally:
///   • **User input** — did the person fill out the daily check-in?
///   • **Passive sensors** — how many of the six HealthKit signals reported in?
///
/// Each side contributes up to 0.5. Same thresholds map score → label:
/// ≥0.7 = high, ≥0.4 = medium, else low. A user who completes the check-in
/// gets credit even on sparse-sensor days; a watch-wearer who skips the
/// check-in still hits medium with a few signals.
enum ConfidenceModel {
    /// Weight split between the two sides. 0.5 each — change here and the
    /// docs above stay accurate.
    static let userInputWeight: Double = 0.5
    static let sensorWeight: Double = 0.5

    /// Daily score for one snapshot + (optional) habit log.
    static func assign(snapshot: DailyHealthSnapshot?, habits: HabitLog?) -> Confidence {
        guard let snapshot else { return .low }
        let userScore = habits != nil ? 1.0 : 0.0
        let sensorScore = snapshot.sourceCompleteness
        return level(for: combined(userScore: userScore, sensorScore: sensorScore))
    }

    /// Weekly score: average user-input presence and average sensor
    /// completeness across the window.
    static func assignWeekly(
        snapshots: [DailyHealthSnapshot],
        habits: [HabitLog]
    ) -> Confidence {
        guard !snapshots.isEmpty else { return .low }
        let habitDates = Set(habits.map(\.date))
        let userScore = Double(
            snapshots.filter { habitDates.contains($0.date) }.count
        ) / Double(snapshots.count)
        let sensorScore = snapshots.map(\.sourceCompleteness).reduce(0, +) / Double(snapshots.count)
        return level(for: combined(userScore: userScore, sensorScore: sensorScore))
    }

    static func combined(userScore: Double, sensorScore: Double) -> Double {
        min(1.0, userInputWeight * userScore + sensorWeight * sensorScore)
    }

    private static func level(for score: Double) -> Confidence {
        if score >= 0.7 { return .high }
        if score >= 0.4 { return .medium }
        return .low
    }
}
