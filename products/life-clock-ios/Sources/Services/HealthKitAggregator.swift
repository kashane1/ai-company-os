import Foundation

/// Pure, testable layer between raw HealthKit values and `DailyHealthSnapshot`.
///
/// `LiveHealthKitService` runs the queries; this struct turns the resulting
/// numbers into a snapshot with a confidence-friendly `sourceCompleteness`.
/// Keeping this separate is what lets us unit-test aggregation without
/// `HKHealthStore`.
struct HealthKitAggregator {
    /// Inputs are all optional — any may be missing. Missing fields lower
    /// `sourceCompleteness` rather than synthesizing fake data.
    static func aggregate(
        date: Date,
        stepCount: Double?,
        exerciseMinutes: Double?,
        activeEnergyKcal: Double?,
        sleepHours: Double?,
        restingHeartRate: Double?,
        weightKg: Double?
    ) -> DailyHealthSnapshot {
        let snapshot = DailyHealthSnapshot(date: date)
        if let s = stepCount { snapshot.stepCount = Int(s.rounded()) }
        snapshot.exerciseMinutes = exerciseMinutes.map { Int($0.rounded()) }
        snapshot.activeEnergyKcal = activeEnergyKcal
        snapshot.sleepHours = sleepHours
        snapshot.restingHeartRate = restingHeartRate.map { Int($0.rounded()) }
        if let s = stepCount { snapshot.distanceMeters = s * 0.78 }
        // weightKg is captured on UserProfile, not the daily snapshot — but it
        // counts toward source completeness if present.
        snapshot.sourceCompleteness = computeCompleteness(
            stepCount: stepCount,
            exerciseMinutes: exerciseMinutes,
            activeEnergyKcal: activeEnergyKcal,
            sleepHours: sleepHours,
            restingHeartRate: restingHeartRate,
            weightKg: weightKg
        )
        return snapshot
    }

    /// Per-signal completeness. Six signals — each contributes 1/6.
    /// `activeEnergyKcal` is included so the importer's "skip empty days"
    /// filter (`sourceCompleteness > 0`) doesn't silently drop days where
    /// active energy is the only signal HK delivered (e.g. Apple Watch
    /// energy ring on a day the phone wasn't carried).
    static func computeCompleteness(
        stepCount: Double?,
        exerciseMinutes: Double?,
        activeEnergyKcal: Double? = nil,
        sleepHours: Double?,
        restingHeartRate: Double?,
        weightKg: Double?
    ) -> Double {
        var score = 0.0
        let weight = 1.0 / 6.0
        if stepCount != nil { score += weight }
        if exerciseMinutes != nil { score += weight }
        if activeEnergyKcal != nil { score += weight }
        if sleepHours != nil { score += weight }
        if restingHeartRate != nil { score += weight }
        if weightKg != nil { score += weight }
        return min(1.0, score)
    }
}
