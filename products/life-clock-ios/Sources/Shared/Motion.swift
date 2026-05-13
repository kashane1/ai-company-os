import SwiftUI

/// Shared motion vocabulary for Life Clock surfaces.
///
/// Single source of truth for animation durations and named curves.
/// Defined by [`docs/products/life-clock/motion-spec.md`](../../../docs/products/life-clock/motion-spec.md) —
/// changes here must be mirrored in the spec.
///
/// The three duration tiers are chosen to land on the
/// `premium-bar.md` § "Motion" rubric thresholds (100ms perception
/// floor / 250ms beat / 500ms breath) while matching distinct points
/// already in the shipped code. New animation sites pick a tier, not a
/// literal — the premium-readiness flag requires zero unresolved
/// `motion-incoherence` prompts, which the audit defines as ad-hoc
/// durations on the wrong tier.
///
/// Durations above `breath` (0.8s+) are narrative beats, not motion;
/// they must come through a vision-question review and stay literal at
/// the call site (e.g., `TodayView.wakeDuration = 1.0`,
/// `WrapUpSheet.animationDuration = 1.4 | 2.2`).
enum Motion {
    /// Duration tiers (binding — match motion-spec.md).
    enum Duration {
        /// ~180 ms. UI confirmation, sheet scroll-to, opacity-only
        /// state changes, selection ring lift, menu open/close.
        static let instant: TimeInterval = 0.18

        /// ~300 ms. Short transitions, card expansion, tab cross-fade,
        /// a value re-counting, reveal of a single element.
        static let beat: TimeInterval = 0.30

        /// ~600 ms. Large reveals, the reveal escalator's per-card
        /// sweep, trajectory chart redraw, life-grid dot fill.
        static let breath: TimeInterval = 0.60
    }

    /// Named curves (binding — match motion-spec.md).
    enum Curve {
        /// Default for opacity, fades, color.
        static let smooth: Animation = .smooth

        /// Spatial motion — anything with position, scale, or rotation.
        /// Springs feel like physical objects.
        static let spring: Animation = .interpolatingSpring()

        /// A spring that overshoots slightly — for celebratory
        /// affordances (purchase success, completion checkmarks,
        /// badge unlocks). Use sparingly.
        static let snappy: Animation = .snappy

        /// Slow-out / hold / slow-in. For once-per-session reveals
        /// (wake animation, reveal-escalator beats).
        static func breathing(duration: TimeInterval) -> Animation {
            .timingCurve(0.2, 0.8, 0.2, 1.0, duration: duration)
        }
    }
}
