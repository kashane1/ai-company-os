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
        // closedHistory has knownParticipantCount: 1 → only host "Mina", no shared participant with higherTrustPlan
        // → pastPartnerCount = 0, so "2 known faces" badge from isKnown still applies
        XCTAssertEqual(loop.affinity(for: higherTrustPlan.id)?.badges, ["Same moment", "2 known faces", "Repeat context"])
    }

    func testPastPartnerCountDetectedWhenParticipantAppearsInMultiplePlans() {
        let context = ContextOption(
            id: UUID(), type: .community, title: "Run Club",
            venueName: "Track", endedAtLabel: "Ended 5 min ago",
            proximityLabel: "4 min away", trustNote: "Runners first."
        )

        // Both plans share "Jordan" as a participant
        let planA = makePlan(title: "Brunch after run", contextTitle: context.title,
                             hostName: "Alex", namedParticipants: ["Jordan"])
        let planB = makePlan(title: "Coffee walk", contextTitle: context.title,
                             hostName: "Sam", namedParticipants: ["Jordan"])

        let loop = ContinuationLoop(
            plans: [planA, planB],
            selectedContext: context,
            blockedUserNames: [],
            currentUserName: "Maya",
            focusedPlanID: nil
        )

        XCTAssertEqual(loop.affinity(for: planA.id)?.pastPartnerCount, 1)
        XCTAssertEqual(loop.affinity(for: planB.id)?.pastPartnerCount, 1)
    }

    func testFamiliarCrewBadgeAndDetailLineAppearsForPastPartners() {
        let context = ContextOption(
            id: UUID(), type: .community, title: "Run Club",
            venueName: "Track", endedAtLabel: "Ended 5 min ago",
            proximityLabel: "4 min away", trustNote: "Runners first."
        )

        let sharedPlan = makePlan(title: "Brunch after run", contextTitle: context.title,
                                  hostName: "Alex", namedParticipants: ["Jordan", "Robin"])
        let otherPlan = makePlan(title: "Coffee walk", contextTitle: context.title,
                                 hostName: "Sam", namedParticipants: ["Robin"])

        let loop = ContinuationLoop(
            plans: [sharedPlan, otherPlan],
            selectedContext: context,
            blockedUserNames: [],
            currentUserName: "Maya",
            focusedPlanID: nil
        )

        let affinity = loop.affinity(for: sharedPlan.id)
        XCTAssertNotNil(affinity)
        XCTAssertTrue(affinity!.badges.contains("Familiar crew"))
        XCTAssertTrue(affinity!.detailLine.hasPrefix("You've planned with"))
    }

    func testRepeatContextDetailLineSpeaksToUser() {
        let context = ContextOption(
            id: UUID(), type: .classSession, title: "Pottery Night",
            venueName: "Clay House Studio", endedAtLabel: "Ended 10 min ago",
            proximityLabel: "3 min away", trustNote: "Pottery people first."
        )

        let openPlan = makePlan(title: "Tea after class", contextTitle: context.title,
                                hostName: "Nia", knownParticipantCount: 0)
        let closedPlan = makePlan(title: "Old tea", contextTitle: context.title,
                                  hostName: "Dev", knownParticipantCount: 0, lifecycle: .closed)

        let loop = ContinuationLoop(
            plans: [openPlan, closedPlan],
            selectedContext: context,
            blockedUserNames: [],
            currentUserName: "Maya",
            focusedPlanID: nil
        )

        let affinity = loop.affinity(for: openPlan.id)
        XCTAssertTrue(affinity?.hasPriorContextHistory == true)
        XCTAssertEqual(affinity?.detailLine, "You've kept going after this context before.")
    }

    func testRecapSummaryCountsFollowThroughsAndDetectsRepeatContexts() {
        let context = ContextOption(
            id: UUID(), type: .classSession, title: "Pottery Night",
            venueName: "Clay House Studio", endedAtLabel: "Ended 10 min ago",
            proximityLabel: "3 min away", trustNote: "Pottery people first."
        )

        let closedA = makePlan(title: "Tea after class", contextTitle: context.title,
                                hostName: "Nia", lifecycle: .closed)
        let closedB = makePlan(title: "Post-class slices", contextTitle: context.title,
                                hostName: "Mina", lifecycle: .closed)
        let openPlan = makePlan(title: "Walk after pottery", contextTitle: context.title,
                                 hostName: "Dev")

        let loop = ContinuationLoop(
            plans: [closedA, closedB, openPlan],
            selectedContext: context,
            blockedUserNames: [],
            currentUserName: "Maya",
            focusedPlanID: nil
        )

        let recap = loop.recapSummary
        XCTAssertEqual(recap.followThroughCount, 2)
        XCTAssertEqual(recap.distinctContextsFollowedThrough, ["Pottery Night"])
        XCTAssertEqual(recap.repeatContextTitle, "Pottery Night")
        XCTAssertTrue(recap.headline.contains("keep coming back"))
    }

    func testRecapSummaryWithNoClosedPlansShowsEmptyState() {
        let context = ContextOption(
            id: UUID(), type: .community, title: "Run Club",
            venueName: "Track", endedAtLabel: "Ended 5 min ago",
            proximityLabel: "4 min away", trustNote: "Runners first."
        )

        let openPlan = makePlan(title: "Coffee walk", contextTitle: context.title,
                                 hostName: "Sam")

        let loop = ContinuationLoop(
            plans: [openPlan],
            selectedContext: context,
            blockedUserNames: [],
            currentUserName: "Maya",
            focusedPlanID: nil
        )

        let recap = loop.recapSummary
        XCTAssertEqual(recap.followThroughCount, 0)
        XCTAssertTrue(recap.distinctContextsFollowedThrough.isEmpty)
        XCTAssertNil(recap.repeatContextTitle)
        XCTAssertTrue(recap.headline.contains("first continuation"))
    }

    func testRecapSummaryMultipleContextsWithoutRepeat() {
        let pottery = ContextOption(
            id: UUID(), type: .classSession, title: "Pottery Night",
            venueName: "Clay House Studio", endedAtLabel: "Ended 10 min ago",
            proximityLabel: "3 min away", trustNote: "Pottery people first."
        )
        let runClub = ContextOption(
            id: UUID(), type: .community, title: "Run Club",
            venueName: "Track", endedAtLabel: "Ended 5 min ago",
            proximityLabel: "4 min away", trustNote: "Runners first."
        )

        let closedPottery = makePlan(title: "Tea after class", contextTitle: pottery.title,
                                      hostName: "Nia", lifecycle: .closed)
        let closedRun = makePlan(title: "Coffee after run", contextTitle: runClub.title,
                                  hostName: "Dev", lifecycle: .closed)

        let loop = ContinuationLoop(
            plans: [closedPottery, closedRun],
            selectedContext: pottery,
            blockedUserNames: [],
            currentUserName: "Maya",
            focusedPlanID: nil
        )

        let recap = loop.recapSummary
        XCTAssertEqual(recap.followThroughCount, 2)
        XCTAssertEqual(recap.distinctContextsFollowedThrough.count, 2)
        XCTAssertNil(recap.repeatContextTitle) // each context only once — no repeat
        XCTAssertTrue(recap.headline.contains("2 follow-throughs"))
    }

    private func makePlan(
        title: String,
        contextTitle: String,
        hostName: String,
        hostDescriptor: String = "Host",
        knownParticipantCount: Int = 1,
        namedParticipants: [String] = [],
        lifecycle: PlanLifecycleState = .open
    ) -> AfterPlan {
        let knownSupporters = (0..<max(knownParticipantCount - 1, 0)).map { index in
            ParticipantSummary(
                id: UUID(),
                name: "Known \(index)",
                descriptor: "Met here before",
                isOrganizer: false,
                isKnown: true
            )
        }

        let namedSupporters = namedParticipants.map { name in
            ParticipantSummary(
                id: UUID(),
                name: name,
                descriptor: "From the same context",
                isOrganizer: false,
                isKnown: false
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
            ] + knownSupporters + namedSupporters,
            interestedCount: 1,
            placeSuggestions: [],
            participationState: .browsing
        )
    }
}
