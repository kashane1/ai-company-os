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
}
