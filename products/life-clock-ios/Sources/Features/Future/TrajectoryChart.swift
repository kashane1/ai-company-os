import SwiftUI
import Charts

/// Future tab trajectory chart. Renders 16 weeks back + 14 weeks
/// forward, anchored against a dashed baseline `RuleMark`.
///
/// V1.7.0 — plan §Phase 3. First SwiftUI Charts use in the repo.
/// The lighting convention (opacity 0.22, offset ratio 0.35/0.85,
/// radius ratio 0.55× of reference size — see
/// `LifeClockMascotView.swift:271-272`) is applied via the wrapping
/// container's shadow. Defer shared `Lighting.swift` extraction to a
/// follow-up — third call site materializes here, which is the DRY
/// trigger.
///
/// Sparse-data rendering: line segment opacity scales with the
/// per-point `confidence`. Past points fade toward 0.4, future points
/// fade similarly. Cap-near compression: when current projection sits
/// within 2y of cap, the Y-domain clamps tight and we surface a
/// neutral annotation.
struct TrajectoryChart: View {
    let points: [TrajectoryPoint]
    let baseline: Double
    let clampState: HealthspanEngine.Projection.ClampState
    /// V1.7.0 Phase 4 perf gate: when true, `.animation` is `nil`.
    /// Animating an already-smooth slider input is wasted GPU and
    /// burns the 120Hz frame budget. Restored on scrub-end.
    let isScrubbing: Bool

    /// 2026-05-12 polish: under Reduce Motion the snap-back animation
    /// is also `nil` (was previously running unconditionally on
    /// scrub-end). The mid-scrub path was already `nil` via
    /// `isScrubbing`, but the 180ms `.smooth` on touch-up violated
    /// the user's AX preference. See polish-2026-05-12-whatif-slider-
    /// scrub-feel.md.
    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    init(
        points: [TrajectoryPoint],
        baseline: Double,
        clampState: HealthspanEngine.Projection.ClampState,
        isScrubbing: Bool = false
    ) {
        self.points = points
        self.baseline = baseline
        self.clampState = clampState
        self.isScrubbing = isScrubbing
    }

    private static let chartHeight: CGFloat = 220

    var body: some View {
        VStack(alignment: .leading, spacing: DesignTokens.Spacing.xs) {
            chart
                .frame(height: Self.chartHeight)
                .padding(DesignTokens.Spacing.md)
                .background(
                    DesignTokens.Palette.elevated,
                    in: RoundedRectangle(cornerRadius: DesignTokens.Radius.md)
                )
                // Lighting convention via shared modifier. Non-rotating
                // surface; constants live in Sources/Shared/Lighting.swift.
                .lightingDepth(referenceSize: Self.chartHeight)

            if case .cappedAt = clampState {
                Text(FutureNeutralCopy.capReached)
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .accessibilityIdentifier("future.chart.capReached")
            } else if case .flooredAt = clampState {
                Text(FutureNeutralCopy.floorReached)
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .accessibilityIdentifier("future.chart.floorReached")
            } else if case .nearCap = clampState {
                Text(FutureNeutralCopy.nearCapCompression)
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .accessibilityIdentifier("future.chart.nearCap")
            }
        }
    }

    @ViewBuilder
    private var chart: some View {
        Chart {
            // Area fill, monotone interpolation (honest — no
            // overshooting data).
            ForEach(points) { point in
                AreaMark(
                    x: .value("Week", point.week),
                    y: .value("Years", point.years)
                )
                .interpolationMethod(.monotone)
                .foregroundStyle(
                    LinearGradient(
                        colors: [
                            Color.accentColor.opacity(0.35 * point.confidence),
                            Color.accentColor.opacity(0.05 * point.confidence),
                        ],
                        startPoint: .top,
                        endPoint: .bottom
                    )
                )
            }
            ForEach(points) { point in
                LineMark(
                    x: .value("Week", point.week),
                    y: .value("Years", point.years)
                )
                .interpolationMethod(.monotone)
                .lineStyle(StrokeStyle(lineWidth: 2))
                .foregroundStyle(Color.accentColor.opacity(point.confidence))
            }
            // Dashed baseline reference.
            RuleMark(y: .value("Baseline", baseline))
                .lineStyle(StrokeStyle(lineWidth: 1, dash: [4]))
                .foregroundStyle(.secondary)
                .annotation(position: .topLeading, alignment: .leading, spacing: 4) {
                    Text("baseline")
                        .font(.caption2)
                        .foregroundStyle(.secondary)
                }
        }
        .chartYScale(domain: yDomain)
        .animation(
            (isScrubbing || reduceMotion) ? nil : .smooth(duration: 0.18),
            value: points
        )
        .accessibilityIdentifier("future.trajectory.chart")
        .accessibilityLabel(accessibilityLabel)
    }

    /// Y-domain compression near cap (P1 review finding #8.2): when
    /// projection is within ~2y of cap, clamp Y range to keep the
    /// visual movement legible even on age-80-all-max scenarios.
    private var yDomain: ClosedRange<Double> {
        let years = points.map(\.years)
        let minY = years.min() ?? baseline
        let maxY = years.max() ?? baseline
        if case .nearCap = clampState {
            return (maxY - 5)...maxY
        }
        // Default: 2y padding either side.
        return (min(minY, baseline) - 1)...(max(maxY, baseline) + 1)
    }

    private var accessibilityLabel: String {
        let currentYears = points.first(where: { $0.week == 0 })?.years ?? baseline
        let formattedBaseline = String(format: "%.0f", baseline)
        let formattedCurrent = String(format: "%.1f", currentYears)
        return "Projected healthspan trajectory. Baseline \(formattedBaseline) years. Current \(formattedCurrent) years."
    }
}
