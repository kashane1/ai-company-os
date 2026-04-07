import XCTest
@testable import AfterPlans

@MainActor
final class AfterPlansStoreTests: XCTestCase {
    func testJoinMovesOpenPlanTowardFormingAndAddsCurrentUser() throws {
        let user = UserProfile(
            id: UUID(),
            firstName: "Maya",
            descriptor: "Verified",
            visibilityDefault: .sameContextOnly,
            trustHeadline: "Identity-light, but real"
        )
        let context = ContextOption(
            id: UUID(),
            type: .meetup,
            title: "Pottery Night",
            venueName: "Clay House Studio",
            endedAtLabel: "Ended 10 min ago",
            proximityLabel: "3 min away",
            trustNote: "Same context first."
        )
        let openPlan = AfterPlan(
            id: UUID(),
            title: "Tea after class",
            summary: "Simple next move",
            contextTitle: context.title,
            hostName: "Nia",
            hostDescriptor: "Host",
            mode: .defaultOption,
            visibility: .sameContextOnly,
            lifecycle: .open,
            timeLabel: "Now",
            venueLabel: "Tea House",
            distanceLabel: "3 min walk",
            trustBlurb: "Visible to the pottery group first.",
            participants: [
                ParticipantSummary(id: UUID(), name: "Nia", descriptor: "Hosting", isOrganizer: true, isKnown: true),
            ],
            interestedCount: 1,
            placeSuggestions: [],
            participationState: .browsing
        )

        let store = AfterPlansStore(
            currentUser: user,
            availableContexts: [context],
            selectedContext: context,
            plans: [openPlan],
            reportReasons: InMemorySafetyService().reportReasons,
            composerService: InMemoryPlanComposerService(),
            participationService: InMemoryPlanParticipationService(),
            inviteService: InMemoryInviteService(),
            analyticsService: NoopAnalyticsService()
        )

        store.join(openPlan.id)

        let updated = try XCTUnwrap(store.plan(with: openPlan.id))
        XCTAssertEqual(updated.lifecycle, .forming)
        XCTAssertEqual(updated.participationState, .joined)
        XCTAssertTrue(updated.participants.contains(where: { $0.name == "Maya" }))
    }

    func testBlockingHostRemovesPlanFromVisibleFeed() throws {
        let store = AfterPlansStore.bootstrap()
        let host = try XCTUnwrap(store.feedPlans.first?.hostName)
        XCTAssertFalse(store.feedPlans.isEmpty)

        store.blockUser(named: host)

        XCTAssertFalse(store.feedPlans.contains(where: { $0.hostName == host }))
    }
}
