import XCTest
@testable import AfterPlans

// Integration test for SupabaseBackend against a live local Supabase stack.
//
// This test is skipped unless both AFTERPLANS_SUPABASE_URL and
// AFTERPLANS_SUPABASE_KEY are present in the process environment. The shared
// scheme sets them to the local-dev defaults, so running `xcodebuild test`
// against a running `supabase start` stack will exercise the real wire path.
//
// The single-user design (one anonymous session plays host *and* joiner) is
// intentional: this test is about wire-shape correctness, not multi-user
// semantics. Multi-user behavior is covered by InMemoryBackendTests against
// the in-memory adapter.
@MainActor
final class SupabaseBackendIntegrationTests: XCTestCase {
    private func makeBackend() async throws -> AfterPlansBackend {
        let env = ProcessInfo.processInfo.environment
        guard let urlString = env["AFTERPLANS_SUPABASE_URL"],
              let url = URL(string: urlString),
              let key = env["AFTERPLANS_SUPABASE_KEY"], !key.isEmpty else {
            throw XCTSkip("Set AFTERPLANS_SUPABASE_URL and AFTERPLANS_SUPABASE_KEY to run integration tests against local Supabase.")
        }
        // Clear any session persisted by an earlier test run. After
        // `supabase db reset` the cached user_id no longer exists in
        // auth.users; reusing it would FK-violate on profile insert.
        await SupabaseBackendFactory.resetSessionForTesting(url: url, anonKey: key)
        guard let backend = SupabaseBackendFactory.make(url: url, anonKey: key) else {
            throw XCTSkip("supabase-swift not linked into the test target.")
        }
        return backend
    }

    // Walks the full lifecycle: identity bootstrap → context discovery →
    // create → join → confirm → mark active → wrap. Asserts each transition.
    func testFullLifecycleAgainstLocalSupabase() async throws {
        let backend = try await makeBackend()

        let user = try await backend.identity.currentUser()
        XCTAssertFalse(user.firstName.isEmpty, "anonymous bootstrap should populate first name")

        let contexts = try await backend.contexts.suggestedContexts()
        let context = try XCTUnwrap(contexts.first, "seed.sql should provide at least one context")

        let draft = CreatePlanDraft(
            mode: .defaultOption,
            title: "Integration test plan",
            summary: "Created by SupabaseBackendIntegrationTests",
            venueHint: "TBD",
            timeHint: "Now",
            visibility: .sameContextOnly
        )
        let created = try await backend.plans.createPlan(from: draft, in: context.id)
        XCTAssertEqual(created.lifecycle, .open, "fresh plan should start at lifecycle=open")
        XCTAssertEqual(created.title, draft.title)
        XCTAssertEqual(created.participants.count, 1, "host should be the sole participant on creation")

        let fetched = try await backend.plans.plan(id: created.id)
        XCTAssertEqual(fetched.id, created.id, "plan(id:) should round-trip via RLS")

        let joined = try await backend.plans.join(planID: created.id)
        XCTAssertEqual(joined.lifecycle, .forming, "join should promote open → forming")

        let confirmed = try await backend.plans.confirm(planID: created.id)
        XCTAssertEqual(confirmed.lifecycle, .confirmed)

        let active = try await backend.plans.markActive(planID: created.id)
        XCTAssertEqual(active.lifecycle, .active)

        let wrapped = try await backend.plans.wrap(planID: created.id)
        XCTAssertEqual(wrapped.lifecycle, .closed)
    }

    // Phase 2g — exercise the new wire surfaces against the live local stack:
    // activity taxonomy, declared interests, venue upsert, push token
    // registration. Auto-context formation is a Phase 7 concern and is not
    // exercised here.
    func testActivityVenueAndPushAgainstLocalSupabase() async throws {
        let backend = try await makeBackend()
        // Trigger anonymous sign-in so the `authenticated` role RLS
        // policies apply for the activity/venue/push surfaces below.
        _ = try await backend.identity.currentUser()

        let activities = try await backend.activities.listActivities()
        XCTAssertGreaterThanOrEqual(activities.count, 6, "seed.sql ships at least the 6 parent activities")
        XCTAssertEqual(activities, activities.sorted { $0.sortRank < $1.sortRank })
        let leaf = try XCTUnwrap(activities.first { $0.parentActivityID != nil }, "seed should include child activities")

        let interestContextID = try await backend.activities.declareInterest(activityID: leaf.id, venueID: nil)
        XCTAssertNil(interestContextID, "auto-context formation is deferred to Phase 7")

        let myInterests = try await backend.activities.myInterests()
        XCTAssertTrue(myInterests.contains { $0.activityID == leaf.id && $0.venueID == nil })

        // declareInterest is upsert-shaped server-side; calling twice should
        // not produce duplicate rows.
        _ = try await backend.activities.declareInterest(activityID: leaf.id, venueID: nil)
        let interestsAfter = try await backend.activities.myInterests()
        XCTAssertEqual(
            interestsAfter.filter { $0.activityID == leaf.id && $0.venueID == nil }.count,
            1,
            "duplicate declareInterest should be idempotent"
        )

        let placeID = "test-place-\(UUID().uuidString)"
        let venue = Venue(
            id: UUID(),
            name: "Integration Test Track",
            address: "100 Test Lane",
            latitude: 37.7,
            longitude: -122.4,
            applePlaceID: placeID,
            isFreeform: false,
            verified: false
        )
        let stored = try await backend.venues.upsertVenue(venue)
        XCTAssertEqual(stored.applePlaceID, placeID)

        // Same Apple Place ID returns the existing row.
        let dup = Venue(
            id: UUID(),
            name: "Different name same place",
            address: nil, latitude: nil, longitude: nil,
            applePlaceID: placeID,
            isFreeform: false, verified: false
        )
        let resolved = try await backend.venues.upsertVenue(dup)
        XCTAssertEqual(resolved.id, stored.id, "Apple Place ID should dedupe the venue")

        let token = "integration-test-token-\(UUID().uuidString)"
        try await backend.push.register(deviceToken: token, platform: "ios")
        // Re-register is upsert via on conflict (token); should not throw.
        try await backend.push.register(deviceToken: token, platform: "ios")
        try await backend.push.unregister(deviceToken: token)

        // Recommendation surfaces are stubbed in Phase 2; Phase 6 fills them in.
        let postWrap = try await backend.recommendations.postWrapRecommendations(planID: UUID())
        XCTAssertTrue(postWrap.isEmpty)
    }
}
