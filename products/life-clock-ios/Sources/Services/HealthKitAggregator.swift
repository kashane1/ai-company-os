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
        workoutsCount: Int?,
        sleepHours: Double?,
        restingHeartRate: Double?,
        heartRateAvg: Double?,
        weightKg: Double?,
        vo2Max: Double?
    ) -> DailyHealthSnapshot {
        let snapshot = DailyHealthSnapshot(date: date)
        if let s = stepCount { snapshot.stepCount = Int(s.rounded()) }
        snapshot.exerciseMinutes = exerciseMinutes.map { Int($0.rounded()) }
        snapshot.activeEnergyKcal = activeEnergyKcal
        snapshot.workoutsCount = workoutsCount
        snapshot.sleepHours = sleepHours
        snapshot.restingHeartRate = restingHeartRate.map { Int($0.rounded()) }
        snapshot.heartRateAvg = heartRateAvg.map { Int($0.rounded()) }
        snapshot.vo2Max = vo2Max
        if let s = stepCount { snapshot.distanceMeters = s * 0.78 }
        // weightKg is captured on UserProfile, not the daily snapshot — but it
        // counts toward source completeness if present.
        snapshot.sourceCompleteness = computeCompleteness(
            stepCount: stepCount,
            exerciseMinutes: exerciseMinutes,
            sleepHours: sleepHours,
            restingHeartRate: restingHeartRate,
            weightKg: weightKg
        )
        return snapshot
    }

    /// Tier-1 MVP completeness: each present signal contributes equally.
    /// Five signals → score in {0.0, 0.2, 0.4, 0.6, 0.8, 1.0}.
    static func computeCompleteness(
        stepCount: Double?,
        exerciseMinutes: Double?,
        sleepHours: Double?,
        restingHeartRate: Double?,
        weightKg: Double?
    ) -> Double {
        var score = 0.0
        if stepCount != nil { score += 0.2 }
        if exerciseMinutes != nil { score += 0.2 }
        if sleepHours != nil { score += 0.2 }
        if restingHeartRate != nil { score += 0.2 }
        if weightKg != nil { score += 0.2 }
        return min(1.0, score)
    }
}
