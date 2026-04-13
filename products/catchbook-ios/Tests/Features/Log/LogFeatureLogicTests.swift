import XCTest
@testable import Catchbook

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

    func testStartTripOptionalDetailsAreCollapsedByDefault() {
        XCTAssertFalse(LogFeatureLogic.startTripOptionalDetailsInitiallyExpanded)
        XCTAssertEqual(LogFeatureLogic.startTripOptionalDetailsLabel, "Optional details")
        XCTAssertEqual(LogFeatureLogic.startTripOptionalDetailsHint, "Add target species or trip notes")
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

    func testQuickCatchFieldGroupingKeepsFastPathCompressed() {
        XCTAssertEqual(
            LogFeatureLogic.quickCatchPrimaryFields,
            [.species, .lureOrBait, .save]
        )
        XCTAssertEqual(
            LogFeatureLogic.quickCatchOptionalFields,
            [.disposition, .method, .weight, .length, .waterDepth, .note, .photo]
        )
    }

    func testResetQuickCatchStateAfterSaveClearsTransientFieldsAndPreservesStickyDefaults() {
        let reset = LogFeatureLogic.resetQuickCatchStateAfterSave(
            lureOrBait: "Spinner",
            method: "Slow roll"
        )

        XCTAssertEqual(reset.species, "")
        XCTAssertEqual(reset.lureOrBait, "Spinner")
        XCTAssertEqual(reset.disposition, .notRecorded)
        XCTAssertEqual(reset.method, "Slow roll")
        XCTAssertEqual(reset.weight, "")
        XCTAssertEqual(reset.length, "")
        XCTAssertEqual(reset.waterDepth, "")
        XCTAssertEqual(reset.note, "")
        XCTAssertFalse(reset.showingOptionalFields)
        XCTAssertNil(reset.photoData)
    }

    func testCatchesPerHourTextReturnsRoundedRateForEndedTripsOnly() {
        let trip = Trip(waterbody: Waterbody(name: "Lake A", type: .lake), startAt: Date(timeIntervalSince1970: 0))
        trip.endAt = Date(timeIntervalSince1970: 7_200)

        XCTAssertEqual(LogFeatureLogic.catchesPerHourText(trip: trip, catchCount: 3), "1.5")
        XCTAssertNil(LogFeatureLogic.catchesPerHourText(trip: Trip(waterbody: nil), catchCount: 3))
        XCTAssertNil(LogFeatureLogic.catchesPerHourText(trip: trip, catchCount: 0))
    }

    func testEndTripOutcomeReflectsCatchCount() {
        XCTAssertEqual(LogFeatureLogic.endTripOutcome(catchCount: 0), .skunked)
        XCTAssertEqual(LogFeatureLogic.endTripOutcome(catchCount: 2), .caught)
    }

    func testQuickCatchContextSummaryUsesCurrentTripSpotAndPrivacyCopy() {
        let waterbody = Waterbody(name: "Lake A", type: .lake)
        let spot = Spot(title: "Dock", waterbody: waterbody)
        let trip = Trip(waterbody: waterbody, spot: spot)

        let summary = LogFeatureLogic.quickCatchContextSummary(
            trip: trip,
            now: Date(timeIntervalSince1970: 100),
            formatTime: { _ in "6:15 AM" }
        )

        XCTAssertEqual(summary.timeText, "6:15 AM")
        XCTAssertEqual(summary.spotText, "Dock")
        XCTAssertEqual(summary.privacyText, "Saved privately")
    }

    func testTripSummaryCardsIncludeDeterministicRecapValues() {
        let waterbody = Waterbody(name: "Lake A", type: .lake)
        let trip = Trip(waterbody: waterbody, startAt: Date(timeIntervalSince1970: 100))
        trip.endAt = Date(timeIntervalSince1970: 220)
        let catches = [
            CatchRecord(species: "Bass", trip: trip, caughtAt: Date(timeIntervalSince1970: 140), lureOrBait: "Spinner", weightKg: 2.4),
            CatchRecord(species: "Bass", trip: trip, caughtAt: Date(timeIntervalSince1970: 150), lureOrBait: "Spinner", lengthCm: 48),
            CatchRecord(species: "Trout", trip: trip, caughtAt: Date(timeIntervalSince1970: 160), lureOrBait: "Spoon"),
        ]

        let formatter = DateComponentsFormatter()
        formatter.allowedUnits = [.minute]
        formatter.unitsStyle = .abbreviated
        let cards = LogFeatureLogic.tripSummaryCards(trip: trip, catches: catches, durationFormatter: formatter)

        XCTAssertEqual(cards.map(\.title), [
            "Total catches",
            "Trip duration",
            "Catches / hour",
            "Top species",
            "Best catch",
            "Top lure",
        ])
        XCTAssertEqual(cards.first?.value, "3")
        XCTAssertEqual(cards[1].value, "2m")
        XCTAssertEqual(cards[2].value, "90")
        XCTAssertEqual(cards[3].value, "Bass")
        XCTAssertEqual(cards[5].value, "Spinner")
    }

    func testShouldOfferCreateSpotFromTripRequiresWaterbodyAndResolvableCoordinate() {
        let waterbody = Waterbody(name: "Lake A", type: .lake, latitude: 47.6, longitude: -122.3)
        let tripWithFallbackCoordinate = Trip(waterbody: waterbody)
        let savedSpot = Spot(title: "Dock", waterbody: waterbody, latitude: 47.61, longitude: -122.31)
        let tripWithSavedSpot = Trip(waterbody: waterbody, spot: savedSpot)
        let unresolvedTrip = Trip(waterbody: Waterbody(name: "Unknown", type: .lake))

        XCTAssertTrue(LogFeatureLogic.shouldOfferCreateSpot(from: tripWithFallbackCoordinate))
        XCTAssertFalse(LogFeatureLogic.shouldOfferCreateSpot(from: tripWithSavedSpot))
        XCTAssertFalse(LogFeatureLogic.shouldOfferCreateSpot(from: unresolvedTrip))
    }

    func testCreateSpotPromptUsesTripConfidenceLanguage() {
        let waterbody = Waterbody(name: "Lake A", type: .lake, latitude: 47.6, longitude: -122.3)
        let trip = Trip(waterbody: waterbody)

        XCTAssertEqual(
            LogFeatureLogic.createSpotPrompt(for: trip),
            "Near this saved trip location into a reusable spot for faster recall next time."
        )
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
            "4 productive trips here matched Morning light • Dry."
        )
    }
}
