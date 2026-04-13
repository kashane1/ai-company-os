import CoreLocation
import ImageIO
import XCTest
@testable import Catchbook

final class CatchPhotoMetadataServiceTests: XCTestCase {
    func testMetadataReadsGPSCoordinateFromProperties() {
        let properties: [CFString: Any] = [
            kCGImagePropertyGPSDictionary: [
                kCGImagePropertyGPSLatitude: 47.61,
                kCGImagePropertyGPSLatitudeRef: "N",
                kCGImagePropertyGPSLongitude: 122.33,
                kCGImagePropertyGPSLongitudeRef: "W",
            ],
        ]

        let metadata = CatchPhotoMetadataService.metadata(from: properties)

        XCTAssertEqual(metadata?.coordinate?.latitude ?? 0, 47.61, accuracy: 0.0001)
        XCTAssertEqual(metadata?.coordinate?.longitude ?? 0, -122.33, accuracy: 0.0001)
    }

    func testMetadataReturnsNilWhenNoUsefulPropertiesExist() {
        XCTAssertNil(CatchPhotoMetadataService.metadata(from: [:]))
    }

    func testNearbySpotMatchesReturnsOnlySpotsInsideRadiusSortedByDistance() {
        let lake = Waterbody(name: "Lake", type: .lake)
        let close = Spot(title: "Dock", waterbody: lake, latitude: 47.6101, longitude: -122.3301)
        let far = Spot(title: "Point", waterbody: lake, latitude: 47.6200, longitude: -122.3400)
        let alsoClose = Spot(title: "Cove", waterbody: lake, latitude: 47.6102, longitude: -122.3302)

        let matches = CatchPhotoMetadataService.nearbySpotMatches(
            for: CLLocationCoordinate2D(latitude: 47.61, longitude: -122.33),
            spots: [far, alsoClose, close],
            radiusMeters: 50
        )

        XCTAssertEqual(matches.map(\.title), ["Dock", "Cove"])
    }
}
