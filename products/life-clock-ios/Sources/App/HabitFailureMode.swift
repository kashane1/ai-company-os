import Foundation

/// What usually breaks the user's habits — captured on the `habitFailureMode`
/// onboarding screen (right after `tone`). One question with five chips.
///
/// Drives the paywall headline branch and the receipt screen's coaching
/// line. NOT a clinical taxonomy — five buckets sourced from the
/// brainstorm on common drop-off shapes ("forget", "lose motivation",
/// "overdo and quit", "no visible progress", "life gets chaotic").
///
/// Persisted as `UserProfile.habitFailureMode` (raw value). Decoded via
/// `fromStored(_:)` with `.unanswered` fallback so unanswered legacy
/// rows render the neutral copy branch instead of crashing.
enum HabitFailureMode: String, CaseIterable, Identifiable {
    case forget
    case loseMotivation = "lose_motivation"
    case overdoAndStop = "overdo_and_stop"
    case noProgressVisible = "no_progress_visible"
    case chaos

    /// Sentinel used by `fromStored` when the persisted value is missing
    /// or unknown. Distinct from any user-selectable case so the paywall
    /// branch can fall through to a neutral default without misattributing
    /// an answer the user didn't actually pick.
    case unanswered

    var id: String { rawValue }

    /// Decode a stored rawValue with explicit fallback. Use this everywhere
    /// the value is read off `UserProfile.habitFailureMode`. Legacy /
    /// unknown values fall back to `.unanswered` rather than crashing —
    /// callers MUST handle `.unanswered` as the no-personalization branch.
    static func fromStored(_ raw: String?) -> HabitFailureMode {
        guard let raw, let value = HabitFailureMode(rawValue: raw) else {
            return .unanswered
        }
        return value
    }

    /// Cases shown on the `habitFailureMode` selection screen. `.unanswered`
    /// is a sentinel and is never offered to the user.
    static var selectableCases: [HabitFailureMode] {
        allCases.filter { $0 != .unanswered }
    }

    /// Short chip label.
    var displayName: String {
        switch self {
        case .forget: return "I forget"
        case .loseMotivation: return "I lose motivation"
        case .overdoAndStop: return "I overdo it and stop"
        case .noProgressVisible: return "I don't see progress"
        case .chaos: return "Life gets chaotic"
        case .unanswered: return ""
        }
    }
}
