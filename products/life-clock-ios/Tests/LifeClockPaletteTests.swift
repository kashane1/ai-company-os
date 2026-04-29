import XCTest
@testable import LifeClock

final class LifeClockPaletteTests: XCTestCase {
    /// Pins the contract that `LifeClockStore.bootstrap` relies on:
    /// unknown raw values return nil so the in-memory default survives.
    func testInitFromUnknownRawValueReturnsNil() {
        XCTAssertNil(LifeClockPalette(rawValue: "ghost"))
        XCTAssertNil(LifeClockPalette(rawValue: ""))
    }
}
