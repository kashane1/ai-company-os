import XCTest
@testable import AfterPlans

final class AfterPlansModelsTests: XCTestCase {
    func testLaunchVisibilityModesStayBounded() {
        XCTAssertEqual(
            PlanVisibility.launchModes,
            [.sameContextOnly, .inviteOnly, .knownPeople]
        )
        XCTAssertFalse(PlanVisibility.launchModes.contains(.friendsOfParticipants))
    }

    func testLifecycleStatesExposeClearConfirmationRoomAvailability() {
        XCTAssertTrue(PlanLifecycleState.open.allowsConfirmationRoom)
        XCTAssertTrue(PlanLifecycleState.confirmed.allowsConfirmationRoom)
        XCTAssertFalse(PlanLifecycleState.closed.allowsConfirmationRoom)
    }
}
