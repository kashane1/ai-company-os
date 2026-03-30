import XCTest
@testable import Fishing_Logbook

final class AppFormattersTests: XCTestCase {
    func testTripDateFormatterProducesReadableOutput() {
        let formatted = AppFormatters.tripDate.string(from: Date(timeIntervalSince1970: 1_711_800_000))

        XCTAssertFalse(formatted.isEmpty)
    }

    func testShortTimeFormatterProducesReadableOutput() {
        let formatted = AppFormatters.shortTime.string(from: Date(timeIntervalSince1970: 1_711_800_000))

        XCTAssertFalse(formatted.isEmpty)
    }

    func testDurationFormatterProducesReadableOutput() {
        let formatted = AppFormatters.duration.string(from: 5_400)

        XCTAssertNotNil(formatted)
        XCTAssertFalse(formatted?.isEmpty ?? true)
    }
}
