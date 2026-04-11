import Foundation
import XCTest
@testable import Catchbook

final class SpotPresentationLogicTests: XCTestCase {
    private func fixedFormatter() -> DateFormatter {
        let formatter = DateFormatter()
        formatter.calendar = Calendar(identifier: .gregorian)
        formatter.locale = Locale(identifier: "en_US_POSIX")
        formatter.timeZone = TimeZone(secondsFromGMT: 0)
        formatter.dateFormat = "yyyy-MM-dd"
        return formatter
    }

    func testRowDetailsProvideWaterLabelPinnedStateAndTrimmedNotes() {
        let waterbody = Waterbody(name: "Lake Union", type: .lake)
        let pinnedSpot = Spot(
            title: "Dock",
            waterbody: waterbody,
            latitude: 47.62,
            longitude: -122.34,
            notes: "  Weed edge  "
        )
        let unknownSpot = Spot(title: "Rock", waterbody: nil, notes: "   ")

        let pinnedDetails = SpotPresentationLogic.rowDetails(for: pinnedSpot)
        let unknownDetails = SpotPresentationLogic.rowDetails(for: unknownSpot)

        XCTAssertEqual(pinnedDetails.waterbodyName, "Lake Union")
        XCTAssertTrue(pinnedDetails.isPinned)
        XCTAssertEqual(pinnedDetails.notesPreview, "Weed edge")
        XCTAssertEqual(unknownDetails.waterbodyName, "Unknown water")
        XCTAssertFalse(unknownDetails.isPinned)
        XCTAssertNil(unknownDetails.notesPreview)
    }

    func testCatchesHereFiltersBySpotIdentity() {
        let waterbody = Waterbody(name: "Lake Union", type: .lake)
        let dock = Spot(title: "Dock", waterbody: waterbody)
        let reeds = Spot(title: "Reeds", waterbody: waterbody)
        let dockTrip = Trip(waterbody: waterbody, spot: dock)
        let reedsTrip = Trip(waterbody: waterbody, spot: reeds)
        let catches = [
            CatchRecord(species: "Bass", trip: dockTrip, caughtAt: Date(timeIntervalSince1970: 200)),
            CatchRecord(species: "Trout", trip: reedsTrip, caughtAt: Date(timeIntervalSince1970: 300)),
            CatchRecord(species: "Perch", trip: dockTrip, caughtAt: Date(timeIntervalSince1970: 400)),
        ]

        let filtered = SpotPresentationLogic.catchesHere(spotID: dock.id, catches: catches)

        XCTAssertEqual(filtered.map(\.species), ["Perch", "Bass"])
    }

    func testStatSummaryFormatsCountsAsStrings() {
        let summary = SpotRecallSummary(
            recentTrips: [],
            tripCount: 7,
            catchCount: 7,
            successfulTripCount: 3,
            recencyInsight: nil,
            productivityInsight: nil,
            speciesInsight: nil,
            conditionsInsight: nil,
            lureInsight: nil,
            bestTimeWindow: nil,
            mostEffectiveLure: nil,
            seasonalityInsight: nil,
            similarConditionsCount: 0,
            similarConditionsLabel: nil
        )

        let stats = SpotPresentationLogic.statSummary(for: summary)

        XCTAssertEqual(stats.tripCountText, "7")
        XCTAssertEqual(stats.catchCountText, "7")
        XCTAssertEqual(stats.productiveTripCountText, "3")
    }

    func testRecentTripSummariesAreTimeStableAndReflectOutcomeState() {
        let waterbody = Waterbody(name: "Lake Union", type: .lake)
        let spot = Spot(title: "Dock", waterbody: waterbody)
        let skunkedTrip = Trip(
            waterbody: waterbody,
            spot: spot,
            conditionSnapshot: ConditionSnapshot(placeSummary: "Dock edge"),
            startAt: Date(timeIntervalSince1970: 1_711_900_000)
        )
        skunkedTrip.outcomeRawValue = TripOutcome.skunked.rawValue
        let productiveTrip = Trip(
            waterbody: waterbody,
            spot: spot,
            startAt: Date(timeIntervalSince1970: 1_711_986_400)
        )
        productiveTrip.outcomeRawValue = TripOutcome.caught.rawValue
        let catches = [
            CatchRecord(species: "Bass", trip: productiveTrip, lureOrBait: "Spinner"),
            CatchRecord(species: "Bass", trip: productiveTrip, lureOrBait: "Spinner"),
            CatchRecord(species: "Trout", trip: productiveTrip, lureOrBait: "Jig"),
        ]

        let summaries = SpotPresentationLogic.recentTripSummaries(
            trips: [skunkedTrip, productiveTrip],
            catches: catches,
            dateFormatter: fixedFormatter()
        )

        XCTAssertEqual(summaries.map(\.dateText), ["2024-03-31", "2024-04-01"])
        XCTAssertEqual(summaries.map(\.outcomeText), ["Skunked", "Caught"])
        XCTAssertEqual(summaries.map(\.catchText), ["Skunked", "3 catches"])
        XCTAssertEqual(summaries.map(\.isSkunked), [true, false])
        XCTAssertNil(summaries.first?.topSpeciesText)
        XCTAssertEqual(summaries.last?.topSpeciesText, "Bass")
        XCTAssertEqual(summaries.last?.topLureText, "Spinner")
        XCTAssertEqual(summaries.first?.conditionSummary, "Dock edge • Weather data unavailable")
    }

    func testRecentCatchSummariesStaySortedAndKeepTripContext() {
        let waterbody = Waterbody(name: "Lake Union", type: .lake)
        let spot = Spot(title: "Dock", waterbody: waterbody)
        let trip = Trip(waterbody: waterbody, spot: spot, startAt: Date(timeIntervalSince1970: 100))
        let olderCatch = CatchRecord(
            species: "Bass",
            trip: trip,
            caughtAt: Date(timeIntervalSince1970: 200),
            lureOrBait: "Spinner"
        )
        let newerCatch = CatchRecord(
            species: "Trout",
            trip: trip,
            caughtAt: Date(timeIntervalSince1970: 300),
            weightKg: 1.8,
            lengthCm: 48
        )

        let summaries = SpotPresentationLogic.recentCatchSummaries(
            catches: [newerCatch, olderCatch],
            dateFormatter: fixedFormatter()
        )

        XCTAssertEqual(summaries.map(\.species), ["Trout", "Bass"])
        XCTAssertEqual(summaries.first?.tripTitle, trip.title)
        XCTAssertEqual(summaries.first?.metricSummary, "48 cm · 1.8 kg")
        XCTAssertEqual(summaries.last?.lureOrBait, "Spinner")
    }

    func testPrivateRecallCardsKeepDeterministicCardsVisibleForSpotDetail() {
        let summary = SpotRecallSummary(
            recentTrips: [],
            catchCount: 5,
            successfulTripCount: 4,
            recencyInsight: nil,
            productivityInsight: nil,
            speciesInsight: nil,
            conditionsInsight: .init(
                title: "Most consistent catch window here",
                body: "Your catches here have lined up most often in morning: 4 completed trips with catches.",
                supportingSampleCount: 4
            ),
            lureInsight: nil,
            bestTimeWindow: "6-9 AM",
            mostEffectiveLure: "Spinner",
            seasonalityInsight: nil,
            similarConditionsCount: 2,
            similarConditionsLabel: "6-9 AM • Morning light"
        )

        let cards = SpotPresentationLogic.privateRecallCards(for: summary)

        XCTAssertNotNil(cards.first(where: { $0.kind == .conditions }))
        XCTAssertNotNil(cards.first(where: { $0.kind == .bestTimeWindow }))
    }

    func testRecallDetailsExposeEvidenceAwareSnapshotRows() {
        let summary = SpotRecallSummary(
            recentTrips: [],
            catchCount: 5,
            successfulTripCount: 4,
            recencyInsight: nil,
            productivityInsight: nil,
            speciesInsight: nil,
            conditionsInsight: .init(
                title: "Most consistent catch window here",
                body: "Your catches here have lined up most often in morning: 4 completed trips with catches.",
                supportingSampleCount: 4
            ),
            lureInsight: nil,
            bestTimeWindow: "6-9 AM",
            bestTimeWindowSupportCount: 4,
            mostEffectiveLure: "Spinner",
            mostEffectiveLureSupportCount: 3,
            seasonalityInsight: nil,
            similarConditionsCount: 0,
            similarConditionsLabel: nil,
            simpleConditionSummary: "Morning light • Dry",
            simpleConditionSupportCount: 3
        )

        let details = SpotPresentationLogic.recallDetails(for: summary)

        XCTAssertEqual(details.map(\.title), [
            "Most effective lure",
            "Best time window",
            "Simple condition summary",
        ])
        XCTAssertEqual(details.first?.evidence, "Based on 3 catches")
        XCTAssertEqual(details[1].evidence, "Based on 4 catches")
        XCTAssertEqual(details[2].evidence, "Based on 3 productive trips")
    }
}
