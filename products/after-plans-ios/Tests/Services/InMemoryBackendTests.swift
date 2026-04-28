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
}
