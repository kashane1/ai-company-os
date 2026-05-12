import SwiftUI

/// Central policy for Life Clock's tactile language.
///
/// Keep this small and boring: haptics should underline agency and confirmation,
/// not become a second emotional voice competing with tone copy.
///
/// **WhatIfSlider scrub policy (V1.7.0 Phase 4 follow-up, 2026-05-12).**
/// Three events, edge-triggered — never per-tick. Per-tick `.selection`
/// (the conventional continuous-slider pattern) was rejected: it fires
/// tens of times per second during a scrub, which is exactly the
/// "second emotional voice" this file's doctrine forbids.
///   * `whatIfScrubBegin` — `.impact(.light)` on touch-down. Mirrors
///     `morningWake`/`firstReveal` weight: signals agency, fires once
///     per touch. Multi-touch is fine — each finger gets its own
///     "agency begins."
///   * `whatIfScrubEdge` — `.impact(.medium)` when the value crosses
///     into its row's `range` lower or upper bound. Edge-trigger only
///     (one tap per landing, not per snapped tick). The visual barely
///     conveys "you hit the rail" because the thumb is already at the
///     same coordinate it was approaching; haptic carries the info.
///   * `whatIfScrubEnd` — `.selection` on touch-up. Soft release;
///     matches `wrapUp(zero)` semantics ("end of an act, no judgment").
///     Lands before the snap-back animation, which is itself Reduce-
///     Motion–gated.
enum LifeClockHaptics {
    static let morningWake: SensoryFeedback = .impact(weight: .light)
    static let firstReveal: SensoryFeedback = .impact(weight: .light)
    static let monthlyMilestone: SensoryFeedback = .success
    static let purchaseSuccess: SensoryFeedback = .success
    static let questCompletion: SensoryFeedback = .success

    static let whatIfScrubBegin: SensoryFeedback = .impact(weight: .light)
    static let whatIfScrubEdge: SensoryFeedback = .impact(weight: .medium)
    static let whatIfScrubEnd: SensoryFeedback = .selection

    static func wrapUp(signedMinutes: Int) -> SensoryFeedback {
        if signedMinutes > 0 { return .success }
        if signedMinutes < 0 { return .impact(weight: .light) }
        return .selection
    }
}
