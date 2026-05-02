import XCTest
@testable import LifeClock

final class EngineRevealPresenterTests: XCTestCase {
    func testZeroDeltaIsZeroMinutes() {
        XCTAssertEqual(EngineRevealPresenter.mascotDelta(displayedYears: 80, baselineYears: 80), 0)
    }

    func testPositiveYearMapsAtSixMinutesPerYear() {
        XCTAssertEqual(EngineRevealPresenter.mascotDelta(displayedYears: 85, baselineYears: 80), 30)
    }

    func testNegativeYearMapsAtSixMinutesPerYear() {
        XCTAssertEqual(EngineRevealPresenter.mascotDelta(displayedYears: 75, baselineYears: 80), -30)
    }

    func testFractionalYearRoundsToNearestMinute() {
        // 2.5 yrs * 6 = 15 min
        XCTAssertEqual(EngineRevealPresenter.mascotDelta(displayedYears: 82.5, baselineYears: 80), 15)
        // 0.25 yrs * 6 = 1.5 → rounds to 2
        XCTAssertEqual(EngineRevealPresenter.mascotDelta(displayedYears: 80.25, baselineYears: 80), 2)
    }

    func testPositiveClampAtMaxMinutes() {
        // +20 yrs would be 120 min; clamp at +60.
        XCTAssertEqual(EngineRevealPresenter.mascotDelta(displayedYears: 100, baselineYears: 80), 60)
    }

    func testNegativeClampAtMinMinutes() {
        XCTAssertEqual(EngineRevealPresenter.mascotDelta(displayedYears: 60, baselineYears: 80), -60)
    }

    func testBoundariesAtExactClamp() {
        // +10 yrs * 6 = 60 → at the cap, not over.
        XCTAssertEqual(EngineRevealPresenter.mascotDelta(displayedYears: 90, baselineYears: 80), 60)
        XCTAssertEqual(EngineRevealPresenter.mascotDelta(displayedYears: 70, baselineYears: 80), -60)
    }
}
