import XCTest
@testable import LifeClock

/// Narrow unit coverage for V1.2.0 additions: `todayRescueBody()` and the
/// `RescueLine.shouldShow` predicate. Exhaustive-switch / literal-string
/// tautologies (every mode returns non-empty, all three are distinct)
/// are skipped — Swift's exhaustive switch makes them framework tests
/// that can't fail silently. Code review catches paste-twice mistakes.
final class ToneModeTests: XCTestCase {

    // MARK: - todayRescueBody

    /// Pin the gentle-mode copy. Catches accidental rewrites of the
    /// "log it and move on" line that's the highest-leverage retention
    /// nudge in the rescue family.
    func testTodayRescueBody_GentleReturnsLogItAndMoveOn() {
        XCTAssertEqual(
            ToneMode.gentle.todayRescueBody(),
            "Rough day? Log it and move on. Tomorrow still counts."
        )
    }

    // MARK: - RescueLine.shouldShow

    private func makeLine(
        netDelta: Int,
        dietQuality: String = "",
        rhythm: String = "",
        anchor: String = ""
    ) -> TodayView.RescueLine {
        TodayView.RescueLine(
            netDelta: netDelta,
            dietQuality: dietQuality,
            rhythm: rhythm,
            anchor: anchor,
            tone: .coach
        )
    }

    func testRescueLine_NegativeDeltaPlusRoughDietShows() {
        XCTAssertTrue(makeLine(netDelta: -5, dietQuality: "rough").shouldShow)
    }

    func testRescueLine_NegativeDeltaPlusSkipBingeShows() {
        XCTAssertTrue(makeLine(netDelta: -5, rhythm: "skipBinge").shouldShow)
    }

    func testRescueLine_NegativeDeltaPlusAnchorNoShows() {
        XCTAssertTrue(makeLine(netDelta: -5, anchor: "no").shouldShow)
    }

    /// Net positive delta suppresses the rescue line even when the user
    /// logged a rough diet — HK steps may have driven a big positive day.
    func testRescueLine_PositiveDeltaSuppresses() {
        XCTAssertFalse(makeLine(netDelta: 30, dietQuality: "rough").shouldShow)
    }

    /// Boundary: delta == 0 is not net-negative, so no rescue line.
    func testRescueLine_DeltaZeroSuppresses() {
        XCTAssertFalse(makeLine(netDelta: 0, dietQuality: "rough").shouldShow)
    }

    /// Negative delta without any of the three diet triggers — no rescue
    /// line. (E.g. negative day from poor sleep alone.)
    func testRescueLine_NegativeDeltaWithNoDietTriggersDoesNotShow() {
        XCTAssertFalse(makeLine(netDelta: -15).shouldShow)
        XCTAssertFalse(makeLine(netDelta: -15, dietQuality: "okay", rhythm: "right", anchor: "yes").shouldShow)
    }
}
