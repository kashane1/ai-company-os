import XCTest
@testable import Fishing_Logbook

final class LogFeatureLogicTests: XCTestCase {
    func testFilteredSpotsReturnsOnlySelectedWaterbodySpots() {
        let waterbodyA = Waterbody(name: "Lake A", type: .lake)
        let waterbodyB = Waterbody(name: "Lake B", type: .lake)
        let spotA = Spot(title: "Dock", waterbody: waterbodyA)
        let spotB = Spot(title: "Point", waterbody: waterbodyB)

        XCTAssertEqual(
            LogFeatureLogic.filteredSpots(
                spots: [spotA, spotB],
                selectedWaterbodyID: waterbodyA.id
            ).map(\.id),
            [spotA.id]
        )
        XCTAssertEqual(
            LogFeatureLogic.filteredSpots(spots: [spotA, spotB], selectedWaterbodyID: nil).map(\.id),
            [spotA.id, spotB.id]
        )
    }

    func testStartTripDraftTrimsOptionalFields() {
        let draft = LogFeatureLogic.startTripDraft(
            targetSpecies: "  Bass, Trout  ",
            notes: "  Wind picked up  "
        )

        XCTAssertEqual(draft.targetSpecies, "Bass, Trout")
        XCTAssertEqual(draft.notes, "Wind picked up")
    }

    func testRecentSpeciesSuggestionsPutTargetsFirstAndDedupeRecentCatchValues() {
        let catches = [
            CatchRecord(species: "Bass", trip: nil),
            CatchRecord(species: "  Trout  ", trip: nil),
            CatchRecord(species: "Bass", trip: nil),
            CatchRecord(species: "Perch", trip: nil),
        ]

        let suggestions = LogFeatureLogic.recentSpeciesSuggestions(
            targetSpeciesList: ["Bass", "Walleye"],
            catches: catches
        )

        XCTAssertEqual(suggestions, ["Bass", "Walleye", "Trout", "Perch"])
    }

    func testRecentSpeciesSuggestionsRespectLimitBeforeReadingCatchHistory() {
        let catches = [
            CatchRecord(species: "Bass", trip: nil),
            CatchRecord(species: "Trout", trip: nil),
        ]

        let suggestions = LogFeatureLogic.recentSpeciesSuggestions(
            targetSpeciesList: ["Bass", "Walleye", "Perch"],
            catches: catches,
            limit: 2
        )

        XCTAssertEqual(suggestions, ["Bass", "Walleye"])
    }

    func testRecentLureSuggestionsPreferSpotHistoryAndIgnoreBlankValues() {
        let spotCatches = [
            CatchRecord(species: "Bass", trip: nil, lureOrBait: "Spinner"),
            CatchRecord(species: "Bass", trip: nil, lureOrBait: "   "),
        ]
        let allCatches = [
            CatchRecord(species: "Bass", trip: nil, lureOrBait: "Spinner"),
            CatchRecord(species: "Bass", trip: nil, lureOrBait: "Jig"),
            CatchRecord(species: "Bass", trip: nil, lureOrBait: "Crankbait"),
        ]

        let suggestions = LogFeatureLogic.recentLureSuggestions(
            catchesForSpot: spotCatches,
            allCatches: allCatches
        )

        XCTAssertEqual(suggestions, ["Spinner", "Jig", "Crankbait"])
    }

    func testRecentLureSuggestionsRespectLimitAcrossSpotAndGlobalHistory() {
        let spotCatches = [
            CatchRecord(species: "Bass", trip: nil, lureOrBait: "Spinner"),
            CatchRecord(species: "Bass", trip: nil, lureOrBait: "Jerkbait"),
        ]
        let allCatches = [
            CatchRecord(species: "Bass", trip: nil, lureOrBait: "Jig"),
        ]

        let suggestions = LogFeatureLogic.recentLureSuggestions(
            catchesForSpot: spotCatches,
            allCatches: allCatches,
            limit: 2
        )

        XCTAssertEqual(suggestions, ["Spinner", "Jerkbait"])
    }

    func testPrimeDefaultsFillsOnlyEmptyFieldsAndRunsOnce() {
        let recentCatch = CatchRecord(species: "Bass", trip: nil, lureOrBait: "Spinner", method: "Slow roll")

        let primed = LogFeatureLogic.primeDefaultsIfNeeded(
            didPrimeDefaults: false,
            lureOrBait: "",
            method: "Burn",
            catchesForSpot: [recentCatch],
            allCatches: []
        )
        XCTAssertEqual(primed.lureOrBait, "Spinner")
        XCTAssertEqual(primed.method, "Burn")
        XCTAssertTrue(primed.didPrimeDefaults)

        let alreadyPrimed = LogFeatureLogic.primeDefaultsIfNeeded(
            didPrimeDefaults: true,
            lureOrBait: "Jig",
            method: "Hop",
            catchesForSpot: [recentCatch],
            allCatches: []
        )
        XCTAssertEqual(alreadyPrimed.lureOrBait, "Jig")
        XCTAssertEqual(alreadyPrimed.method, "Hop")
        XCTAssertTrue(alreadyPrimed.didPrimeDefaults)
    }

    func testPrimeDefaultsWithoutCatchHistoryOnlyMarksPrimed() {
        let primed = LogFeatureLogic.primeDefaultsIfNeeded(
            didPrimeDefaults: false,
            lureOrBait: "Jig",
            method: "Hop",
            catchesForSpot: [],
            allCatches: []
        )

        XCTAssertEqual(primed.lureOrBait, "Jig")
        XCTAssertEqual(primed.method, "Hop")
        XCTAssertTrue(primed.didPrimeDefaults)
    }

    func testEndTripOutcomeReflectsCatchCount() {
        XCTAssertEqual(LogFeatureLogic.endTripOutcome(catchCount: 0), .skunked)
        XCTAssertEqual(LogFeatureLogic.endTripOutcome(catchCount: 2), .caught)
    }

    func testSharedRecallCardsStillIncludeBestTimeWindowForLogConsumers() {
        let summary = SpotRecallSummary(
            recentTrips: [],
            catchCount: 5,
            successfulTripCount: 4,
            recencyInsight: nil,
            productivityInsight: nil,
            speciesInsight: nil,
            conditionsInsight: nil,
            lureInsight: nil,
            bestTimeWindow: "6-9 AM",
            mostEffectiveLure: nil,
            seasonalityInsight: nil,
            similarConditionsCount: 0,
            similarConditionsLabel: nil
        )

        XCTAssertNotNil(summary.cards.first(where: { $0.kind == .bestTimeWindow }))
    }

    func testSharedRecallCardsStillIncludeSimilarConditionsForLogConsumers() {
        let summary = SpotRecallSummary(
            recentTrips: [],
            catchCount: 5,
            successfulTripCount: 4,
            recencyInsight: nil,
            productivityInsight: nil,
            speciesInsight: nil,
            conditionsInsight: nil,
            lureInsight: nil,
            bestTimeWindow: nil,
            mostEffectiveLure: nil,
            seasonalityInsight: nil,
            similarConditionsCount: 4,
            similarConditionsLabel: "Morning light • Dry"
        )

        XCTAssertEqual(
            summary.cards.first(where: { $0.kind == .similarConditions })?.body,
            "4 completed trips with catches here lined up with Morning light • Dry."
        )
    }
}
