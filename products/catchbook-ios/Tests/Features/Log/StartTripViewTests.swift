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

        let selectedTrip = Trip(
            waterbody: waterbody,
            spot: selectedSpot,
            startAt: utcDate(year: 2025, month: 1, day: 3, hour: 6)
        )
        selectedTrip.endAt = utcDate(year: 2025, month: 1, day: 3, hour: 8)

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
        ]

        let card = HomeDashboardLogic.lastTimeHereCard(
            trip: selectedTrip,
            catches: catches,
            calendar: utcCalendar()
        )

        XCTAssertEqual(card?.title, "Last time at Dock")
        XCTAssertNotNil(card?.body)
    }

    func testLastTimeHereCardReturnsNilWhenTripIsNil() {
        let card = HomeDashboardLogic.lastTimeHereCard(
            trip: nil,
            catches: [],
            calendar: utcCalendar()
        )

        XCTAssertNil(card)
    }

    func testLastTimeHereCardReturnsNilWhenTripHasNoSpot() {
        let waterbody = Waterbody(name: "Lake", type: .lake)
        let spotlessTrip = Trip(
            waterbody: waterbody,
            spot: nil,
            startAt: utcDate(year: 2025, month: 1, day: 3, hour: 6)
        )

        let card = HomeDashboardLogic.lastTimeHereCard(
            trip: spotlessTrip,
            catches: [],
            calendar: utcCalendar()
        )

        XCTAssertNil(card)
    }
}
