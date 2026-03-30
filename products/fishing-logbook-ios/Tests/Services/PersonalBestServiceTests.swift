import SwiftData
import XCTest
@testable import Fishing_Logbook

final class PersonalBestServiceTests: XCTestCase {
    func testRefreshInsertsNewPersonalBestForSpecies() throws {
        let store = try ModelTestSupport.makeStore()
        let trip = Trip(waterbody: nil)
        let catchRecord = CatchRecord(
            species: "Bass",
            trip: trip,
            weightKg: 2.3,
            lengthCm: 45
        )

        store.context.insert(trip)
        store.context.insert(catchRecord)

        try PersonalBestService.refresh(with: catchRecord, in: store.context)

        let records = try store.context.fetch(FetchDescriptor<PersonalBest>())
        XCTAssertEqual(records.count, 1)
        XCTAssertEqual(records.first?.species, "Bass")
        XCTAssertEqual(records.first?.longestLengthCm, 45)
        XCTAssertEqual(records.first?.heaviestWeightKg, 2.3)
    }

    func testRefreshUpdatesLongestAndHeaviestValues() throws {
        let store = try ModelTestSupport.makeStore()
        let trip = Trip(waterbody: nil)
        let originalCatch = CatchRecord(
            species: "Bass",
            trip: trip,
            weightKg: 1.8,
            lengthCm: 40
        )
        let largerCatch = CatchRecord(
            species: "Bass",
            trip: trip,
            weightKg: 2.6,
            lengthCm: 48
        )

        store.context.insert(trip)
        store.context.insert(originalCatch)
        try PersonalBestService.refresh(with: originalCatch, in: store.context)

        store.context.insert(largerCatch)
        try PersonalBestService.refresh(with: largerCatch, in: store.context)

        let records = try store.context.fetch(FetchDescriptor<PersonalBest>())
        XCTAssertEqual(records.count, 1)
        XCTAssertEqual(records.first?.longestLengthCm, 48)
        XCTAssertEqual(records.first?.heaviestWeightKg, 2.6)
    }

    func testRefreshIgnoresBlankSpecies() throws {
        let store = try ModelTestSupport.makeStore()
        let catchRecord = CatchRecord(species: "   ", trip: nil, weightKg: 1.2, lengthCm: 30)

        try PersonalBestService.refresh(with: catchRecord, in: store.context)

        let records = try store.context.fetch(FetchDescriptor<PersonalBest>())
        XCTAssertTrue(records.isEmpty)
    }

    func testRebuildRecomputesPersonalBestRecords() throws {
        let store = try ModelTestSupport.makeStore()
        let trip = Trip(waterbody: nil)
        let bassOne = CatchRecord(species: "Bass", trip: trip, weightKg: 2.1, lengthCm: 44)
        let bassTwo = CatchRecord(species: "Bass", trip: trip, weightKg: 2.8, lengthCm: 41)
        let trout = CatchRecord(species: "Trout", trip: trip, weightKg: 1.4, lengthCm: 39)

        store.context.insert(trip)
        store.context.insert(PersonalBest(species: "Old species", longestLengthCm: 10, heaviestWeightKg: 1))
        store.context.insert(bassOne)
        store.context.insert(bassTwo)
        store.context.insert(trout)

        try PersonalBestService.rebuild(in: store.context)

        let records = try store.context.fetch(
            FetchDescriptor<PersonalBest>(sortBy: [SortDescriptor(\.species)])
        )
        XCTAssertEqual(records.count, 2)
        XCTAssertEqual(records[0].species, "Bass")
        XCTAssertEqual(records[0].longestLengthCm, 44)
        XCTAssertEqual(records[0].heaviestWeightKg, 2.8)
        XCTAssertEqual(records[1].species, "Trout")
    }
}
