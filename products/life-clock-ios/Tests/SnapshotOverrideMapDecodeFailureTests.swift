import XCTest
import SwiftData
@testable import LifeClock

/// Pins the decode-failure fallback in `SnapshotOverrideMap.decode(from:)`:
/// if the bytes can't be decoded (corruption, future schema mismatch), we
/// return an empty map AND fire `assertionFailure` in DEBUG so the
/// regression is loud during development. Production behavior remains
/// "fail closed to empty" so a single bad row doesn't crash the app.
@MainActor
final class SnapshotOverrideMapDecodeFailureTests: XCTestCase {
    func testGarbageBytesDecodeToEmptyMap() {
        // Production behavior: corrupt bytes return empty map (fail-closed).
        // DEBUG also prints to stderr (verified manually — XCTest can't
        // capture stdout/stderr without test infra additions).
        let garbage = Data([0xFF, 0xFE, 0xFD, 0xFC])
        let map = SnapshotOverrideMap.decode(from: garbage)
        XCTAssertTrue(map.isEmpty,
                      "Decode failure must fall through to an empty map in production")
    }

    func testEmptyDataDecodesToEmptyMapWithoutAssertion() {
        // Storage default `Data()` is the "never written" case and must
        // NOT trigger the assertion path.
        let map = SnapshotOverrideMap.decode(from: Data())
        XCTAssertTrue(map.isEmpty)
    }

    func testValidEncodedRoundTrips() {
        var original = SnapshotOverrideMap()
        original.set(12_000, for: .stepCount)
        original.set(8.5, for: .sleepHours)
        let bytes = try! original.encode()
        let decoded = SnapshotOverrideMap.decode(from: bytes)
        XCTAssertEqual(decoded.value(for: .stepCount), 12_000)
        XCTAssertEqual(decoded.value(for: .sleepHours), 8.5)
        XCTAssertNil(decoded.value(for: .exerciseMinutes))
    }
}
