import XCTest
@testable import AfterPlans

@MainActor
final class AfterPlansStoreTests: XCTestCase {
    private func testUser(name: String = "Maya") -> UserProfile {
        UserProfile(
            id: UUID(),
            firstName: name,
            descriptor: "Verified",
            visibilityDefault: .sameContextOnly,
            trustHeadline: "Identity-light, but real"
        )
    }

    private func testContext(title: String = "Pottery Night") -> ContextOption {
        ContextOption(
            id: UUID(),
            type: .meetup,
            title: title,
            venueName: "Clay House Studio",
            endedAtLabel: "Ended 10 min ago",
            proximityLabel: "3 min away",
            trustNote: "Same context first."
        )
    }

    private func openPlan(in context: ContextOption, title: String = "Tea after class") -> AfterPlan {
        AfterPlan(
            id: UUID(),
            title: title,
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
    }

    func testJoinMovesOpenPlanTowardFormingAndAddsCurrentUser() async throws {
        let user = testUser()
        let context = testContext()
        let plan = openPlan(in: context)
        let store = AfterPlansStore.testStore(
            currentUser: user,
            availableContexts: [context],
            selectedContext: context,
            plans: [plan]
        )

        await store.join(plan.id)

        let updated = try XCTUnwrap(store.plan(with: plan.id))
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

    func testCreatePlanPinsItAsCurrentMoveAndSetsFeedbackMessage() async throws {
        let store = AfterPlansStore.bootstrap()
        let draft = CreatePlanDraft(
            mode: .defaultOption,
            title: "Tea after pottery",
            summary: "Keep talking a bit longer",
            venueHint: "Lantern Tea",
            timeHint: "Right now",
            visibility: .sameContextOnly
        )

        let created = await store.createPlan(from: draft)
        XCTAssertTrue(created)

        let focused = try XCTUnwrap(store.focusedPlan)
        XCTAssertEqual(focused.title, "Tea after pottery")
        XCTAssertEqual(store.focusedPlanID, focused.id)
        XCTAssertEqual(store.lastActionMessage, "Your plan is live for Pottery Night.")
    }

    func testSelectingContextRetargetsFocusedPlanToThatContext() throws {
        let store = AfterPlansStore.bootstrap()
        let newContext = try XCTUnwrap(store.availableContexts.last)

        store.selectContext(newContext)

        let focused = try XCTUnwrap(store.focusedPlan)
        XCTAssertEqual(focused.contextTitle, newContext.title)
        XCTAssertEqual(store.lastActionMessage, "Showing what's next after \(newContext.title).")
    }

    func testPlanCanProgressFullLifecycleIncludingWrap() async throws {
        let user = testUser()
        let context = testContext()
        let plan = openPlan(in: context)
        let store = AfterPlansStore.testStore(
            currentUser: user,
            availableContexts: [context],
            selectedContext: context,
            plans: [plan]
        )

        await store.join(plan.id)
        await store.confirm(plan.id)
        await store.markPlanActive(plan.id)
        XCTAssertEqual(try XCTUnwrap(store.plan(with: plan.id)).lifecycle, .active)

        await store.wrapPlan(plan.id)
        let closed = try XCTUnwrap(store.plan(with: plan.id))
        XCTAssertEqual(closed.lifecycle, .closed)
        XCTAssertTrue(store.lastActionMessage?.contains("wrapped") == true)
        XCTAssertFalse(closed.recapLine.isEmpty)
    }

    func testPlanCanProgressFromOpenToFormingToConfirmedToActive() async throws {
        let user = testUser()
        let context = testContext()
        let plan = openPlan(in: context)
        let store = AfterPlansStore.testStore(
            currentUser: user,
            availableContexts: [context],
            selectedContext: context,
            plans: [plan]
        )

        await store.join(plan.id)
        XCTAssertEqual(try XCTUnwrap(store.plan(with: plan.id)).lifecycle, .forming)

        await store.confirm(plan.id)
        XCTAssertEqual(try XCTUnwrap(store.plan(with: plan.id)).lifecycle, .confirmed)

        await store.markPlanActive(plan.id)
        let active = try XCTUnwrap(store.plan(with: plan.id))
        XCTAssertEqual(active.lifecycle, .active)
        XCTAssertEqual(store.lastActionMessage, "Tea after class is now in motion.")
    }

    func testPreparingInviteShareStoresBoundedShareStateForCurrentLoopPlan() async throws {
        let store = AfterPlansStore.bootstrap()
        let plan = try XCTUnwrap(store.currentContextPlans.first)

        XCTAssertTrue(plan.canShareInvite)
        XCTAssertEqual(store.inviteChannels(for: plan), plan.inviteChannels)

        await store.prepareInviteShare(for: plan.id, channel: plan.inviteChannels[0])

        let state = try XCTUnwrap(store.inviteShareState(for: plan.id))
        XCTAssertEqual(state.channel, plan.inviteChannels[0])
        XCTAssertEqual(store.focusedPlanID, plan.id)
        XCTAssertEqual(store.lastActionMessage, state.statusTitle)
    }

    func testIncomingInviteLinkFocusesPlanAndRestoresItsContext() throws {
        let store = AfterPlansStore.bootstrap()
        let plan = try XCTUnwrap(store.secondaryFeedPlans.first)
        store.hasCompletedOnboarding = false

        let handled = store.handleIncomingURL(plan.shareable.url)

        XCTAssertTrue(handled)
        XCTAssertTrue(store.hasCompletedOnboarding)
        XCTAssertEqual(store.selectedTab, .home)
        XCTAssertEqual(store.focusedPlanID, plan.id)
        XCTAssertEqual(store.selectedContext?.title, plan.contextTitle)
        XCTAssertEqual(store.lastActionMessage, "Opened invite for \(plan.title).")
    }

    func testUnavailableIncomingInviteReportsUnavailableInvite() {
        let store = AfterPlansStore.bootstrap()
        let url = URL(string: "afterplans://join/\(UUID().uuidString)")!

        XCTAssertFalse(store.handleIncomingURL(url))
        XCTAssertEqual(store.selectedTab, .home)
        XCTAssertEqual(store.lastActionMessage, "That invite is no longer available.")
    }

    func testNonInviteURLIsIgnored() {
        let store = AfterPlansStore.bootstrap()

        XCTAssertFalse(store.handleIncomingURL(URL(string: "afterplans://profile")!))
        XCTAssertNil(store.lastActionMessage)
    }

    func testClosedPlanCannotPrepareInviteShare() async {
        let user = testUser()
        let context = testContext()
        var closedPlan = openPlan(in: context)
        closedPlan.lifecycle = .closed
        let store = AfterPlansStore.testStore(
            currentUser: user,
            availableContexts: [context],
            selectedContext: context,
            plans: [closedPlan]
        )

        await store.prepareInviteShare(for: closedPlan.id, channel: .sameContext)

        XCTAssertNil(store.inviteShareState(for: closedPlan.id))
    }

    func testCurrentLoopPlanCanReachSafetyActionsThroughStore() async throws {
        let store = AfterPlansStore.bootstrap()
        let plan = try XCTUnwrap(store.currentContextPlans.first)

        await store.reportPlan(plan)

        XCTAssertEqual(store.focusedPlanID, plan.id)
        XCTAssertEqual(store.reportLog.last, "Reported plan: \(plan.title)")
        XCTAssertTrue(store.blockEffectNote.contains("disappear"))
    }
}
