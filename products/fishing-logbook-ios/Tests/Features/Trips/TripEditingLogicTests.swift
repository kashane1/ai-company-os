import Foundation
import XCTest
@testable import Fishing_Logbook

final class TripEditingLogicTests: XCTestCase {
    func testFilteredSpotsAndSelectionResetStayScopedToSelectedWaterbody() {
        let waterbodyA = Waterbody(name: "Lake A", type: .lake)
        let waterbodyB = Waterbody(name: "Lake B", type: .lake)
        let spotA = Spot(title: "Dock", waterbody: waterbodyA)
        let spotB = Spot(title: "Point", waterbody: waterbodyB)

        let filtered = TripEditingLogic.filteredSpots(
            spots: [spotA, spotB],
            selectedWaterbodyID: waterbodyA.id
        )

        XCTAssertEqual(filtered.map(\.id), [spotA.id])
        XCTAssertEqual(
            TripEditingLogic.selectedSpotIDAfterWaterbodyChange(
                selectedSpotID: spotA.id,
                filteredSpots: filtered
            ),
            spotA.id
        )
        XCTAssertNil(
            TripEditingLogic.selectedSpotIDAfterWaterbodyChange(
                selectedSpotID: spotB.id,
                filteredSpots: filtered
            )
        )
    }

    func testCanSaveRequiresWaterbodyAndValidEndedRange() {
        let startAt = Date(timeIntervalSince1970: 100)
        let endAt = Date(timeIntervalSince1970: 200)

        XCTAssertFalse(
            TripEditingLogic.canSave(
                selectedWaterbodyID: nil,
                isTripActive: true,
                startAt: startAt,
                endAt: endAt
            )
        )
        XCTAssertFalse(
            TripEditingLogic.canSave(
                selectedWaterbodyID: UUID(),
                isTripActive: false,
                startAt: endAt,
                endAt: startAt
            )
        )
        XCTAssertTrue(
            TripEditingLogic.canSave(
                selectedWaterbodyID: UUID(),
                isTripActive: true,
                startAt: endAt,
                endAt: startAt
            )
        )
    }

    func testTripOutcomeReflectsActivityAndCatchCount() {
        XCTAssertEqual(TripEditingLogic.tripOutcome(endAt: nil, catchCount: 0), .active)
        XCTAssertEqual(TripEditingLogic.tripOutcome(endAt: Date(), catchCount: 0), .skunked)
        XCTAssertEqual(TripEditingLogic.tripOutcome(endAt: Date(), catchCount: 1), .caught)
    }

    func testConditionDraftNormalizesTextAndNumericFields() {
        let draft = TripEditingLogic.conditionDraft(
            placeSummary: "  Dock  ",
            timeWindowSummary: " ",
            lightLevelSummary: " Morning light ",
            weatherSummary: "Cloudy",
            windSummary: " 10 kt ",
            cloudCoverSummary: " ",
            precipitationSummary: " Dry ",
            temperatureC: " 12.5 ",
            latitude: " 47.6205 ",
            longitude: " -122.3493 "
        )

        XCTAssertEqual(draft.placeSummary, "Dock")
        XCTAssertNil(draft.timeWindowSummary)
        XCTAssertEqual(draft.lightLevelSummary, "Morning light")
        XCTAssertEqual(draft.windSummary, "10 kt")
        XCTAssertNil(draft.cloudCoverSummary)
        XCTAssertEqual(draft.precipitationSummary, "Dry")
        XCTAssertEqual(draft.temperatureC, 12.5)
        XCTAssertEqual(draft.latitude, 47.6205)
        XCTAssertEqual(draft.longitude, -122.3493)
    }

    func testCatchDraftTrimsFieldsAndReflectsPhotoMetadata() {
        let withPhoto = TripEditingLogic.catchDraft(
            species: "  Bass ",
            lureOrBait: " Spinner ",
            method: " Burn ",
            weight: " 1.4 ",
            length: " 42 ",
            note: " Healthy fish ",
            photoData: Data([1, 2, 3])
        )
        XCTAssertEqual(withPhoto.species, "Bass")
        XCTAssertEqual(withPhoto.lureOrBait, "Spinner")
        XCTAssertEqual(withPhoto.method, "Burn")
        XCTAssertEqual(withPhoto.weightKg, 1.4)
        XCTAssertEqual(withPhoto.lengthCm, 42)
        XCTAssertEqual(withPhoto.note, "Healthy fish")
        XCTAssertEqual(withPhoto.photoReference, "embedded-photo")
        XCTAssertEqual(withPhoto.photoContentType, "image/jpeg")

        let withoutPhoto = TripEditingLogic.catchDraft(
            species: "  ",
            lureOrBait: "",
            method: "",
            weight: "invalid",
            length: " ",
            note: "  ",
            photoData: nil
        )
        XCTAssertEqual(withoutPhoto.species, "")
        XCTAssertNil(withoutPhoto.weightKg)
        XCTAssertNil(withoutPhoto.lengthCm)
        XCTAssertEqual(withoutPhoto.note, "")
        XCTAssertNil(withoutPhoto.photoReference)
        XCTAssertNil(withoutPhoto.photoContentType)
    }
}
