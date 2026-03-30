import XCTest
@testable import Fishing_Logbook

final class FormLogicTests: XCTestCase {
    func testSpotFormLogicRequiresTrimmedTitleAndSelectedWaterbody() {
        XCTAssertFalse(SpotFormLogic.canSave(title: "   ", selectedWaterbodyID: UUID()))
        XCTAssertFalse(SpotFormLogic.canSave(title: "Dock", selectedWaterbodyID: nil))
        XCTAssertTrue(SpotFormLogic.canSave(title: " Dock ", selectedWaterbodyID: UUID()))
    }

    func testSpotFormDraftTrimsFields() {
        let draft = SpotFormLogic.draft(title: "  Dock  ", notes: "  Cast along reeds  ")

        XCTAssertEqual(draft.title, "Dock")
        XCTAssertEqual(draft.notes, "Cast along reeds")
    }

    func testWaterbodyFormLogicTrimsAndValidatesName() {
        XCTAssertFalse(WaterbodyFormLogic.canSave(name: "   "))
        XCTAssertTrue(WaterbodyFormLogic.canSave(name: "  Lake Union "))
        XCTAssertEqual(WaterbodyFormLogic.normalizedName("  Lake Union "), "Lake Union")
    }
}
