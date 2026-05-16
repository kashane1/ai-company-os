import SwiftUI
import Charts
import Accessibility

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

    /// 2026-05-12 polish: at AX content sizes the `topLeading`
    /// "baseline" annotation overflows the chart's plot area (it
    /// anchors at the leftmost data mark and extends further left,
    /// which gets clipped by the container's padding at XXL). The
    /// dashed RuleMark + Y-axis tick at the baseline value already
    /// convey the same info visually; the AX descriptor names the
    /// baseline number explicitly in its summary. So at AX sizes we
    /// drop the text annotation rather than fight the layout. See
    /// polish-2026-05-12-trajectory-chart-a11y-colorblind-xxl.md.
    @Environment(\.dynamicTypeSize) private var dynamicTypeSize

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
                    if !dynamicTypeSize.isAccessibilitySize {
                        Text("baseline")
                            .font(.caption2)
                            .foregroundStyle(.secondary)
                    }
                }
        }
        .chartYScale(domain: yDomain)
        .animation(
            (isScrubbing || reduceMotion) ? nil : .smooth(duration: Motion.Duration.instant),
            value: points
        )
        .accessibilityIdentifier("future.trajectory.chart")
        .accessibilityLabel(accessibilityLabel)
        .accessibilityChartDescriptor(self)
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

    /// One-breath VoiceOver announce. Reads in ~3 seconds: what the
    /// chart shows, where the user is today, and which way the line
    /// runs. Adaptive to clamp state — when the projection is pinned
    /// at the cap/floor we say so, because "gains 0 years" reads
    /// wrong when the engine actively capped a larger gain.
    private var accessibilityLabel: String {
        "Healthspan trajectory chart. \(summarySentence)"
    }

    private var summarySentence: String {
        let currentYears = points.first(where: { $0.week == 0 })?.years ?? baseline
        let delta = currentYears - baseline
        let baselineStr = String(format: "%.0f", baseline)
        let deltaStr = String(format: "%.1f", abs(delta))

        let direction: String
        if abs(delta) < 0.05 {
            direction = "tracking at baseline"
        } else if delta > 0 {
            direction = "up \(deltaStr) years"
        } else {
            direction = "down \(deltaStr) years"
        }

        let clampNote: String
        switch clampState {
        case .cappedAt(let v):
            clampNote = " Capped at \(String(format: "%.0f", v)) years."
        case .flooredAt(let v):
            clampNote = " Floored at \(String(format: "%.0f", v)) years."
        case .nearCap:
            clampNote = " Near the cap, so vertical movement is compressed."
        case .none:
            clampNote = ""
        }

        return "Baseline \(baselineStr) years; today \(direction). 16 weeks of past data, 14 weeks projected.\(clampNote)"
    }
}

// MARK: - AXChartDescriptorRepresentable
//
// Custom descriptor wins over Swift Charts' generic auto-generated
// one because (a) the X axis isn't a unit-free index — `Today` and
// `12 weeks ago` read far better than `0` and `-12`; (b) splitting
// observed-past from projected-future lets the VoiceOver rotor switch
// between them, which is a real semantic distinction in this chart;
// (c) the summary sentence is the same one a sighted user would read
// off the headline, kept in sync via `summarySentence`.
extension TrajectoryChart: AXChartDescriptorRepresentable {
    func makeChartDescriptor() -> AXChartDescriptor {
        let weeks = points.map { Double($0.week) }
        let years = points.map(\.years)
        let xMin = weeks.min() ?? -16
        let xMax = weeks.max() ?? 14
        let yLow = min(years.min() ?? baseline, baseline) - 1
        let yHigh = max(years.max() ?? baseline, baseline) + 1

        let xAxis = AXNumericDataAxisDescriptor(
            title: "Time",
            range: xMin...xMax,
            gridlinePositions: [0],
            valueDescriptionProvider: Self.weekDescription
        )
        let yAxis = AXNumericDataAxisDescriptor(
            title: "Projected healthspan in years",
            range: yLow...yHigh,
            gridlinePositions: [baseline],
            valueDescriptionProvider: { value in
                String(format: "%.1f years", value)
            }
        )

        let past = points.filter { $0.week <= 0 }
        let future = points.filter { $0.week >= 0 }
        let series: [AXDataSeriesDescriptor] = [
            AXDataSeriesDescriptor(
                name: "Past 16 weeks",
                isContinuous: true,
                dataPoints: past.map {
                    AXDataPoint(x: Double($0.week), y: $0.years)
                }
            ),
            AXDataSeriesDescriptor(
                name: "Next 14 weeks projected",
                isContinuous: true,
                dataPoints: future.map {
                    AXDataPoint(x: Double($0.week), y: $0.years)
                }
            ),
        ]

        return AXChartDescriptor(
            title: "Healthspan trajectory",
            summary: summarySentence,
            xAxis: xAxis,
            yAxis: yAxis,
            additionalAxes: [],
            series: series
        )
    }

    private static func weekDescription(_ value: Double) -> String {
        let w = Int(value.rounded())
        switch w {
        case 0: return "today"
        case 1: return "1 week from now"
        case -1: return "1 week ago"
        case let n where n > 0: return "\(n) weeks from now"
        default: return "\(abs(w)) weeks ago"
        }
    }
}
