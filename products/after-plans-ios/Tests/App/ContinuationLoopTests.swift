import XCTest
@testable import AfterPlans

final class ContinuationLoopTests: XCTestCase {
    func testCurrentContextPlansRankAheadOfSecondaryPlans() {
        let pottery = ContextOption(
            id: UUID(),
            type: .classSession,
            title: "Pottery Night",
            venueName: "Clay House Studio",
            endedAtLabel: "Ended 10 min ago",
            proximityLabel: "3 min away",
            trustNote: "Pottery people first."
        )
        let runClub = ContextOption(
            id: UUID(),
            type: .community,
            title: "Run Club",
            venueName: "Track",
            endedAtLabel: "Ended 5 min ago",
            proximityLabel: "4 min away",
            trustNote: "Run club first."
        )

        let potteryPlan = makePlan(title: "Tea after class", contextTitle: pottery.title, hostName: "Nia")
        let runPlan = makePlan(title: "Walk to the steps", contextTitle: runClub.title, hostName: "Dev")

        let loop = ContinuationLoop(
            plans: [runPlan, potteryPlan],
            selectedContext: pottery,
            blockedUserNames: [],
            currentUserName: "Maya",
            focusedPlanID: nil
        )

        XCTAssertEqual(loop.currentContextPlans.map(\.title), ["Tea after class"])
        XCTAssertEqual(loop.secondaryPlans.map(\.title), ["Walk to the steps"])
        XCTAssertEqual(loop.rankedPlans.first?.title, "Tea after class")
    }

    func testFocusedPlanFallsBackToCurrentContextLeadWhenSelectionIsMissing() {
        let context = ContextOption(
            id: UUID(),
            type: .classSession,
            title: "Pottery Night",
            venueName: "Clay House Studio",
            endedAtLabel: "Ended 10 min ago",
            proximityLabel: "3 min away",
            trustNote: "Pottery people first."
        )
        let plan = makePlan(title: "Tea after class", contextTitle: context.title, hostName: "Nia")

        let loop = ContinuationLoop(
            plans: [plan],
            selectedContext: context,
            blockedUserNames: [],
            currentUserName: "Maya",
            focusedPlanID: UUID()
        )

        XCTAssertEqual(loop.focusedPlan?.id, plan.id)
    }

    func testKnownPeopleAndRepeatContextPushPlanHigherWithinSameContext() {
        let context = ContextOption(
            id: UUID(),
            type: .classSession,
            title: "Pottery Night",
            venueName: "Clay House Studio",
            endedAtLabel: "Ended 10 min ago",
            proximityLabel: "3 min away",
            trustNote: "Pottery people first."
        )

        let lowerTrustPlan = makePlan(
            title: "Anywhere nearby",
            contextTitle: context.title,
            hostName: "Sam",
            hostDescriptor: "Hosting",
            knownParticipantCount: 0
        )

        let higherTrustPlan = makePlan(
            title: "Tacos with Nia",
            contextTitle: context.title,
            hostName: "Nia",
            hostDescriptor: "You've planned with Nia twice.",
            knownParticipantCount: 2
        )

        let closedHistory = makePlan(
            title: "Last week's tea",
            contextTitle: context.title,
            hostName: "Mina",
            hostDescriptor: "Hosted",
            knownParticipantCount: 1,
            lifecycle: .closed
        )

        let loop = ContinuationLoop(
            plans: [lowerTrustPlan, higherTrustPlan, closedHistory],
            selectedContext: context,
            blockedUserNames: [],
            currentUserName: "Maya",
            focusedPlanID: nil
        )

        XCTAssertEqual(loop.currentContextPlans.first?.title, "Tacos with Nia")
        XCTAssertEqual(loop.affinity(for: higherTrustPlan.id)?.badges, ["Same moment", "2 known faces", "Repeat context"])
    }

    private func makePlan(
        title: String,
        contextTitle: String,
        hostName: String,
        hostDescriptor: String = "Host",
        knownParticipantCount: Int = 1,
        lifecycle: PlanLifecycleState = .open
    ) -> AfterPlan {
        let supportingParticipants = (0..<max(knownParticipantCount - 1, 0)).map { index in
            ParticipantSummary(
                id: UUID(),
                name: "Known \(index)",
                descriptor: "Met here before",
                isOrganizer: false,
                isKnown: true
            )
        }

        return AfterPlan(
            id: UUID(),
            title: title,
            summary: "Simple next move",
            contextTitle: contextTitle,
            hostName: hostName,
            hostDescriptor: hostDescriptor,
            mode: .defaultOption,
            visibility: .sameContextOnly,
            lifecycle: lifecycle,
            timeLabel: "Now",
            venueLabel: "Tea House",
            distanceLabel: "3 min walk",
            trustBlurb: "Same context first.",
            participants: [
                ParticipantSummary(
                    id: UUID(),
                    name: hostName,
                    descriptor: "Hosting",
                    isOrganizer: true,
                    isKnown: knownParticipantCount > 0
                ),
            ] + supportingParticipants,
            interestedCount: 1,
            placeSuggestions: [],
            participationState: .browsing
        )
    }
}
