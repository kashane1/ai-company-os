import XCTest
@testable import AfterPlans

final class AfterPlansModelsTests: XCTestCase {
    func testLaunchVisibilityModesStayBounded() {
        XCTAssertEqual(
            PlanVisibility.launchModes,
            [.sameContextOnly, .publicMatch, .inviteOnly]
        )
        XCTAssertFalse(PlanVisibility.launchModes.contains(.friendsOfParticipants))
        XCTAssertFalse(PlanVisibility.launchModes.contains(.knownPeople))
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
        XCTAssertEqual(makePlan(lifecycle: .active, participationState: .confirmed).confirmationAction, .wrapPlan)
        XCTAssertEqual(makePlan(lifecycle: .active, participationState: .joined).confirmationAction, .wrapPlan)
        XCTAssertEqual(makePlan(lifecycle: .active, participationState: .browsing).confirmationAction, .none)
        XCTAssertEqual(makePlan(lifecycle: .closed, participationState: .confirmed).confirmationAction, .none)
    }

    func testWrapPlanActionTitleAndCanTakeAction() {
        let activePlan = makePlan(lifecycle: .active, participationState: .confirmed)
        XCTAssertEqual(activePlan.confirmationActionTitle, "Wrap this plan")
        XCTAssertTrue(activePlan.canTakeConfirmationAction)

        let closedPlan = makePlan(lifecycle: .closed, participationState: .confirmed)
        XCTAssertEqual(closedPlan.confirmationActionTitle, "Plan wrapped")
        XCTAssertFalse(closedPlan.canTakeConfirmationAction)
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

    func testShareablePayloadURLContainsPlanID() {
        let plan = makePlan(lifecycle: .open, participationState: .browsing)
        let payload = plan.shareable
        XCTAssertTrue(payload.url.absoluteString.contains(plan.id.uuidString))
        XCTAssertTrue(payload.qrString.contains(plan.id.uuidString))
    }

    func testShareablePayloadTextContainsTitleAndContext() {
        let plan = makePlan(lifecycle: .forming, participationState: .joined)
        let payload = plan.shareable
        XCTAssertFalse(payload.text.isEmpty)
        XCTAssertTrue(payload.text.contains(plan.title))
        XCTAssertTrue(payload.text.contains(plan.contextTitle))
    }

    func testShareablePayloadURLIsAfterPlansScheme() {
        let plan = makePlan(lifecycle: .confirmed, participationState: .confirmed)
        XCTAssertEqual(plan.shareable.url.scheme, "afterplans")
    }

    func testShareablePayloadQRStringMatchesURLString() {
        let plan = makePlan(lifecycle: .open, participationState: .browsing)
        XCTAssertEqual(plan.shareable.qrString, plan.shareable.url.absoluteString)
    }

    // MARK: - Join-confidence and lifecycle-clarity cues

    func testJoinConfidenceCueReflectsLifecycleAndMomentum() {
        let openEmpty = makePlan(lifecycle: .open, participationState: .browsing, participantCount: 0)
        XCTAssertEqual(openEmpty.joinConfidenceCue, "Still early — soft interest helps")

        let openWithJoins = makePlan(lifecycle: .open, participationState: .browsing, participantCount: 2)
        XCTAssertTrue(openWithJoins.joinConfidenceCue.contains("a few more makes it real"))

        let forming = makePlan(lifecycle: .forming, participationState: .joined, participantCount: 2)
        XCTAssertEqual(forming.joinConfidenceCue, "Already taking shape")

        let formingHigh = makePlan(lifecycle: .forming, participationState: .joined, participantCount: 3)
        XCTAssertEqual(formingHigh.joinConfidenceCue, "Close to confirming")

        let confirmed = makePlan(lifecycle: .confirmed, participationState: .joined)
        XCTAssertEqual(confirmed.joinConfidenceCue, "Good to join — this is happening")

        let active = makePlan(lifecycle: .active, participationState: .confirmed)
        XCTAssertEqual(active.joinConfidenceCue, "Already in motion")

        let closed = makePlan(lifecycle: .closed, participationState: .confirmed)
        XCTAssertTrue(closed.joinConfidenceCue.isEmpty)
    }

    func testReadinessHintReflectsLifecycleAndMomentum() {
        let openEmpty = makePlan(lifecycle: .open, participationState: .browsing, participantCount: 0)
        XCTAssertTrue(openEmpty.readinessHint.contains("first yes"))

        let openWithJoins = makePlan(lifecycle: .open, participationState: .browsing, participantCount: 2)
        XCTAssertTrue(openWithJoins.readinessHint.contains("couple more"))

        let forming = makePlan(lifecycle: .forming, participationState: .joined, participantCount: 2)
        XCTAssertTrue(forming.readinessHint.contains("locks your spot"))

        let formingHigh = makePlan(lifecycle: .forming, participationState: .joined, participantCount: 3)
        XCTAssertTrue(formingHigh.readinessHint.contains("one more person"))

        let confirmed = makePlan(lifecycle: .confirmed, participationState: .joined)
        XCTAssertTrue(confirmed.readinessHint.contains("join with confidence"))

        let closed = makePlan(lifecycle: .closed, participationState: .confirmed)
        XCTAssertTrue(closed.readinessHint.isEmpty)
    }

    func testRecapLineOnlyPopulatesForClosedPlans() {
        let open = makePlan(lifecycle: .open, participationState: .browsing)
        XCTAssertTrue(open.recapLine.isEmpty)

        let forming = makePlan(lifecycle: .forming, participationState: .joined)
        XCTAssertTrue(forming.recapLine.isEmpty)

        let closedSmall = makePlan(lifecycle: .closed, participationState: .confirmed, participantCount: 2)
        XCTAssertTrue(closedSmall.recapLine.contains("followed through"))
        XCTAssertTrue(closedSmall.recapLine.contains("Pottery Night"))

        let closedLarge = makePlan(lifecycle: .closed, participationState: .confirmed, participantCount: 4)
        XCTAssertTrue(closedLarge.recapLine.contains("4 people"))
        XCTAssertTrue(closedLarge.recapLine.contains("kept the moment going"))

        let closedEmpty = makePlan(lifecycle: .closed, participationState: .confirmed, participantCount: 0)
        XCTAssertTrue(closedEmpty.recapLine.contains("continuation from"))
    }

    func testHandoffToTextAvailabilityMatchesLifecycle() {
        XCTAssertFalse(makePlan(lifecycle: .open, participationState: .browsing).canHandoffToText)
        XCTAssertFalse(makePlan(lifecycle: .forming, participationState: .joined).canHandoffToText)
        XCTAssertTrue(makePlan(lifecycle: .confirmed, participationState: .confirmed).canHandoffToText)
        XCTAssertTrue(makePlan(lifecycle: .active, participationState: .confirmed).canHandoffToText)
        XCTAssertFalse(makePlan(lifecycle: .closed, participationState: .confirmed).canHandoffToText)
    }

    func testHandoffTextBodyContainsPlanDetailsAndDeepLink() {
        let plan = makePlan(lifecycle: .confirmed, participationState: .confirmed)
        let body = plan.handoffTextBody
        XCTAssertTrue(body.contains(plan.title))
        XCTAssertTrue(body.contains(plan.venueLabel))
        XCTAssertTrue(body.contains("afterplans://join/"))
        XCTAssertTrue(body.contains(plan.id.uuidString))
    }

    func testConfirmationDisabledReasonIsLifecycleAware() {
        let open = makePlan(lifecycle: .open, participationState: .browsing)
        XCTAssertTrue(open.confirmationDisabledReason.contains("first yes"))

        let forming = makePlan(lifecycle: .forming, participationState: .joined)
        XCTAssertTrue(forming.confirmationDisabledReason.contains("lock in"))

        let confirmed = makePlan(lifecycle: .confirmed, participationState: .joined)
        XCTAssertTrue(confirmed.confirmationDisabledReason.contains("confirmed"))

        let active = makePlan(lifecycle: .active, participationState: .confirmed)
        XCTAssertTrue(active.confirmationDisabledReason.isEmpty)

        let closed = makePlan(lifecycle: .closed, participationState: .confirmed)
        XCTAssertTrue(closed.confirmationDisabledReason.isEmpty)
    }

    private func makePlan(
        lifecycle: PlanLifecycleState,
        participationState: PlanParticipationState,
        participantCount: Int = 1
    ) -> AfterPlan {
        let participants: [ParticipantSummary]
        if participantCount == 0 {
            participants = []
        } else {
            participants = (0..<participantCount).map { index in
                ParticipantSummary(
                    id: UUID(),
                    name: index == 0 ? "Nia" : "Person \(index)",
                    descriptor: index == 0 ? "Hosting" : "Joined",
                    isOrganizer: index == 0,
                    isKnown: index == 0
                )
            }
        }
        return AfterPlan(
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
            participants: participants,
            interestedCount: 0,
            placeSuggestions: [],
            participationState: participationState
        )
    }
}
