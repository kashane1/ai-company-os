import Foundation
import XCTest
@testable import Catchbook

final class CatchHistoryLogicTests: XCTestCase {
    private func utcCalendar() -> Calendar {
        var calendar = Calendar(identifier: .gregorian)
        calendar.timeZone = TimeZone(secondsFromGMT: 0)!
        return calendar
    }

    private func utcDate(year: Int, month: Int, day: Int) -> Date {
        utcCalendar().date(from: DateComponents(year: year, month: month, day: day))!
    }

    func testFilteredCatchesMatchesQueryAcrossSpeciesLureNotesAndPlaceNames() {
        let waterbody = Waterbody(name: "Lake Union", type: .lake)
        let spot = Spot(title: "Dock Edge", waterbody: waterbody)
        let trip = Trip(waterbody: waterbody, spot: spot)
        let bass = CatchRecord(species: "Bass", trip: trip, lureOrBait: "Spinner", note: "Healthy fish")
        let trout = CatchRecord(species: "Trout", trip: trip, lureOrBait: "Spoon", note: "Deep water")

        XCTAssertEqual(
            CatchHistoryLogic.filteredCatches(
                catches: [bass, trout],
                filter: CatchHistoryFilter(query: "dock")
            ).map(\.id),
            [bass.id, trout.id]
        )

        XCTAssertEqual(
            CatchHistoryLogic.filteredCatches(
                catches: [bass, trout],
                filter: CatchHistoryFilter(query: "spinner")
            ).map(\.id),
            [bass.id]
        )
    }

    func testFilteredCatchesRespectsWaterDateSeasonAndLureFilters() {
        let calendar = utcCalendar()
        let now = utcDate(year: 2025, month: 1, day: 15)
        let lake = Waterbody(name: "Lake", type: .lake)
        let river = Waterbody(name: "River", type: .river)
        let lakeTrip = Trip(waterbody: lake)
        let riverTrip = Trip(waterbody: river)
        let recentLakeCatch = CatchRecord(species: "Bass", trip: lakeTrip, caughtAt: utcDate(year: 2025, month: 1, day: 10), lureOrBait: "Jig")
        let olderRiverCatch = CatchRecord(species: "Trout", trip: riverTrip, caughtAt: utcDate(year: 2024, month: 10, day: 1), lureOrBait: "Spoon")

        let results = CatchHistoryLogic.filteredCatches(
            catches: [olderRiverCatch, recentLakeCatch],
            filter: CatchHistoryFilter(
                query: "",
                selectedWaterbodyID: lake.id,
                dateFilter: .last30Days,
                seasonFilter: .winter,
                selectedLure: "Jig"
            ),
            now: now,
            calendar: calendar
        )

        XCTAssertEqual(results.map(\.id), [recentLakeCatch.id])
    }
}
