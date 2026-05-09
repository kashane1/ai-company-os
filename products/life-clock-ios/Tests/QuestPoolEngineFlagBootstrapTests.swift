import XCTest
import SwiftData
@testable import LifeClock

/// Phase 5a (V1.6.0): default for `UserProfile.useQuestPoolEngine`
/// flipped from false → true. Existing rows persisted under V1.5.0
/// stay at the value SwiftData wrote, so a startup-time backfill in
/// `LifeClockStore.bootstrapQuestPoolEngineFlag()` flips the legacy
/// false → true once.
///
/// These tests pin the idempotency contract directly. The end-to-end
/// path is exercised by the bootstrap call inside `LifeClockStore`.
@MainActor
final class QuestPoolEngineFlagBootstrapTests: XCTestCase {
    private let birthDate = Date(timeIntervalSince1970: 631_152_000)

    private func makeStore() throws -> (LifeClockStore, ModelContext) {
        let container = try LifeClockContainer.make(inMemory: true)
        let context = container.mainContext
        let mockHealth = MockHealthKitService(seed: 42)
        let store = LifeClockStore(
            healthService: mockHealth,
            modelContext: context,
            engineClock: .fixed(Date(timeIntervalSince1970: 1_800_000_000))
        )
        return (store, context)
    }

    // MARK: - Backfill behavior

    /// Simulates the post-V1.6.0 first launch for an existing user whose
    /// V1.5.0 store wrote `useQuestPoolEngine = false`. Bootstrap must
    /// flip them forward.
    func testBootstrapFlipsLegacyFalseToTrue() throws {
        let (store, _) = try makeStore()
        let profile = UserProfile(birthDate: birthDate, biologicalSex: "female")
        profile.useQuestPoolEngine = false   // legacy V1.5.0 stored value
        store.completeOnboarding(profile: profile, tone: .coach, disclaimerAccepted: true)

        store.bootstrapQuestPoolEngineFlag()

        XCTAssertTrue(
            store.profile?.useQuestPoolEngine ?? false,
            "Bootstrap must flip legacy false → true on next launch"
        )
    }

    /// Bootstrap must be a no-op when the flag is already true. Covers:
    ///   - Fresh install (V1.6.0 schema default = true)
    ///   - Subsequent launches after the first migration
    func testBootstrapIsIdempotentWhenAlreadyTrue() throws {
        let (store, _) = try makeStore()
        let profile = UserProfile(birthDate: birthDate, biologicalSex: "female")
        XCTAssertTrue(profile.useQuestPoolEngine, "V1.6.0 default should be true")
        store.completeOnboarding(profile: profile, tone: .coach, disclaimerAccepted: true)

        store.bootstrapQuestPoolEngineFlag()
        store.bootstrapQuestPoolEngineFlag()
        store.bootstrapQuestPoolEngineFlag()

        XCTAssertTrue(store.profile?.useQuestPoolEngine ?? false)
    }

    /// Bootstrap with no profile loaded (pre-onboarding state) must not
    /// crash and must not insert anything.
    func testBootstrapWithNoProfileIsNoOp() throws {
        let (store, _) = try makeStore()
        XCTAssertNil(store.profile)
        XCTAssertNoThrow(store.bootstrapQuestPoolEngineFlag())
        XCTAssertNil(store.profile)
    }

    // MARK: - Schema-default verification (V1.6.0)

    func testFreshUserProfileV160DefaultsToFlagOn() {
        let profile = UserProfile(birthDate: birthDate, biologicalSex: "female")
        XCTAssertTrue(
            profile.useQuestPoolEngine,
            "V1.6.0 fresh-init default for useQuestPoolEngine must be true"
        )
    }
}
