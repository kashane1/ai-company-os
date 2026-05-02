import Foundation
import Observation

/// Transient in-progress draft of an onboarding session. Mirrors the
/// fields that `UserProfile` will hold but with all-optional types so
/// the engine can compute a partial estimate after each answer.
///
/// **Not persisted.** No UserDefaults, no Keychain, no file. A
/// mid-onboarding crash discards the draft; the user restarts. This
/// is deliberate — storing `parentMotherAgeAtDeath`, `perceivedStressScore`,
/// and `lonelinessScore` in any unencrypted-at-rest store leaks PII to
/// iCloud device backup and violates the on-device privacy stance set
/// by `cloudKitDatabase: .none`. The flow is ≤5 minutes; a re-entry
/// after a process kill is acceptable UX.
///
/// Materializes into a `UserProfile` via `materialize()` at the end of
/// the flow; the resulting profile is what `LifeClockStore.completeOnboarding`
/// receives — the store-level signature stays stable.
@Observable
@MainActor
final class OnboardingDraft {
    // MARK: - Baseline (collected on baselineDOB + baselineSex)

    var birthDate: Date?
    var biologicalSex: String?

    // MARK: - Body composition (existing UserProfile fields, repurposed)

    var heightCm: Double?
    var weightKg: Double?

    // MARK: - Healthspan dial

    var personalAdjustmentYears: Double?
    var anchorAdjustedAt: Date?

    // MARK: - Existing lifestyle inputs

    var smokingStatus: String?
    var alcoholFrequency: String?
    var strengthFrequencyPerWeek: Int?
    var sleepGoalHours: Double?
    var dietQualityBaseline: String?

    // MARK: - New lifestyle inputs (reveal-onboarding rebuild)

    var cardioMinsPerWeek: Int?
    var parentMotherAlive: Bool?
    var parentMotherAgeAtDeath: Int?
    var parentFatherAlive: Bool?
    var parentFatherAgeAtDeath: Int?
    var perceivedStressScore: Int?
    var lonelinessScore: Int?

    // MARK: - Onboarding-specific

    var primaryGoal: OnboardingGoal?
    var toneMode: ToneMode?
    /// `priorAttempts` informs archetype sub-meter weighting and recovery
    /// copy tone. Captured on the `priorAttempts` screen but not persisted
    /// to `UserProfile` — it's an onboarding-only signal.
    var priorAttempts: PriorAttempts?

    // MARK: - Reactive engine output

    /// Last-computed running estimate. `nil` until both `birthDate` AND
    /// `biologicalSex` are set (engine needs both for population baseline).
    /// Updated by `recomputeEstimate(using:)` after each answer.
    var runningEstimate: LifeClockEstimate?

    /// Per-answer "why" caption accompanying the most recent estimate
    /// movement. Cleared on `birthDate` / `biologicalSex` first-set
    /// (initial estimate has no delta to explain).
    var lastDelta: AnswerDelta?

    init() {}

    // MARK: - Reactive recomputation

    /// Recompute `runningEstimate` against the engine. Caller passes the
    /// engine because the draft must not own a clock. Called after every
    /// answer screen; cheap (the engine is rules-based arithmetic).
    func recomputeEstimate(using engine: ClockEngine) {
        guard let bd = birthDate, let sex = biologicalSex else {
            runningEstimate = nil
            lastDelta = nil
            return
        }

        // Build a transient UserProfile from current draft state.
        // We DON'T insert this into a ModelContext — it's a value-only
        // snapshot for the engine to read. SwiftData @Model objects can
        // be constructed without a context for this read-only purpose.
        let snapshot = UserProfile(birthDate: bd, biologicalSex: sex)
        snapshot.heightCm = heightCm
        snapshot.weightKg = weightKg
        if let s = smokingStatus { snapshot.smokingStatus = s }
        if let a = alcoholFrequency { snapshot.alcoholFrequency = a }
        if let s = strengthFrequencyPerWeek { snapshot.strengthFrequencyPerWeek = s }
        if let h = sleepGoalHours { snapshot.sleepGoalHours = h }
        if let d = dietQualityBaseline { snapshot.dietQualityBaseline = d }
        if let c = cardioMinsPerWeek { snapshot.cardioMinsPerWeek = c }
        snapshot.parentMotherAlive = parentMotherAlive
        snapshot.parentMotherAgeAtDeath = parentMotherAgeAtDeath
        snapshot.parentFatherAlive = parentFatherAlive
        snapshot.parentFatherAgeAtDeath = parentFatherAgeAtDeath
        snapshot.perceivedStressScore = perceivedStressScore
        snapshot.lonelinessScore = lonelinessScore

        let previous = runningEstimate
        let next = engine.calculateBaseline(profile: snapshot)
        runningEstimate = next

        if let previous {
            let deltaYears = next.projectedAgeYears - previous.projectedAgeYears
            if abs(deltaYears) > 0.05 {
                lastDelta = AnswerDelta(years: deltaYears, caption: "")
            } else {
                lastDelta = nil
            }
        } else {
            lastDelta = nil
        }
    }

    /// Materialize the draft into a fully-populated `UserProfile` for
    /// `LifeClockStore.completeOnboarding`. Caller is responsible for
    /// inserting the result into the model context; the draft does not
    /// touch persistence. Defaults match the `UserProfile` initializer
    /// when the draft never collected a field (safety net — onboarding
    /// flow should always set at minimum birthDate, biologicalSex, tone).
    func materialize() -> UserProfile {
        let bd = birthDate ?? Date(timeIntervalSince1970: 0)
        let sex = biologicalSex ?? "unspecified"
        let tone = toneMode?.rawValue ?? "coach"
        let profile = UserProfile(
            birthDate: bd,
            biologicalSex: sex,
            toneMode: tone
        )
        profile.heightCm = heightCm
        profile.weightKg = weightKg
        profile.personalAdjustmentYears = personalAdjustmentYears
        profile.anchorAdjustedAt = anchorAdjustedAt
        if let s = smokingStatus { profile.smokingStatus = s }
        if let a = alcoholFrequency { profile.alcoholFrequency = a }
        if let s = strengthFrequencyPerWeek { profile.strengthFrequencyPerWeek = s }
        if let h = sleepGoalHours { profile.sleepGoalHours = h }
        if let d = dietQualityBaseline { profile.dietQualityBaseline = d }
        if let c = cardioMinsPerWeek { profile.cardioMinsPerWeek = c }
        profile.parentMotherAlive = parentMotherAlive
        profile.parentMotherAgeAtDeath = parentMotherAgeAtDeath
        profile.parentFatherAlive = parentFatherAlive
        profile.parentFatherAgeAtDeath = parentFatherAgeAtDeath
        profile.perceivedStressScore = perceivedStressScore
        profile.lonelinessScore = lonelinessScore
        profile.primaryGoal = primaryGoal?.rawValue
        return profile
    }
}

/// Per-answer delta + caption for the reactive estimate. `years` is
/// signed — positive = estimate moved up (good news) — and caption is
/// the agency-framed "why" string shown beneath the running number.
struct AnswerDelta: Equatable {
    let years: Double
    let caption: String
}

/// Captured on the `priorAttempts` screen. Informs archetype sub-meters
/// and recovery-copy tone. Onboarding-only — not persisted to
/// `UserProfile`.
enum PriorAttempts: String, CaseIterable, Identifiable {
    case firstTime
    case triedDidntStick
    case triedBrieflyWorked

    var id: String { rawValue }

    var displayName: String {
        switch self {
        case .firstTime: return "First time"
        case .triedDidntStick: return "Tried before, didn't stick"
        case .triedBrieflyWorked: return "Tried before, briefly worked"
        }
    }
}
