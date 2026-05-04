import XCTest
@testable import LifeClock

@MainActor
final class OnboardingDraftTests: XCTestCase {
    private let fixedDate = Date(timeIntervalSince1970: 1_800_000_000) // 2027-01-15
    private let birthDate = Date(timeIntervalSince1970: 631_152_000)   // 1990-01-01

    private func makeEngine() -> ClockEngine {
        ClockEngine(clock: .fixed(fixedDate))
    }

    // MARK: - runningEstimate gating

    func testRunningEstimate_NilUntilBaselineKnown() {
        let draft = OnboardingDraft()
        let engine = makeEngine()

        draft.recomputeEstimate(using: engine)
        XCTAssertNil(draft.runningEstimate)

        // Only birthDate set — still nil
        draft.birthDate = birthDate
        draft.recomputeEstimate(using: engine)
        XCTAssertNil(draft.runningEstimate)

        // Only sex set — still nil
        draft.birthDate = nil
        draft.biologicalSex = "male"
        draft.recomputeEstimate(using: engine)
        XCTAssertNil(draft.runningEstimate)

        // Both set — populated
        draft.birthDate = birthDate
        draft.recomputeEstimate(using: engine)
        XCTAssertNotNil(draft.runningEstimate)
    }

    func testRunningEstimate_TracksAddedAnswers() {
        let draft = OnboardingDraft()
        draft.birthDate = birthDate
        draft.biologicalSex = "female"
        let engine = makeEngine()

        draft.recomputeEstimate(using: engine)
        let baseline = draft.runningEstimate?.projectedAgeYears ?? 0
        XCTAssertGreaterThan(baseline, 0)

        // Add a positive lifestyle factor — estimate should move up.
        draft.cardioMinsPerWeek = 200
        draft.recomputeEstimate(using: engine)
        let withCardio = draft.runningEstimate?.projectedAgeYears ?? 0
        XCTAssertGreaterThan(withCardio, baseline)
        XCTAssertNotNil(draft.lastDelta)
        XCTAssertGreaterThan(draft.lastDelta?.years ?? 0, 0)
    }

    func testRunningEstimate_NoMovementProducesNoDelta() {
        let draft = OnboardingDraft()
        draft.birthDate = birthDate
        draft.biologicalSex = "male"
        let engine = makeEngine()

        draft.recomputeEstimate(using: engine)
        // Set a field that contributes 0 (default sleepGoalHours of 7.5
        // hits the +1 yr bonus on first compute, but a re-set of an
        // already-7.5 value shouldn't move anything).
        draft.sleepGoalHours = 7.5
        draft.recomputeEstimate(using: engine)
        XCTAssertNil(draft.lastDelta)
    }

    // MARK: - materialize

    func testMaterialize_PopulatesAllFields() {
        let draft = OnboardingDraft()
        draft.birthDate = birthDate
        draft.biologicalSex = "female"
        draft.heightCm = 170
        draft.weightKg = 65
        draft.smokingStatus = "former"
        draft.alcoholFrequency = "weekly"
        draft.strengthFrequencyPerWeek = 3
        draft.sleepGoalHours = 8.0
        draft.dietQualityBaseline = "great"
        draft.cardioMinsPerWeek = 200
        draft.parentMotherAlive = true
        draft.parentFatherAlive = false
        draft.parentFatherAgeAtDeath = 88
        draft.perceivedStressScore = 12
        draft.lonelinessScore = 4
        draft.primaryGoal = .moreEnergy
        draft.toneMode = .gentle
        draft.personalAdjustmentYears = -2.25
        draft.anchorAdjustedAt = fixedDate

        let profile = draft.materialize()

        XCTAssertEqual(profile.birthDate.timeIntervalSince1970, birthDate.timeIntervalSince1970, accuracy: 0.001)
        XCTAssertEqual(profile.biologicalSex, "female")
        XCTAssertEqual(profile.heightCm, 170)
        XCTAssertEqual(profile.weightKg, 65)
        XCTAssertEqual(profile.smokingStatus, "former")
        XCTAssertEqual(profile.alcoholFrequency, "weekly")
        XCTAssertEqual(profile.strengthFrequencyPerWeek, 3)
        XCTAssertEqual(profile.sleepGoalHours, 8.0)
        XCTAssertEqual(profile.dietQualityBaseline, "great")
        XCTAssertEqual(profile.cardioMinsPerWeek, 200)
        XCTAssertEqual(profile.parentMotherAlive, true)
        XCTAssertEqual(profile.parentFatherAlive, false)
        XCTAssertEqual(profile.parentFatherAgeAtDeath, 88)
        XCTAssertEqual(profile.perceivedStressScore, 12)
        XCTAssertEqual(profile.lonelinessScore, 4)
        XCTAssertEqual(profile.primaryGoal, "moreEnergy")
        XCTAssertEqual(profile.toneMode, "gentle")
        XCTAssertEqual(profile.personalAdjustmentYears, -2.25)
        XCTAssertEqual(profile.anchorAdjustedAt, fixedDate)
    }

    func testMaterialize_LeavesDialGateNilUntilUserConfirmsDial() {
        let draft = OnboardingDraft()
        draft.birthDate = birthDate
        draft.biologicalSex = "female"

        let profile = draft.materialize()

        XCTAssertNil(profile.personalAdjustmentYears)
        XCTAssertNil(profile.anchorAdjustedAt)
    }

    func testMaterialize_DefaultsWhenDraftEmpty() {
        let draft = OnboardingDraft()
        let profile = draft.materialize()
        // Defaults used: epoch birthDate, "unspecified" sex, "coach" tone
        XCTAssertEqual(profile.birthDate, Date(timeIntervalSince1970: 0))
        XCTAssertEqual(profile.biologicalSex, "unspecified")
        XCTAssertEqual(profile.toneMode, "coach")
        XCTAssertNil(profile.heightCm)
        XCTAssertNil(profile.cardioMinsPerWeek == 0 ? nil : profile.cardioMinsPerWeek) // cardio defaults to 0
    }

    // MARK: - Goal & PriorAttempts enums

    func testOnboardingGoal_FromStored_FallsBackToJustCurious() {
        XCTAssertEqual(OnboardingGoal.fromStored(nil), .justCurious)
        XCTAssertEqual(OnboardingGoal.fromStored(""), .justCurious)
        XCTAssertEqual(OnboardingGoal.fromStored("unknown_legacy_value"), .justCurious)
        XCTAssertEqual(OnboardingGoal.fromStored("moreEnergy"), .moreEnergy)
    }

    func testOnboardingGoal_AllCasesHaveDisplayCopy() {
        for goal in OnboardingGoal.allCases {
            XCTAssertFalse(goal.displayName.isEmpty, "Missing displayName for \(goal)")
            XCTAssertFalse(goal.detail.isEmpty, "Missing detail for \(goal)")
        }
    }

    func testArchetype_FromStored_FallsBackToMarathoner() {
        XCTAssertEqual(Archetype.fromStored(nil), .marathoner)
        XCTAssertEqual(Archetype.fromStored("unknown"), .marathoner)
        XCTAssertEqual(Archetype.fromStored("sprinter"), .sprinter)
    }

    func testArchetype_AllCasesHaveDisplayCopy() {
        for archetype in Archetype.allCases {
            XCTAssertFalse(archetype.displayName.isEmpty)
            XCTAssertFalse(archetype.description.isEmpty)
        }
    }

    func testRecoveryPreviewCopy_HeadlineHandlesZeroAndPositive() {
        XCTAssertEqual(
            RecoveryPreviewCopy.headline(yearsBack: 0),
            "More years ahead"
        )
        XCTAssertEqual(
            RecoveryPreviewCopy.headline(yearsBack: 3),
            "3 more years"
        )
    }

    func testRecoveryPreviewCopy_PhraseUsesCorrectConnector() {
        // Phrases that already start with a preposition keep them.
        XCTAssertEqual(
            RecoveryPreviewCopy.phrase(goal: .beThereForFamily, phrase: "with your kids"),
            "with your kids"
        )
        XCTAssertEqual(
            RecoveryPreviewCopy.phrase(goal: .beThereForFamily, phrase: "at the dinner table"),
            "at the dinner table"
        )
        // Naked phrases get an "of " connector so the line reads naturally.
        XCTAssertEqual(
            RecoveryPreviewCopy.phrase(goal: .liveLonger, phrase: "living"),
            "of living"
        )
    }
}
