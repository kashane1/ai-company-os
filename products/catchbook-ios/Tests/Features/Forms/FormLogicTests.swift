import CoreLocation
import XCTest
@testable import Catchbook

final class FormLogicTests: XCTestCase {
    func testSpotFormLogicRequiresTrimmedTitleAndSelectedWaterbody() {
        XCTAssertFalse(SpotFormLogic.canSave(title: "   ", selectedWaterbodyID: UUID()))
        XCTAssertFalse(SpotFormLogic.canSave(title: "Dock", selectedWaterbodyID: nil))
        XCTAssertTrue(SpotFormLogic.canSave(title: " Dock ", selectedWaterbodyID: UUID()))
    }

    func testSpotFormDraftTrimsFields() {
        let draft = SpotFormLogic.draft(
            title: "  Dock  ",
            notes: "  Cast along reeds  ",
            coordinate: CLLocationCoordinate2D(latitude: 47.62, longitude: -122.35)
        )

        XCTAssertEqual(draft.title, "Dock")
        XCTAssertEqual(draft.notes, "Cast along reeds")
        XCTAssertEqual(draft.latitude ?? 0, 47.62, accuracy: 0.0001)
        XCTAssertEqual(draft.longitude ?? 0, -122.35, accuracy: 0.0001)
    }

    func testWaterbodyFormLogicTrimsAndValidatesName() {
        XCTAssertFalse(WaterbodyFormLogic.canSave(name: "   "))
        XCTAssertTrue(WaterbodyFormLogic.canSave(name: "  Lake Union "))
        XCTAssertEqual(WaterbodyFormLogic.normalizedName("  Lake Union "), "Lake Union")
    }

    func testWaterbodyFormDraftCapturesCanonicalCoordinate() {
        let draft = WaterbodyFormLogic.draft(
            name: "  Lake Union ",
            type: .lake,
            coordinate: CLLocationCoordinate2D(latitude: 47.6397, longitude: -122.3360)
        )

        XCTAssertEqual(draft.name, "Lake Union")
        XCTAssertEqual(draft.type, .lake)
        XCTAssertEqual(draft.latitude ?? 0, 47.6397, accuracy: 0.0001)
        XCTAssertEqual(draft.longitude ?? 0, -122.3360, accuracy: 0.0001)
    }
}
