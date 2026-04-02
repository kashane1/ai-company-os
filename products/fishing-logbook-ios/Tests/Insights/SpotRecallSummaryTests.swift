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
        XCTAssertNil(summary.recencyInsight)
        XCTAssertNil(summary.productivityInsight)
        XCTAssertNil(summary.speciesInsight)
        XCTAssertNil(summary.conditionsInsight)
        XCTAssertNil(summary.lureInsight)
        XCTAssertEqual(summary.bestTimeWindow, "6-9 AM")
        XCTAssertEqual(summary.mostEffectiveLure, "Spinner")
        XCTAssertNil(summary.seasonalityInsight)
        XCTAssertEqual(summary.similarConditionsCount, 2)
        XCTAssertEqual(summary.similarConditionsLabel, "6-9 AM • Morning light")
        XCTAssertEqual(summary.cards.count, 3)
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
        XCTAssertNil(summary.recencyInsight)
        XCTAssertNil(summary.productivityInsight)
        XCTAssertNil(summary.speciesInsight)
        XCTAssertNil(summary.conditionsInsight)
        XCTAssertNil(summary.lureInsight)
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
        XCTAssertNil(summary.recencyInsight)
        XCTAssertNil(summary.productivityInsight)
        XCTAssertNil(summary.speciesInsight)
        XCTAssertNil(summary.conditionsInsight)
        XCTAssertNil(summary.lureInsight)
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

    func testBuildAddsSpeciesCardForStrongSupportedPattern() {
        let waterbody = Waterbody(name: "River Bend", type: .river)
        let spot = Spot(title: "Dock", waterbody: waterbody)
        let trips = [
            completedTrip(waterbody: waterbody, spot: spot, year: 2025, month: 6, day: 22),
            completedTrip(waterbody: waterbody, spot: spot, year: 2025, month: 6, day: 15),
            completedTrip(waterbody: waterbody, spot: spot, year: 2025, month: 6, day: 8),
            completedTrip(waterbody: waterbody, spot: spot, year: 2025, month: 6, day: 1),
            completedTrip(waterbody: waterbody, spot: spot, year: 2025, month: 5, day: 25),
        ]
        let catches = [
            CatchRecord(species: "Bass", trip: trips[0], caughtAt: trips[0].startAt),
            CatchRecord(species: "Bass", trip: trips[0], caughtAt: trips[0].startAt.addingTimeInterval(60)),
            CatchRecord(species: "Bass", trip: trips[1], caughtAt: trips[1].startAt),
            CatchRecord(species: "Bass", trip: trips[2], caughtAt: trips[2].startAt),
            CatchRecord(species: "Bass", trip: trips[4], caughtAt: trips[4].startAt),
            CatchRecord(species: "Trout", trip: trips[3], caughtAt: trips[3].startAt),
        ]

        let summary = SpotRecallSummary.build(for: spot, trips: trips, catches: catches)

        XCTAssertEqual(summary.speciesInsight?.title, "Most reliable species here")
        XCTAssertEqual(
            summary.speciesInsight?.body,
            "Bass has been your most reliable species here: 5 bass across 4 completed trips."
        )
        XCTAssertEqual(summary.speciesInsight?.supportingSampleCount, 4)
        XCTAssertEqual(summary.cards.first(where: { $0.kind == .species })?.title, "Most reliable species here")
    }

    func testBuildAddsSpeciesCardWithSofterCopyForNarrowerTripLead() {
        let waterbody = Waterbody(name: "River Bend", type: .river)
        let spot = Spot(title: "Dock", waterbody: waterbody)
        let trips = [
            completedTrip(waterbody: waterbody, spot: spot, year: 2025, month: 7, day: 20),
            completedTrip(waterbody: waterbody, spot: spot, year: 2025, month: 7, day: 13),
            completedTrip(waterbody: waterbody, spot: spot, year: 2025, month: 7, day: 6),
            completedTrip(waterbody: waterbody, spot: spot, year: 2025, month: 6, day: 29),
        ]
        let catches = [
            CatchRecord(species: "Bass", trip: trips[0], caughtAt: trips[0].startAt),
            CatchRecord(species: "Bass", trip: trips[0], caughtAt: trips[0].startAt.addingTimeInterval(60)),
            CatchRecord(species: "Bass", trip: trips[1], caughtAt: trips[1].startAt),
            CatchRecord(species: "Bass", trip: trips[2], caughtAt: trips[2].startAt),
            CatchRecord(species: "Trout", trip: trips[1], caughtAt: trips[1].startAt.addingTimeInterval(120)),
            CatchRecord(species: "Trout", trip: trips[3], caughtAt: trips[3].startAt),
            CatchRecord(species: "Trout", trip: trips[3], caughtAt: trips[3].startAt.addingTimeInterval(60)),
        ]

        let summary = SpotRecallSummary.build(for: spot, trips: trips, catches: catches)

        XCTAssertEqual(
            summary.speciesInsight?.body,
            "Bass shows up most often here: 4 bass across 3 completed trips."
        )
        XCTAssertEqual(summary.speciesInsight?.supportingSampleCount, 3)
    }

    func testBuildSuppressesSpeciesCardWhenHistoryIsMixedOrTied() {
        let waterbody = Waterbody(name: "River Bend", type: .river)
        let spot = Spot(title: "Dock", waterbody: waterbody)
        let trips = [
            completedTrip(waterbody: waterbody, spot: spot, year: 2025, month: 8, day: 17),
            completedTrip(waterbody: waterbody, spot: spot, year: 2025, month: 8, day: 10),
            completedTrip(waterbody: waterbody, spot: spot, year: 2025, month: 8, day: 3),
            completedTrip(waterbody: waterbody, spot: spot, year: 2025, month: 7, day: 27),
        ]
        let catches = [
            CatchRecord(species: "Bass", trip: trips[0], caughtAt: trips[0].startAt),
            CatchRecord(species: "Bass", trip: trips[1], caughtAt: trips[1].startAt),
            CatchRecord(species: "Bass", trip: trips[2], caughtAt: trips[2].startAt),
            CatchRecord(species: "Bass", trip: trips[2], caughtAt: trips[2].startAt.addingTimeInterval(60)),
            CatchRecord(species: "Trout", trip: trips[0], caughtAt: trips[0].startAt.addingTimeInterval(120)),
            CatchRecord(species: "Trout", trip: trips[1], caughtAt: trips[1].startAt.addingTimeInterval(120)),
            CatchRecord(species: "Trout", trip: trips[3], caughtAt: trips[3].startAt),
            CatchRecord(species: "Trout", trip: trips[3], caughtAt: trips[3].startAt.addingTimeInterval(60)),
        ]

        let summary = SpotRecallSummary.build(for: spot, trips: trips, catches: catches)

        XCTAssertNil(summary.speciesInsight)
        XCTAssertNil(summary.cards.first(where: { $0.kind == .species }))
    }

    func testBuildSuppressesSpeciesCardWhenSupportIsTooThin() {
        let waterbody = Waterbody(name: "River Bend", type: .river)
        let spot = Spot(title: "Dock", waterbody: waterbody)
        let trips = [
            completedTrip(waterbody: waterbody, spot: spot, year: 2025, month: 5, day: 18),
            completedTrip(waterbody: waterbody, spot: spot, year: 2025, month: 5, day: 11),
            completedTrip(waterbody: waterbody, spot: spot, year: 2025, month: 5, day: 4),
        ]
        let catches = [
            CatchRecord(species: "Bass", trip: trips[0], caughtAt: trips[0].startAt),
            CatchRecord(species: "Bass", trip: trips[1], caughtAt: trips[1].startAt),
            CatchRecord(species: "Bass", trip: trips[2], caughtAt: trips[2].startAt),
            CatchRecord(species: "Bass", trip: trips[2], caughtAt: trips[2].startAt.addingTimeInterval(60)),
        ]

        let summary = SpotRecallSummary.build(for: spot, trips: trips, catches: catches)

        XCTAssertNil(summary.speciesInsight)
        XCTAssertNil(summary.cards.first(where: { $0.kind == .species }))
    }

    func testBuildSuppressesSpeciesCardForSingleBannerTripSkew() {
        let waterbody = Waterbody(name: "River Bend", type: .river)
        let spot = Spot(title: "Dock", waterbody: waterbody)
        let trips = [
            completedTrip(waterbody: waterbody, spot: spot, year: 2025, month: 9, day: 21),
            completedTrip(waterbody: waterbody, spot: spot, year: 2025, month: 9, day: 14),
            completedTrip(waterbody: waterbody, spot: spot, year: 2025, month: 9, day: 7),
            completedTrip(waterbody: waterbody, spot: spot, year: 2025, month: 8, day: 31),
        ]
        let catches = [
            CatchRecord(species: "Bass", trip: trips[0], caughtAt: trips[0].startAt),
            CatchRecord(species: "Bass", trip: trips[0], caughtAt: trips[0].startAt.addingTimeInterval(60)),
            CatchRecord(species: "Bass", trip: trips[0], caughtAt: trips[0].startAt.addingTimeInterval(120)),
            CatchRecord(species: "Bass", trip: trips[0], caughtAt: trips[0].startAt.addingTimeInterval(180)),
            CatchRecord(species: "Bass", trip: trips[1], caughtAt: trips[1].startAt),
            CatchRecord(species: "Trout", trip: trips[2], caughtAt: trips[2].startAt),
            CatchRecord(species: "Trout", trip: trips[3], caughtAt: trips[3].startAt),
            CatchRecord(species: "Trout", trip: trips[3], caughtAt: trips[3].startAt.addingTimeInterval(60)),
        ]

        let summary = SpotRecallSummary.build(for: spot, trips: trips, catches: catches)

        XCTAssertNil(summary.speciesInsight)
        XCTAssertNil(summary.cards.first(where: { $0.kind == .species }))
    }

    func testBuildIgnoresActiveTripsForSpeciesSupport() {
        let waterbody = Waterbody(name: "River Bend", type: .river)
        let spot = Spot(title: "Dock", waterbody: waterbody)
        let activeTrip = Trip(
            waterbody: waterbody,
            spot: spot,
            startAt: date(year: 2025, month: 10, day: 26)
        )
        let completedTrips = [
            completedTrip(waterbody: waterbody, spot: spot, year: 2025, month: 10, day: 19),
            completedTrip(waterbody: waterbody, spot: spot, year: 2025, month: 10, day: 12),
            completedTrip(waterbody: waterbody, spot: spot, year: 2025, month: 10, day: 5),
            completedTrip(waterbody: waterbody, spot: spot, year: 2025, month: 9, day: 28),
        ]
        let catches = [
            CatchRecord(species: "Trout", trip: activeTrip, caughtAt: activeTrip.startAt),
            CatchRecord(species: "Bass", trip: completedTrips[0], caughtAt: completedTrips[0].startAt),
            CatchRecord(species: "Bass", trip: completedTrips[0], caughtAt: completedTrips[0].startAt.addingTimeInterval(60)),
            CatchRecord(species: "Bass", trip: completedTrips[1], caughtAt: completedTrips[1].startAt),
            CatchRecord(species: "Bass", trip: completedTrips[2], caughtAt: completedTrips[2].startAt),
            CatchRecord(species: "Trout", trip: completedTrips[3], caughtAt: completedTrips[3].startAt),
        ]

        let summary = SpotRecallSummary.build(
            for: spot,
            trips: [activeTrip] + completedTrips,
            catches: catches
        )

        XCTAssertEqual(
            summary.speciesInsight?.body,
            "Bass has been your most reliable species here: 4 bass across 3 completed trips."
        )
        XCTAssertEqual(summary.speciesInsight?.supportingSampleCount, 3)
    }

    func testBuildNormalizesSpeciesLabelsCaseInsensitively() {
        let waterbody = Waterbody(name: "River Bend", type: .river)
        let spot = Spot(title: "Dock", waterbody: waterbody)
        let trips = [
            completedTrip(waterbody: waterbody, spot: spot, year: 2025, month: 11, day: 16),
            completedTrip(waterbody: waterbody, spot: spot, year: 2025, month: 11, day: 9),
            completedTrip(waterbody: waterbody, spot: spot, year: 2025, month: 11, day: 2),
            completedTrip(waterbody: waterbody, spot: spot, year: 2025, month: 10, day: 26),
        ]
        let catches = [
            CatchRecord(species: " Bass ", trip: trips[0], caughtAt: trips[0].startAt),
            CatchRecord(species: "bass", trip: trips[1], caughtAt: trips[1].startAt),
            CatchRecord(species: "BASS", trip: trips[2], caughtAt: trips[2].startAt),
            CatchRecord(species: "Bass", trip: trips[2], caughtAt: trips[2].startAt.addingTimeInterval(60)),
            CatchRecord(species: "Trout", trip: trips[3], caughtAt: trips[3].startAt),
        ]

        let summary = SpotRecallSummary.build(for: spot, trips: trips, catches: catches)

        XCTAssertEqual(
            summary.speciesInsight?.body,
            "Bass has been your most reliable species here: 4 bass across 3 completed trips."
        )
    }

    func testBuildAddsConditionsCardForStrongSupportedCatchWindowPattern() {
        let waterbody = Waterbody(name: "River Bend", type: .river)
        let spot = Spot(title: "Dock", waterbody: waterbody)
        let trips = [
            completedTrip(waterbody: waterbody, spot: spot, snapshot: snapshot(timeWindow: "Morning", lightLevel: "Low light", wind: "Low wind"), year: 2025, month: 11, day: 23),
            completedTrip(waterbody: waterbody, spot: spot, snapshot: snapshot(timeWindow: "Morning", lightLevel: "Low light", wind: "Moderate wind"), year: 2025, month: 11, day: 16),
            completedTrip(waterbody: waterbody, spot: spot, snapshot: snapshot(timeWindow: "Morning", lightLevel: "Bright", wind: "Low wind"), year: 2025, month: 11, day: 9),
            completedTrip(waterbody: waterbody, spot: spot, snapshot: snapshot(timeWindow: "Morning", lightLevel: "Low light", wind: "Low wind"), year: 2025, month: 11, day: 2),
            completedTrip(waterbody: waterbody, spot: spot, snapshot: snapshot(timeWindow: "Evening", lightLevel: "Low light", wind: "Low wind"), year: 2025, month: 10, day: 26),
        ]
        let catches = [
            CatchRecord(species: "Bass", trip: trips[0], caughtAt: trips[0].startAt),
            CatchRecord(species: "Bass", trip: trips[1], caughtAt: trips[1].startAt),
            CatchRecord(species: "Bass", trip: trips[2], caughtAt: trips[2].startAt),
            CatchRecord(species: "Bass", trip: trips[3], caughtAt: trips[3].startAt),
        ]

        let summary = SpotRecallSummary.build(for: spot, trips: trips, catches: catches)

        XCTAssertEqual(summary.conditionsInsight?.title, "Most consistent catch window here")
        XCTAssertEqual(
            summary.conditionsInsight?.body,
            "Your catches here have lined up most often in morning: 4 completed trips with catches."
        )
        XCTAssertEqual(summary.conditionsInsight?.supportingSampleCount, 4)
        XCTAssertEqual(summary.cards.first(where: { $0.kind == .conditions })?.title, "Most consistent catch window here")
    }

    func testBuildAddsLureCardForStrongSupportedPattern() {
        let waterbody = Waterbody(name: "River Bend", type: .river)
        let spot = Spot(title: "Dock", waterbody: waterbody)
        let trips = [
            completedTrip(waterbody: waterbody, spot: spot, year: 2025, month: 12, day: 28),
            completedTrip(waterbody: waterbody, spot: spot, year: 2025, month: 12, day: 21),
            completedTrip(waterbody: waterbody, spot: spot, year: 2025, month: 12, day: 14),
            completedTrip(waterbody: waterbody, spot: spot, year: 2025, month: 12, day: 7),
            completedTrip(waterbody: waterbody, spot: spot, year: 2025, month: 11, day: 30),
        ]
        let catches = [
            CatchRecord(species: "Bass", trip: trips[0], caughtAt: trips[0].startAt, lureOrBait: "Spinner"),
            CatchRecord(species: "Bass", trip: trips[0], caughtAt: trips[0].startAt.addingTimeInterval(60), lureOrBait: "Spinner"),
            CatchRecord(species: "Bass", trip: trips[1], caughtAt: trips[1].startAt, lureOrBait: "Spinner"),
            CatchRecord(species: "Bass", trip: trips[2], caughtAt: trips[2].startAt, lureOrBait: "Spinner"),
            CatchRecord(species: "Bass", trip: trips[3], caughtAt: trips[3].startAt, lureOrBait: "Spinner"),
            CatchRecord(species: "Bass", trip: trips[4], caughtAt: trips[4].startAt, lureOrBait: "Jig"),
        ]

        let summary = SpotRecallSummary.build(for: spot, trips: trips, catches: catches)

        XCTAssertEqual(summary.lureInsight?.title, "Most reliable lure here")
        XCTAssertEqual(
            summary.lureInsight?.body,
            "Spinner has shown up on 4 completed trips with catches here."
        )
        XCTAssertEqual(summary.lureInsight?.supportingSampleCount, 4)
        XCTAssertEqual(summary.cards.first(where: { $0.kind == .lure })?.title, "Most reliable lure here")
        XCTAssertNil(summary.cards.first(where: { $0.kind == .mostEffectiveLure }))
    }

    func testBuildSuppressesLureCardWhenSupportIsTooThin() {
        let waterbody = Waterbody(name: "River Bend", type: .river)
        let spot = Spot(title: "Dock", waterbody: waterbody)
        let trips = [
            completedTrip(waterbody: waterbody, spot: spot, year: 2025, month: 4, day: 27),
            completedTrip(waterbody: waterbody, spot: spot, year: 2025, month: 4, day: 20),
            completedTrip(waterbody: waterbody, spot: spot, year: 2025, month: 4, day: 13),
        ]
        let catches = [
            CatchRecord(species: "Bass", trip: trips[0], caughtAt: trips[0].startAt, lureOrBait: "Spinner"),
            CatchRecord(species: "Bass", trip: trips[1], caughtAt: trips[1].startAt, lureOrBait: "Spinner"),
            CatchRecord(species: "Bass", trip: trips[2], caughtAt: trips[2].startAt, lureOrBait: "Spinner"),
        ]

        let summary = SpotRecallSummary.build(for: spot, trips: trips, catches: catches)

        XCTAssertNil(summary.lureInsight)
        XCTAssertNil(summary.cards.first(where: { $0.kind == .lure }))
    }

    func testBuildSuppressesLureCardWhenTripSupportIsTied() {
        let waterbody = Waterbody(name: "River Bend", type: .river)
        let spot = Spot(title: "Dock", waterbody: waterbody)
        let trips = [
            completedTrip(waterbody: waterbody, spot: spot, year: 2025, month: 8, day: 31),
            completedTrip(waterbody: waterbody, spot: spot, year: 2025, month: 8, day: 24),
            completedTrip(waterbody: waterbody, spot: spot, year: 2025, month: 8, day: 17),
            completedTrip(waterbody: waterbody, spot: spot, year: 2025, month: 8, day: 10),
        ]
        let catches = [
            CatchRecord(species: "Bass", trip: trips[0], caughtAt: trips[0].startAt, lureOrBait: "Spinner"),
            CatchRecord(species: "Bass", trip: trips[1], caughtAt: trips[1].startAt, lureOrBait: "Spinner"),
            CatchRecord(species: "Bass", trip: trips[2], caughtAt: trips[2].startAt, lureOrBait: "Jig"),
            CatchRecord(species: "Bass", trip: trips[3], caughtAt: trips[3].startAt, lureOrBait: "Jig"),
        ]

        let summary = SpotRecallSummary.build(for: spot, trips: trips, catches: catches)

        XCTAssertNil(summary.lureInsight)
        XCTAssertNil(summary.cards.first(where: { $0.kind == .lure }))
    }

    func testBuildSuppressesLureCardWhenTripSupportIsNearTied() {
        let waterbody = Waterbody(name: "River Bend", type: .river)
        let spot = Spot(title: "Dock", waterbody: waterbody)
        let trips = [
            completedTrip(waterbody: waterbody, spot: spot, year: 2025, month: 9, day: 28),
            completedTrip(waterbody: waterbody, spot: spot, year: 2025, month: 9, day: 21),
            completedTrip(waterbody: waterbody, spot: spot, year: 2025, month: 9, day: 14),
            completedTrip(waterbody: waterbody, spot: spot, year: 2025, month: 9, day: 7),
            completedTrip(waterbody: waterbody, spot: spot, year: 2025, month: 8, day: 31),
        ]
        let catches = [
            CatchRecord(species: "Bass", trip: trips[0], caughtAt: trips[0].startAt, lureOrBait: "Spinner"),
            CatchRecord(species: "Bass", trip: trips[1], caughtAt: trips[1].startAt, lureOrBait: "Spinner"),
            CatchRecord(species: "Bass", trip: trips[2], caughtAt: trips[2].startAt, lureOrBait: "Spinner"),
            CatchRecord(species: "Bass", trip: trips[3], caughtAt: trips[3].startAt, lureOrBait: "Jig"),
            CatchRecord(species: "Bass", trip: trips[4], caughtAt: trips[4].startAt, lureOrBait: "Jig"),
        ]

        let summary = SpotRecallSummary.build(for: spot, trips: trips, catches: catches)

        XCTAssertNil(summary.lureInsight)
        XCTAssertNil(summary.cards.first(where: { $0.kind == .lure }))
    }

    func testBuildIgnoresActiveTripsForLureSupport() {
        let waterbody = Waterbody(name: "River Bend", type: .river)
        let spot = Spot(title: "Dock", waterbody: waterbody)
        let activeTrip = Trip(
            waterbody: waterbody,
            spot: spot,
            startAt: date(year: 2025, month: 10, day: 26)
        )
        let completedTrips = [
            completedTrip(waterbody: waterbody, spot: spot, year: 2025, month: 10, day: 19),
            completedTrip(waterbody: waterbody, spot: spot, year: 2025, month: 10, day: 12),
            completedTrip(waterbody: waterbody, spot: spot, year: 2025, month: 10, day: 5),
            completedTrip(waterbody: waterbody, spot: spot, year: 2025, month: 9, day: 28),
        ]
        let catches = [
            CatchRecord(species: "Bass", trip: activeTrip, caughtAt: activeTrip.startAt, lureOrBait: "Jig"),
            CatchRecord(species: "Bass", trip: completedTrips[0], caughtAt: completedTrips[0].startAt, lureOrBait: "Spinner"),
            CatchRecord(species: "Bass", trip: completedTrips[1], caughtAt: completedTrips[1].startAt, lureOrBait: "Spinner"),
            CatchRecord(species: "Bass", trip: completedTrips[2], caughtAt: completedTrips[2].startAt, lureOrBait: "Spinner"),
            CatchRecord(species: "Bass", trip: completedTrips[3], caughtAt: completedTrips[3].startAt, lureOrBait: "Spinner"),
        ]

        let summary = SpotRecallSummary.build(
            for: spot,
            trips: [activeTrip] + completedTrips,
            catches: catches
        )

        XCTAssertEqual(
            summary.lureInsight?.body,
            "Spinner has shown up on 4 completed trips with catches here."
        )
        XCTAssertEqual(summary.lureInsight?.supportingSampleCount, 4)
    }

    func testBuildSuppressesLureCardForBannerTripAntiSkew() {
        let waterbody = Waterbody(name: "River Bend", type: .river)
        let spot = Spot(title: "Dock", waterbody: waterbody)
        let trips = [
            completedTrip(waterbody: waterbody, spot: spot, year: 2025, month: 11, day: 23),
            completedTrip(waterbody: waterbody, spot: spot, year: 2025, month: 11, day: 16),
            completedTrip(waterbody: waterbody, spot: spot, year: 2025, month: 11, day: 9),
            completedTrip(waterbody: waterbody, spot: spot, year: 2025, month: 11, day: 2),
            completedTrip(waterbody: waterbody, spot: spot, year: 2025, month: 10, day: 26),
        ]
        let catches = [
            CatchRecord(species: "Bass", trip: trips[0], caughtAt: trips[0].startAt, lureOrBait: "Spinner"),
            CatchRecord(species: "Bass", trip: trips[0], caughtAt: trips[0].startAt.addingTimeInterval(60), lureOrBait: "Spinner"),
            CatchRecord(species: "Bass", trip: trips[0], caughtAt: trips[0].startAt.addingTimeInterval(120), lureOrBait: "Spinner"),
            CatchRecord(species: "Bass", trip: trips[0], caughtAt: trips[0].startAt.addingTimeInterval(180), lureOrBait: "Spinner"),
            CatchRecord(species: "Bass", trip: trips[1], caughtAt: trips[1].startAt, lureOrBait: "Spinner"),
            CatchRecord(species: "Bass", trip: trips[2], caughtAt: trips[2].startAt, lureOrBait: "Jig"),
            CatchRecord(species: "Bass", trip: trips[3], caughtAt: trips[3].startAt, lureOrBait: "Jig"),
            CatchRecord(species: "Bass", trip: trips[4], caughtAt: trips[4].startAt, lureOrBait: "Jig"),
        ]

        let summary = SpotRecallSummary.build(for: spot, trips: trips, catches: catches)

        XCTAssertNil(summary.lureInsight)
        XCTAssertNil(summary.cards.first(where: { $0.kind == .lure }))
    }

    func testBuildNormalizesLureLabelsCaseAndWhitespaceInsensitively() {
        let waterbody = Waterbody(name: "River Bend", type: .river)
        let spot = Spot(title: "Dock", waterbody: waterbody)
        let trips = [
            completedTrip(waterbody: waterbody, spot: spot, year: 2025, month: 12, day: 29),
            completedTrip(waterbody: waterbody, spot: spot, year: 2025, month: 12, day: 22),
            completedTrip(waterbody: waterbody, spot: spot, year: 2025, month: 12, day: 15),
            completedTrip(waterbody: waterbody, spot: spot, year: 2025, month: 12, day: 8),
        ]
        let catches = [
            CatchRecord(species: "Bass", trip: trips[0], caughtAt: trips[0].startAt, lureOrBait: " Spinner "),
            CatchRecord(species: "Bass", trip: trips[1], caughtAt: trips[1].startAt, lureOrBait: "spinner"),
            CatchRecord(species: "Bass", trip: trips[2], caughtAt: trips[2].startAt, lureOrBait: "SPINNER"),
            CatchRecord(species: "Bass", trip: trips[3], caughtAt: trips[3].startAt, lureOrBait: "Spinner"),
        ]

        let summary = SpotRecallSummary.build(for: spot, trips: trips, catches: catches)

        XCTAssertEqual(
            summary.lureInsight?.body,
            "Spinner has shown up on 4 completed trips with catches here."
        )
        XCTAssertEqual(summary.lureInsight?.supportingSampleCount, 4)
    }

    func testBuildIgnoresBlankLureValuesWhenSupportedPatternIsStillClear() {
        let waterbody = Waterbody(name: "River Bend", type: .river)
        let spot = Spot(title: "Dock", waterbody: waterbody)
        let trips = [
            completedTrip(waterbody: waterbody, spot: spot, year: 2025, month: 7, day: 27),
            completedTrip(waterbody: waterbody, spot: spot, year: 2025, month: 7, day: 20),
            completedTrip(waterbody: waterbody, spot: spot, year: 2025, month: 7, day: 13),
            completedTrip(waterbody: waterbody, spot: spot, year: 2025, month: 7, day: 6),
            completedTrip(waterbody: waterbody, spot: spot, year: 2025, month: 6, day: 29),
        ]
        let catches = [
            CatchRecord(species: "Bass", trip: trips[0], caughtAt: trips[0].startAt, lureOrBait: "Spinner"),
            CatchRecord(species: "Bass", trip: trips[0], caughtAt: trips[0].startAt.addingTimeInterval(60), lureOrBait: "   "),
            CatchRecord(species: "Bass", trip: trips[1], caughtAt: trips[1].startAt, lureOrBait: "Spinner"),
            CatchRecord(species: "Bass", trip: trips[2], caughtAt: trips[2].startAt, lureOrBait: "Spinner"),
            CatchRecord(species: "Bass", trip: trips[3], caughtAt: trips[3].startAt, lureOrBait: "Spinner"),
            CatchRecord(species: "Bass", trip: trips[4], caughtAt: trips[4].startAt, lureOrBait: "Jig"),
            CatchRecord(species: "Bass", trip: trips[4], caughtAt: trips[4].startAt.addingTimeInterval(60), lureOrBait: ""),
        ]

        let summary = SpotRecallSummary.build(for: spot, trips: trips, catches: catches)

        XCTAssertEqual(
            summary.lureInsight?.body,
            "Spinner has shown up on 4 completed trips with catches here."
        )
        XCTAssertEqual(summary.lureInsight?.supportingSampleCount, 4)
    }

    func testBuildSuppressesConditionsCardWhenHistoryIsMixedOrNoisy() {
        let waterbody = Waterbody(name: "River Bend", type: .river)
        let spot = Spot(title: "Dock", waterbody: waterbody)
        let trips = [
            completedTrip(waterbody: waterbody, spot: spot, snapshot: snapshot(timeWindow: "Morning", lightLevel: "Low light", wind: "Low wind"), year: 2025, month: 12, day: 21),
            completedTrip(waterbody: waterbody, spot: spot, snapshot: snapshot(timeWindow: "Morning", lightLevel: "Bright", wind: "Moderate wind"), year: 2025, month: 12, day: 14),
            completedTrip(waterbody: waterbody, spot: spot, snapshot: snapshot(timeWindow: "Evening", lightLevel: "Low light", wind: "Low wind"), year: 2025, month: 12, day: 7),
            completedTrip(waterbody: waterbody, spot: spot, snapshot: snapshot(timeWindow: "Evening", lightLevel: "Bright", wind: "High wind"), year: 2025, month: 11, day: 30),
        ]
        let catches = trips.map { CatchRecord(species: "Bass", trip: $0, caughtAt: $0.startAt) }

        let summary = SpotRecallSummary.build(for: spot, trips: trips, catches: catches)

        XCTAssertNil(summary.conditionsInsight)
        XCTAssertNil(summary.cards.first(where: { $0.kind == .conditions }))
    }

    func testBuildSuppressesConditionsCardWhenSupportIsTooThin() {
        let waterbody = Waterbody(name: "River Bend", type: .river)
        let spot = Spot(title: "Dock", waterbody: waterbody)
        let trips = [
            completedTrip(waterbody: waterbody, spot: spot, snapshot: snapshot(timeWindow: "Morning"), year: 2025, month: 4, day: 20),
            completedTrip(waterbody: waterbody, spot: spot, snapshot: snapshot(timeWindow: "Morning"), year: 2025, month: 4, day: 13),
            completedTrip(waterbody: waterbody, spot: spot, snapshot: snapshot(timeWindow: "Morning"), year: 2025, month: 4, day: 6),
        ]
        let catches = trips.map { CatchRecord(species: "Bass", trip: $0, caughtAt: $0.startAt) }

        let summary = SpotRecallSummary.build(for: spot, trips: trips, catches: catches)

        XCTAssertNil(summary.conditionsInsight)
        XCTAssertNil(summary.cards.first(where: { $0.kind == .conditions }))
    }

    func testBuildIgnoresActiveTripsForConditionsSupport() {
        let waterbody = Waterbody(name: "River Bend", type: .river)
        let spot = Spot(title: "Dock", waterbody: waterbody)
        let activeTrip = Trip(
            waterbody: waterbody,
            spot: spot,
            conditionSnapshot: snapshot(timeWindow: "Evening"),
            startAt: date(year: 2025, month: 10, day: 26)
        )
        let completedTrips = [
            completedTrip(waterbody: waterbody, spot: spot, snapshot: snapshot(timeWindow: "Morning"), year: 2025, month: 10, day: 19),
            completedTrip(waterbody: waterbody, spot: spot, snapshot: snapshot(timeWindow: "Morning"), year: 2025, month: 10, day: 12),
            completedTrip(waterbody: waterbody, spot: spot, snapshot: snapshot(timeWindow: "Morning"), year: 2025, month: 10, day: 5),
            completedTrip(waterbody: waterbody, spot: spot, snapshot: snapshot(timeWindow: "Morning"), year: 2025, month: 9, day: 28),
        ]
        let catches = [
            CatchRecord(species: "Bass", trip: activeTrip, caughtAt: activeTrip.startAt),
            CatchRecord(species: "Bass", trip: completedTrips[0], caughtAt: completedTrips[0].startAt),
            CatchRecord(species: "Bass", trip: completedTrips[1], caughtAt: completedTrips[1].startAt),
            CatchRecord(species: "Bass", trip: completedTrips[2], caughtAt: completedTrips[2].startAt),
            CatchRecord(species: "Bass", trip: completedTrips[3], caughtAt: completedTrips[3].startAt),
        ]

        let summary = SpotRecallSummary.build(
            for: spot,
            trips: [activeTrip] + completedTrips,
            catches: catches
        )

        XCTAssertEqual(
            summary.conditionsInsight?.body,
            "Your catches here have lined up most often in morning: 4 completed trips with catches."
        )
        XCTAssertEqual(summary.conditionsInsight?.supportingSampleCount, 4)
    }

    func testBuildAddsRecencyCardForStrongRecentActivePattern() {
        let waterbody = Waterbody(name: "River Bend", type: .river)
        let spot = Spot(title: "Dock", waterbody: waterbody)
        let trips = [
            completedTrip(waterbody: waterbody, spot: spot, year: 2025, month: 7, day: 21),
            completedTrip(waterbody: waterbody, spot: spot, year: 2025, month: 7, day: 14),
            completedTrip(waterbody: waterbody, spot: spot, year: 2025, month: 7, day: 7),
            completedTrip(waterbody: waterbody, spot: spot, year: 2025, month: 6, day: 30),
        ]
        let catches = [
            CatchRecord(species: "Bass", trip: trips[0], caughtAt: trips[0].startAt),
            CatchRecord(species: "Bass", trip: trips[0], caughtAt: trips[0].startAt.addingTimeInterval(60)),
            CatchRecord(species: "Bass", trip: trips[1], caughtAt: trips[1].startAt),
        ]

        let summary = SpotRecallSummary.build(for: spot, trips: trips, catches: catches)

        XCTAssertEqual(summary.recencyInsight?.title, "Recently active here")
        XCTAssertEqual(
            summary.recencyInsight?.body,
            "Your catches here have clustered recently: 3 fish across your last 2 completed trips."
        )
        XCTAssertEqual(summary.recencyInsight?.supportingSampleCount, 4)
        XCTAssertEqual(summary.cards.dropFirst().first?.kind, .recency)
    }

    func testBuildAddsRecencyCardForStrongRecentQuietPattern() {
        let waterbody = Waterbody(name: "River Bend", type: .river)
        let spot = Spot(title: "Dock", waterbody: waterbody)
        let trips = [
            completedTrip(waterbody: waterbody, spot: spot, year: 2025, month: 8, day: 24),
            completedTrip(waterbody: waterbody, spot: spot, year: 2025, month: 8, day: 17),
            completedTrip(waterbody: waterbody, spot: spot, year: 2025, month: 8, day: 10),
            completedTrip(waterbody: waterbody, spot: spot, year: 2025, month: 8, day: 3),
        ]
        let catches = [
            CatchRecord(species: "Bass", trip: trips[3], caughtAt: trips[3].startAt)
        ]

        let summary = SpotRecallSummary.build(for: spot, trips: trips, catches: catches)

        XCTAssertEqual(summary.recencyInsight?.title, "Quiet lately here")
        XCTAssertEqual(
            summary.recencyInsight?.body,
            "This spot has been quiet lately: no fish on your last 3 completed trips here."
        )
        XCTAssertEqual(summary.recencyInsight?.supportingSampleCount, 4)
    }

    func testBuildSuppressesRecencyCardWhenRecentHistoryIsMixed() {
        let waterbody = Waterbody(name: "River Bend", type: .river)
        let spot = Spot(title: "Dock", waterbody: waterbody)
        let trips = [
            completedTrip(waterbody: waterbody, spot: spot, year: 2025, month: 9, day: 22),
            completedTrip(waterbody: waterbody, spot: spot, year: 2025, month: 9, day: 15),
            completedTrip(waterbody: waterbody, spot: spot, year: 2025, month: 9, day: 8),
            completedTrip(waterbody: waterbody, spot: spot, year: 2025, month: 9, day: 1),
        ]
        let catches = [
            CatchRecord(species: "Bass", trip: trips[0], caughtAt: trips[0].startAt),
            CatchRecord(species: "Bass", trip: trips[2], caughtAt: trips[2].startAt)
        ]

        let summary = SpotRecallSummary.build(for: spot, trips: trips, catches: catches)

        XCTAssertNil(summary.recencyInsight)
        XCTAssertNil(summary.cards.first(where: { $0.kind == .recency }))
    }

    func testBuildSuppressesRecencyCardWhenSupportIsTooThin() {
        let waterbody = Waterbody(name: "River Bend", type: .river)
        let spot = Spot(title: "Dock", waterbody: waterbody)
        let trips = [
            completedTrip(waterbody: waterbody, spot: spot, year: 2025, month: 5, day: 20),
            completedTrip(waterbody: waterbody, spot: spot, year: 2025, month: 5, day: 13),
            completedTrip(waterbody: waterbody, spot: spot, year: 2025, month: 5, day: 6),
        ]
        let catches = [
            CatchRecord(species: "Bass", trip: trips[0], caughtAt: trips[0].startAt),
            CatchRecord(species: "Bass", trip: trips[0], caughtAt: trips[0].startAt.addingTimeInterval(60)),
            CatchRecord(species: "Bass", trip: trips[1], caughtAt: trips[1].startAt)
        ]

        let summary = SpotRecallSummary.build(for: spot, trips: trips, catches: catches)

        XCTAssertNil(summary.recencyInsight)
        XCTAssertNil(summary.cards.first(where: { $0.kind == .recency }))
    }

    func testBuildIgnoresActiveTripsForRecencyWindow() {
        let waterbody = Waterbody(name: "River Bend", type: .river)
        let spot = Spot(title: "Dock", waterbody: waterbody)
        let activeTrip = Trip(
            waterbody: waterbody,
            spot: spot,
            startAt: date(year: 2025, month: 10, day: 20)
        )
        let completedTrips = [
            completedTrip(waterbody: waterbody, spot: spot, year: 2025, month: 10, day: 13),
            completedTrip(waterbody: waterbody, spot: spot, year: 2025, month: 10, day: 6),
            completedTrip(waterbody: waterbody, spot: spot, year: 2025, month: 9, day: 29),
            completedTrip(waterbody: waterbody, spot: spot, year: 2025, month: 9, day: 22),
        ]
        let catches = [
            CatchRecord(species: "Bass", trip: activeTrip, caughtAt: activeTrip.startAt),
            CatchRecord(species: "Bass", trip: completedTrips[0], caughtAt: completedTrips[0].startAt),
            CatchRecord(species: "Bass", trip: completedTrips[0], caughtAt: completedTrips[0].startAt.addingTimeInterval(60)),
            CatchRecord(species: "Bass", trip: completedTrips[1], caughtAt: completedTrips[1].startAt),
        ]

        let summary = SpotRecallSummary.build(
            for: spot,
            trips: [activeTrip] + completedTrips,
            catches: catches
        )

        XCTAssertEqual(
            summary.recencyInsight?.body,
            "Your catches here have clustered recently: 3 fish across your last 2 completed trips."
        )
        XCTAssertEqual(summary.recencyInsight?.supportingSampleCount, 4)
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
        snapshot: ConditionSnapshot? = nil,
        year: Int,
        month: Int,
        day: Int
    ) -> Trip {
        let trip = Trip(
            waterbody: waterbody,
            spot: spot,
            conditionSnapshot: snapshot,
            startAt: date(year: year, month: month, day: day)
        )
        trip.endAt = trip.startAt.addingTimeInterval(60 * 60)
        trip.outcomeRawValue = TripOutcome.skunked.rawValue
        return trip
    }

    private func snapshot(
        timeWindow: String,
        lightLevel: String? = nil,
        wind: String? = nil
    ) -> ConditionSnapshot {
        ConditionSnapshot(
            capturedAt: .now,
            timeWindowSummary: timeWindow,
            lightLevelSummary: lightLevel,
            windSummary: wind
        )
    }
}
