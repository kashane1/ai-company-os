import XCTest
@testable import Catchbook

final class TripEditingLogicTests: XCTestCase {
    func testDuplicateCatchSeedPreservesFieldsAndResetsTimestamp() {
        let waterbody = Waterbody(name: "Lake", type: .lake)
        let trip = Trip(waterbody: waterbody)
        let catchRecord = CatchRecord(
            species: "Bass",
            trip: trip,
            caughtAt: Date(timeIntervalSince1970: 10),
            lureOrBait: "Spinner",
            method: "Slow roll",
            weightKg: 2.5,
            lengthCm: 50,
            waterDepthM: 1.2,
            note: "Outside weedline",
            disposition: .released
        )

        let seed = TripEditingLogic.duplicateCatchSeed(
            from: catchRecord,
            duplicateTimestamp: Date(timeIntervalSince1970: 100)
        )

        XCTAssertEqual(seed.species, "Bass")
        XCTAssertEqual(seed.caughtAt, Date(timeIntervalSince1970: 100))
        XCTAssertEqual(seed.lureOrBait, "Spinner")
        XCTAssertEqual(seed.method, "Slow roll")
        XCTAssertEqual(seed.weight, "2.5")
        XCTAssertEqual(seed.length, "50.0")
        XCTAssertEqual(seed.waterDepth, "1.2")
        XCTAssertEqual(seed.note, "Outside weedline")
        XCTAssertEqual(seed.disposition, .released)
    }
}
