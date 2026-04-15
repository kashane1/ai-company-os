import Foundation
import XCTest
@testable import Catchbook

final class FishingStatsLogicTests: XCTestCase {
    // MARK: - Headline

    func testHeadlineEmptyCaseReportsZeros() {
        let stats = FishingStatsLogic.build(trips: [], catches: [], personalBests: [])
        XCTAssertEqual(stats.headline.totalTrips, 0)
        XCTAssertEqual(stats.headline.totalCatches, 0)
        XCTAssertEqual(stats.headline.catchesPerTrip, 0)
        XCTAssertEqual(stats.headline.skunkRate, 0)
        XCTAssertFalse(stats.hasAnyData)
    }

    func testHeadlineComputesCatchesPerTripAndSkunkRate() {
        let tripA = makeCompletedTrip(
            id: "A",
            start: Date(timeIntervalSince1970: 0),
            end: Date(timeIntervalSince1970: 3_600),
            outcome: .caught
        )
        let tripB = makeCompletedTrip(
            id: "B",
            start: Date(timeIntervalSince1970: 10_000),
            end: Date(timeIntervalSince1970: 17_200),
            outcome: .skunked
        )
        let c1 = CatchRecord(species: "Bass", trip: tripA, caughtAt: Date(timeIntervalSince1970: 1_000))
        let c2 = CatchRecord(species: "Bass", trip: tripA, caughtAt: Date(timeIntervalSince1970: 2_000))

        let stats = FishingStatsLogic.build(trips: [tripA, tripB], catches: [c1, c2], personalBests: [])

        XCTAssertEqual(stats.headline.totalTrips, 2)
        XCTAssertEqual(stats.headline.totalCatches, 2)
        XCTAssertEqual(stats.headline.catchesPerTrip, 1.0, accuracy: 0.01)
        XCTAssertEqual(stats.headline.skunkedTrips, 1)
        XCTAssertEqual(stats.headline.skunkRate, 0.5, accuracy: 0.01)
        XCTAssertEqual(stats.headline.totalHoursFished, 3.0, accuracy: 0.05)
    }

    func testActiveTripsAreExcludedFromHeadline() {
        let active = Trip(waterbody: nil, targetSpecies: "", startAt: Date(timeIntervalSince1970: 0))
        let completed = makeCompletedTrip(
            id: "A",
            start: Date(timeIntervalSince1970: 1_000),
            end: Date(timeIntervalSince1970: 4_600),
            outcome: .caught
        )
        let record = CatchRecord(species: "Bass", trip: completed, caughtAt: Date(timeIntervalSince1970: 2_000))

        let stats = FishingStatsLogic.build(trips: [active, completed], catches: [record], personalBests: [])

        XCTAssertEqual(stats.headline.totalTrips, 1)
        XCTAssertEqual(stats.headline.totalCatches, 1)
    }

    // MARK: - Top species

    func testTopSpeciesIsCountedCaseInsensitivelyAndSortedByCountDescending() {
        let trip = makeCompletedTrip(id: "A", start: Date(timeIntervalSince1970: 0), end: Date(timeIntervalSince1970: 3_600), outcome: .caught)
        let catches = [
            CatchRecord(species: "Bass", trip: trip, caughtAt: Date(timeIntervalSince1970: 100)),
            CatchRecord(species: "bass", trip: trip, caughtAt: Date(timeIntervalSince1970: 200)),
            CatchRecord(species: "Pike", trip: trip, caughtAt: Date(timeIntervalSince1970: 300)),
            CatchRecord(species: "Trout", trip: trip, caughtAt: Date(timeIntervalSince1970: 400)),
            CatchRecord(species: "Trout", trip: trip, caughtAt: Date(timeIntervalSince1970: 500)),
        ]
        let species = FishingStatsLogic.topSpecies(catches: catches, limit: 5)

        XCTAssertEqual(species.count, 3)
        // Trout and Bass tie at 2 → alphabetical Bass first.
        XCTAssertEqual(species[0].label, "Bass")
        XCTAssertEqual(species[0].count, 2)
        XCTAssertEqual(species[1].label, "Trout")
        XCTAssertEqual(species[1].count, 2)
        XCTAssertEqual(species[2].label, "Pike")
        XCTAssertEqual(species[2].count, 1)
    }

    func testEmptySpeciesStringIsIgnored() {
        let trip = makeCompletedTrip(id: "A", start: Date(timeIntervalSince1970: 0), end: Date(timeIntervalSince1970: 3_600), outcome: .caught)
        let catches = [
            CatchRecord(species: "", trip: trip, caughtAt: Date(timeIntervalSince1970: 100)),
            CatchRecord(species: "   ", trip: trip, caughtAt: Date(timeIntervalSince1970: 200)),
            CatchRecord(species: "Bass", trip: trip, caughtAt: Date(timeIntervalSince1970: 300)),
        ]
        XCTAssertEqual(FishingStatsLogic.topSpecies(catches: catches, limit: 5).count, 1)
    }

    // MARK: - Top spots

    func testTopSpotsCountsCatchesPerSpot() {
        let alki = Spot(title: "Alki", waterbody: nil)
        let edmonds = Spot(title: "Edmonds", waterbody: nil)
        let trip1 = Trip(waterbody: nil, spot: alki, startAt: Date(timeIntervalSince1970: 0))
        trip1.endAt = Date(timeIntervalSince1970: 3_600)
        let trip2 = Trip(waterbody: nil, spot: edmonds, startAt: Date(timeIntervalSince1970: 10_000))
        trip2.endAt = Date(timeIntervalSince1970: 13_600)

        let catches = [
            CatchRecord(species: "Bass", trip: trip1, caughtAt: Date(timeIntervalSince1970: 100)),
            CatchRecord(species: "Bass", trip: trip1, caughtAt: Date(timeIntervalSince1970: 200)),
            CatchRecord(species: "Pike", trip: trip2, caughtAt: Date(timeIntervalSince1970: 10_500)),
        ]
        let spots = FishingStatsLogic.topSpots(catches: catches, limit: 5)
        XCTAssertEqual(spots.first?.label, "Alki")
        XCTAssertEqual(spots.first?.count, 2)
    }

    // MARK: - Disposition

    func testDispositionBreakdownCountsEachCategory() {
        let trip = makeCompletedTrip(id: "A", start: Date(timeIntervalSince1970: 0), end: Date(timeIntervalSince1970: 3_600), outcome: .caught)
        let catches = [
            CatchRecord(species: "Bass", trip: trip, caughtAt: Date(timeIntervalSince1970: 100), disposition: .released),
            CatchRecord(species: "Bass", trip: trip, caughtAt: Date(timeIntervalSince1970: 200), disposition: .released),
            CatchRecord(species: "Pike", trip: trip, caughtAt: Date(timeIntervalSince1970: 300), disposition: .kept),
            CatchRecord(species: "Trout", trip: trip, caughtAt: Date(timeIntervalSince1970: 400)),
        ]
        let disposition = FishingStatsLogic.dispositionBreakdown(catches: catches)
        XCTAssertEqual(disposition.released, 2)
        XCTAssertEqual(disposition.kept, 1)
        XCTAssertEqual(disposition.unknown, 1)
        XCTAssertEqual(disposition.total, 4)
    }

    // MARK: - Activity highlights

    func testActivityPicksHeaviestAndLongestCatch() {
        let trip = makeCompletedTrip(id: "A", start: Date(timeIntervalSince1970: 0), end: Date(timeIntervalSince1970: 3_600), outcome: .caught)
        let big = CatchRecord(
            species: "Pike",
            trip: trip,
            caughtAt: Date(timeIntervalSince1970: 100),
            weightKg: 4.0,
            lengthCm: 60
        )
        let small = CatchRecord(
            species: "Bass",
            trip: trip,
            caughtAt: Date(timeIntervalSince1970: 200),
            weightKg: 1.0,
            lengthCm: 30
        )

        let stats = FishingStatsLogic.build(trips: [trip], catches: [big, small], personalBests: [])

        XCTAssertEqual(stats.activity.biggestByWeight?.species, "Pike")
        XCTAssertEqual(stats.activity.biggestByWeight?.value ?? 0, 4.0, accuracy: 0.01)
        XCTAssertEqual(stats.activity.longestByLength?.species, "Pike")
        XCTAssertEqual(stats.activity.longestByLength?.value ?? 0, 60, accuracy: 0.01)
        XCTAssertEqual(stats.activity.distinctSpecies, 2)
    }

    // MARK: - Monthly breakdown

    func testMonthlyBreakdownCoversTwelveMonthsEndingAtNow() {
        let calendar = Calendar(identifier: .gregorian)
        let now = Date(timeIntervalSince1970: 1_700_000_000) // mid-Nov 2023

        let trip = makeCompletedTrip(
            id: "A",
            start: Date(timeIntervalSince1970: 1_699_000_000),
            end: Date(timeIntervalSince1970: 1_699_010_000),
            outcome: .caught
        )
        let record = CatchRecord(
            species: "Bass",
            trip: trip,
            caughtAt: Date(timeIntervalSince1970: 1_699_005_000)
        )

        let months = FishingStatsLogic.monthlyBreakdown(
            trips: [trip],
            catches: [record],
            now: now,
            calendar: calendar
        )
        XCTAssertEqual(months.count, 12)
        let totalCatches = months.reduce(0) { $0 + $1.catchCount }
        XCTAssertEqual(totalCatches, 1)
    }

    // MARK: - Helpers

    private func makeCompletedTrip(id: String, start: Date, end: Date, outcome: TripOutcome) -> Trip {
        let trip = Trip(waterbody: nil, targetSpecies: id, startAt: start)
        trip.endAt = end
        trip.outcomeRawValue = outcome.rawValue
        return trip
    }
}
