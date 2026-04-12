import XCTest
@testable import Catchbook

final class StartTripViewTests: XCTestCase {
    private func utcCalendar() -> Calendar {
        var calendar = Calendar(identifier: .gregorian)
        calendar.timeZone = TimeZone(secondsFromGMT: 0)!
        return calendar
    }

    private func utcDate(year: Int, month: Int, day: Int, hour: Int, minute: Int = 0) -> Date {
        utcCalendar().date(from: DateComponents(year: year, month: month, day: day, hour: hour, minute: minute))!
    }

    func testLastTimeHereCardBuildsReplayCopyForSelectedSpot() {
        let waterbody = Waterbody(name: "Lake", type: .lake)
        let selectedSpot = Spot(title: "Dock", waterbody: waterbody)
        let otherSpot = Spot(title: "Reeds", waterbody: waterbody)

        let selectedTrip = Trip(
            waterbody: waterbody,
            spot: selectedSpot,
            startAt: utcDate(year: 2025, month: 1, day: 3, hour: 6)
        )
        selectedTrip.endAt = utcDate(year: 2025, month: 1, day: 3, hour: 8)

        let activeTrip = Trip(
            waterbody: waterbody,
            spot: selectedSpot,
            startAt: utcDate(year: 2025, month: 1, day: 4, hour: 6)
        )

        let otherSpotTrip = Trip(
            waterbody: waterbody,
            spot: otherSpot,
            startAt: utcDate(year: 2025, month: 1, day: 2, hour: 6)
        )
        otherSpotTrip.endAt = utcDate(year: 2025, month: 1, day: 2, hour: 8)

        let catches = [
            CatchRecord(
                species: "Bass",
                trip: selectedTrip,
                caughtAt: utcDate(year: 2025, month: 1, day: 3, hour: 6, minute: 10),
                lureOrBait: "Spinner"
            ),
            CatchRecord(
                species: "Bass",
                trip: selectedTrip,
                caughtAt: utcDate(year: 2025, month: 1, day: 3, hour: 6, minute: 20),
                lureOrBait: "Spinner"
            ),
            CatchRecord(
                species: "Perch",
                trip: otherSpotTrip,
                caughtAt: utcDate(year: 2025, month: 1, day: 2, hour: 6, minute: 15),
                lureOrBait: "Spoon"
            ),
        ]

        let card = StartTripView.lastTimeHereCard(
            selectedSpotID: selectedSpot.id,
            trips: [activeTrip, selectedTrip, otherSpotTrip],
            catches: catches,
            calendar: utcCalendar()
        )

        XCTAssertEqual(card?.title, "Last time at Dock")
        XCTAssertEqual(card?.body, "2 catches · Top species Bass")
        XCTAssertEqual(card?.footer, "Top lure Spinner · 6-9 AM")
    }

    func testLastTimeHereCardReturnsNilWhenSpotIsNotSelected() {
        let card = StartTripView.lastTimeHereCard(
            selectedSpotID: nil,
            trips: [],
            catches: [],
            calendar: utcCalendar()
        )

        XCTAssertNil(card)
    }
}
