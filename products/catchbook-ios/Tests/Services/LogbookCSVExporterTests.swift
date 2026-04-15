import Foundation
import XCTest
@testable import Catchbook

final class LogbookCSVExporterTests: XCTestCase {
    func testHeaderRowIsEmittedFirst() {
        let csv = LogbookCSVExporter.makeCSV(catches: [])
        let firstLine = csv.split(separator: "\n").first.map(String.init) ?? ""
        XCTAssertEqual(firstLine, LogbookCSVExporter.header.joined(separator: ","))
    }

    func testEmptyInputStillProducesHeaderAndTrailingNewline() {
        let csv = LogbookCSVExporter.makeCSV(catches: [])
        XCTAssertTrue(csv.hasSuffix("\n"))
        XCTAssertEqual(csv.split(separator: "\n").count, 1)
    }

    func testRowContainsDenormalizedTripAndSpotContext() {
        let waterbody = Waterbody(
            name: "Puget Sound",
            type: .coastal,
            createdAt: Date(timeIntervalSince1970: 0)
        )
        let spot = Spot(
            title: "Alki Point",
            waterbody: waterbody,
            latitude: 47.576,
            longitude: -122.420,
            notes: "",
            createdAt: Date(timeIntervalSince1970: 0)
        )
        let trip = Trip(
            waterbody: waterbody,
            spot: spot,
            targetSpecies: "Coho",
            notes: "",
            startAt: Date(timeIntervalSince1970: 1_000)
        )
        trip.endAt = Date(timeIntervalSince1970: 2_000)
        trip.outcomeRawValue = TripOutcome.caught.rawValue

        let record = CatchRecord(
            species: "Coho",
            trip: trip,
            caughtAt: Date(timeIntervalSince1970: 1_500),
            lureOrBait: "Buzz Bomb",
            method: "Casting",
            gear: "8wt",
            weightKg: 3.2,
            lengthCm: 52,
            waterDepthM: 4.5,
            note: "Strong run",
            disposition: .released
        )

        let csv = LogbookCSVExporter.makeCSV(catches: [record])
        let lines = csv.split(separator: "\n", omittingEmptySubsequences: false)
        XCTAssertGreaterThanOrEqual(lines.count, 2)
        let row = String(lines[1])

        XCTAssertTrue(row.contains("Coho"))
        XCTAssertTrue(row.contains("Buzz Bomb"))
        XCTAssertTrue(row.contains("released"))
        XCTAssertTrue(row.contains("Alki Point"))
        XCTAssertTrue(row.contains("Puget Sound"))
        XCTAssertTrue(row.contains("coastal"))
        XCTAssertTrue(row.contains("3.2"))
        XCTAssertTrue(row.contains("52"))
    }

    func testFieldsContainingCommasAreQuoted() {
        let trip = Trip(waterbody: nil, targetSpecies: "", startAt: Date(timeIntervalSince1970: 0))
        let record = CatchRecord(
            species: "Bass",
            trip: trip,
            caughtAt: Date(timeIntervalSince1970: 0),
            note: "Caught in wind, rain, and chop"
        )
        let csv = LogbookCSVExporter.makeCSV(catches: [record])
        XCTAssertTrue(csv.contains("\"Caught in wind, rain, and chop\""))
    }

    func testFieldsContainingQuotesAreEscapedWithDoubleQuotes() {
        let trip = Trip(waterbody: nil, targetSpecies: "", startAt: Date(timeIntervalSince1970: 0))
        let record = CatchRecord(
            species: "Bass",
            trip: trip,
            caughtAt: Date(timeIntervalSince1970: 0),
            lureOrBait: "Blue \"Rapala\""
        )
        let csv = LogbookCSVExporter.makeCSV(catches: [record])
        XCTAssertTrue(csv.contains("\"Blue \"\"Rapala\"\"\""))
    }

    func testRowsAreSortedByCaughtAtAscending() {
        let trip = Trip(waterbody: nil, targetSpecies: "", startAt: Date(timeIntervalSince1970: 0))
        let later = CatchRecord(species: "Later", trip: trip, caughtAt: Date(timeIntervalSince1970: 2_000))
        let earlier = CatchRecord(species: "Earlier", trip: trip, caughtAt: Date(timeIntervalSince1970: 1_000))

        let csv = LogbookCSVExporter.makeCSV(catches: [later, earlier])
        let lines = csv.split(separator: "\n").map(String.init)
        // lines[0] header, lines[1] earlier, lines[2] later
        XCTAssertTrue(lines[1].contains("Earlier"))
        XCTAssertTrue(lines[2].contains("Later"))
    }

    func testNumericFieldsUseLocaleIndependentFormatting() {
        let trip = Trip(waterbody: nil, targetSpecies: "", startAt: Date(timeIntervalSince1970: 0))
        let record = CatchRecord(
            species: "Pike",
            trip: trip,
            caughtAt: Date(timeIntervalSince1970: 0),
            weightKg: 1.5,
            lengthCm: 40.0
        )
        let csv = LogbookCSVExporter.makeCSV(catches: [record])
        // 1.5 stays as "1.5", 40.0 collapses to "40"
        let row = String(csv.split(separator: "\n")[1])
        XCTAssertTrue(row.contains(",1.5,"))
        XCTAssertTrue(row.contains(",40,"))
    }
}
