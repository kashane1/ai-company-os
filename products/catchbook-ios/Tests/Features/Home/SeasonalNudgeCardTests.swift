import XCTest
@testable import Catchbook

final class SeasonalNudgeCardTests: XCTestCase {
    private func utcCalendar() -> Calendar {
        var calendar = Calendar(identifier: .gregorian)
        calendar.timeZone = TimeZone(secondsFromGMT: 0)!
        return calendar
    }

    private func utcDate(year: Int, month: Int, day: Int, hour: Int = 12, minute: Int = 0) -> Date {
        utcCalendar().date(from: DateComponents(year: year, month: month, day: day, hour: hour, minute: minute))!
    }

    private func makeTrip(
        spot: Spot? = nil,
        waterbody: Waterbody? = nil,
        startAt: Date,
        endAt: Date? = nil
    ) -> Trip {
        let wb = waterbody ?? Waterbody(name: "Lake", type: .lake)
        let trip = Trip(waterbody: wb, spot: spot, startAt: startAt)
        trip.endAt = endAt ?? startAt.addingTimeInterval(3600)
        return trip
    }

    private func makeCatch(
        species: String = "Bass",
        trip: Trip,
        caughtAt: Date? = nil,
        weightKg: Double? = nil,
        lengthCm: Double? = nil
    ) -> CatchRecord {
        CatchRecord(
            species: species,
            trip: trip,
            caughtAt: caughtAt ?? trip.startAt.addingTimeInterval(600),
            weightKg: weightKg,
            lengthCm: lengthCm
        )
    }

    // MARK: - PB Anniversary Tests

    func testPBAnniversaryFiresWhenCatchWasSet365DaysAgo() {
        let calendar = utcCalendar()
        let now = utcDate(year: 2026, month: 4, day: 11)
        let lastYear = utcDate(year: 2025, month: 4, day: 11)

        let spot = Spot(title: "Dock", waterbody: Waterbody(name: "Lake", type: .lake))
        let trip = makeTrip(spot: spot, startAt: lastYear)
        let catchRecord = makeCatch(species: "Bass", trip: trip, caughtAt: lastYear, lengthCm: 55)

        let pb = PersonalBest(
            species: "Bass",
            longestLengthCm: 55,
            longestCatchID: catchRecord.id,
            updatedAt: lastYear
        )

        let cards = HomeDashboardLogic.seasonalNudgeCards(
            trips: [trip],
            catches: [catchRecord],
            personalBests: [pb],
            now: now,
            calendar: calendar
        )

        XCTAssertFalse(cards.isEmpty, "Should produce a PB anniversary card")
        XCTAssertEqual(cards.first?.kind, .pbAnniversary)
        XCTAssertTrue(cards.first?.body.contains("55") ?? false)
        XCTAssertTrue(cards.first?.body.contains("Bass") ?? false)
    }

    func testPBAnniversaryFiresWithin7DayWindow() {
        let calendar = utcCalendar()
        let now = utcDate(year: 2026, month: 4, day: 11)
        let catchDate = utcDate(year: 2025, month: 4, day: 5) // 6 days off

        let spot = Spot(title: "Dock", waterbody: Waterbody(name: "Lake", type: .lake))
        let trip = makeTrip(spot: spot, startAt: catchDate)
        let catchRecord = makeCatch(species: "Trout", trip: trip, caughtAt: catchDate, weightKg: 2.5)

        let pb = PersonalBest(
            species: "Trout",
            heaviestWeightKg: 2.5,
            heaviestCatchID: catchRecord.id,
            updatedAt: catchDate
        )

        let cards = HomeDashboardLogic.seasonalNudgeCards(
            trips: [trip],
            catches: [catchRecord],
            personalBests: [pb],
            now: now,
            calendar: calendar
        )

        XCTAssertFalse(cards.isEmpty, "Should fire within ±7 day window")
        XCTAssertEqual(cards.first?.kind, .pbAnniversary)
    }

    func testPBAnniversaryDoesNotFireForCatch200DaysAgo() {
        let calendar = utcCalendar()
        let now = utcDate(year: 2026, month: 4, day: 11)
        let catchDate = utcDate(year: 2025, month: 9, day: 23) // ~200 days ago, different month

        let spot = Spot(title: "Dock", waterbody: Waterbody(name: "Lake", type: .lake))
        let trip = makeTrip(spot: spot, startAt: catchDate)
        let catchRecord = makeCatch(species: "Bass", trip: trip, caughtAt: catchDate, lengthCm: 55)

        let pb = PersonalBest(
            species: "Bass",
            longestLengthCm: 55,
            longestCatchID: catchRecord.id,
            updatedAt: catchDate
        )

        let cards = HomeDashboardLogic.seasonalNudgeCards(
            trips: [trip],
            catches: [catchRecord],
            personalBests: [pb],
            now: now,
            calendar: calendar
        )

        let pbCards = cards.filter { $0.kind == .pbAnniversary }
        XCTAssertTrue(pbCards.isEmpty, "Should NOT fire for a catch ~200 days ago")
    }

    // MARK: - Seasonal Spot Tests

    func testSeasonalSpotFiresWithThreeOrMoreProductiveTrips() {
        let calendar = utcCalendar()
        let now = utcDate(year: 2026, month: 4, day: 11) // April = spring

        let spot = Spot(title: "River Bend", waterbody: Waterbody(name: "River", type: .river))

        // 3 productive spring trips across different years
        let trip1 = makeTrip(spot: spot, startAt: utcDate(year: 2023, month: 4, day: 10))
        let trip2 = makeTrip(spot: spot, startAt: utcDate(year: 2024, month: 5, day: 15))
        let trip3 = makeTrip(spot: spot, startAt: utcDate(year: 2025, month: 3, day: 20))

        let catches = [
            makeCatch(trip: trip1), makeCatch(trip: trip2), makeCatch(trip: trip3),
        ]

        let cards = HomeDashboardLogic.seasonalNudgeCards(
            trips: [trip1, trip2, trip3],
            catches: catches,
            personalBests: [],
            now: now,
            calendar: calendar
        )

        let seasonalCards = cards.filter { $0.kind == .seasonalSpot }
        XCTAssertEqual(seasonalCards.count, 1)
        // Spot name lives in the title ("Spring at River Bend"), season in the body.
        XCTAssertTrue(seasonalCards.first?.title.contains("River Bend") ?? false)
        XCTAssertTrue(seasonalCards.first?.body.contains("Spring") ?? false)
    }

    func testSeasonalSpotDoesNotFireWithOnly2ProductiveTrips() {
        let calendar = utcCalendar()
        let now = utcDate(year: 2026, month: 4, day: 11) // spring

        let spot = Spot(title: "River Bend", waterbody: Waterbody(name: "River", type: .river))

        let trip1 = makeTrip(spot: spot, startAt: utcDate(year: 2024, month: 4, day: 10))
        let trip2 = makeTrip(spot: spot, startAt: utcDate(year: 2025, month: 5, day: 15))

        let catches = [makeCatch(trip: trip1), makeCatch(trip: trip2)]

        let cards = HomeDashboardLogic.seasonalNudgeCards(
            trips: [trip1, trip2],
            catches: catches,
            personalBests: [],
            now: now,
            calendar: calendar
        )

        let seasonalCards = cards.filter { $0.kind == .seasonalSpot }
        XCTAssertTrue(seasonalCards.isEmpty, "Should NOT fire with only 2 productive trips")
    }

    // MARK: - Same-Month-Last-Year Tests

    func testSameMonthLastYearFiresWhenProductiveTripExistsInPriorYear() {
        let calendar = utcCalendar()
        let now = utcDate(year: 2026, month: 4, day: 11)
        let lastApril = utcDate(year: 2025, month: 4, day: 20)

        let spot = Spot(title: "Cove", waterbody: Waterbody(name: "Lake", type: .lake))
        let trip = makeTrip(spot: spot, startAt: lastApril)
        let catchRecord = makeCatch(trip: trip, caughtAt: lastApril)

        let cards = HomeDashboardLogic.seasonalNudgeCards(
            trips: [trip],
            catches: [catchRecord],
            personalBests: [],
            now: now,
            calendar: calendar
        )

        let monthCards = cards.filter { $0.kind == .sameMonthLastYear }
        XCTAssertEqual(monthCards.count, 1)
        XCTAssertTrue(monthCards.first?.body.contains("Cove") ?? false)
    }

    // MARK: - Max Cards Limit

    func testMaxTwoCardsReturnedEvenWhenAllConditionsMet() {
        let calendar = utcCalendar()
        let now = utcDate(year: 2026, month: 4, day: 11) // spring

        let spot = Spot(title: "Dock", waterbody: Waterbody(name: "Lake", type: .lake))

        // PB anniversary — catch exactly 1 year ago
        let pbTrip = makeTrip(spot: spot, startAt: utcDate(year: 2025, month: 4, day: 11))
        let pbCatch = makeCatch(species: "Bass", trip: pbTrip, caughtAt: utcDate(year: 2025, month: 4, day: 11), lengthCm: 60)
        let pb = PersonalBest(species: "Bass", longestLengthCm: 60, longestCatchID: pbCatch.id, updatedAt: utcDate(year: 2025, month: 4, day: 11))

        // Same month last year (different trip)
        let lastYearTrip = makeTrip(spot: spot, startAt: utcDate(year: 2025, month: 4, day: 20))
        let lastYearCatch = makeCatch(trip: lastYearTrip, caughtAt: utcDate(year: 2025, month: 4, day: 20))

        // 3 spring productive trips for seasonal spot
        let springTrip1 = makeTrip(spot: spot, startAt: utcDate(year: 2023, month: 3, day: 15))
        let springTrip2 = makeTrip(spot: spot, startAt: utcDate(year: 2024, month: 4, day: 10))
        let springTrip3 = makeTrip(spot: spot, startAt: utcDate(year: 2024, month: 5, day: 5))
        let springCatches = [
            makeCatch(trip: springTrip1), makeCatch(trip: springTrip2), makeCatch(trip: springTrip3),
        ]

        let allTrips = [pbTrip, lastYearTrip, springTrip1, springTrip2, springTrip3]
        let allCatches = [pbCatch, lastYearCatch] + springCatches

        let cards = HomeDashboardLogic.seasonalNudgeCards(
            trips: allTrips,
            catches: allCatches,
            personalBests: [pb],
            now: now,
            calendar: calendar
        )

        XCTAssertLessThanOrEqual(cards.count, 2, "Should return at most 2 cards")
    }

    // MARK: - Empty State

    func testEmptyArrayReturnedWhenUserHasNoTrips() {
        let calendar = utcCalendar()
        let now = utcDate(year: 2026, month: 4, day: 11)

        let cards = HomeDashboardLogic.seasonalNudgeCards(
            trips: [],
            catches: [],
            personalBests: [],
            now: now,
            calendar: calendar
        )

        XCTAssertTrue(cards.isEmpty, "Should return empty array when no trips exist")
    }

    func testEmptyArrayReturnedWhenOnlyActiveTripsExist() {
        let calendar = utcCalendar()
        let now = utcDate(year: 2026, month: 4, day: 11)

        let trip = Trip(waterbody: Waterbody(name: "Lake", type: .lake), startAt: now)
        // Active — no endAt set

        let cards = HomeDashboardLogic.seasonalNudgeCards(
            trips: [trip],
            catches: [],
            personalBests: [],
            now: now,
            calendar: calendar
        )

        XCTAssertTrue(cards.isEmpty, "Should return empty array when only active trips exist")
    }
}
