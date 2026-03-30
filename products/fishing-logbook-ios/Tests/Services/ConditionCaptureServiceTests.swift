import CoreLocation
import XCTest
@testable import Fishing_Logbook

final class ConditionCaptureServiceTests: XCTestCase {
    func testSnapshotUsesDeviceLocationWhenAvailable() {
        let waterbody = Waterbody(name: "River Bend", type: .river, latitude: 44.0, longitude: -122.0)
        let spot = Spot(title: "Dock", waterbody: waterbody, latitude: 45.0, longitude: -123.0)
        let location = CLLocation(latitude: 46.0, longitude: -124.0)
        let capturedAt = Date(timeIntervalSince1970: 1_711_800_000)

        let snapshot = ConditionCaptureService.snapshot(
            waterbody: waterbody,
            spot: spot,
            location: location,
            capturedAt: capturedAt
        )

        XCTAssertEqual(snapshot.captureStatus, .ready)
        XCTAssertEqual(snapshot.source, .deviceLocation)
        XCTAssertEqual(snapshot.latitude, 46.0)
        XCTAssertEqual(snapshot.longitude, -124.0)
        XCTAssertEqual(snapshot.placeSummary, "Dock • River Bend")
    }

    func testSnapshotFallsBackToSpotCoordinateWithoutDeviceLocation() {
        let waterbody = Waterbody(name: "Lake Blue", type: .lake, latitude: 44.0, longitude: -122.0)
        let spot = Spot(title: "Reeds", waterbody: waterbody, latitude: 45.5, longitude: -123.5)

        let snapshot = ConditionCaptureService.snapshot(
            waterbody: waterbody,
            spot: spot,
            location: nil,
            capturedAt: Date(timeIntervalSince1970: 1_711_820_000)
        )

        XCTAssertEqual(snapshot.captureStatus, .fallback)
        XCTAssertEqual(snapshot.source, .tripFallback)
        XCTAssertEqual(snapshot.latitude, 45.5)
        XCTAssertEqual(snapshot.longitude, -123.5)
    }

    func testSnapshotIsPendingWhenNoCoordinateOrPlaceIsAvailable() {
        let snapshot = ConditionCaptureService.snapshot(
            waterbody: nil,
            spot: nil,
            location: nil,
            capturedAt: Date(timeIntervalSince1970: 1_711_840_000)
        )

        XCTAssertEqual(snapshot.captureStatus, .pending)
        XCTAssertEqual(snapshot.source, .tripFallback)
        XCTAssertNil(snapshot.latitude)
        XCTAssertNil(snapshot.placeSummary)
    }

    func testPreviewReportsLocationReadiness() {
        let preview = ConditionCaptureService.preview(
            waterbody: nil,
            spot: nil,
            location: CLLocation(latitude: 47.0, longitude: -121.0)
        )

        XCTAssertTrue(preview.isLocationReady)
        XCTAssertEqual(preview.snapshot.captureStatus, .ready)
    }
}
