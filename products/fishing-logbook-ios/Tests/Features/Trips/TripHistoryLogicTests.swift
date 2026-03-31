import Foundation
import XCTest
@testable import Fishing_Logbook

final class TripHistoryLogicTests: XCTestCase {
    private func utcCalendar() -> Calendar {
        var calendar = Calendar(identifier: .gregorian)
        calendar.timeZone = TimeZone(secondsFromGMT: 0)!
        return calendar
    }

    func testAvailableWaterbodiesIncludesOnlyWatersUsedByTrips() {
        let lake = Waterbody(name: "Lake", type: .lake)
        let river = Waterbody(name: "River", type: .river)
        let coastal = Waterbody(name: "Coast", type: .coastal)
        let trip = Trip(waterbody: lake)
        let secondTrip = Trip(waterbody: river)

        let result = TripHistoryLogic.availableWaterbodies(
            waterbodies: [lake, river, coastal],
            trips: [trip, secondTrip]
        )

        XCTAssertEqual(result.map { $0.id }, [lake.id, river.id])
    }

    func testFilteredTripsMatchesSelectedWaterbody() {
        let lake = Waterbody(name: "Lake", type: .lake)
        let river = Waterbody(name: "River", type: .river)
        let lakeTrip = Trip(waterbody: lake, startAt: Date(timeIntervalSince1970: 100))
        let riverTrip = Trip(waterbody: river, startAt: Date(timeIntervalSince1970: 200))

        let result = TripHistoryLogic.filteredTrips(
            trips: [riverTrip, lakeTrip],
            catches: [],
            selectedWaterbodyID: lake.id,
            speciesQuery: "",
            dateFilter: .all
        )

        XCTAssertEqual(result.map { $0.id }, [lakeTrip.id])
    }

    func testFilteredTripsMatchesSpeciesAgainstTargetsAndCatches() {
        let waterbody = Waterbody(name: "Lake", type: .lake)
        let targetedTrip = Trip(
            waterbody: waterbody,
            targetSpecies: "Smallmouth Bass",
            startAt: Date(timeIntervalSince1970: 100)
        )
        let catchTrip = Trip(waterbody: waterbody, startAt: Date(timeIntervalSince1970: 200))
        let unmatchedTrip = Trip(waterbody: waterbody, startAt: Date(timeIntervalSince1970: 300))
        let catches = [
            CatchRecord(species: "Rainbow Trout", trip: catchTrip),
            CatchRecord(species: "Perch", trip: unmatchedTrip),
        ]

        let bassTrips = TripHistoryLogic.filteredTrips(
            trips: [unmatchedTrip, catchTrip, targetedTrip],
            catches: catches,
            selectedWaterbodyID: nil,
            speciesQuery: " bass ",
            dateFilter: .all
        )
        let troutTrips = TripHistoryLogic.filteredTrips(
            trips: [unmatchedTrip, catchTrip, targetedTrip],
            catches: catches,
            selectedWaterbodyID: nil,
            speciesQuery: "trout",
            dateFilter: .all
        )

        XCTAssertEqual(bassTrips.map { $0.id }, [targetedTrip.id])
        XCTAssertEqual(troutTrips.map { $0.id }, [catchTrip.id])
    }

    func testFilteredTripsMatchesDateWindowsDeterministically() {
        let waterbody = Waterbody(name: "Lake", type: .lake)
        let calendar = utcCalendar()
        let now = Date(timeIntervalSince1970: 1_736_899_200) // 2025-01-15 00:00:00 UTC
        let thisMonthTrip = Trip(waterbody: waterbody, startAt: Date(timeIntervalSince1970: 1_736_467_200)) // 2025-01-10
        let autumnTrip = Trip(waterbody: waterbody, startAt: Date(timeIntervalSince1970: 1_729_123_200)) // 2024-10-17
        let oldTrip = Trip(waterbody: waterbody, startAt: Date(timeIntervalSince1970: 1_703_635_200)) // 2023-12-27

        let last30Days = TripHistoryLogic.filteredTrips(
            trips: [thisMonthTrip, autumnTrip, oldTrip],
            catches: [],
            selectedWaterbodyID: nil,
            speciesQuery: "",
            dateFilter: .last30Days,
            now: now,
            calendar: calendar
        )
        let last90Days = TripHistoryLogic.filteredTrips(
            trips: [thisMonthTrip, autumnTrip, oldTrip],
            catches: [],
            selectedWaterbodyID: nil,
            speciesQuery: "",
            dateFilter: .last90Days,
            now: now,
            calendar: calendar
        )
        let thisYear = TripHistoryLogic.filteredTrips(
            trips: [thisMonthTrip, autumnTrip, oldTrip],
            catches: [],
            selectedWaterbodyID: nil,
            speciesQuery: "",
            dateFilter: .thisYear,
            now: now,
            calendar: calendar
        )

        XCTAssertEqual(last30Days.map { $0.id }, [thisMonthTrip.id])
        XCTAssertEqual(last90Days.map { $0.id }, [thisMonthTrip.id, autumnTrip.id])
        XCTAssertEqual(thisYear.map { $0.id }, [thisMonthTrip.id])
    }

    func testHasActiveFiltersReflectsAnySelectedInput() {
        XCTAssertFalse(
            TripHistoryLogic.hasActiveFilters(
                selectedWaterbodyID: nil,
                speciesQuery: " ",
                dateFilter: .all
            )
        )
        XCTAssertTrue(
            TripHistoryLogic.hasActiveFilters(
                selectedWaterbodyID: UUID(),
                speciesQuery: "",
                dateFilter: .all
            )
        )
        XCTAssertTrue(
            TripHistoryLogic.hasActiveFilters(
                selectedWaterbodyID: nil,
                speciesQuery: "Bass",
                dateFilter: .all
            )
        )
        XCTAssertTrue(
            TripHistoryLogic.hasActiveFilters(
                selectedWaterbodyID: nil,
                speciesQuery: "",
                dateFilter: .last30Days
            )
        )
    }
}
