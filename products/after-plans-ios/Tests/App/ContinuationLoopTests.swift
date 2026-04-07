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

    private func makePlan(title: String, contextTitle: String, hostName: String) -> AfterPlan {
        AfterPlan(
            id: UUID(),
            title: title,
            summary: "Simple next move",
            contextTitle: contextTitle,
            hostName: hostName,
            hostDescriptor: "Host",
            mode: .defaultOption,
            visibility: .sameContextOnly,
            lifecycle: .open,
            timeLabel: "Now",
            venueLabel: "Tea House",
            distanceLabel: "3 min walk",
            trustBlurb: "Same context first.",
            participants: [
                ParticipantSummary(id: UUID(), name: hostName, descriptor: "Hosting", isOrganizer: true, isKnown: true),
            ],
            interestedCount: 1,
            placeSuggestions: [],
            participationState: .browsing
        )
    }
}
