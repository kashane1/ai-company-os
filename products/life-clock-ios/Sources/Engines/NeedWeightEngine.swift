import Foundation

/// Per-genre priority computation: how badly does the user *need* a
/// quest in each genre today? Driven by HealthKit baselines + onboarding
/// signals.
///
/// Phase 3 of the quest-pool affinity engine
/// (docs/plans/2026-05-08-feat-quest-pool-phase-3-engines-plan.md).
///
/// `affinity` (preference) and `needWeight` (priority) are intentionally
/// SEPARATE in the selector's score formula. Affinity is "what the user
/// likes"; need-weight is "what the user's body is telling us." They
/// multiply at scoring time so a high-priority genre still surfaces
/// even if the user doesn't love it (the hard genre floor is the
/// last-resort safety net for that).
///
/// **HK trumps onboarding self-report on disagreement** (master plan D7).
/// E.g., if `dietQualityBaseline == "great"` but HK shows 2,400 daily
/// steps, activity need-weight stays high regardless. For genres
/// where HK doesn't provide a metric (diet today), onboarding is the
/// only signal source.
///
/// Banding thresholds are pinned as `static let` constants so a
/// product call to retune them is one place.
enum NeedWeightEngine {
    // MARK: - Banding thresholds

    /// Activity: HK steps p50 over recent days. Below this → high need.
    static let stepsLowThreshold: Double = 5_000
    /// Activity: HK steps p50 above this → low need.
    static let stepsHighThreshold: Double = 8_000

    /// Sleep: HK p50 sleep hours below this → high need.
    static let sleepLowThreshold: Double = 6.5
    /// Sleep: HK p50 sleep hours at or above this → low need.
    static let sleepHighThreshold: Double = 7.5

    /// Minimum HK days needed to trust the p50. Below this we fall back
    /// to onboarding self-report. Mirrors `QuestEngine.movementStepTarget`.
    static let minHKDaysForBaseline: Int = 5

    /// Recent-days window for HK percentile reads.
    static let hkWindowDays: Int = 14

    // MARK: - Need-weight bands

    static let high: Double = 0.9
    static let medium: Double = 0.6
    static let low: Double = 0.3

    // MARK: - Public

    /// Compute per-genre need-weight from a snapshot of the user's
    /// state. Caller passes a slice of recent `DailyHealthSnapshot`
    /// rows (the engine doesn't query HK directly — keeps it pure).
    static func compute(
        profile: UserProfile,
        recentSnapshots: [DailyHealthSnapshot]
    ) -> [Genre: Double] {
        var weights: [Genre: Double] = [:]
        weights[.activity] = activityNeedWeight(profile: profile, snapshots: recentSnapshots)
        weights[.sleep] = sleepNeedWeight(profile: profile, snapshots: recentSnapshots)
        weights[.diet] = dietNeedWeight(profile: profile)
        return weights
    }

    // MARK: - Per-genre

    static func activityNeedWeight(profile: UserProfile, snapshots: [DailyHealthSnapshot]) -> Double {
        let recent = snapshots.suffix(hkWindowDays)
        let validSteps = recent.compactMap { $0.stepCount }.filter { $0 > 0 }.map(Double.init)
        guard validSteps.count >= minHKDaysForBaseline, let p50 = p50Of(validSteps) else {
            // Insufficient HK data → fall back to onboarding cardio
            // signal. cardioMinsPerWeek == 0 reads as "low cardio →
            // activity need is high"; ≥150 → low. Linear bands kept
            // simple; product can refine later.
            if profile.cardioMinsPerWeek >= 150 { return low }
            if profile.cardioMinsPerWeek >= 75 { return medium }
            return high
        }
        if p50 < stepsLowThreshold { return high }
        if p50 < stepsHighThreshold { return medium }
        return low
    }

    static func sleepNeedWeight(profile: UserProfile, snapshots: [DailyHealthSnapshot]) -> Double {
        let recent = snapshots.suffix(hkWindowDays)
        let validHours = recent.compactMap { $0.sleepHours }.filter { $0 > 0 }
        guard validHours.count >= minHKDaysForBaseline, let p50 = p50Of(validHours) else {
            // Insufficient HK data → fall back to sleepGoalHours.
            // Treat "the user said they want N hours of sleep" as a
            // proxy for current pattern when no measurements exist.
            if profile.sleepGoalHours < sleepLowThreshold { return high }
            if profile.sleepGoalHours < sleepHighThreshold { return medium }
            return low
        }
        if p50 < sleepLowThreshold { return high }
        if p50 < sleepHighThreshold { return medium }
        return low
    }

    static func dietNeedWeight(profile: UserProfile) -> Double {
        // Diet has no HK metric today; baseline is the onboarding
        // self-report. Heavy alcohol forces high regardless.
        let base: Double = {
            switch profile.dietQualityBaseline {
            case "rough": return high
            case "okay":  return medium
            case "great": return low
            default:      return medium
            }
        }()
        if profile.alcoholFrequency == "heavy" {
            return high
        }
        return base
    }

    // MARK: - Helpers

    /// p50 (median) of an unsorted array. Returns nil for empty input.
    /// Pure function; safe for concurrent use.
    static func p50Of<T: Comparable>(_ values: [T]) -> T? {
        guard !values.isEmpty else { return nil }
        let sorted = values.sorted()
        return sorted[sorted.count / 2]
    }
}
