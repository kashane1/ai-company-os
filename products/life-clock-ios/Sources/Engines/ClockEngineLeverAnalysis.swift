import Foundation

/// Extension to `ClockEngine` providing two onboarding-only analyses:
///
/// 1. `topLever(profile:)` — picks the single lifestyle lever that
///    contributes the largest negative pull to the user's projected
///    healthspan. Used by `ArchetypeRevealView` to confirm-or-surprise
///    the user's guess from the `leverGuess` screen, by
///    `RecoveryPreviewView` to choose which slider unlocks, and by the
///    paywall body to name the lever inline.
///
/// 2. `normalizedDriverPositions(profile:)` — returns a 0..1 position
///    for each lever, where 0 = worst (most negative) and 1 = best
///    (most positive). Used by `HealthspanRevealView` to render pinned
///    sliders showing where the user's answers actually landed.
///
/// **Why a separate file:** these are derived presentation helpers, not
/// engine-core arithmetic. They quote the same coefficients that
/// `lifestyleAdjustmentYears` uses but live outside that hot path so
/// the daily-delta code stays small and auditable.
extension ClockEngine {

    // MARK: - Top lever

    /// Pick the single `LifeClockLever` with the largest negative
    /// contribution to the user's projected healthspan. Ties are broken
    /// by the canonical lever order (sleep > movement > food > drinking
    /// > stressRecovery) — stable across launches, deterministic.
    ///
    /// Returns `.unanswered` when no lever scores meaningfully negative
    /// (i.e. the user is roughly balanced across every input) so the
    /// reveal copy can fall through to a neutral framing instead of
    /// inventing a "top lever" out of noise.
    func topLever(profile: UserProfile) -> LifeClockLever {
        let contributions = negativeContributions(profile: profile)
        guard let worst = contributions.max(by: { $0.magnitude < $1.magnitude }),
              worst.magnitude >= Self.topLeverThreshold
        else {
            return .unanswered
        }
        return worst.lever
    }

    /// Minimum magnitude (in lost years) a lever must contribute before
    /// we'll declare it "the top lever." Below this, every lever reads
    /// roughly even — calling one of them "your top lever" would be
    /// noise-fitting. 0.4 years lines up with the smallest non-trivial
    /// hit any single answer can produce in `lifestyleAdjustmentYears`
    /// (alcohol "weekly" = -0.5y).
    private static let topLeverThreshold: Double = 0.4

    /// All negative contributions for the levers we surface to the user.
    /// Positive contributions (e.g. "great" diet) are NOT included — the
    /// "top lever" frame is about what's pulling the clock down, not
    /// what's already helping. Tied directly to coefficients in
    /// `lifestyleAdjustmentYears`; if those shift, this must too.
    private func negativeContributions(profile: UserProfile)
        -> [(lever: LifeClockLever, magnitude: Double)]
    {
        var out: [(lever: LifeClockLever, magnitude: Double)] = []

        // Sleep — outside 7..9h range is a lever; in-range is neutral.
        let sleepHours = profile.sleepGoalHours
        if sleepHours > 0 {
            if sleepHours < 7.0 || sleepHours > 9.0 {
                // Sleep doesn't appear in lifestyleAdjustmentYears as a
                // negative — the engine only awards a +1.0y bonus for
                // in-range. We surface it here as a soft -1.0y lever
                // because the user perceives "5 hours" as a clear pull,
                // and zero penalty in the lever ranking would hide it.
                out.append((.sleep, 1.0))
            }
        }

        // Movement combines cardio + strength into one user-facing
        // lever ("movement"). Magnitudes sum, capped at the larger
        // single coefficient so a totally-sedentary user doesn't
        // double-count.
        var movementMagnitude = 0.0
        if profile.cardioMinsPerWeek == 0 { movementMagnitude += 1.0 }
        if profile.strengthFrequencyPerWeek < 2 {
            // Note: strength missing entirely is the worst bucket;
            // 0..1/wk both fall short of the +1.5y bonus the engine
            // would award. We surface that as a 0.5y "movement"
            // contribution so movement competes fairly with sleep.
            movementMagnitude += 0.5
        }
        if movementMagnitude > 0 {
            out.append((.movement, movementMagnitude))
        }

        // Food — only the "rough" bucket is a negative lever. "okay"
        // is the engine's neutral midpoint, "great" is positive.
        if profile.dietQualityBaseline.lowercased() == "rough" {
            out.append((.food, 1.5))
        }

        // Drinking — engine penalizes "heavy"/"daily" (-2.5) and
        // "frequent"/"weekly" (-0.5). Both surface as the same lever.
        switch profile.alcoholFrequency.lowercased() {
        case "heavy", "daily":
            out.append((.drinking, 2.5))
        case "frequent", "weekly":
            out.append((.drinking, 0.5))
        default:
            break
        }

        // Stress recovery — combines perceived stress + loneliness into
        // one user-facing lever. The two engine coefficients sum.
        var stressMagnitude = 0.0
        if let pss = profile.perceivedStressScore {
            switch pss {
            case 27...: stressMagnitude += 1.5
            case 14..<27: stressMagnitude += 0.5
            default: break
            }
        }
        if let ucla = profile.lonelinessScore, ucla >= 6 {
            stressMagnitude += 1.5
        }
        if stressMagnitude > 0 {
            out.append((.stressRecovery, stressMagnitude))
        }

        return out
    }

    // MARK: - Normalized driver positions

    /// 0..1 normalized position for every surfaced lever, where 0 is
    /// the worst answer the user could have given and 1 is the best.
    /// Missing answers return 0.5 (the neutral midpoint), so a user
    /// who skipped sensitive questions doesn't have those sliders
    /// pinned to either extreme.
    ///
    /// Used by `HealthspanRevealView` to render read-only sliders.
    func normalizedDriverPositions(profile: UserProfile) -> [LifeClockLever: Double] {
        [
            .sleep: sleepPosition(hours: profile.sleepGoalHours),
            .movement: movementPosition(
                cardioMinsPerWeek: profile.cardioMinsPerWeek,
                strengthPerWeek: profile.strengthFrequencyPerWeek
            ),
            .food: foodPosition(quality: profile.dietQualityBaseline),
            .drinking: drinkingPosition(frequency: profile.alcoholFrequency),
            .stressRecovery: stressRecoveryPosition(
                pss: profile.perceivedStressScore,
                ucla: profile.lonelinessScore
            ),
        ]
    }

    private func sleepPosition(hours: Double) -> Double {
        // Peak at 8h, falls off either side. 5h or 10h ⇒ ~0.0; 8h ⇒ 1.0.
        guard hours > 0 else { return 0.5 }
        let distanceFromIdeal = abs(hours - 8.0)
        let normalized = max(0.0, 1.0 - (distanceFromIdeal / 3.0))
        return normalized
    }

    private func movementPosition(cardioMinsPerWeek: Int, strengthPerWeek: Int) -> Double {
        // Cardio target: 150–300 min/wk. Strength target: ≥2/wk.
        // Combine on equal weight.
        let cardioScore: Double
        switch cardioMinsPerWeek {
        case 0: cardioScore = 0.0
        case 1..<150: cardioScore = 0.5
        case 150...300: cardioScore = 0.9
        default: cardioScore = 1.0
        }
        let strengthScore: Double
        switch strengthPerWeek {
        case 0: strengthScore = 0.0
        case 1: strengthScore = 0.5
        default: strengthScore = 1.0
        }
        return (cardioScore + strengthScore) / 2.0
    }

    private func foodPosition(quality: String) -> Double {
        switch quality.lowercased() {
        case "great": return 1.0
        case "okay": return 0.5
        case "rough": return 0.1
        default: return 0.5
        }
    }

    private func drinkingPosition(frequency: String) -> Double {
        switch frequency.lowercased() {
        case "none", "rare": return 1.0
        case "frequent", "weekly": return 0.5
        case "heavy", "daily": return 0.1
        default: return 0.5
        }
    }

    private func stressRecoveryPosition(pss: Int?, ucla: Int?) -> Double {
        // Two unrelated signals; average them after individual mapping.
        // PSS-10: 0..40, lower is better. UCLA-3: 3..9, lower is better.
        let stressScore: Double
        if let pss {
            switch pss {
            case 27...: stressScore = 0.1
            case 14..<27: stressScore = 0.5
            default: stressScore = 0.9
            }
        } else {
            stressScore = 0.5
        }
        let lonelinessScore: Double
        if let ucla {
            lonelinessScore = ucla >= 6 ? 0.2 : 0.8
        } else {
            lonelinessScore = 0.5
        }
        return (stressScore + lonelinessScore) / 2.0
    }
}
