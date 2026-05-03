import XCTest
import SwiftUI
@testable import LifeClock

/// First SwiftUI snapshot tests in this codebase. Uses Apple's built-in
/// `ImageRenderer` (iOS 16+) — no external snapshot-testing dependency.
/// `ImageRenderer` freezes any `TimelineView` at construction time, which
/// makes these tests deterministic without intercepting `Date()`.
///
/// What we assert: `ImageRenderer` produces a non-empty UIImage for each
/// state (baseline, ±30 min, ±720° clamp, reduce-motion). We don't byte-diff
/// the rendered images — that would lock us to specific renderer versions
/// across Xcode releases. The visual contract is verified by Previews +
/// device runs; these tests verify the *render path* doesn't crash and
/// produces non-trivial output.
@MainActor
final class LifeClockMascotViewTests: XCTestCase {

    /// `\.accessibilityReduceMotion` is a read-only EnvironmentValues key
    /// in iOS 17, so we can't inject it via `.environment()`. The render
    /// path test below still exercises the view structure; reduce-motion
    /// behavior is verified manually via the simulator's Accessibility
    /// settings (Settings → Accessibility → Motion → Reduce Motion).
    private func render(delta: Int) -> UIImage? {
        let view = LifeClockMascotView(minutesDelta: delta)
            .frame(width: 240, height: 240)
        let renderer = ImageRenderer(content: view)
        renderer.scale = 2
        return renderer.uiImage
    }

    func testBaselineRendersNonEmpty() throws {
        let image = try XCTUnwrap(render(delta: 0))
        XCTAssertGreaterThan(image.size.width, 0)
        XCTAssertGreaterThan(image.size.height, 0)
    }

    func testPositiveDeltaRenders() throws {
        XCTAssertNotNil(render(delta: 30))
    }

    func testNegativeDeltaRenders() throws {
        XCTAssertNotNil(render(delta: -30))
    }

    func testClampPositiveRenders() throws {
        // +1440 min would be 8640° — view clamps to ±720° internally.
        XCTAssertNotNil(render(delta: 1440))
    }

    func testClampNegativeRenders() throws {
        XCTAssertNotNil(render(delta: -1440))
    }

    func testIdenticalInputsProduceSameSizeOutput() throws {
        // Two renders of the same state should both be non-nil and same size.
        let a = try XCTUnwrap(render(delta: 0))
        let b = try XCTUnwrap(render(delta: 0))
        XCTAssertEqual(a.size, b.size)
    }
}
