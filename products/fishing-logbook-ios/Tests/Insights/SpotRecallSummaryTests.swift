import XCTest
@testable import Fishing_Logbook

final class SpotRecallSummaryTests: XCTestCase {
    func testBuildAggregatesRecentTripsAndCatchInsights() {
        let waterbody = Waterbody(name: "River Bend", type: .river)
        let spot = Spot(title: "Dock", waterbody: waterbody)
        let olderTrip = Trip(
            waterbody: waterbody,
            spot: spot,
            conditionSnapshot: ConditionSnapshot(
                capturedAt: Date(timeIntervalSince1970: 1_711_700_000),
                timeWindowSummary: "6-9 AM",
                lightLevelSummary: "Morning light"
            ),
            startAt: Date(timeIntervalSince1970: 1_711_700_000)
        )
        let recentTrip = Trip(
            waterbody: waterbody,
            spot: spot,
            conditionSnapshot: ConditionSnapshot(
                capturedAt: Date(timeIntervalSince1970: 1_711_900_000),
                timeWindowSummary: "6-9 AM",
                lightLevelSummary: "Morning light"
            ),
            startAt: Date(timeIntervalSince1970: 1_711_900_000)
        )
        let offSpotTrip = Trip(
            waterbody: waterbody,
            spot: Spot(title: "Different", waterbody: waterbody),
            startAt: Date(timeIntervalSince1970: 1_711_950_000)
        )

        let catches = [
            CatchRecord(
                species: "Bass",
                trip: recentTrip,
                caughtAt: Date(timeIntervalSince1970: 1_711_900_100),
                lureOrBait: "Spinner"
            ),
            CatchRecord(
                species: "Bass",
                trip: recentTrip,
                caughtAt: Date(timeIntervalSince1970: 1_711_900_200),
                lureOrBait: "Spinner"
            ),
            CatchRecord(
                species: "Trout",
                trip: olderTrip,
                caughtAt: Date(timeIntervalSince1970: 1_711_700_100),
                lureOrBait: "Jig"
            ),
            CatchRecord(
                species: "Bass",
                trip: offSpotTrip,
                caughtAt: Date(timeIntervalSince1970: 1_711_950_100),
                lureOrBait: "Spoon"
            ),
        ]

        let summary = SpotRecallSummary.build(
            for: spot,
            trips: [olderTrip, recentTrip, offSpotTrip],
            catches: catches
        )

        XCTAssertEqual(summary.recentTrips.count, 2)
        XCTAssertEqual(summary.recentTrips.first?.id, recentTrip.id)
        XCTAssertEqual(summary.catchCount, 3)
        XCTAssertEqual(summary.successfulTripCount, 2)
        XCTAssertNil(summary.productivityInsight)
        XCTAssertEqual(summary.bestTimeWindow, "6-9 AM")
        XCTAssertEqual(summary.mostEffectiveLure, "Spinner")
        XCTAssertNil(summary.seasonalityInsight)
        XCTAssertEqual(summary.similarConditionsCount, 2)
        XCTAssertEqual(summary.similarConditionsLabel, "6-9 AM • Morning light")
        XCTAssertEqual(summary.cards.count, 4)
    }

    func testNormalizedSpeciesTokensDeduplicatesAndTrimsValues() {
        let tokens = normalizedSpeciesTokens(from: "Bass, trout\nBass ; Pike ; trout")

        XCTAssertEqual(tokens, ["Bass", "trout", "Pike"])
    }

    func testBuildReturnsEmptySummaryWhenSpotHasNoTripsOrCatches() {
        let waterbody = Waterbody(name: "River Bend", type: .river)
        let spot = Spot(title: "Dock", waterbody: waterbody)

        let summary = SpotRecallSummary.build(for: spot, trips: [], catches: [])

        XCTAssertTrue(summary.recentTrips.isEmpty)
        XCTAssertEqual(summary.catchCount, 0)
        XCTAssertEqual(summary.successfulTripCount, 0)
        XCTAssertNil(summary.productivityInsight)
        XCTAssertNil(summary.bestTimeWindow)
        XCTAssertNil(summary.mostEffectiveLure)
        XCTAssertNil(summary.seasonalityInsight)
        XCTAssertEqual(summary.similarConditionsCount, 0)
        XCTAssertNil(summary.similarConditionsLabel)
        XCTAssertTrue(summary.cards.isEmpty)
    }

    func testBuildKeepsOnlyThreeMostRecentTripsAndIgnoresBlankLures() {
        let waterbody = Waterbody(name: "River Bend", type: .river)
        let spot = Spot(title: "Dock", waterbody: waterbody)
        let trips = (0..<4).map { offset in
            let month = offset + 1
            return Trip(
                waterbody: waterbody,
                spot: spot,
                startAt: date(year: 2025, month: month, day: 10)
            )
        }
        let catches = [
            CatchRecord(species: "Bass", trip: trips[3], lureOrBait: "   "),
            CatchRecord(species: "Bass", trip: trips[2], lureOrBait: "Spinner"),
            CatchRecord(species: "Bass", trip: trips[1], lureOrBait: "Spinner"),
        ]

        let summary = SpotRecallSummary.build(for: spot, trips: trips, catches: catches)

        XCTAssertEqual(summary.recentTrips.count, 3)
        XCTAssertEqual(summary.recentTrips.map(\.id), [trips[3].id, trips[2].id, trips[1].id])
        XCTAssertNil(summary.productivityInsight)
        XCTAssertEqual(summary.mostEffectiveLure, "Spinner")
        XCTAssertNil(summary.seasonalityInsight)
    }

    func testBuildPrefersConditionSimilarityDescriptionOverTimeWindowFallback() {
        let waterbody = Waterbody(name: "River Bend", type: .river)
        let spot = Spot(title: "Dock", waterbody: waterbody)
        let trip = Trip(
            waterbody: waterbody,
            spot: spot,
            conditionSnapshot: ConditionSnapshot(
                capturedAt: Date(timeIntervalSince1970: 1_711_900_000),
                timeWindowSummary: "6-9 AM",
                lightLevelSummary: "Morning light",
                windSummary: "10 kt",
                precipitationSummary: "Dry"
            ),
            startAt: Date(timeIntervalSince1970: 1_711_900_000)
        )
        let catches = [
            CatchRecord(
                species: "Bass",
                trip: trip,
                caughtAt: Date(timeIntervalSince1970: 1_711_900_100),
                lureOrBait: "Spinner"
            )
        ]

        let summary = SpotRecallSummary.build(for: spot, trips: [trip], catches: catches)

        XCTAssertEqual(summary.similarConditionsLabel, "6-9 AM • Morning light • 10 kt • Dry")
        XCTAssertEqual(summary.similarConditionsCount, 1)
    }

    func testBuildAddsProductivityCardForStrongRecentSuccessPattern() {
        let waterbody = Waterbody(name: "River Bend", type: .river)
        let spot = Spot(title: "Dock", waterbody: waterbody)
        let trips = [
            completedTrip(waterbody: waterbody, spot: spot, year: 2025, month: 6, day: 10),
            completedTrip(waterbody: waterbody, spot: spot, year: 2025, month: 6, day: 5),
            completedTrip(waterbody: waterbody, spot: spot, year: 2025, month: 5, day: 28),
            completedTrip(waterbody: waterbody, spot: spot, year: 2025, month: 5, day: 20),
            completedTrip(waterbody: waterbody, spot: spot, year: 2025, month: 5, day: 12),
        ]
        let catches = [
            CatchRecord(species: "Bass", trip: trips[0], caughtAt: trips[0].startAt),
            CatchRecord(species: "Bass", trip: trips[1], caughtAt: trips[1].startAt),
            CatchRecord(species: "Bass", trip: trips[2], caughtAt: trips[2].startAt),
            CatchRecord(species: "Bass", trip: trips[3], caughtAt: trips[3].startAt),
        ]

        let summary = SpotRecallSummary.build(for: spot, trips: trips, catches: catches)

        XCTAssertEqual(summary.productivityInsight?.title, "Recent success here")
        XCTAssertEqual(
            summary.productivityInsight?.body,
            "You caught fish on 4 of your last 5 completed trips here."
        )
        XCTAssertEqual(summary.productivityInsight?.supportingSampleCount, 5)
        XCTAssertEqual(summary.cards.dropFirst().first?.kind, .productivity)
    }

    func testBuildAddsProductivityCardForAllProductiveRecentTrips() {
        let waterbody = Waterbody(name: "River Bend", type: .river)
        let spot = Spot(title: "Dock", waterbody: waterbody)
        let trips = [
            completedTrip(waterbody: waterbody, spot: spot, year: 2025, month: 7, day: 8),
            completedTrip(waterbody: waterbody, spot: spot, year: 2025, month: 7, day: 1),
            completedTrip(waterbody: waterbody, spot: spot, year: 2025, month: 6, day: 24),
        ]
        let catches = trips.map { trip in
            CatchRecord(species: "Bass", trip: trip, caughtAt: trip.startAt)
        }

        let summary = SpotRecallSummary.build(for: spot, trips: trips, catches: catches)

        XCTAssertEqual(
            summary.productivityInsight?.body,
            "You caught fish on all 3 of your last 3 completed trips here."
        )
        XCTAssertEqual(summary.productivityInsight?.supportingSampleCount, 3)
    }

    func testBuildAddsProductivityCardForRecentSkunkPattern() {
        let waterbody = Waterbody(name: "River Bend", type: .river)
        let spot = Spot(title: "Dock", waterbody: waterbody)
        let trips = [
            completedTrip(waterbody: waterbody, spot: spot, year: 2025, month: 9, day: 14),
            completedTrip(waterbody: waterbody, spot: spot, year: 2025, month: 9, day: 7),
            completedTrip(waterbody: waterbody, spot: spot, year: 2025, month: 8, day: 31),
        ]

        let summary = SpotRecallSummary.build(for: spot, trips: trips, catches: [])

        XCTAssertEqual(
            summary.productivityInsight?.body,
            "Your last 3 completed trips here ended without a catch."
        )
        XCTAssertEqual(summary.productivityInsight?.supportingSampleCount, 3)
    }

    func testBuildSuppressesProductivityCardWhenSupportIsTooThin() {
        let waterbody = Waterbody(name: "River Bend", type: .river)
        let spot = Spot(title: "Dock", waterbody: waterbody)
        let trips = [
            completedTrip(waterbody: waterbody, spot: spot, year: 2025, month: 4, day: 3),
            completedTrip(waterbody: waterbody, spot: spot, year: 2025, month: 3, day: 27),
        ]
        let catches = [
            CatchRecord(species: "Bass", trip: trips[0], caughtAt: trips[0].startAt)
        ]

        let summary = SpotRecallSummary.build(for: spot, trips: trips, catches: catches)

        XCTAssertNil(summary.productivityInsight)
        XCTAssertNil(summary.cards.first(where: { $0.kind == .productivity }))
    }

    func testBuildSuppressesProductivityCardWhenRecentCompletedTripsAreMixed() {
        let waterbody = Waterbody(name: "River Bend", type: .river)
        let spot = Spot(title: "Dock", waterbody: waterbody)
        let trips = [
            completedTrip(waterbody: waterbody, spot: spot, year: 2025, month: 10, day: 9),
            completedTrip(waterbody: waterbody, spot: spot, year: 2025, month: 10, day: 2),
            completedTrip(waterbody: waterbody, spot: spot, year: 2025, month: 9, day: 25),
            completedTrip(waterbody: waterbody, spot: spot, year: 2025, month: 9, day: 18),
            completedTrip(waterbody: waterbody, spot: spot, year: 2025, month: 9, day: 11),
        ]
        let catches = [
            CatchRecord(species: "Bass", trip: trips[0], caughtAt: trips[0].startAt),
            CatchRecord(species: "Bass", trip: trips[1], caughtAt: trips[1].startAt),
            CatchRecord(species: "Bass", trip: trips[2], caughtAt: trips[2].startAt),
        ]

        let summary = SpotRecallSummary.build(for: spot, trips: trips, catches: catches)

        XCTAssertNil(summary.productivityInsight)
        XCTAssertNil(summary.cards.first(where: { $0.kind == .productivity }))
    }

    func testBuildIgnoresActiveTripsForProductivityWindow() {
        let waterbody = Waterbody(name: "River Bend", type: .river)
        let spot = Spot(title: "Dock", waterbody: waterbody)
        let activeTrip = Trip(
            waterbody: waterbody,
            spot: spot,
            startAt: date(year: 2025, month: 11, day: 12)
        )
        let completedTrips = [
            completedTrip(waterbody: waterbody, spot: spot, year: 2025, month: 11, day: 5),
            completedTrip(waterbody: waterbody, spot: spot, year: 2025, month: 10, day: 29),
            completedTrip(waterbody: waterbody, spot: spot, year: 2025, month: 10, day: 22),
        ]
        let catches = [
            CatchRecord(species: "Bass", trip: activeTrip, caughtAt: activeTrip.startAt),
            CatchRecord(species: "Bass", trip: completedTrips[0], caughtAt: completedTrips[0].startAt),
            CatchRecord(species: "Bass", trip: completedTrips[1], caughtAt: completedTrips[1].startAt),
            CatchRecord(species: "Bass", trip: completedTrips[2], caughtAt: completedTrips[2].startAt),
        ]

        let summary = SpotRecallSummary.build(
            for: spot,
            trips: [activeTrip] + completedTrips,
            catches: catches
        )

        XCTAssertEqual(
            summary.productivityInsight?.body,
            "You caught fish on all 3 of your last 3 completed trips here."
        )
        XCTAssertEqual(summary.productivityInsight?.supportingSampleCount, 3)
    }

    func testBuildAddsMonthSeasonalityCardWhenOneMonthHasClearLead() {
        let waterbody = Waterbody(name: "River Bend", type: .river)
        let spot = Spot(title: "Dock", waterbody: waterbody)
        let marchTrips = [3, 10, 17].map { day in
            Trip(
                waterbody: waterbody,
                spot: spot,
                startAt: date(year: 2025, month: 3, day: day)
            )
        }
        let mayTrip = Trip(
            waterbody: waterbody,
            spot: spot,
            startAt: date(year: 2025, month: 5, day: 2)
        )
        let catches = marchTrips.map { trip in
            CatchRecord(species: "Bass", trip: trip, caughtAt: trip.startAt)
        } + [
            CatchRecord(species: "Bass", trip: mayTrip, caughtAt: mayTrip.startAt)
        ]

        let summary = SpotRecallSummary.build(
            for: spot,
            trips: marchTrips + [mayTrip],
            catches: catches
        )

        XCTAssertEqual(summary.seasonalityInsight?.title, "March has been strongest here")
        XCTAssertEqual(
            summary.seasonalityInsight?.body,
            "March accounts for 3 of your 4 productive trips at this spot."
        )
        XCTAssertEqual(summary.seasonalityInsight?.supportingSampleCount, 3)
        XCTAssertEqual(summary.cards.first(where: { $0.kind == .seasonality })?.title, "March has been strongest here")
    }

    func testBuildFallsBackToSeasonWhenMonthSignalIsSplitButSeasonIsClear() {
        let waterbody = Waterbody(name: "River Bend", type: .river)
        let spot = Spot(title: "Dock", waterbody: waterbody)
        let productiveTrips = [
            Trip(waterbody: waterbody, spot: spot, startAt: date(year: 2024, month: 3, day: 8)),
            Trip(waterbody: waterbody, spot: spot, startAt: date(year: 2024, month: 4, day: 12)),
            Trip(waterbody: waterbody, spot: spot, startAt: date(year: 2024, month: 5, day: 6)),
            Trip(waterbody: waterbody, spot: spot, startAt: date(year: 2024, month: 8, day: 14)),
        ]
        let catches = productiveTrips.map { trip in
            CatchRecord(species: "Bass", trip: trip, caughtAt: trip.startAt)
        }

        let summary = SpotRecallSummary.build(for: spot, trips: productiveTrips, catches: catches)

        XCTAssertEqual(summary.seasonalityInsight?.title, "Spring has been strongest here")
        XCTAssertEqual(
            summary.seasonalityInsight?.body,
            "Spring accounts for 3 of your 4 productive trips at this spot."
        )
        XCTAssertEqual(summary.seasonalityInsight?.supportingSampleCount, 3)
    }

    func testBuildSuppressesSeasonalityCardWhenSupportIsThinOrTied() {
        let waterbody = Waterbody(name: "River Bend", type: .river)
        let spot = Spot(title: "Dock", waterbody: waterbody)
        let trips = [
            Trip(waterbody: waterbody, spot: spot, startAt: date(year: 2024, month: 3, day: 1)),
            Trip(waterbody: waterbody, spot: spot, startAt: date(year: 2024, month: 3, day: 9)),
            Trip(waterbody: waterbody, spot: spot, startAt: date(year: 2024, month: 6, day: 1)),
            Trip(waterbody: waterbody, spot: spot, startAt: date(year: 2024, month: 6, day: 9)),
        ]
        let catches = trips.map { trip in
            CatchRecord(species: "Bass", trip: trip, caughtAt: trip.startAt)
        }

        let summary = SpotRecallSummary.build(for: spot, trips: trips, catches: catches)

        XCTAssertNil(summary.seasonalityInsight)
        XCTAssertNil(summary.cards.first(where: { $0.kind == .seasonality }))
    }

    private func date(year: Int, month: Int, day: Int) -> Date {
        var components = DateComponents()
        components.calendar = Calendar(identifier: .gregorian)
        components.timeZone = TimeZone(secondsFromGMT: 0)
        components.year = year
        components.month = month
        components.day = day
        components.hour = 12
        return components.date ?? .distantPast
    }

    private func completedTrip(
        waterbody: Waterbody,
        spot: Spot,
        year: Int,
        month: Int,
        day: Int
    ) -> Trip {
        let trip = Trip(
            waterbody: waterbody,
            spot: spot,
            startAt: date(year: year, month: month, day: day)
        )
        trip.endAt = trip.startAt.addingTimeInterval(60 * 60)
        trip.outcomeRawValue = TripOutcome.skunked.rawValue
        return trip
    }
}
