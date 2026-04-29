import XCTest
@testable import AfterPlans

final class CreatePlanDraftTests: XCTestCase {
    func testDraftRequiresContextBeforePublishing() {
        let draft = CreatePlanDraft(title: "Tea after class")

        XCTAssertEqual(
            draft.validationMessage(hasContext: false),
            "Pick the activity that just ended before you start what's next."
        )
    }

    func testExactPlanRequiresNamedPlace() {
        let draft = CreatePlanDraft(mode: .exact, title: "Tea after class", venueHint: "")

        XCTAssertEqual(
            draft.validationMessage(hasContext: true),
            "Exact plans should name the place up front."
        )
    }

    func testOpenIntentCanValidateWithoutPlaceWhenTitleExists() {
        let draft = CreatePlanDraft(mode: .openIntent, title: "Keep it going", venueHint: "")

        XCTAssertNil(draft.validationMessage(hasContext: true))
    }

    // MARK: - Phase 5 — publicMatch validation

    func testPublicMatchPlanRequiresActivity() {
        let draft = CreatePlanDraft(title: "Pickup game", visibility: .publicMatch, activityID: nil, venueID: UUID())
        XCTAssertEqual(
            draft.validationMessage(hasContext: false),
            "Pick an activity so the right people see this."
        )
    }

    func testPublicMatchPlanRequiresVenue() {
        let draft = CreatePlanDraft(title: "Pickup game", visibility: .publicMatch, activityID: UUID(), venueID: nil)
        XCTAssertEqual(
            draft.validationMessage(hasContext: false),
            "Pick a place so people know where to show up."
        )
    }

    func testPublicMatchPlanIgnoresContextRequirement() {
        let draft = CreatePlanDraft(title: "Pickup game", visibility: .publicMatch, activityID: UUID(), venueID: UUID())
        XCTAssertNil(draft.validationMessage(hasContext: false))
    }

    func testPublicMatchExactModeDoesNotDoubleRequireVenueHint() {
        // venueID is the structured field; venueHint stays freeform copy.
        // The exact-mode "name the place up front" rule should NOT fire
        // for publicMatch plans, since the venue is already structured.
        let draft = CreatePlanDraft(
            mode: .exact,
            title: "Climb at Mission Cliffs",
            venueHint: "",
            visibility: .publicMatch,
            activityID: UUID(),
            venueID: UUID()
        )
        XCTAssertNil(draft.validationMessage(hasContext: false))
    }
}
