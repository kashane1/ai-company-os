import Foundation

/// User-visible reinforcement card emitted from `LifeClockStore` after
/// onboarding completion, daily check-in, plan-action completion, etc.
///
/// The `Tone` enum was reviewed for collapse to `Bool isCelebration`
/// during Phase 3.B sweep. Decision: keep the enum. Two named cases
/// (`celebration` vs `calm`) read more clearly at call sites and
/// inside `SupportMomentToast`'s icon/tint switch than a boolean would,
/// and a future third tone (e.g. a milestone celebration distinct from
/// per-action celebration) would be additive rather than a Bool→enum
/// rewrite.
struct SupportMoment: Equatable {
    enum Tone {
        case calm
        case celebration
    }

    let title: String
    let detail: String
    let tone: Tone
}
