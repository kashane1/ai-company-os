import Foundation

/// Maps store-level intents to user-facing `SupportMoment` copy.
///
/// `LifeClockStore` used to construct `SupportMoment` literals at six
/// mutation sites; copy lived in the same file as persistence and engine
/// orchestration. This presenter centralizes all UX prose for support
/// moments so the store stops branching on display strings, and so copy
/// (or future tone-aware copy) is testable without a `ModelContainer`.
///
/// Stateless and value-typed — safe to instantiate on the main actor or
/// hand to tests.
struct SupportMomentPresenter {
    enum Intent {
        case onboardingComplete
        case questCompleted(rewardMinutes: Int)
        case questUndone
        /// Emitted after `setTodayHabits(_:)` saves. The presenter picks
        /// among four states based on the inputs: a positive delta wins,
        /// then a strength-training log, then a "check-in updated" state
        /// for re-saves, otherwise a calm "check-in saved" first-time
        /// state.
        case checkInSaved(deltaMinutes: Int, strengthLogged: Bool, hadPriorCheckIn: Bool)
        case reset
    }

    func moment(for intent: Intent) -> SupportMoment? {
        switch intent {
        case .onboardingComplete:
            return SupportMoment(
                title: "You're set.",
                detail: "We'll help you notice which daily choices support your health most.",
                tone: .calm
            )

        case let .questCompleted(rewardMinutes):
            return SupportMoment(
                title: "Nice work.",
                detail: "Added to your progress log. Possible impact: \(TimeDeltaFormatter.format(minutes: rewardMinutes)).",
                tone: .celebration
            )

        case .questUndone:
            return SupportMoment(
                title: "Action removed.",
                detail: "Today's plan is updated.",
                tone: .calm
            )

        case let .checkInSaved(delta, strength, hadPrior):
            if delta > 0 {
                return SupportMoment(
                    title: "Nice work.",
                    detail: "Your check-in moved today's progress by \(TimeDeltaFormatter.format(minutes: delta)).",
                    tone: .celebration
                )
            }
            if strength {
                return SupportMoment(
                    title: "Strength training logged.",
                    detail: "Saved to today's progress log. Small wins compound over time.",
                    tone: .celebration
                )
            }
            if hadPrior {
                return SupportMoment(
                    title: "Check-in updated.",
                    detail: "You're building a clearer picture of what supports you.",
                    tone: .calm
                )
            }
            return SupportMoment(
                title: "Check-in saved.",
                detail: "You're building a clearer picture of what supports you.",
                tone: .calm
            )

        case .reset:
            return nil
        }
    }
}
