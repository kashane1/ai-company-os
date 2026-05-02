import Foundation

/// Why-are-you-here goal selected on the `goalPick` screen during the new
/// onboarding flow. Personalizes the recovery animation cycling words and
/// softens the framing of the mortality escalator (`bigNumberPenalty`,
/// `lifeGridRemaining`) for `.justCurious` users.
///
/// Persisted as `UserProfile.primaryGoal` (raw value).
///
/// Tone: every label is agency-framed; no medical-claim or doom verbs.
enum OnboardingGoal: String, CaseIterable, Identifiable {
    case liveLonger
    case moreEnergy
    case beThereForFamily
    case beatFamilyHistory
    case justCurious

    var id: String { rawValue }

    /// Decode a stored rawValue with explicit fallback. Use this everywhere
    /// the value is read off `UserProfile.primaryGoal`. Legacy / unknown
    /// values fall back to `.justCurious` rather than crashing — the
    /// most-neutral framing path.
    static func fromStored(_ raw: String?) -> OnboardingGoal {
        guard let raw, let value = OnboardingGoal(rawValue: raw) else {
            return .justCurious
        }
        return value
    }

    /// Short label shown on the `goalPick` screen.
    var displayName: String {
        switch self {
        case .liveLonger: return "Live longer"
        case .moreEnergy: return "Have more energy"
        case .beThereForFamily: return "Be there for family"
        case .beatFamilyHistory: return "Beat my family history"
        case .justCurious: return "Just curious"
        }
    }

    /// One-line clarifier shown beneath `displayName`.
    var detail: String {
        switch self {
        case .liveLonger: return "Add years where it counts."
        case .moreEnergy: return "Show up more in your day."
        case .beThereForFamily: return "Stay present, stay around."
        case .beatFamilyHistory: return "Outwork what you inherited."
        case .justCurious: return "See what the data says."
        }
    }
}
