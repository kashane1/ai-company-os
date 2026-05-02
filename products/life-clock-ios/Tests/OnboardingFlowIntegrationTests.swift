import XCTest
import SwiftData
@testable import LifeClock

/// End-to-end integration test for the new reveal-onboarding flow.
/// Walks an `OnboardingDraft` through every answer the way each
/// onboarding screen would, then materializes a `UserProfile` and
/// drives `LifeClockStore.completeOnboarding` + `applyAnchorAdjustment`.
/// Asserts the full state graph at completion: persisted fields,
/// dial-gate atomicity, and engine-output sanity.
///
/// This is the smoke test that catches regressions XCUITest can't —
/// SwiftData persistence shape, store↔engine integration after
/// onboarding completion, and the dial's atomic gate behavior.
@MainActor
final class OnboardingFlowIntegrationTests: XCTestCase {
    private let fixedDate = Date(timeIntervalSince1970: 1_800_000_000) // 2027-01-15
    private let birthDate = Date(timeIntervalSince1970: 631_152_000)   // 1990-01-01

    // MARK: - Happy path: full draft → materialize → completeOnboarding → dial

    func testFullDraftFlowProducesPopulatedProfileAndAppliesDial() async throws {
        let container = try LifeClockContainer.make(inMemory: true)
        let store = LifeClockStore(
            healthService: MockHealthKitService(seed: 17, preAuthorized: true),
            modelContext: container.mainContext,
            engineClock: .fixed(fixedDate)
        )
        await store.bootstrap()
        XCTAssertNil(store.profile, "first launch must NOT seed a profile")

        // ----- Walk the draft as if every screen submitted -----
        let draft = OnboardingDraft()
        // Lead-ins capture nothing; first capture is goalPick.
        draft.primaryGoal = .moreEnergy
        // Baseline
        draft.birthDate = birthDate
        draft.biologicalSex = "female"
        // Body comp
        draft.heightCm = 168
        draft.weightKg = 62
        // Existing lifestyle
        draft.smokingStatus = "former"
        draft.alcoholFrequency = "rare"
        draft.strengthFrequencyPerWeek = 3
        draft.cardioMinsPerWeek = 200
        draft.sleepGoalHours = 8.0
        draft.dietQualityBaseline = "great"
        // Sensitive block
        draft.parentMotherAlive = true
        draft.parentFatherAlive = false
        draft.parentFatherAgeAtDeath = 88
        draft.perceivedStressScore = 14
        draft.lonelinessScore = 4
        // Tone + meta
        draft.toneMode = .gentle
        draft.priorAttempts = .triedDidntStick

        // Reactive estimate must populate after baseline known.
        draft.recomputeEstimate(using: ClockEngine(clock: .fixed(fixedDate)))
        XCTAssertNotNil(draft.runningEstimate, "running estimate must be live after baseline answers")

        // ----- Materialize + complete onboarding -----
        let profile = draft.materialize()
        profile.onboardingV2CompletedAt = fixedDate
        let didComplete = store.completeOnboarding(
            profile: profile,
            tone: draft.toneMode ?? .coach,
            disclaimerAccepted: true
        )
        XCTAssertTrue(didComplete)
        XCTAssertTrue(store.hasCompletedOnboarding)
        let stored = try XCTUnwrap(store.profile)

        // Verify every reveal-onboarding-rebuild field round-tripped.
        XCTAssertEqual(stored.heightCm, 168)
        XCTAssertEqual(stored.weightKg, 62)
        XCTAssertEqual(stored.smokingStatus, "former")
        XCTAssertEqual(stored.alcoholFrequency, "rare")
        XCTAssertEqual(stored.strengthFrequencyPerWeek, 3)
        XCTAssertEqual(stored.cardioMinsPerWeek, 200)
        XCTAssertEqual(stored.sleepGoalHours, 8.0)
        XCTAssertEqual(stored.dietQualityBaseline, "great")
        XCTAssertEqual(stored.parentMotherAlive, true)
        XCTAssertEqual(stored.parentFatherAlive, false)
        XCTAssertEqual(stored.parentFatherAgeAtDeath, 88)
        XCTAssertEqual(stored.perceivedStressScore, 14)
        XCTAssertEqual(stored.lonelinessScore, 4)
        XCTAssertEqual(stored.primaryGoal, "moreEnergy")
        XCTAssertEqual(stored.toneMode, "gentle")
        XCTAssertEqual(stored.onboardingV2CompletedAt, fixedDate)
        XCTAssertNil(stored.personalAdjustmentYears, "dial not yet applied")
        XCTAssertNil(stored.anchorAdjustedAt, "dial not yet applied")

        // ----- Apply the dial -----
        let preAdjustEstimate = ClockEngine(clock: .fixed(fixedDate))
            .calculateBaseline(profile: stored)
            .projectedAgeYears
        store.applyAnchorAdjustment(years: 2.5)

        let adjusted = try XCTUnwrap(store.profile)
        XCTAssertEqual(adjusted.personalAdjustmentYears, 2.5)
        XCTAssertNotNil(adjusted.anchorAdjustedAt)
        XCTAssertEqual(adjusted.anchorAdjustedAt, fixedDate)

        // Engine baseline must reflect the +2.5 yr dial.
        let postAdjustEstimate = ClockEngine(clock: .fixed(fixedDate))
            .calculateBaseline(profile: adjusted)
            .projectedAgeYears
        XCTAssertEqual(postAdjustEstimate - preAdjustEstimate, 2.5, accuracy: 0.0001)
    }

    // MARK: - Sensitive-skip path

    func testSensitiveSkipPathLeavesParentalAndStressFieldsNil() async throws {
        let container = try LifeClockContainer.make(inMemory: true)
        let store = LifeClockStore(
            healthService: MockHealthKitService(seed: 17, preAuthorized: true),
            modelContext: container.mainContext,
            engineClock: .fixed(fixedDate)
        )
        await store.bootstrap()

        let draft = OnboardingDraft()
        draft.primaryGoal = .justCurious
        draft.birthDate = birthDate
        draft.biologicalSex = "unspecified"
        draft.smokingStatus = "none"
        draft.alcoholFrequency = "rare"
        draft.cardioMinsPerWeek = 100
        draft.dietQualityBaseline = "okay"
        draft.toneMode = .coach
        // Sensitive block intentionally NOT populated (user took skip path)

        let profile = draft.materialize()
        store.completeOnboarding(profile: profile, tone: .coach, disclaimerAccepted: true)
        let stored = try XCTUnwrap(store.profile)

        XCTAssertNil(stored.parentMotherAlive)
        XCTAssertNil(stored.parentMotherAgeAtDeath)
        XCTAssertNil(stored.parentFatherAlive)
        XCTAssertNil(stored.parentFatherAgeAtDeath)
        XCTAssertNil(stored.perceivedStressScore)
        XCTAssertNil(stored.lonelinessScore)

        // Engine still produces a sensible baseline despite missing sensitive
        // inputs (population baseline + a few existing-lifestyle factors).
        let estimate = ClockEngine(clock: .fixed(fixedDate)).calculateBaseline(profile: stored)
        XCTAssertGreaterThan(estimate.projectedAgeYears, 70)
        XCTAssertLessThan(estimate.projectedAgeYears, 90)
    }

    // MARK: - Dial idempotency

    func testApplyAnchorAdjustmentIsIdempotent() async throws {
        let container = try LifeClockContainer.make(inMemory: true)
        let store = LifeClockStore(
            healthService: MockHealthKitService(seed: 17, preAuthorized: true),
            modelContext: container.mainContext,
            engineClock: .fixed(fixedDate)
        )
        await store.bootstrap()

        let profile = UserProfile(birthDate: birthDate, biologicalSex: "female")
        store.completeOnboarding(profile: profile, tone: .coach, disclaimerAccepted: true)

        store.applyAnchorAdjustment(years: 2.0)
        let firstAdjustedAt = store.profile?.anchorAdjustedAt
        XCTAssertEqual(store.profile?.personalAdjustmentYears, 2.0)
        XCTAssertNotNil(firstAdjustedAt)

        // Second call MUST be a no-op (one-time-only contract).
        store.applyAnchorAdjustment(years: 4.0)
        XCTAssertEqual(store.profile?.personalAdjustmentYears, 2.0,
            "second applyAnchorAdjustment must NOT overwrite the first value")
        XCTAssertEqual(store.profile?.anchorAdjustedAt, firstAdjustedAt,
            "anchorAdjustedAt must NOT advance on the second call")
    }

    // MARK: - Cold-restart survives the dial value

    func testDialValueSurvivesColdRestart() async throws {
        let storeURL = URL.temporaryDirectory
            .appendingPathComponent("integration-\(UUID()).store")
        addTeardownBlock { try? FileManager.default.removeItem(at: storeURL) }

        // Session 1 — onboard + dial.
        let schema = Schema(versionedSchema: LifeClockSchemaV1.self)
        let config = ModelConfiguration(
            "LifeClockIntegrationTest",
            schema: schema,
            url: storeURL,
            allowsSave: true,
            cloudKitDatabase: .none
        )
        let containerA = try ModelContainer(
            for: schema,
            migrationPlan: LifeClockMigrationPlan.self,
            configurations: [config]
        )
        let storeA = LifeClockStore(
            healthService: MockHealthKitService(seed: 17, preAuthorized: true),
            modelContext: containerA.mainContext,
            engineClock: .fixed(fixedDate)
        )
        await storeA.bootstrap()

        let profile = UserProfile(birthDate: birthDate, biologicalSex: "male")
        profile.cardioMinsPerWeek = 150
        storeA.completeOnboarding(profile: profile, tone: .coach, disclaimerAccepted: true)
        storeA.applyAnchorAdjustment(years: -1.5)

        // Session 2 — reopen the same on-disk store.
        let containerB = try ModelContainer(
            for: schema,
            migrationPlan: LifeClockMigrationPlan.self,
            configurations: [config]
        )
        let storeB = LifeClockStore(
            healthService: MockHealthKitService(seed: 17, preAuthorized: true),
            modelContext: containerB.mainContext,
            engineClock: .fixed(fixedDate)
        )
        await storeB.bootstrap()

        let restored = try XCTUnwrap(storeB.profile)
        XCTAssertEqual(restored.personalAdjustmentYears, -1.5)
        XCTAssertEqual(restored.anchorAdjustedAt, fixedDate)
        // Engine continues to apply the adjustment after restart.
        let engineYears = ClockEngine(clock: .fixed(fixedDate))
            .calculateBaseline(profile: restored)
            .projectedAgeYears
        let baselineNoDial: Double = 76.5  // male anchor
        // Cardio at 150 = +1.5; sleep at 7.5 default = +1.0; dial -1.5
        // Net: 76.5 + 1.5 + 1.0 - 1.5 = 77.5
        XCTAssertEqual(engineYears, 77.5, accuracy: 0.0001)
    }
}
