import XCTest
import SwiftUI
@testable import LifeClock

final class LifeClockHapticsTests: XCTestCase {
    func testWrapUpHapticsMatchApprovedPolicy() {
        XCTAssertEqual(LifeClockHaptics.wrapUp(signedMinutes: 42), .success)
        XCTAssertEqual(LifeClockHaptics.wrapUp(signedMinutes: 0), .selection)
        XCTAssertEqual(LifeClockHaptics.wrapUp(signedMinutes: -42), .impact(weight: .light))
    }

    /// V1.7.0 polish (2026-05-12 — polish-2026-05-12-whatif-slider-scrub-feel):
    /// pin the three WhatIfSlider scrub keys so a future copy-edit can't
    /// silently retune the haptic intensity without revisiting the policy
    /// doc-comment on `LifeClockHaptics`.
    func testWhatIfScrubHapticsMatchApprovedPolicy() {
        XCTAssertEqual(LifeClockHaptics.whatIfScrubBegin, .impact(weight: .light))
        XCTAssertEqual(LifeClockHaptics.whatIfScrubEdge, .impact(weight: .medium))
        XCTAssertEqual(LifeClockHaptics.whatIfScrubEnd, .selection)
    }
}
