import XCTest
@testable import LifeClock

/// Tests for the 2026-05-01 reveal-onboarding-rebuild engine extensions:
/// five new lifestyle factors in `lifestyleAdjustmentYears`, the atomic
/// healthspan-dial gate in `calculateBaseline`, and `computeArchetype`.
/// Boundary-test the load-bearing curves (BMI, cardio); spot-check the
/// rest. Per the plan, PSS/UCLA boundaries are tuning placeholders and
/// not pinned here.
final class ClockEngineRebuildTests: XCTestCase {
    private let fixedDate = Date(timeIntervalSince1970: 1_800_000_000) // 2027-01-15
    private let birthDate = Date(timeIntervalSince1970: 631_152_000)   // 1990-01-01

    private func makeEngine() -> ClockEngine {
        ClockEngine(clock: .fixed(fixedDate))
    }

    private func makeProfile(
        sex: String = "male"
    ) -> UserProfile {
        UserProfile(birthDate: birthDate, biologicalSex: sex)
    }

    // MARK: - All-five-zero regression

    /// With every new optional field nil and `cardioMinsPerWeek = 0`, the
    /// baseline must equal the population anchor + the legacy adjustments.
    /// (Cardio = 0 still applies its −1 yr bucket.)
    func testNewFactorsAllNeutralRegression() {
        let engine = makeEngine()
        let profile = makeProfile(sex: "male")
        // No new optional fields set; cardioMinsPerWeek defaults to 0.
        let result = engine.calculateBaseline(profile: profile)
        // Population baseline = 76.5; legacy lifestyle adjustment = 0
        // (no smoking, no alcohol, sleep 7.5h is in-range so +1.0,
        // strength 0/wk = 0, diet "okay" = neutral); cardio 0 = -1.0;
        // dial gate inactive ⇒ +0. Net: 76.5 + 1.0 - 1.0 = 76.5.
        XCTAssertEqual(result.projectedAgeYears, 76.5, accuracy: 0.0001)
    }

    // MARK: - BMI boundary cases

    func testBMI_Underweight_AppliesPenalty() {
        let engine = makeEngine()
        let profile = makeProfile()
        profile.heightCm = 170     // 1.70m
        profile.weightKg = 50      // BMI ≈ 17.3 → underweight
        let lower = engine.calculateBaseline(profile: profile).projectedAgeYears
        let baseline = engine.calculateBaseline(profile: makeProfile()).projectedAgeYears
        XCTAssertEqual(baseline - lower, 1.5, accuracy: 0.0001)
    }

    func testBMI_HealthyRange_Neutral() {
        let engine = makeEngine()
        let profile = makeProfile()
        profile.heightCm = 170
        profile.weightKg = 65      // BMI ≈ 22.5 → healthy
        let val = engine.calculateBaseline(profile: profile).projectedAgeYears
        let baseline = engine.calculateBaseline(profile: makeProfile()).projectedAgeYears
        XCTAssertEqual(val, baseline, accuracy: 0.0001)
    }

    func testBMI_Obese_AppliesLargePenalty() {
        let engine = makeEngine()
        let profile = makeProfile()
        profile.heightCm = 170
        profile.weightKg = 105     // BMI ≈ 36.3 → 35+ bucket
        let val = engine.calculateBaseline(profile: profile).projectedAgeYears
        let baseline = engine.calculateBaseline(profile: makeProfile()).projectedAgeYears
        XCTAssertEqual(baseline - val, 4.0, accuracy: 0.0001)
    }

    func testBMI_MissingHeightOrWeight_Neutral() {
        let engine = makeEngine()
        let profile = makeProfile()
        profile.weightKg = 100
        // heightCm nil
        let val = engine.calculateBaseline(profile: profile).projectedAgeYears
        let baseline = engine.calculateBaseline(profile: makeProfile()).projectedAgeYears
        XCTAssertEqual(val, baseline, accuracy: 0.0001)
    }

    // MARK: - Cardio boundary cases

    func testCardio_None_AppliesPenalty() {
        let engine = makeEngine()
        let baseline = engine.calculateBaseline(profile: makeProfile()).projectedAgeYears
        let profile = makeProfile()
        profile.cardioMinsPerWeek = 0
        let val = engine.calculateBaseline(profile: profile).projectedAgeYears
        XCTAssertEqual(val, baseline, accuracy: 0.0001) // baseline already had 0
    }

    func testCardio_RecommendedRange_AppliesBonus() {
        let engine = makeEngine()
        let baseline = engine.calculateBaseline(profile: makeProfile()).projectedAgeYears
        let profile = makeProfile()
        profile.cardioMinsPerWeek = 200  // in 150-300 sweet spot
        let val = engine.calculateBaseline(profile: profile).projectedAgeYears
        // baseline had cardio = 0 (=  -1.0 yr penalty);
        // +1.5 yr at 200 min ⇒ delta of +2.5 yr
        XCTAssertEqual(val - baseline, 2.5, accuracy: 0.0001)
    }

    func testCardio_HighVolume_AppliesLargerBonus() {
        let engine = makeEngine()
        let profile = makeProfile()
        profile.cardioMinsPerWeek = 400  // 301+ bucket
        let val = engine.calculateBaseline(profile: profile).projectedAgeYears
        let baseline = engine.calculateBaseline(profile: makeProfile()).projectedAgeYears
        XCTAssertEqual(val - baseline, 3.0, accuracy: 0.0001)  // +2.0 vs -1.0
    }

    // MARK: - Family longevity

    func testFamilyLongevity_BothLongLived_AppliesBonus() {
        let engine = makeEngine()
        let baseline = engine.calculateBaseline(profile: makeProfile()).projectedAgeYears
        let profile = makeProfile()
        profile.parentMotherAlive = false
        profile.parentMotherAgeAtDeath = 92
        profile.parentFatherAlive = false
        profile.parentFatherAgeAtDeath = 95
        let val = engine.calculateBaseline(profile: profile).projectedAgeYears
        XCTAssertEqual(val - baseline, 2.0, accuracy: 0.0001) // +1 each parent
    }

    func testFamilyLongevity_BothShort_AppliesPenalty() {
        let engine = makeEngine()
        let baseline = engine.calculateBaseline(profile: makeProfile()).projectedAgeYears
        let profile = makeProfile()
        profile.parentMotherAlive = false
        profile.parentMotherAgeAtDeath = 60
        profile.parentFatherAlive = false
        profile.parentFatherAgeAtDeath = 55
        let val = engine.calculateBaseline(profile: profile).projectedAgeYears
        XCTAssertEqual(baseline - val, 2.0, accuracy: 0.0001) // -1 each
    }

    func testFamilyLongevity_MixedSignals_BalanceOut() {
        let engine = makeEngine()
        let baseline = engine.calculateBaseline(profile: makeProfile()).projectedAgeYears
        let profile = makeProfile()
        profile.parentMotherAlive = false
        profile.parentMotherAgeAtDeath = 92  // +1
        profile.parentFatherAlive = false
        profile.parentFatherAgeAtDeath = 60  // -1
        let val = engine.calculateBaseline(profile: profile).projectedAgeYears
        XCTAssertEqual(val, baseline, accuracy: 0.0001)
    }

    func testFamilyLongevity_BothUnknown_Neutral() {
        let engine = makeEngine()
        let baseline = engine.calculateBaseline(profile: makeProfile()).projectedAgeYears
        let profile = makeProfile()
        // All four parent fields nil
        let val = engine.calculateBaseline(profile: profile).projectedAgeYears
        XCTAssertEqual(val, baseline, accuracy: 0.0001)
    }

    // MARK: - Stress & loneliness

    func testStress_HighScore_AppliesPenalty() {
        let engine = makeEngine()
        let baseline = engine.calculateBaseline(profile: makeProfile()).projectedAgeYears
        let profile = makeProfile()
        profile.perceivedStressScore = 30
        let val = engine.calculateBaseline(profile: profile).projectedAgeYears
        XCTAssertEqual(baseline - val, 1.5, accuracy: 0.0001)
    }

    func testLoneliness_HighScore_AppliesPenalty() {
        let engine = makeEngine()
        let baseline = engine.calculateBaseline(profile: makeProfile()).projectedAgeYears
        let profile = makeProfile()
        profile.lonelinessScore = 7
        let val = engine.calculateBaseline(profile: profile).projectedAgeYears
        XCTAssertEqual(baseline - val, 1.5, accuracy: 0.0001)
    }

    // MARK: - Healthspan dial atomic gate

    /// The race-fix: the engine must NOT apply `personalAdjustmentYears`
    /// when `anchorAdjustedAt` is nil, even if the years field has been
    /// written. This makes the (years, timestamp) pair logically atomic.
    func testDialAdjustment_OnlyAppliedWhenTimestampSet() {
        let engine = makeEngine()
        let baseline = engine.calculateBaseline(profile: makeProfile()).projectedAgeYears

        // Years set but timestamp NOT set → simulates partial write
        // failure between the two store mutations. Engine MUST treat
        // this as 0 to prevent double-application on next launch.
        let halfWritten = makeProfile()
        halfWritten.personalAdjustmentYears = 3.0
        halfWritten.anchorAdjustedAt = nil
        XCTAssertEqual(
            engine.calculateBaseline(profile: halfWritten).projectedAgeYears,
            baseline,
            accuracy: 0.0001,
            "Adjustment must NOT apply when anchorAdjustedAt is nil"
        )

        // Both set → engine applies the adjustment.
        let fullyWritten = makeProfile()
        fullyWritten.personalAdjustmentYears = 3.0
        fullyWritten.anchorAdjustedAt = Date(timeIntervalSince1970: 1_700_000_000)
        XCTAssertEqual(
            engine.calculateBaseline(profile: fullyWritten).projectedAgeYears - baseline,
            3.0,
            accuracy: 0.0001
        )
    }

    // MARK: - Archetype computation

    func testArchetype_LowRisk_PicksMarathoner() {
        let engine = makeEngine()
        let profile = makeProfile()
        profile.cardioMinsPerWeek = 200
        profile.dietQualityBaseline = "great"
        profile.strengthFrequencyPerWeek = 3
        profile.heightCm = 175
        profile.weightKg = 70  // BMI ~22.9
        profile.perceivedStressScore = 8
        profile.lonelinessScore = 3
        let result = engine.computeArchetype(profile: profile)
        XCTAssertEqual(result.archetype, .marathoner)
        XCTAssertLessThan(result.behavioralRisk, 0.3)
        XCTAssertGreaterThan(result.recoveryCapacity, 0.7)
    }

    func testArchetype_HighRiskYoung_PicksSprinter() {
        let engine = makeEngine()
        // Build a young (~37 in 2027) profile with high behavioral risk
        let profile = makeProfile()  // birthDate 1990 ⇒ ~37 in 2027
        profile.smokingStatus = "heavy"
        profile.alcoholFrequency = "heavy"
        profile.cardioMinsPerWeek = 0
        profile.strengthFrequencyPerWeek = 0
        profile.dietQualityBaseline = "rough"
        profile.heightCm = 175
        profile.weightKg = 110  // BMI ~35.9
        profile.perceivedStressScore = 32
        profile.lonelinessScore = 8
        let result = engine.computeArchetype(profile: profile)
        XCTAssertEqual(result.archetype, .sprinter)
        XCTAssertGreaterThan(result.behavioralRisk, 0.6)
    }

    func testArchetype_StrongGenes_HighRisk_PicksOutlier() {
        let engine = makeEngine()
        // Older user (>= 50) with high behavioral risk and excellent genes
        // ⇒ outlier
        let oldBirth = Date(timeIntervalSince1970: 0)  // 1970 ⇒ ~57 in 2027
        let profile = UserProfile(birthDate: oldBirth, biologicalSex: "male")
        profile.smokingStatus = "heavy"
        profile.cardioMinsPerWeek = 0
        profile.dietQualityBaseline = "rough"
        profile.parentMotherAlive = false
        profile.parentMotherAgeAtDeath = 95
        profile.parentFatherAlive = false
        profile.parentFatherAgeAtDeath = 92
        let result = engine.computeArchetype(profile: profile)
        XCTAssertEqual(result.archetype, .outlier)
    }

    func testArchetype_FallbackIsMarathoner() {
        let engine = makeEngine()
        // Empty-ish profile with no signals ⇒ should fall back to marathoner
        let profile = makeProfile()
        let result = engine.computeArchetype(profile: profile)
        XCTAssertEqual(result.archetype, .marathoner)
    }
}
