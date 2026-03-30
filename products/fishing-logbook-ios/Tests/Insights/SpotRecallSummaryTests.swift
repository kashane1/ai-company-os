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
        XCTAssertEqual(summary.bestTimeWindow, "6-9 AM")
        XCTAssertEqual(summary.mostEffectiveLure, "Spinner")
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
        XCTAssertNil(summary.bestTimeWindow)
        XCTAssertNil(summary.mostEffectiveLure)
        XCTAssertEqual(summary.similarConditionsCount, 0)
        XCTAssertNil(summary.similarConditionsLabel)
        XCTAssertTrue(summary.cards.isEmpty)
    }

    func testBuildKeepsOnlyThreeMostRecentTripsAndIgnoresBlankLures() {
        let waterbody = Waterbody(name: "River Bend", type: .river)
        let spot = Spot(title: "Dock", waterbody: waterbody)
        let trips = (0..<4).map { offset in
            Trip(
                waterbody: waterbody,
                spot: spot,
                startAt: Date(timeIntervalSince1970: 1_711_900_000 + Double(offset * 600))
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
        XCTAssertEqual(summary.mostEffectiveLure, "Spinner")
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
}
