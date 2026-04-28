import Foundation

enum Confidence: String, CaseIterable, Codable {
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

enum ConfidenceModel {
    /// Confidence is a function of data-source completeness. Missing data
    /// reduces confidence; it never produces a negative time delta. The
    /// `sourceCompleteness` field on `DailyHealthSnapshot` is in [0, 1].
    static func assign(snapshot: DailyHealthSnapshot?) -> Confidence {
        guard let snapshot else { return .low }
        let score = snapshot.sourceCompleteness
        if score >= 0.7 { return .high }
        if score >= 0.4 { return .medium }
        return .low
    }

    /// Estimate completeness from the population of fields actually present.
    /// Tier-1 MVP signals (per HEALTH_DATA_STRATEGY): steps, exercise minutes,
    /// sleep, weight, resting HR. Each present field contributes 0.2.
    static func computeCompleteness(snapshot: DailyHealthSnapshot) -> Double {
        var score = 0.0
        if snapshot.stepCount != nil { score += 0.2 }
        if snapshot.exerciseMinutes != nil { score += 0.2 }
        if snapshot.sleepHours != nil { score += 0.2 }
        if snapshot.weightKgIfTracked() { score += 0.2 }
        if snapshot.restingHeartRate != nil { score += 0.2 }
        return min(1.0, score)
    }
}

private extension DailyHealthSnapshot {
    /// Body composition is a baseline-style signal, not a daily one — but we
    /// count it as "present" if `activeEnergyKcal` is recorded (close-enough
    /// proxy for an Apple Watch wearer who's also tracking weight).
    func weightKgIfTracked() -> Bool { activeEnergyKcal != nil }
}
