import Foundation

/// Pace-based longevity archetype surfaced on the archetype-reveal screen
/// during the new onboarding flow. Decided by `ClockEngine.computeArchetype`
/// from the user's lifestyle factors and family-longevity inputs.
///
/// Persisted as `UserProfile.archetype` (raw value). Decoded via
/// `fromStored(_:)` with explicit `.marathoner` fallback so legacy /
/// missing values never crash a screen that depends on this.
///
/// **Tone discipline:** archetype names + descriptions are agency-framed.
/// Never use "diagnose / prescribe / guarantee / predict" language; never
/// imply medical authority. See `CLAUDE_HANDOFF.md` for the gate.
enum Archetype: String, CaseIterable, Identifiable {
    /// Steady, well-paced. Low behavioral risk; no urgent course-corrections
    /// suggested. Default fallback when other rules don't fire.
    case marathoner

    /// High behavioral risk but young enough that course-correction has
    /// outsized payoff. Engine selects when `age < 50` AND `behavioralRisk > 0.6`.
    case sprinter

    /// Moderate behavioral risk paired with poor genetic anchor. The
    /// "huge upside if you engage" archetype — small, sustained changes
    /// matter most here.
    case sleeper

    /// Strong genetic anchor (long-lived parents) carrying weight despite
    /// elevated behavioral risk. Framing reminds the user that genes are
    /// one signal, not a hall pass.
    case outlier

    var id: String { rawValue }

    /// Decode a stored rawValue with explicit fallback. Use this everywhere
    /// the value is read off `UserProfile.archetype`. Legacy / unknown
    /// values fall back to `.marathoner` rather than crashing.
    static func fromStored(_ raw: String?) -> Archetype {
        guard let raw, let value = Archetype(rawValue: raw) else {
            return .marathoner
        }
        return value
    }

    /// Short label used as the archetype headline on the reveal screen.
    var displayName: String {
        switch self {
        case .marathoner: return "The Marathoner"
        case .sprinter: return "The Sprinter"
        case .sleeper: return "The Sleeper"
        case .outlier: return "The Outlier"
        }
    }

    /// One-paragraph descriptor shown beneath the displayName. Intentionally
    /// agency-framed; no medical-claim verbs.
    var description: String {
        switch self {
        case .marathoner:
            return "Steady, well-paced. Your habits are already pulling in the right direction."
        case .sprinter:
            return "High momentum, high friction. The same energy that's working against you can flip — small swaps go far at this stage."
        case .sleeper:
            return "Quietly stacked upside. The leverage is in the small things you haven't started yet."
        case .outlier:
            return "Genes carry weight, but they're one signal, not a hall pass. Your habits still set the pace."
        }
    }
}
