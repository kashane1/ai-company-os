import XCTest
import Accessibility
@testable import LifeClock

/// Locks the audio-graph chart descriptor for `TrajectoryChart` so a
/// future refactor that drops `.accessibilityChartDescriptor(self)` or
/// flattens the past/future series split fails loudly. Swift Charts'
/// auto-generated descriptor describes the X axis as a unit-free
/// index ("0", "-12") which is unreadable for the healthspan
/// trajectory — the custom descriptor is the difference between a
/// VoiceOver user understanding the chart and not.
final class TrajectoryChartAccessibilityTests: XCTestCase {
    private func points(currentDelta: Double, baseline: Double = 84) -> [TrajectoryPoint] {
        var pts: [TrajectoryPoint] = []
        for w in -16...(-1) { pts.append(TrajectoryPoint(week: w, years: baseline)) }
        pts.append(TrajectoryPoint(week: 0, years: baseline + currentDelta))
        for w in 1...14 { pts.append(TrajectoryPoint(week: w, years: baseline + currentDelta)) }
        return pts
    }

    func test_descriptor_titleAndAxes() {
        let chart = TrajectoryChart(
            points: points(currentDelta: 1.2),
            baseline: 84,
            clampState: .none
        )
        let d = chart.makeChartDescriptor()
        XCTAssertEqual(d.title, "Healthspan trajectory")
        XCTAssertEqual((d.xAxis as? AXNumericDataAxisDescriptor)?.title, "Time")
        XCTAssertEqual(d.yAxis?.title, "Projected healthspan in years")
    }

    func test_descriptor_splitsPastAndFutureSeries() {
        let chart = TrajectoryChart(
            points: points(currentDelta: 0),
            baseline: 84,
            clampState: .none
        )
        let d = chart.makeChartDescriptor()
        XCTAssertEqual(d.series.count, 2)
        XCTAssertEqual(d.series[0].name, "Past 16 weeks")
        XCTAssertEqual(d.series[1].name, "Next 14 weeks projected")
        // Week 0 is the seam — present in both series so VoiceOver
        // rotor-walking either series lands on "today" without a gap.
        XCTAssertEqual(d.series[0].dataPoints.count, 17)
        XCTAssertEqual(d.series[1].dataPoints.count, 15)
    }

    private func summary(_ chart: TrajectoryChart) -> String {
        chart.makeChartDescriptor().summary ?? ""
    }

    func test_summary_directionAdaptive() {
        let up = TrajectoryChart(points: points(currentDelta: 2.4), baseline: 84, clampState: .none)
        XCTAssertTrue(summary(up).contains("up 2.4 years"))

        let down = TrajectoryChart(points: points(currentDelta: -1.7), baseline: 84, clampState: .none)
        XCTAssertTrue(summary(down).contains("down 1.7 years"))

        let flat = TrajectoryChart(points: points(currentDelta: 0.0), baseline: 84, clampState: .none)
        XCTAssertTrue(summary(flat).contains("tracking at baseline"))
    }

    func test_summary_appendsClampNote() {
        let capped = TrajectoryChart(points: points(currentDelta: 14), baseline: 84, clampState: .cappedAt(98))
        XCTAssertTrue(summary(capped).contains("Capped at 98 years"))

        let floored = TrajectoryChart(points: points(currentDelta: -10), baseline: 84, clampState: .flooredAt(50))
        XCTAssertTrue(summary(floored).contains("Floored at 50 years"))

        let near = TrajectoryChart(points: points(currentDelta: 12), baseline: 84, clampState: .nearCap)
        XCTAssertTrue(summary(near).contains("Near the cap"))
    }

    func test_xAxisValueDescription_speaksTimeNotIndex() {
        let chart = TrajectoryChart(points: points(currentDelta: 1), baseline: 84, clampState: .none)
        let provider = (chart.makeChartDescriptor().xAxis as? AXNumericDataAxisDescriptor)?
            .valueDescriptionProvider
        XCTAssertEqual(provider?(0), "today")
        XCTAssertEqual(provider?(1), "1 week from now")
        XCTAssertEqual(provider?(-1), "1 week ago")
        XCTAssertEqual(provider?(8), "8 weeks from now")
        XCTAssertEqual(provider?(-12), "12 weeks ago")
    }
}
