import SwiftUI

/// Brand motion primitive: a clock minute hand that sweeps from 12:00 to a
/// signed final angle in one calm ease-out. Clockwise for positive deltas,
/// counterclockwise for negative. Visual sweep is capped at ±720° so very
/// large deltas don't spin forever; the numeric readout next to the clock
/// is the source of truth.
///
/// Honors Reduce Motion: replaces rotation with a 250ms cross-fade between
/// 12:00 and the final-angle frame.
///
/// First animation in the codebase. Pinned to `withAnimation` +
/// `.rotationEffect`; deliberately NOT `TimelineView` (continuous) or
/// `Canvas` (overkill) per the deepening pass.
struct ClockHandView: View {
    let signedMinutes: Int
    let duration: Double  // 1.4s daily, 2.2s weekly per spec
    let haptic: SensoryFeedback
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @State private var rotated = false

    /// Cap visual sweep at ±720° regardless of underlying minute count.
    private static let maxSweepDegrees: Double = 720

    private var finalAngle: Angle {
        // Map each minute to 6° (one full rotation = 60 minutes), capped.
        let raw = Double(signedMinutes) * 6
        let clamped = max(-Self.maxSweepDegrees, min(Self.maxSweepDegrees, raw))
        return .degrees(clamped)
    }

    var body: some View {
        ZStack {
            // Static clock face.
            Circle()
                .stroke(DesignTokens.Palette.elevated, lineWidth: 6)
            ForEach(0..<12, id: \.self) { hour in
                Rectangle()
                    .fill(DesignTokens.Palette.elevated)
                    .frame(width: hour % 3 == 0 ? 3 : 1, height: hour % 3 == 0 ? 12 : 6)
                    .offset(y: -78)
                    .rotationEffect(.degrees(Double(hour) * 30))
            }
            // The hand.
            Capsule()
                .fill(handColor)
                .frame(width: 4, height: 64)
                .offset(y: -32)
                .rotationEffect(rotated ? finalAngle : .degrees(0))
                .opacity(reduceMotion ? (rotated ? 1 : 0.2) : 1)
            // Center pivot.
            Circle()
                .fill(handColor)
                .frame(width: 10, height: 10)
        }
        .frame(width: 180, height: 180)
        .accessibilityElement()
        .accessibilityLabel("Clock showing \(accessibleDelta)")
        .sensoryFeedback(haptic, trigger: rotated)
        .onAppear { animate() }
    }

    private var handColor: Color {
        if signedMinutes == 0 { return DesignTokens.Palette.elevated }
        return signedMinutes > 0
            ? DesignTokens.Palette.positive
            : DesignTokens.Palette.negative
    }

    private var accessibleDelta: String {
        let sign = signedMinutes >= 0 ? "plus" : "minus"
        return "\(sign) \(abs(signedMinutes)) minutes"
    }

    private func animate() {
        guard !rotated else { return }
        if reduceMotion {
            withAnimation(.easeInOut(duration: Motion.Duration.beat)) { rotated = true }
            return
        }
        if signedMinutes == 0 {
            // No rotation; brief pulse only via opacity in `body`.
            rotated = true
            return
        }
        // `duration` is a narrative beat (1.4s yesterday / 2.2s weekly per
        // wrap-up-spec.md) — above the breath tier on purpose. The curve
        // is canonical, the duration is content.
        withAnimation(Motion.Curve.breathing(duration: duration)) {
            rotated = true
        }
    }
}
