import Foundation
import XCTest
@testable import Fishing_Logbook

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
            CatchRecord(species: "Bass", trip: dockTrip),
            CatchRecord(species: "Trout", trip: reedsTrip),
        ]

        let filtered = SpotPresentationLogic.catchesHere(spotID: dock.id, catches: catches)

        XCTAssertEqual(filtered.map(\.species), ["Bass"])
    }

    func testStatSummaryFormatsCountsAsStrings() {
        let summary = SpotRecallSummary(
            recentTrips: [],
            catchCount: 7,
            successfulTripCount: 3,
            bestTimeWindow: nil,
            mostEffectiveLure: nil,
            seasonalityInsight: nil,
            similarConditionsCount: 0,
            similarConditionsLabel: nil
        )

        let stats = SpotPresentationLogic.statSummary(for: summary)

        XCTAssertEqual(stats.tripCountText, "0")
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

        let summaries = SpotPresentationLogic.recentTripSummaries(
            trips: [skunkedTrip, productiveTrip],
            dateFormatter: fixedFormatter()
        )

        XCTAssertEqual(summaries.map(\.dateText), ["2024-03-31", "2024-04-01"])
        XCTAssertEqual(summaries.map(\.outcomeText), ["Skunked", "Caught"])
        XCTAssertEqual(summaries.map(\.isSkunked), [true, false])
        XCTAssertEqual(summaries.first?.conditionSummary, "Dock edge • Live weather deferred for this MVP")
    }
}
