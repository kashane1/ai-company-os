import XCTest
@testable import Catchbook

final class CatchbookMapStyleTests: XCTestCase {
    func testNextCyclesThroughAllStyles() {
        XCTAssertEqual(CatchbookMapStyle.standard.next, .hybrid)
        XCTAssertEqual(CatchbookMapStyle.hybrid.next, .satellite)
        XCTAssertEqual(CatchbookMapStyle.satellite.next, .standard)
    }
}
