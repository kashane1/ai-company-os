import SwiftUI

/// The animated Life Clock mascot. Brand focal point of the app.
///
/// Drawn entirely in SwiftUI so the hands are real layers we can rotate;
/// the heartbeat is a `Path` we own. Hour and minute hands rotate from a
/// 12:00 baseline by `minutesDelta` minutes (1 minute = 6° on the minute
/// hand, 0.5° on the hour hand — the same convention as
/// `ClockHandView.swift:25-28` in WrapUp). Visual sweep is clamped at
/// ±720°; the numeric readout adjacent to the mascot is the source of
/// truth past the cap.
///
/// **Why TimelineView, not `withAnimation`:** the heartbeat is a continuous,
/// always-running pulse — `ClockHandView` deliberately rejects `TimelineView`
/// for its one-shot hand sweep, but this is the opposite case (continuous
/// state, redrawn per tick) where TimelineView is exactly right. Schedule
/// branches at the view itself (`@ViewBuilder` if/else on
/// `reduceMotion || !isVisible`) because `.animation(...)` and `.explicit(...)`
/// return different concrete `TimelineSchedule` types — they can't unify
/// behind a single `let schedule:` binding.
///
/// **Heartbeat color exception:** the ECG line uses
/// `LifeClockPalette.heartbeatRed`, the documented exception to the
/// orange-not-red invariant in `LifeClockPalette.swift:1-5`. Direction
/// (gain vs. loss) is conveyed by hand motion, not color.
///
/// **Reduce Motion:** hands snap (no spring), heartbeat schedule swaps
/// to `.explicit([.distantFuture])` so the line stays drawn at
/// mid-amplitude (NOT a flatline — flatline reads as "dead", wrong
/// metaphor for a life clock), no center-hub pulse.
///
/// **Visibility gating:** `TimelineView(.animation)` does NOT auto-pause
/// when scrolled offscreen inside a `ScrollView`. Today's hero uses an
/// `.onGeometryChange` (iOS 17) frame-intersection check to drive
/// `isVisible`; onboarding lead-ins (full-screen, no scroll) use
/// `.onAppear` / `.onDisappear`.
struct LifeClockMascotView: View {
    /// Minutes gained (+) or lost (−) relative to baseline.
    /// `0` means at-baseline. If the call site has no estimate yet,
    /// it should not render the mascot at all (gate at the call site).
    let minutesDelta: Int

    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @State private var isVisible: Bool = true

    // MARK: - Constants

    /// Heartbeat redraw rate. 30Hz is visually indistinguishable from 60Hz
    /// for a heartbeat pulse and halves the per-tick CPU work.
    private static let heartbeatHz: Double = 30

    /// Visual sweep cap on the minute hand input. Equivalent to
    /// ±720° given the 6°/min mapping below — matches
    /// `ClockHandView.maxSweepDegrees` (`Sources/Features/WrapUp/ClockHandView.swift:22`).
    /// The numeric readout adjacent to the mascot is the source of truth past the cap.
    private static let maxMinutesDelta: Int = 120

    /// Each minute on the input maps to this many degrees of minute-hand
    /// rotation. Same convention as `ClockHandView.swift:25-28`.
    private static let degreesPerMinute: Double = 6

    /// Hub scale modulation range during a heartbeat pulse.
    private static let hubPulseRange: ClosedRange<CGFloat> = 1.0...1.12

    // MARK: - Derived angles

    private var clampedMinutes: Int {
        min(max(minutesDelta, -Self.maxMinutesDelta), Self.maxMinutesDelta)
    }

    private var minuteAngle: Angle {
        .degrees(Double(clampedMinutes) * Self.degreesPerMinute)
    }

    private var hourAngle: Angle {
        .degrees(Double(clampedMinutes) * (Self.degreesPerMinute / 12.0))
    }

    // MARK: - Body

    var body: some View {
        GeometryReader { geo in
            let size = min(geo.size.width, geo.size.height)
            ZStack {
                bezel(size: size)
                tickMarks(size: size)
                heartbeat(size: size)
                hand(length: size * 0.30, thickness: size * 0.04, angle: hourAngle)
                hand(length: size * 0.40, thickness: size * 0.03, angle: minuteAngle)
                centerHub(size: size)
            }
            .frame(width: size, height: size)
            .frame(maxWidth: .infinity, maxHeight: .infinity)
        }
        .aspectRatio(1, contentMode: .fit)
        .animation(reduceMotion ? nil : .interpolatingSpring(), value: minutesDelta)
        .onAppear { isVisible = true }
        .onDisappear { isVisible = false }
        // Note: `TimelineView(.animation)` pauses on backgrounding via the
        // system's scenePhase signal, so we don't need an explicit
        // `.onChange(of: scenePhase)` toggle. `isVisible` only handles the
        // appear/disappear case (e.g., scrolled offscreen on Today).
        .accessibilityElement(children: .ignore)
        .accessibilityLabel("Life clock")
        .accessibilityValue(TimeDeltaFormatter.format(minutes: minutesDelta))
        .accessibilityAddTraits(.updatesFrequently)
    }

    // MARK: - Layers

    private func bezel(size: CGFloat) -> some View {
        ZStack {
            Circle()
                .fill(Color(.systemBackground))
                .shadow(color: .black.opacity(0.10), radius: size * 0.04, x: 0, y: size * 0.012)
            Circle()
                .strokeBorder(
                    AngularGradient(
                        colors: [
                            .blue.opacity(0.85),
                            .blue.opacity(0.55),
                            LifeClockPalette.heartbeatRed.opacity(0.55),
                            LifeClockPalette.heartbeatRed.opacity(0.85),
                            LifeClockPalette.heartbeatRed.opacity(0.55),
                            .blue.opacity(0.55),
                            .blue.opacity(0.85)
                        ],
                        center: .center,
                        startAngle: .degrees(180),
                        endAngle: .degrees(540)
                    ),
                    lineWidth: size * 0.018
                )
                .padding(size * 0.02)
        }
    }

    private func tickMarks(size: CGFloat) -> some View {
        ZStack {
            ForEach(0..<60, id: \.self) { i in
                let isMajor = i % 5 == 0
                let leftHalf = i > 30 || i == 0
                let color: Color = leftHalf ? .blue : LifeClockPalette.heartbeatRed
                Capsule()
                    .fill(color.opacity(isMajor ? 0.85 : 0.30))
                    .frame(
                        width: isMajor ? size * 0.012 : size * 0.005,
                        height: isMajor ? size * 0.05 : size * 0.022
                    )
                    .offset(y: -size * 0.42)
                    .rotationEffect(.degrees(Double(i) * 6))
            }
        }
    }

    /// The ECG line is static — no phase animation today, the silhouette
    /// IS the brand mark. Reduce-motion and visibility don't change its
    /// appearance, so no TimelineView needed here. (Pulse motion lives on
    /// the center hub.)
    private func heartbeat(size: CGFloat) -> some View {
        HeartbeatLine()
            .stroke(
                LifeClockPalette.heartbeatRed,
                style: StrokeStyle(lineWidth: size * 0.012, lineCap: .round, lineJoin: .round)
            )
            .frame(width: size * 0.78, height: size * 0.18)
            .opacity(0.95)
    }

    private func hand(length: CGFloat, thickness: CGFloat, angle: Angle) -> some View {
        // `Color.primary` auto-adapts: dark in light mode, light in dark mode.
        // Solves the white-on-white invisibility against the SwiftUI-drawn
        // light face. When the designer-produced bezel ships (asset slot),
        // the hand color may need to be revisited per the new artwork.
        Capsule()
            .fill(Color.primary)
            .shadow(color: .black.opacity(0.18), radius: thickness * 0.5, x: 0, y: thickness * 0.2)
            .frame(width: thickness, height: length)
            .offset(y: -length / 2)
            .rotationEffect(angle)
    }

    @ViewBuilder
    private func centerHub(size: CGFloat) -> some View {
        let hubSize = size * 0.07
        let frozen = reduceMotion || !isVisible
        if frozen {
            Circle()
                .fill(LifeClockPalette.heartbeatRed)
                .frame(width: hubSize, height: hubSize)
        } else {
            TimelineView(.animation(minimumInterval: 1.0 / Self.heartbeatHz)) { ctx in
                Circle()
                    .fill(LifeClockPalette.heartbeatRed)
                    .frame(width: hubSize, height: hubSize)
                    .scaleEffect(hubScale(at: ctx.date))
            }
        }
    }

    // MARK: - Phase math

    /// Sine-driven scale on the center hub at ~1Hz (60bpm), mapped into
    /// `hubPulseRange`. The line stays static; only the hub pulses.
    private func hubScale(at date: Date) -> CGFloat {
        let phase = date.timeIntervalSinceReferenceDate.truncatingRemainder(dividingBy: 1.0)
        let wave = (sin(phase * 2 * .pi) + 1) / 2
        let lo = Self.hubPulseRange.lowerBound
        let hi = Self.hubPulseRange.upperBound
        return lo + (hi - lo) * CGFloat(wave)
    }
}

// MARK: - HeartbeatLine

/// ECG-style polyline. Static — the silhouette IS the brand mark; pulse
/// motion lives on the center hub.
private struct HeartbeatLine: Shape {
    func path(in rect: CGRect) -> Path {
        var p = Path()
        let w = rect.width
        let h = rect.height
        // Normalized control points: (x in 0…1, y in 0…1, where 0.5 is mid-line).
        // Two ECG complexes mirrored across the center.
        let pts: [(CGFloat, CGFloat)] = [
            (0.00, 0.50),
            (0.18, 0.50),
            (0.22, 0.42),
            (0.26, 0.58),
            (0.30, 0.20),
            (0.34, 0.85),
            (0.38, 0.50),
            (0.50, 0.50),
            (0.62, 0.50),
            (0.66, 0.20),
            (0.70, 0.85),
            (0.74, 0.42),
            (0.78, 0.58),
            (0.82, 0.50),
            (1.00, 0.50)
        ]
        let first = pts[0]
        p.move(to: CGPoint(x: first.0 * w, y: first.1 * h))
        for (fx, fy) in pts.dropFirst() {
            p.addLine(to: CGPoint(x: fx * w, y: fy * h))
        }
        return p
    }
}

// MARK: - Previews

#if DEBUG
#Preview("Baseline") {
    LifeClockMascotView(minutesDelta: 0)
        .frame(width: 240, height: 240)
        .padding()
}

#Preview("+30 minutes") {
    LifeClockMascotView(minutesDelta: 30)
        .frame(width: 240, height: 240)
        .padding()
}

#Preview("−30 minutes") {
    LifeClockMascotView(minutesDelta: -30)
        .frame(width: 240, height: 240)
        .padding()
}

// Reduce-Motion preview is omitted — `\.accessibilityReduceMotion` is a
// read-only EnvironmentValues key that can't be set from preview code.
// Toggle "Differentiate Without Color → Reduce Motion" in the simulator's
// Accessibility settings to verify the reduce-motion path on device.

#Preview("Clamp (+1440 → +720°)") {
    LifeClockMascotView(minutesDelta: 1440)
        .frame(width: 240, height: 240)
        .padding()
}
#endif
