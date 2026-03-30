import Foundation
import XCTest
@testable import Fishing_Logbook

final class TripPresentationLogicTests: XCTestCase {
    private func formatter() -> DateComponentsFormatter {
        let formatter = DateComponentsFormatter()
        formatter.allowedUnits = [.hour, .minute]
        formatter.unitsStyle = .abbreviated
        return formatter
    }

    func testTripRowSummaryReflectsActiveAndSkunkedStates() {
        let waterbody = Waterbody(name: "Lake Union", type: .lake)
        let spot = Spot(title: "Dock", waterbody: waterbody)
        let activeTrip = Trip(waterbody: waterbody, spot: spot, startAt: Date(timeIntervalSince1970: 100))
        let completedTrip = Trip(waterbody: waterbody, spot: spot, startAt: Date(timeIntervalSince1970: 100))
        completedTrip.endAt = Date(timeIntervalSince1970: 4_300)

        let activeSummary = TripPresentationLogic.tripRowSummary(
            trip: activeTrip,
            catchCount: 2,
            durationFormatter: formatter()
        )
        let skunkedSummary = TripPresentationLogic.tripRowSummary(
            trip: completedTrip,
            catchCount: 0,
            durationFormatter: formatter()
        )

        XCTAssertEqual(activeSummary.catchCountText, "2")
        XCTAssertFalse(activeSummary.showsSkunkedStyle)
        XCTAssertNil(activeSummary.durationText)
        XCTAssertEqual(activeSummary.spotTitle, "Dock")

        XCTAssertEqual(skunkedSummary.catchCountText, "Skunked")
        XCTAssertTrue(skunkedSummary.showsSkunkedStyle)
        XCTAssertEqual(skunkedSummary.durationText, "1h 10m")
    }

    func testTopStatsIncludeDurationAndTargetSpeciesOnlyWhenPresent() {
        let withExtras = TripPresentationLogic.topStats(
            catchCount: 3,
            durationText: "2h 15m",
            targetSpeciesCount: 2
        )
        let basic = TripPresentationLogic.topStats(
            catchCount: 1,
            durationText: nil,
            targetSpeciesCount: 0
        )

        XCTAssertEqual(withExtras.map(\.id), ["catches", "duration", "targets"])
        XCTAssertEqual(withExtras.map(\.label), ["Catches", "Duration", "Targets"])
        XCTAssertEqual(withExtras.map(\.value), ["3", "2h 15m", "2"])

        XCTAssertEqual(basic.map(\.id), ["catches"])
        XCTAssertEqual(basic.first?.label, "Catch")
        XCTAssertEqual(basic.first?.value, "1")
    }
}
