import XCTest
@testable import LifeClock

final class DailyCheckInMappingTests: XCTestCase {
    func testExtrasLevelMapsToExistingAlcoholBuckets() {
        XCTAssertEqual(DailyCheckInMapping.alcoholLevel(for: "none"), "none")
        XCTAssertEqual(DailyCheckInMapping.alcoholLevel(for: "one"), "light")
        XCTAssertEqual(DailyCheckInMapping.alcoholLevel(for: "few"), "light")
        XCTAssertEqual(DailyCheckInMapping.alcoholLevel(for: "lot"), "heavy")
    }

    func testExistingAlcoholBucketsHydrateBackIntoExtrasChoices() {
        XCTAssertEqual(DailyCheckInMapping.extrasLevel(for: "none"), "none")
        XCTAssertEqual(DailyCheckInMapping.extrasLevel(for: "light"), "few")
        XCTAssertEqual(DailyCheckInMapping.extrasLevel(for: "heavy"), "lot")
    }
}
