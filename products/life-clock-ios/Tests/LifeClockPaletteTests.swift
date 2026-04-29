import XCTest
@testable import LifeClock

final class LifeClockPaletteTests: XCTestCase {
    func testInitFromKnownRawValue() {
        XCTAssertEqual(LifeClockPalette(rawValue: "default-navy"), .defaultNavy)
        XCTAssertEqual(LifeClockPalette(rawValue: "aurora-cool"), .auroraCool)
        XCTAssertEqual(LifeClockPalette(rawValue: "sunset-warm"), .sunsetWarm)
    }

    /// Pins the contract that `LifeClockStore.bootstrap` relies on:
    /// unknown raw values return nil so the in-memory default survives.
    func testInitFromUnknownRawValueReturnsNil() {
        XCTAssertNil(LifeClockPalette(rawValue: "ghost"))
        XCTAssertNil(LifeClockPalette(rawValue: ""))
    }

    func testAllCasesHasThreePresets() {
        XCTAssertEqual(LifeClockPalette.allCases.count, 3)
    }
}
