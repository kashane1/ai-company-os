import CoreLocation
import SwiftData
import XCTest
@testable import Catchbook

final class WaterbodyAutoDetectionServiceTests: XCTestCase {

    // MARK: - inferType(from:)

    func testInferTypeReturnsRiverForRiverNames() {
        XCTAssertEqual(WaterbodyAutoDetectionService.inferType(from: "Columbia River"), .river)
        XCTAssertEqual(WaterbodyAutoDetectionService.inferType(from: "Salmon Creek"), .river)
        XCTAssertEqual(WaterbodyAutoDetectionService.inferType(from: "Duvall Stream"), .river)
    }

    func testInferTypeReturnsPondForPondNames() {
        XCTAssertEqual(WaterbodyAutoDetectionService.inferType(from: "Walden Pond"), .pond)
    }

    func testInferTypeReturnsCoastalForOceanNames() {
        XCTAssertEqual(WaterbodyAutoDetectionService.inferType(from: "Pacific Ocean"), .coastal)
        XCTAssertEqual(WaterbodyAutoDetectionService.inferType(from: "Salish Sea"), .coastal)
        XCTAssertEqual(WaterbodyAutoDetectionService.inferType(from: "Gulf of Alaska"), .coastal)
        XCTAssertEqual(WaterbodyAutoDetectionService.inferType(from: "Puget Bay"), .coastal)
    }

    func testInferTypeFallsBackToLake() {
        XCTAssertEqual(WaterbodyAutoDetectionService.inferType(from: "Lake Tahoe"), .lake)
        XCTAssertEqual(WaterbodyAutoDetectionService.inferType(from: "Loch Ness"), .lake)
    }

    // MARK: - findOrCreate existing match

    @MainActor
    func testFindOrCreateReturnsExistingMatchByCaseInsensitiveName() throws {
        let store = try ModelTestSupport.makeStore()
        let existing = Waterbody(
            name: "Lake Tahoe",
            type: .lake,
            latitude: 39.0968,
            longitude: -120.0324
        )
        store.context.insert(existing)
        try store.context.save()

        let detected = WaterbodyAutoDetectionService.Detected(
            name: "lake tahoe",
            type: .lake,
            coordinate: CLLocationCoordinate2D(latitude: 39.0968, longitude: -120.0324)
        )

        let result = try WaterbodyAutoDetectionService.findOrCreate(detected, in: store.context)

        XCTAssertEqual(result.id, existing.id)
        let count = try store.context.fetchCount(FetchDescriptor<Waterbody>())
        XCTAssertEqual(count, 1, "findOrCreate must not insert a duplicate when a case-insensitive name match exists")
    }

    // MARK: - findOrCreate new insert

    @MainActor
    func testFindOrCreateInsertsNewWaterbodyWhenNoMatch() throws {
        let store = try ModelTestSupport.makeStore()

        let detected = WaterbodyAutoDetectionService.Detected(
            name: "Green River",
            type: .river,
            coordinate: CLLocationCoordinate2D(latitude: 47.2530, longitude: -122.2430)
        )

        let result = try WaterbodyAutoDetectionService.findOrCreate(detected, in: store.context)

        XCTAssertEqual(result.name, "Green River")
        XCTAssertEqual(result.type, .river)
        XCTAssertEqual(result.latitude ?? 0, 47.2530, accuracy: 0.0001)
        XCTAssertEqual(result.longitude ?? 0, -122.2430, accuracy: 0.0001)

        let all = try store.context.fetch(FetchDescriptor<Waterbody>())
        XCTAssertEqual(all.count, 1)
        XCTAssertEqual(all.first?.id, result.id)
    }
}
