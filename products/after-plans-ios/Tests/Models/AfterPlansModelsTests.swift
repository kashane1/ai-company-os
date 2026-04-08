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

    func testMeaningfulHostMemoryFiltersGenericHostLabels() {
        let generic = AfterPlan(
            id: UUID(),
            title: "Tea after class",
            summary: "Simple next move",
            contextTitle: "Pottery Night",
            hostName: "Nia",
            hostDescriptor: "Hosting",
            mode: .defaultOption,
            visibility: .sameContextOnly,
            lifecycle: .open,
            timeLabel: "Now",
            venueLabel: "Tea House",
            distanceLabel: "3 min walk",
            trustBlurb: "Same context first.",
            participants: [
                ParticipantSummary(id: UUID(), name: "Nia", descriptor: "Hosting", isOrganizer: true, isKnown: true),
            ],
            interestedCount: 0,
            placeSuggestions: [],
            participationState: .browsing
        )

        var meaningful = generic
        meaningful.hostDescriptor = "You've planned with Nia twice."

        XCTAssertNil(generic.meaningfulHostMemory)
        XCTAssertEqual(meaningful.meaningfulHostMemory, "You've planned with Nia twice.")
    }

    func testActiveAndClosedPlansSuppressMisleadingActions() {
        var active = makePlan(lifecycle: .active, participationState: .browsing)
        var closed = makePlan(lifecycle: .closed, participationState: .browsing)

        active.placeSuggestions = ["Mercado"]
        closed.placeSuggestions = ["Mercado"]

        XCTAssertFalse(active.canJoin)
        XCTAssertFalse(active.canExpressInterest)
        XCTAssertFalse(active.canSuggestPlace)
        XCTAssertEqual(active.joinActionTitle, "Already started")
        XCTAssertEqual(active.suggestPlaceActionTitle, "Already moving")

        XCTAssertFalse(closed.canJoin)
        XCTAssertFalse(closed.canExpressInterest)
        XCTAssertFalse(closed.canSuggestPlace)
        XCTAssertEqual(closed.joinActionTitle, "Wrapped")
        XCTAssertEqual(closed.suggestPlaceActionTitle, "Wrapped")
    }

    func testConfirmationActionMapsLifecycleProgression() {
        XCTAssertEqual(makePlan(lifecycle: .open, participationState: .browsing).confirmationAction, .join)
        XCTAssertEqual(makePlan(lifecycle: .forming, participationState: .joined).confirmationAction, .confirm)
        XCTAssertEqual(makePlan(lifecycle: .confirmed, participationState: .joined).confirmationAction, .markActive)
        XCTAssertEqual(makePlan(lifecycle: .active, participationState: .confirmed).confirmationAction, .none)
        XCTAssertEqual(makePlan(lifecycle: .closed, participationState: .confirmed).confirmationAction, .none)
    }

    func testInviteShareAvailabilityMatchesLifecycle() {
        XCTAssertTrue(makePlan(lifecycle: .open, participationState: .browsing).canShareInvite)
        XCTAssertTrue(makePlan(lifecycle: .forming, participationState: .joined).canShareInvite)
        XCTAssertTrue(makePlan(lifecycle: .confirmed, participationState: .confirmed).canShareInvite)
        XCTAssertFalse(makePlan(lifecycle: .active, participationState: .confirmed).canShareInvite)
        XCTAssertFalse(makePlan(lifecycle: .closed, participationState: .confirmed).canShareInvite)
    }

    func testInviteShareFramingStaysLowPressureAndContinuationOriented() {
        let plan = makePlan(lifecycle: .forming, participationState: .joined)

        XCTAssertEqual(plan.shareActionTitle, "Bring in the right people")
        XCTAssertEqual(plan.shareAudienceHeadline, "Start with people from this same context.")
        XCTAssertTrue(plan.shareActionSubtitle.contains("bounded invites"))
        XCTAssertTrue(plan.shareJoinFraming.contains("lightweight join"))
        XCTAssertEqual(plan.inviteChannels, [.sameContext, .nearbyQR])
    }

    func testVisibilityFramingStaysBoundedToLaunchTrustRules() {
        let plan = makePlan(lifecycle: .open, participationState: .browsing)

        XCTAssertEqual(plan.visibilityHeadline, "Visible to people from this context")
        XCTAssertTrue(plan.visibilityDetail.contains("Pottery Night"))
        XCTAssertTrue(plan.visibilityFootnote.contains("shared activity"))
        XCTAssertTrue(plan.safetyEntryDetail.contains("Report or block"))
    }

    func testActiveAndClosedPlansDoNotDescribeVisibilityAsFreshOutreach() {
        let active = makePlan(lifecycle: .active, participationState: .confirmed)
        let closed = makePlan(lifecycle: .closed, participationState: .confirmed)

        XCTAssertFalse(active.canShareInvite)
        XCTAssertTrue(active.visibilityDetail.contains("already in motion"))
        XCTAssertTrue(active.safetyEntryDetail.contains("still apply"))

        XCTAssertFalse(closed.canShareInvite)
        XCTAssertTrue(closed.visibilityDetail.contains("history only"))
        XCTAssertTrue(closed.safetyEntryDetail.contains("follow-up"))
    }

    private func makePlan(
        lifecycle: PlanLifecycleState,
        participationState: PlanParticipationState
    ) -> AfterPlan {
        AfterPlan(
            id: UUID(),
            title: "Tea after class",
            summary: "Simple next move",
            contextTitle: "Pottery Night",
            hostName: "Nia",
            hostDescriptor: "Hosting",
            mode: .defaultOption,
            visibility: .sameContextOnly,
            lifecycle: lifecycle,
            timeLabel: "Now",
            venueLabel: "Tea House",
            distanceLabel: "3 min walk",
            trustBlurb: "Same context first.",
            participants: [
                ParticipantSummary(id: UUID(), name: "Nia", descriptor: "Hosting", isOrganizer: true, isKnown: true),
            ],
            interestedCount: 0,
            placeSuggestions: [],
            participationState: participationState
        )
    }
}
