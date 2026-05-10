import XCTest
import SwiftUI
@testable import LifeClock

final class LifeClockHapticsTests: XCTestCase {
    func testWrapUpHapticsMatchApprovedPolicy() {
        XCTAssertEqual(LifeClockHaptics.wrapUp(signedMinutes: 42), .success)
        XCTAssertEqual(LifeClockHaptics.wrapUp(signedMinutes: 0), .selection)
        XCTAssertEqual(LifeClockHaptics.wrapUp(signedMinutes: -42), .impact(weight: .light))
    }
}
