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
}
