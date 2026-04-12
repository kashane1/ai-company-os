import Foundation
import MapKit
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

    func testWaterbodySummariesReturnCountsPerWaterbody() {
        let lake = Waterbody(name: "Lake", type: .lake, latitude: 47.6, longitude: -122.3)
        let river = Waterbody(name: "River", type: .river, latitude: 47.7, longitude: -122.2)
        let lakeSpotA = Spot(title: "Dock", waterbody: lake, latitude: 47.61, longitude: -122.31)
        let lakeSpotB = Spot(title: "Point", waterbody: lake, latitude: 47.62, longitude: -122.32)
        let riverSpot = Spot(title: "Bend", waterbody: river, latitude: 47.71, longitude: -122.21)
        let lakeTripA = Trip(waterbody: lake, spot: lakeSpotA, startAt: utcDate(year: 2025, month: 5, day: 1))
        let lakeTripB = Trip(waterbody: lake, spot: lakeSpotB, startAt: utcDate(year: 2025, month: 5, day: 2))
        let riverTrip = Trip(waterbody: river, spot: riverSpot, startAt: utcDate(year: 2025, month: 5, day: 3))
        let catches = [
            CatchRecord(species: "Bass", trip: lakeTripA),
            CatchRecord(species: "Bass", trip: lakeTripB),
            CatchRecord(species: "Trout", trip: riverTrip),
            CatchRecord(species: "Trout", trip: riverTrip),
        ]

        let summaries = TripHistoryLogic.waterbodySummaries(
            trips: [lakeTripA, lakeTripB, riverTrip],
            catches: catches,
            spots: [lakeSpotA, lakeSpotB, riverSpot],
            waterbodies: [lake, river]
        )

        let byID = Dictionary(uniqueKeysWithValues: summaries.map { ($0.waterbodyID, $0) })
        XCTAssertEqual(summaries.count, 2)
        XCTAssertEqual(byID[lake.id]?.tripCount, 2)
        XCTAssertEqual(byID[lake.id]?.catchCount, 2)
        XCTAssertEqual(byID[lake.id]?.spotCount, 2)
        XCTAssertEqual(byID[river.id]?.tripCount, 1)
        XCTAssertEqual(byID[river.id]?.catchCount, 2)
        XCTAssertEqual(byID[river.id]?.spotCount, 1)
    }

    func testWaterbodySummariesUseWaterbodyCoordinatesWhenAvailable() {
        let lake = Waterbody(name: "Lake", type: .lake, latitude: 47.6, longitude: -122.3)
        let spot = Spot(title: "Dock", waterbody: lake, latitude: 40.0, longitude: -120.0)
        let trip = Trip(waterbody: lake, spot: spot)

        let summaries = TripHistoryLogic.waterbodySummaries(
            trips: [trip],
            catches: [],
            spots: [spot],
            waterbodies: [lake]
        )

        XCTAssertEqual(summaries.count, 1)
        XCTAssertEqual(summaries[0].coordinate.latitude, 47.6, accuracy: 0.0001)
        XCTAssertEqual(summaries[0].coordinate.longitude, -122.3, accuracy: 0.0001)
        XCTAssertEqual(summaries[0].coordinateSource, .canonicalWaterbody)
    }

    func testWaterbodySummariesFallBackToSpotCentroid() {
        let lake = Waterbody(name: "Lake", type: .lake)
        let spotA = Spot(title: "Dock", waterbody: lake, latitude: 47.0, longitude: -122.0)
        let spotB = Spot(title: "Point", waterbody: lake, latitude: 49.0, longitude: -120.0)
        let trip = Trip(waterbody: lake, spot: spotA)

        let summaries = TripHistoryLogic.waterbodySummaries(
            trips: [trip],
            catches: [],
            spots: [spotA, spotB],
            waterbodies: [lake]
        )

        XCTAssertEqual(summaries.count, 1)
        XCTAssertEqual(summaries[0].coordinate.latitude, 48.0, accuracy: 0.0001)
        XCTAssertEqual(summaries[0].coordinate.longitude, -121.0, accuracy: 0.0001)
        XCTAssertEqual(summaries[0].coordinateSource, .legacySpotCentroid)
    }

    func testWaterbodySummariesOmitWatersWithoutResolvableCoordinates() {
        let lake = Waterbody(name: "Lake", type: .lake)
        let drySpot = Spot(title: "Dock", waterbody: lake)
        let trip = Trip(waterbody: lake, spot: drySpot)

        let summaries = TripHistoryLogic.waterbodySummaries(
            trips: [trip],
            catches: [],
            spots: [drySpot],
            waterbodies: [lake]
        )

        XCTAssertTrue(summaries.isEmpty)
    }

    func testWaterbodySummariesReturnEmptyArrayWhenNoTripsExist() {
        let lake = Waterbody(name: "Lake", type: .lake, latitude: 47.6, longitude: -122.3)
        let spot = Spot(title: "Dock", waterbody: lake, latitude: 47.61, longitude: -122.31)

        let summaries = TripHistoryLogic.waterbodySummaries(
            trips: [],
            catches: [],
            spots: [spot],
            waterbodies: [lake]
        )

        XCTAssertTrue(summaries.isEmpty)
    }

    func testWaterbodySummariesUseMostRecentTripDatePerWaterbody() {
        let lake = Waterbody(name: "Lake", type: .lake, latitude: 47.6, longitude: -122.3)
        let spot = Spot(title: "Dock", waterbody: lake, latitude: 47.61, longitude: -122.31)
        let olderTrip = Trip(waterbody: lake, spot: spot, startAt: utcDate(year: 2025, month: 4, day: 10))
        let newerTrip = Trip(waterbody: lake, spot: spot, startAt: utcDate(year: 2025, month: 5, day: 10))

        let summaries = TripHistoryLogic.waterbodySummaries(
            trips: [olderTrip, newerTrip],
            catches: [],
            spots: [spot],
            waterbodies: [lake]
        )

        XCTAssertEqual(summaries.count, 1)
        XCTAssertEqual(summaries[0].lastTripDate, utcDate(year: 2025, month: 5, day: 10))
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
