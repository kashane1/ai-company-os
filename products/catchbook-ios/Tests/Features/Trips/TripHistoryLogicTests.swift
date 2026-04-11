import Foundation
import XCTest
@testable import Catchbook

final class TripHistoryLogicTests: XCTestCase {
    private func utcCalendar() -> Calendar {
        var calendar = Calendar(identifier: .gregorian)
        calendar.timeZone = TimeZone(secondsFromGMT: 0)!
        return calendar
    }

    private func utcDate(year: Int, month: Int, day: Int) -> Date {
        utcCalendar().date(from: DateComponents(year: year, month: month, day: day))!
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
            dateFilter: .all,
            seasonFilter: .all,
            selectedLure: nil
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
            dateFilter: .all,
            seasonFilter: .all,
            selectedLure: nil
        )
        let troutTrips = TripHistoryLogic.filteredTrips(
            trips: [unmatchedTrip, catchTrip, targetedTrip],
            catches: catches,
            selectedWaterbodyID: nil,
            speciesQuery: "trout",
            dateFilter: .all,
            seasonFilter: .all,
            selectedLure: nil
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
            seasonFilter: .all,
            selectedLure: nil,
            now: now,
            calendar: calendar
        )
        let last90Days = TripHistoryLogic.filteredTrips(
            trips: [thisMonthTrip, autumnTrip, oldTrip],
            catches: [],
            selectedWaterbodyID: nil,
            speciesQuery: "",
            dateFilter: .last90Days,
            seasonFilter: .all,
            selectedLure: nil,
            now: now,
            calendar: calendar
        )
        let thisYear = TripHistoryLogic.filteredTrips(
            trips: [thisMonthTrip, autumnTrip, oldTrip],
            catches: [],
            selectedWaterbodyID: nil,
            speciesQuery: "",
            dateFilter: .thisYear,
            seasonFilter: .all,
            selectedLure: nil,
            now: now,
            calendar: calendar
        )

        XCTAssertEqual(last30Days.map { $0.id }, [thisMonthTrip.id])
        XCTAssertEqual(last90Days.map { $0.id }, [thisMonthTrip.id, autumnTrip.id])
        XCTAssertEqual(thisYear.map { $0.id }, [thisMonthTrip.id])
    }

    func testFilteredTripsMatchesSeasonAcrossAllSeasons() {
        let waterbody = Waterbody(name: "Lake", type: .lake)
        let calendar = utcCalendar()
        let springTrip = Trip(waterbody: waterbody, startAt: utcDate(year: 2025, month: 4, day: 10))
        let summerTrip = Trip(waterbody: waterbody, startAt: utcDate(year: 2025, month: 7, day: 10))
        let fallTrip = Trip(waterbody: waterbody, startAt: utcDate(year: 2025, month: 10, day: 10))
        let winterTrip = Trip(waterbody: waterbody, startAt: utcDate(year: 2025, month: 1, day: 10))

        let spring = TripHistoryLogic.filteredTrips(
            trips: [fallTrip, summerTrip, springTrip, winterTrip],
            catches: [],
            selectedWaterbodyID: nil,
            speciesQuery: "",
            dateFilter: .all,
            seasonFilter: .spring,
            selectedLure: nil,
            calendar: calendar
        )
        let summer = TripHistoryLogic.filteredTrips(
            trips: [fallTrip, summerTrip, springTrip, winterTrip],
            catches: [],
            selectedWaterbodyID: nil,
            speciesQuery: "",
            dateFilter: .all,
            seasonFilter: .summer,
            selectedLure: nil,
            calendar: calendar
        )
        let fall = TripHistoryLogic.filteredTrips(
            trips: [fallTrip, summerTrip, springTrip, winterTrip],
            catches: [],
            selectedWaterbodyID: nil,
            speciesQuery: "",
            dateFilter: .all,
            seasonFilter: .fall,
            selectedLure: nil,
            calendar: calendar
        )
        let winter = TripHistoryLogic.filteredTrips(
            trips: [fallTrip, summerTrip, springTrip, winterTrip],
            catches: [],
            selectedWaterbodyID: nil,
            speciesQuery: "",
            dateFilter: .all,
            seasonFilter: .winter,
            selectedLure: nil,
            calendar: calendar
        )

        XCTAssertEqual(spring.map(\.id), [springTrip.id])
        XCTAssertEqual(summer.map(\.id), [summerTrip.id])
        XCTAssertEqual(fall.map(\.id), [fallTrip.id])
        XCTAssertEqual(winter.map(\.id), [winterTrip.id])
    }

    func testFilteredTripsTreatsDecemberJanuaryAndFebruaryAsWinter() {
        let waterbody = Waterbody(name: "Lake", type: .lake)
        let calendar = utcCalendar()
        let decemberTrip = Trip(waterbody: waterbody, startAt: utcDate(year: 2024, month: 12, day: 15))
        let januaryTrip = Trip(waterbody: waterbody, startAt: utcDate(year: 2025, month: 1, day: 15))
        let februaryTrip = Trip(waterbody: waterbody, startAt: utcDate(year: 2025, month: 2, day: 15))
        let marchTrip = Trip(waterbody: waterbody, startAt: utcDate(year: 2025, month: 3, day: 15))

        let winterTrips = TripHistoryLogic.filteredTrips(
            trips: [marchTrip, februaryTrip, januaryTrip, decemberTrip],
            catches: [],
            selectedWaterbodyID: nil,
            speciesQuery: "",
            dateFilter: .all,
            seasonFilter: .winter,
            selectedLure: nil,
            calendar: calendar
        )

        XCTAssertEqual(winterTrips.map(\.id), [februaryTrip.id, januaryTrip.id, decemberTrip.id])
    }

    func testFilteredTripsMatchesSelectedLureCaseInsensitivelyAndExcludesBlankValues() {
        let waterbody = Waterbody(name: "Lake", type: .lake)
        let spinnerTrip = Trip(waterbody: waterbody, startAt: utcDate(year: 2025, month: 5, day: 10))
        let lowercaseSpinnerTrip = Trip(waterbody: waterbody, startAt: utcDate(year: 2025, month: 5, day: 9))
        let blankLureTrip = Trip(waterbody: waterbody, startAt: utcDate(year: 2025, month: 5, day: 8))
        let jigTrip = Trip(waterbody: waterbody, startAt: utcDate(year: 2025, month: 5, day: 7))

        let catches = [
            CatchRecord(species: "Bass", trip: jigTrip, lureOrBait: "Jig"),
            CatchRecord(species: "Bass", trip: blankLureTrip, lureOrBait: "   "),
            CatchRecord(species: "Bass", trip: lowercaseSpinnerTrip, lureOrBait: "spinner"),
            CatchRecord(species: "Bass", trip: spinnerTrip, lureOrBait: " Spinner "),
        ]

        let result = TripHistoryLogic.filteredTrips(
            trips: [jigTrip, blankLureTrip, lowercaseSpinnerTrip, spinnerTrip],
            catches: catches,
            selectedWaterbodyID: nil,
            speciesQuery: "",
            dateFilter: .all,
            seasonFilter: .all,
            selectedLure: "  SPINNER  "
        )

        XCTAssertEqual(result.map(\.id), [lowercaseSpinnerTrip.id, spinnerTrip.id])
    }

    func testAvailableLuresUsesCurrentNonLureFiltersAndKeepsTrimmedUniqueValues() {
        let waterbody = Waterbody(name: "Lake", type: .lake)
        let bassTrip = Trip(
            waterbody: waterbody,
            targetSpecies: "Bass",
            startAt: utcDate(year: 2025, month: 5, day: 10)
        )
        let troutTrip = Trip(
            waterbody: waterbody,
            targetSpecies: "Trout",
            startAt: utcDate(year: 2025, month: 5, day: 9)
        )
        let catches = [
            CatchRecord(species: "Trout", trip: troutTrip, lureOrBait: "Spoon"),
            CatchRecord(species: "Bass", trip: bassTrip, lureOrBait: " Spinner "),
            CatchRecord(species: "Bass", trip: bassTrip, lureOrBait: "spinner"),
            CatchRecord(species: "Bass", trip: bassTrip, lureOrBait: "Jig"),
            CatchRecord(species: "Bass", trip: bassTrip, lureOrBait: "   "),
        ]

        let result = TripHistoryLogic.availableLures(
            trips: [troutTrip, bassTrip],
            catches: catches,
            selectedWaterbodyID: nil,
            speciesQuery: " bass ",
            dateFilter: .all,
            seasonFilter: .all
        )

        XCTAssertEqual(result, ["Spinner", "Jig"])
    }

    func testHasActiveFiltersReflectsAnySelectedInput() {
        XCTAssertFalse(
            TripHistoryLogic.hasActiveFilters(
                selectedWaterbodyID: nil,
                speciesQuery: " ",
                dateFilter: .all,
                seasonFilter: .all,
                selectedLure: nil
            )
        )
        XCTAssertTrue(
            TripHistoryLogic.hasActiveFilters(
                selectedWaterbodyID: UUID(),
                speciesQuery: "",
                dateFilter: .all,
                seasonFilter: .all,
                selectedLure: nil
            )
        )
        XCTAssertTrue(
            TripHistoryLogic.hasActiveFilters(
                selectedWaterbodyID: nil,
                speciesQuery: "Bass",
                dateFilter: .all,
                seasonFilter: .all,
                selectedLure: nil
            )
        )
        XCTAssertTrue(
            TripHistoryLogic.hasActiveFilters(
                selectedWaterbodyID: nil,
                speciesQuery: "",
                dateFilter: .last30Days,
                seasonFilter: .all,
                selectedLure: nil
            )
        )
        XCTAssertTrue(
            TripHistoryLogic.hasActiveFilters(
                selectedWaterbodyID: nil,
                speciesQuery: "",
                dateFilter: .all,
                seasonFilter: .winter,
                selectedLure: nil
            )
        )
        XCTAssertTrue(
            TripHistoryLogic.hasActiveFilters(
                selectedWaterbodyID: nil,
                speciesQuery: "",
                dateFilter: .all,
                seasonFilter: .all,
                selectedLure: " Spinner "
            )
        )
    }

    func testSectionsGroupTripsBySpotAndOrderByMostRecentTrip() {
        let waterbody = Waterbody(name: "Lake", type: .lake)
        let northPoint = Spot(title: "North Point", waterbody: waterbody)
        let dock = Spot(title: "Dock", waterbody: waterbody)
        let latestDockTrip = Trip(waterbody: waterbody, spot: dock, startAt: utcDate(year: 2025, month: 7, day: 12))
        let earlierDockTrip = Trip(waterbody: waterbody, spot: dock, startAt: utcDate(year: 2025, month: 7, day: 10))
        let northPointTrip = Trip(waterbody: waterbody, spot: northPoint, startAt: utcDate(year: 2025, month: 7, day: 11))
        let generalTrip = Trip(waterbody: waterbody, startAt: utcDate(year: 2025, month: 7, day: 9))
        let catches = [
            CatchRecord(species: "Bass", trip: latestDockTrip),
            CatchRecord(species: "Bass", trip: latestDockTrip),
            CatchRecord(species: "Trout", trip: northPointTrip),
        ]

        let sections = TripHistoryLogic.sections(
            trips: [generalTrip, latestDockTrip, earlierDockTrip, northPointTrip],
            catches: catches
        )

        XCTAssertEqual(sections.map(\.title), ["Dock", "North Point", "General Area"])
        XCTAssertEqual(sections.first?.subtitle, "2 trips · 2 catches")
        XCTAssertEqual(sections.first?.trips.map(\.id), [latestDockTrip.id, earlierDockTrip.id])
        XCTAssertEqual(sections.last?.subtitle, "Trips without a saved spot still stay private and easy to revisit.")
    }
}
