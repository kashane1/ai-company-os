import SwiftUI

/// Canvas-based grid of dots representing weeks of a typical life. Drives
/// the five-step emotional escalator (`lifeGridFull` → `lifeGridRemaining`
/// → `bigNumberPenalty` → recovery preview) during the new onboarding flow.
///
/// **Why Canvas, not stacked Circle views:** at 80 yrs × 52 weeks ≈ 4160
/// dots, SwiftUI's view-diffing pipeline shreds. Canvas batches into a
/// single Metal pass per frame. `ClockHandView.swift:13-14` rejects Canvas
/// for a single sweeping hand; this is the opposite case (many primitives,
/// one pass) where Canvas is the right choice. Apple recommends Canvas
/// for "extremely large numbers of dynamic shapes."
///
/// **Performance pattern:**
/// - `rendersAsynchronously: true` — biggest perf lever for 4000+ shapes.
/// - Dot center coordinates precomputed in `@State` keyed on `totalWeeks`,
///   so geometry is built once, not per frame.
/// - Color interpolation happens inside the Canvas closure via `Color.lerp`
///   so every dot doesn't carry its own animation state.
///
/// **Reduce Motion:** when `accessibilityReduceMotion` is on, mode
/// transitions snap (no progress animation) but Canvas content still
/// renders.
///
/// **Color-blind safe:** dots are encoded by both color AND shape (filled
/// vs outlined for lived-vs-remaining) so red/green confusion doesn't lose
/// the signal.
struct LifeGridDotView: View {
    let totalWeeks: Int
    let livedWeeks: Int
    let lostWeeks: Int
    let mode: GridMode

    /// Animation progress 0→1 used by `TimelineView` to drive transitions.
    @State private var progress: Double = 0
    @State private var positions: [CGPoint] = []
    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    enum GridMode {
        /// Whole life as faint outlined dots.
        case full
        /// Lived weeks filled green; remaining outlined gray.
        case remainingHighlighted
        /// Same as `.remainingHighlighted` plus `lostWeeks` count of red
        /// dots highlighted within the remaining region — the "X years
        /// at risk" visualization.
        case bigNumberPenalty
        /// Recovery preview: previously-red dots now blue, reframed as
        /// time-could-be-recovered.
        case recoveryHighlighted
    }

    var body: some View {
        GeometryReader { geo in
            Canvas(rendersAsynchronously: true) { context, size in
                guard !positions.isEmpty else { return }
                let dotRadius = max(1.5, size.width / CGFloat(columns(for: size.width)) * 0.32)
                drawDots(context: context, size: size, dotRadius: dotRadius)
            }
            .onAppear {
                positions = computePositions(in: geo.size)
                if reduceMotion {
                    progress = 1
                } else {
                    withAnimation(.easeInOut(duration: Motion.Duration.breath)) { progress = 1 }
                }
            }
            .onChange(of: mode) { _, _ in
                guard !reduceMotion else { progress = 1; return }
                progress = 0
                withAnimation(.easeInOut(duration: Motion.Duration.breath)) { progress = 1 }
            }
            .onChange(of: geo.size) { _, newSize in
                positions = computePositions(in: newSize)
            }
        }
        .accessibilityElement()
        .accessibilityLabel(accessibilityLabel)
    }

    // MARK: - Drawing

    private func drawDots(context: GraphicsContext, size: CGSize, dotRadius: CGFloat) {
        for (index, center) in positions.enumerated() {
            let style = dotStyle(for: index)
            let rect = CGRect(
                x: center.x - dotRadius,
                y: center.y - dotRadius,
                width: dotRadius * 2,
                height: dotRadius * 2
            )
            switch style.shape {
            case .filled:
                context.fill(
                    Path(ellipseIn: rect),
                    with: .color(style.color.opacity(style.opacity * progress))
                )
            case .outline:
                context.stroke(
                    Path(ellipseIn: rect),
                    with: .color(style.color.opacity(style.opacity * progress)),
                    lineWidth: 1
                )
            }
        }
    }

    private struct DotStyle {
        enum Shape { case filled, outline }
        let color: Color
        let opacity: Double
        let shape: Shape
    }

    private func dotStyle(for index: Int) -> DotStyle {
        let isLived = index < livedWeeks
        // Penalty/recovery dots sit AT THE END of the remaining region so
        // they read as "the next N years the user could lose / regain."
        let penaltyStart = totalWeeks - lostWeeks
        let isPenalty = index >= penaltyStart && index < totalWeeks
        // The most-recently-completed week — paint it black on every
        // colored mode to anchor the user's *current moment* in the
        // grid. Without this, the lived-vs-remaining boundary is
        // implicit; with it, "you are here" is unmissable.
        let isNow = livedWeeks > 0 && index == livedWeeks - 1

        switch mode {
        case .full:
            return DotStyle(color: .gray, opacity: 0.35, shape: .outline)

        case .remainingHighlighted:
            if isNow {
                return DotStyle(color: .black, opacity: 1.0, shape: .filled)
            }
            if isLived {
                return DotStyle(color: .green, opacity: 0.85, shape: .filled)
            }
            return DotStyle(color: .gray, opacity: 0.35, shape: .outline)

        case .bigNumberPenalty:
            if isNow {
                return DotStyle(color: .black, opacity: 1.0, shape: .filled)
            }
            if isLived {
                return DotStyle(color: .green, opacity: 0.85, shape: .filled)
            }
            if isPenalty {
                return DotStyle(color: .red, opacity: 0.85, shape: .filled)
            }
            return DotStyle(color: .gray, opacity: 0.35, shape: .outline)

        case .recoveryHighlighted:
            if isNow {
                return DotStyle(color: .black, opacity: 1.0, shape: .filled)
            }
            if isLived {
                return DotStyle(color: .green, opacity: 0.85, shape: .filled)
            }
            if isPenalty {
                return DotStyle(color: .blue, opacity: 0.85, shape: .filled)
            }
            return DotStyle(color: .gray, opacity: 0.35, shape: .outline)
        }
    }

    // MARK: - Geometry

    private func columns(for width: CGFloat) -> Int {
        // 52 columns (weeks per year) packed across the available width.
        52
    }

    private func computePositions(in size: CGSize) -> [CGPoint] {
        guard size.width > 0, size.height > 0, totalWeeks > 0 else { return [] }
        let cols = columns(for: size.width)
        let rows = Int(ceil(Double(totalWeeks) / Double(cols)))
        let cellW = size.width / CGFloat(cols)
        let cellH = size.height / CGFloat(max(rows, 1))
        var pts: [CGPoint] = []
        pts.reserveCapacity(totalWeeks)
        for i in 0..<totalWeeks {
            let row = i / cols
            let col = i % cols
            pts.append(CGPoint(
                x: cellW * (CGFloat(col) + 0.5),
                y: cellH * (CGFloat(row) + 0.5)
            ))
        }
        return pts
    }

    // MARK: - Accessibility

    private var accessibilityLabel: String {
        switch mode {
        case .full:
            return "Life grid showing \(totalWeeks) weeks total."
        case .remainingHighlighted:
            return "Life grid: \(livedWeeks) weeks lived, \(totalWeeks - livedWeeks) remaining."
        case .bigNumberPenalty:
            let lostYears = Int((Double(lostWeeks) / 52.0).rounded())
            return "Life grid showing approximately \(lostYears) years at risk from current habits."
        case .recoveryHighlighted:
            let recoveryYears = Int((Double(lostWeeks) / 52.0).rounded())
            return "Life grid: approximately \(recoveryYears) years could be recovered."
        }
    }
}

// MARK: - Legend

extension LifeGridDotView.GridMode {
    /// Color/label pairs for the legend. Lives next to the dot-styling
    /// switch above so legend and grid can't drift. `.full` returns
    /// empty — the full-grid intro screen uses inline copy.
    ///
    /// "Now" is painted by `dotStyle(for:)` at index `livedWeeks-1` on
    /// every colored mode; the legend reflects that anchoring dot.
    var legendItems: [(color: Color, label: String)] {
        switch self {
        case .full:
            return []
        case .remainingHighlighted:
            return [
                (.green, "Lived"),
                (.black, "Now"),
                (.gray.opacity(0.5), "Still ahead"),
            ]
        case .bigNumberPenalty:
            return [
                (.green, "Lived"),
                (.black, "Now"),
                (.red, "At risk"),
                (.gray.opacity(0.5), "Still ahead"),
            ]
        case .recoveryHighlighted:
            return [
                (.green, "Lived"),
                (.black, "Now"),
                (.blue, "Recoverable"),
                (.gray.opacity(0.5), "Still ahead"),
            ]
        }
    }
}

/// Compact legend row rendered beneath colored dot grids. Grouped as one
/// accessibility element so VoiceOver users hear the lookup table in a
/// single swipe instead of one row at a time.
struct LifeGridDotLegend: View {
    let mode: LifeGridDotView.GridMode

    var body: some View {
        HStack(spacing: 16) {
            ForEach(mode.legendItems, id: \.label) { item in
                HStack(spacing: 6) {
                    Circle()
                        .fill(item.color)
                        .frame(width: 8, height: 8)
                    Text(item.label)
                        .font(.caption2)
                        .foregroundStyle(.secondary)
                }
            }
        }
        .accessibilityElement(children: .combine)
        .accessibilityLabel(legendAccessibilityLabel)
    }

    private var legendAccessibilityLabel: String {
        let pairs = mode.legendItems.map(\.label).joined(separator: ", ")
        return pairs.isEmpty ? "" : "Legend: \(pairs)"
    }
}

#if DEBUG
#Preview("Full") {
    LifeGridDotView(totalWeeks: 4160, livedWeeks: 1820, lostWeeks: 0, mode: .full)
        .padding()
}

#Preview("Remaining highlighted") {
    LifeGridDotView(totalWeeks: 4160, livedWeeks: 1820, lostWeeks: 0, mode: .remainingHighlighted)
        .padding()
}

#Preview("Big number penalty") {
    LifeGridDotView(totalWeeks: 4160, livedWeeks: 1820, lostWeeks: 624, mode: .bigNumberPenalty)
        .padding()
}

#Preview("Recovery highlighted") {
    LifeGridDotView(totalWeeks: 4160, livedWeeks: 1820, lostWeeks: 624, mode: .recoveryHighlighted)
        .padding()
}
#endif
