import XCTest
@testable import LifeClock

/// Narrow coverage for `formatProjectionA11y`. The VoiceOver pairing for
/// `TodayView.trajectoryPeek` depends on this formatter producing
/// spoken units rather than bare letters — see ToneModeTests for the
/// label half.
final class TimeDeltaFormatterTests: XCTestCase {

    func testProjectionA11y_WholeYearsOmitsMonths() {
        XCTAssertEqual(
            TimeDeltaFormatter.formatProjectionA11y(years: 87.0),
            "87 years"
        )
    }

    func testProjectionA11y_MixedYearsAndMonthsExpandsBothUnits() {
        // 87 + 2/12 = 87.1666...; rounded to nearest month = 1046 months
        // = 87y 2m.
        XCTAssertEqual(
            TimeDeltaFormatter.formatProjectionA11y(years: 87 + 2.0 / 12),
            "87 years 2 months"
        )
    }

    func testProjectionA11y_SingularUnitsPluralizeCorrectly() {
        XCTAssertEqual(
            TimeDeltaFormatter.formatProjectionA11y(years: 1.0),
            "1 year"
        )
        XCTAssertEqual(
            TimeDeltaFormatter.formatProjectionA11y(years: 1 + 1.0 / 12),
            "1 year 1 month"
        )
    }

    func testProjectionA11y_RoundingMatchesPeekVisibleString() {
        // Peek's visible formatter (TodayView.currentProjectionForPeek)
        // uses Int((years * 12).rounded()); this method MUST match so
        // VO and the visible "Xy Ym" never disagree.
        let years = 88.04
        let total = Int((years * 12).rounded())
        let y = total / 12
        let m = total % 12
        let expected = m == 0 ? "\(y) years" : "\(y) years \(m) months"
        XCTAssertEqual(
            TimeDeltaFormatter.formatProjectionA11y(years: years),
            expected
        )
    }
}
