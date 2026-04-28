import XCTest
@testable import AfterPlans

@MainActor
final class InMemoryBackendTests: XCTestCase {
    func testBackendBootstrapsWithCanonicalSeed() async throws {
        let backend = InMemoryBackendFactory.make()
        let user = try await backend.identity.currentUser()
        XCTAssertFalse(user.firstName.isEmpty)
        let contexts = try await backend.contexts.suggestedContexts()
        XCTAssertGreaterThanOrEqual(contexts.count, 1)
    }

    func testFeedReturnsPlansForSelectedContext() async throws {
        let backend = InMemoryBackendFactory.make()
        let context = try await backend.contexts.suggestedContexts().first!
        let plans = try await backend.plans.feed(in: context.id)
        XCTAssertFalse(plans.isEmpty)
    }

    func testJoinAdvancesLifecycleAndParticipation() async throws {
        let backend = InMemoryBackendFactory.make()
        let context = try await backend.contexts.suggestedContexts().first!
        let plans = try await backend.plans.feed(in: context.id)
        let openPlan = plans.first { $0.lifecycle == .open || $0.lifecycle == .forming }
        let target = try XCTUnwrap(openPlan)

        let joined = try await backend.plans.join(planID: target.id)

        XCTAssertEqual(joined.participationState, .joined)
        XCTAssertNotEqual(joined.lifecycle, .open, "join should promote open → forming")
    }

    func testWrapClosesPlan() async throws {
        let backend = InMemoryBackendFactory.make()
        let context = try await backend.contexts.suggestedContexts().first!
        let plans = try await backend.plans.feed(in: context.id)
        let target = try XCTUnwrap(plans.first)

        _ = try await backend.plans.markActive(planID: target.id)
        let closed = try await backend.plans.wrap(planID: target.id)

        XCTAssertEqual(closed.lifecycle, .closed)
    }

    func testReportPlanDoesNotThrow() async throws {
        let backend = InMemoryBackendFactory.make()
        let context = try await backend.contexts.suggestedContexts().first!
        let plans = try await backend.plans.feed(in: context.id)
        let target = try XCTUnwrap(plans.first)
        try await backend.reports.reportPlan(target.id, reasonID: "harassment", note: nil)
    }

    func testResolveUnknownInviteThrowsNotFound() async throws {
        let backend = InMemoryBackendFactory.make()
        do {
            _ = try await backend.invites.resolveInvite(code: UUID().uuidString)
            XCTFail("expected notFound for unknown invite")
        } catch let error as AfterPlansServiceError {
            XCTAssertEqual(error, .notFound)
        }
    }

    // MARK: - Phase 2g — activity / venue / recommendation / push

    func testListActivitiesReturnsSeededTaxonomyWithParents() async throws {
        let backend = InMemoryBackendFactory.make()
        let activities = try await backend.activities.listActivities()
        XCTAssertFalse(activities.isEmpty)
        let parents = activities.filter { $0.parentActivityID == nil }
        let children = activities.filter { $0.parentActivityID != nil }
        XCTAssertGreaterThanOrEqual(parents.count, 1, "seed should include at least one parent activity")
        XCTAssertGreaterThanOrEqual(children.count, 1, "seed should include at least one child activity")
        XCTAssertEqual(activities, activities.sorted { $0.sortRank < $1.sortRank }, "activities should arrive pre-sorted by sortRank")
    }

    func testDeclareInterestPersistsAndIsIdempotent() async throws {
        let backend = InMemoryBackendFactory.make()
        let activities = try await backend.activities.listActivities()
        let target = try XCTUnwrap(activities.first { $0.parentActivityID != nil })

        let firstResult = try await backend.activities.declareInterest(activityID: target.id, venueID: nil)
        XCTAssertNil(firstResult, "in-memory shell does not auto-form contexts")

        _ = try await backend.activities.declareInterest(activityID: target.id, venueID: nil)
        let interests = try await backend.activities.myInterests()
        let matching = interests.filter { $0.activityID == target.id && $0.venueID == nil }
        XCTAssertEqual(matching.count, 1, "duplicate declarations should not create duplicate rows")
    }

    func testAutoJoinMatchingContextsReturnsZeroInMemory() async throws {
        let backend = InMemoryBackendFactory.make()
        let count = try await backend.activities.autoJoinMatchingContexts()
        XCTAssertEqual(count, 0)
    }

    func testUpsertVenueDeduplicatesByApplePlaceID() async throws {
        let backend = InMemoryBackendFactory.make()
        let placeID = "ABCD-1234"
        let first = Venue(
            id: UUID(),
            name: "Westside Track",
            address: "123 Main St",
            latitude: 37.0,
            longitude: -122.0,
            applePlaceID: placeID,
            isFreeform: false,
            verified: true
        )
        let stored = try await backend.venues.upsertVenue(first)

        let dup = Venue(
            id: UUID(),
            name: "Westside Track (alt name)",
            address: nil,
            latitude: nil,
            longitude: nil,
            applePlaceID: placeID,
            isFreeform: false,
            verified: false
        )
        let resolved = try await backend.venues.upsertVenue(dup)

        XCTAssertEqual(resolved.id, stored.id, "same Apple Place ID should resolve to existing venue")
        XCTAssertEqual(resolved.name, "Westside Track")
    }

    func testUpsertFreeformVenueIsStoredAsNew() async throws {
        let backend = InMemoryBackendFactory.make()
        let v1 = Venue(id: UUID(), name: "Mystery spot A", address: nil, latitude: nil, longitude: nil,
                       applePlaceID: nil, isFreeform: true, verified: false)
        let v2 = Venue(id: UUID(), name: "Mystery spot B", address: nil, latitude: nil, longitude: nil,
                       applePlaceID: nil, isFreeform: true, verified: false)
        let r1 = try await backend.venues.upsertVenue(v1)
        let r2 = try await backend.venues.upsertVenue(v2)
        XCTAssertNotEqual(r1.id, r2.id, "freeform venues without place IDs should not collapse")
    }

    func testRecommendationsReturnEmptyInMemory() async throws {
        let backend = InMemoryBackendFactory.make()
        let context = try await backend.contexts.suggestedContexts().first!
        let plans = try await backend.plans.feed(in: context.id)
        let target = try XCTUnwrap(plans.first)

        let postWrap = try await backend.recommendations.postWrapRecommendations(planID: target.id)
        let coInvite = try await backend.recommendations.coInviteSuggestions(planID: target.id)
        XCTAssertTrue(postWrap.isEmpty)
        XCTAssertTrue(coInvite.isEmpty)
        try await backend.recommendations.dismiss(recommendationID: UUID())
    }

    func testPushRegisterAndUnregisterDoNotThrow() async throws {
        let backend = InMemoryBackendFactory.make()
        try await backend.push.register(deviceToken: "test-token-001", platform: "apns")
        try await backend.push.unregister(deviceToken: "test-token-001")
    }
}
