import Foundation

/// One of the lifestyle levers the engine reads. Used in two places:
///   - the `leverGuess` onboarding screen (user picks which they think
///     moves their clock most)
///   - `ClockEngine.topLever(profile:)` (engine's actual top driver of
///     the user's negative lifestyle adjustment)
///
/// The archetype reveal compares the two — match = "you called it",
/// mismatch = "most people guess wrong on this".
///
/// Persisted on `UserProfile.leverGuess` (the user's guess only —
/// the engine-computed top lever is recomputed on demand, not stored).
/// Decoded via `fromStored(_:)` with `.unanswered` fallback.
enum LifeClockLever: String, CaseIterable, Identifiable {
    case sleep
    case movement
    case food
    case drinking
    case stressRecovery = "stress_recovery"

    /// Sentinel for unanswered / unknown reads. Distinct from any
    /// selectable case so callers can branch on "we have no signal".
    case unanswered

    var id: String { rawValue }

    static func fromStored(_ raw: String?) -> LifeClockLever {
        guard let raw, let value = LifeClockLever(rawValue: raw) else {
            return .unanswered
        }
        return value
    }

    static var selectableCases: [LifeClockLever] {
        allCases.filter { $0 != .unanswered }
    }

    /// Short chip label. The lever names intentionally mirror everyday
    /// language, not the engine's internal driver IDs ("cardio" reads as
    /// "movement" to a non-runner).
    var displayName: String {
        switch self {
        case .sleep: return "Sleep"
        case .movement: return "Movement"
        case .food: return "Food"
        case .drinking: return "Drinking"
        case .stressRecovery: return "Stress recovery"
        case .unanswered: return ""
        }
    }

    /// Sub-line under `displayName` on selection screens.
    var detail: String {
        switch self {
        case .sleep: return "Hours and consistency."
        case .movement: return "Steps, cardio, strength."
        case .food: return "What and when you eat."
        case .drinking: return "Alcohol over the week."
        case .stressRecovery: return "Pressure and how you wind down."
        case .unanswered: return ""
        }
    }
}
