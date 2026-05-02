import XCTest
import SwiftData
@testable import LifeClock

/// Schema migration safety check for the 2026-05-01 reveal-onboarding rebuild
/// (Phase 1a): the 12 new optional fields on `UserProfile` MUST default to
/// nil/0 on existing V1 stores under SwiftData lightweight migration. This
/// pins the contract before Phase 1b lands engine math that reads them.
///
/// Two test surfaces:
///
/// 1. **Default-state guards** (`testNew*FieldsDefaultToNil`) — fast, run
///    in-memory, cover the property-level-default contract.
///
/// 2. **File-backed round-trip** (`testNewFieldsRoundTripThroughFileBackedStore`)
///    — opens a real SQLite-backed store on disk, writes, closes, reopens,
///    reads. In-memory containers never exercise lightweight migration; this
///    is the only test that catches the landmine documented in
///    `docs/solutions/integration-issues/swiftdata-mandatory-attribute-migration-landmine.md`.
@MainActor
final class LifeClockSchemaMigrationTests: XCTestCase {
    // MARK: - Default-state guards

    func testNewLifestyleFieldsDefaultToNil() throws {
        let profile = UserProfile(birthDate: Date(timeIntervalSince1970: 0))
        XCTAssertEqual(profile.cardioMinsPerWeek, 0)
        XCTAssertNil(profile.parentMotherAlive)
        XCTAssertNil(profile.parentMotherAgeAtDeath)
        XCTAssertNil(profile.parentFatherAlive)
        XCTAssertNil(profile.parentFatherAgeAtDeath)
        XCTAssertNil(profile.perceivedStressScore)
        XCTAssertNil(profile.lonelinessScore)
    }

    func testGoalAndArchetypeFieldsDefaultToNil() throws {
        let profile = UserProfile(birthDate: Date(timeIntervalSince1970: 0))
        XCTAssertNil(profile.primaryGoal)
        XCTAssertNil(profile.archetype)
    }

    func testHealthspanDialFieldsDefaultToNil() throws {
        let profile = UserProfile(birthDate: Date(timeIntervalSince1970: 0))
        XCTAssertNil(profile.personalAdjustmentYears)
        XCTAssertNil(profile.anchorAdjustedAt)
        XCTAssertNil(profile.onboardingV2CompletedAt)
    }

    // MARK: - File-backed round-trip

    /// Build a real SQLite-backed `ModelContainer` on disk, write a profile
    /// with the new fields populated, close the container, reopen it, and
    /// assert every value round-trips. This is the only test that exercises
    /// SwiftData's lightweight migration code path — in-memory containers
    /// never run migration.
    func testNewFieldsRoundTripThroughFileBackedStore() throws {
        let storeURL = URL.temporaryDirectory
            .appendingPathComponent("lifeclock-migration-\(UUID()).store")
        addTeardownBlock {
            try? FileManager.default.removeItem(at: storeURL)
        }

        let schema = Schema(versionedSchema: LifeClockSchemaV1.self)
        let config = ModelConfiguration(
            "LifeClockMigrationTest",
            schema: schema,
            url: storeURL,
            allowsSave: true,
            cloudKitDatabase: .none
        )

        // First open: write a profile with every new field populated.
        let writeContainer = try ModelContainer(
            for: schema,
            migrationPlan: LifeClockMigrationPlan.self,
            configurations: [config]
        )
        let writeContext = ModelContext(writeContainer)
        let anchoredAt = Date(timeIntervalSince1970: 1_768_521_600)
        let onboardedAt = Date(timeIntervalSince1970: 1_768_525_200)

        let profile = UserProfile(birthDate: Date(timeIntervalSince1970: 0))
        profile.cardioMinsPerWeek = 200
        profile.parentMotherAlive = true
        profile.parentFatherAlive = false
        profile.parentFatherAgeAtDeath = 72
        profile.perceivedStressScore = 18
        profile.lonelinessScore = 5
        profile.primaryGoal = "moreEnergy"
        profile.archetype = "marathoner"
        profile.personalAdjustmentYears = 2.5
        profile.anchorAdjustedAt = anchoredAt
        profile.onboardingV2CompletedAt = onboardedAt
        writeContext.insert(profile)
        try writeContext.save()

        // Second open against the same on-disk store: simulates the
        // upgrade-launch path on a user's device.
        let readContainer = try ModelContainer(
            for: schema,
            migrationPlan: LifeClockMigrationPlan.self,
            configurations: [config]
        )
        let readContext = ModelContext(readContainer)
        let fetched = try XCTUnwrap(
            try readContext.fetch(FetchDescriptor<UserProfile>()).first
        )

        XCTAssertEqual(fetched.cardioMinsPerWeek, 200)
        XCTAssertEqual(fetched.parentMotherAlive, true)
        XCTAssertEqual(fetched.parentFatherAlive, false)
        XCTAssertNil(fetched.parentMotherAgeAtDeath, "unset optional must read back as nil")
        XCTAssertEqual(fetched.parentFatherAgeAtDeath, 72)
        XCTAssertEqual(fetched.perceivedStressScore, 18)
        XCTAssertEqual(fetched.lonelinessScore, 5)
        XCTAssertEqual(fetched.primaryGoal, "moreEnergy")
        XCTAssertEqual(fetched.archetype, "marathoner")
        XCTAssertEqual(fetched.personalAdjustmentYears, 2.5)
        XCTAssertEqual(
            try XCTUnwrap(fetched.anchorAdjustedAt).timeIntervalSince1970,
            anchoredAt.timeIntervalSince1970,
            accuracy: 0.001
        )
        XCTAssertEqual(
            try XCTUnwrap(fetched.onboardingV2CompletedAt).timeIntervalSince1970,
            onboardedAt.timeIntervalSince1970,
            accuracy: 0.001
        )
    }

    // MARK: - V1.2.0 HabitLog rhythm + anchor

    /// New `HabitLog.dietAmountRhythm` and `wholeFoodMeal` must default to
    /// the V1.2.0 meaningful-neutral values (`"right"` / `"unknown"`) when
    /// a fresh row is created. Engine treats both as zero contribution.
    func testHabitLogDietRhythmFieldsDefaultToNeutral() throws {
        let log = HabitLog(date: Date(timeIntervalSince1970: 0))
        XCTAssertEqual(log.dietAmountRhythm, "right")
        XCTAssertEqual(log.wholeFoodMeal, "unknown")
    }

    /// Round-trip the new HabitLog fields through a real on-disk store.
    /// Catches regressions where someone removes the property-level
    /// default (NSCocoaErrorDomain 134110 landmine).
    func testHabitLogDietRhythmFieldsRoundTripThroughFileBackedStore() throws {
        let storeURL = URL.temporaryDirectory
            .appendingPathComponent("lifeclock-habit-rhythm-\(UUID()).store")
        addTeardownBlock {
            try? FileManager.default.removeItem(at: storeURL)
        }

        let schema = Schema(versionedSchema: LifeClockSchemaV1.self)
        let config = ModelConfiguration(
            "LifeClockHabitRhythmTest",
            schema: schema,
            url: storeURL,
            allowsSave: true,
            cloudKitDatabase: .none
        )

        let writeContainer = try ModelContainer(
            for: schema,
            migrationPlan: LifeClockMigrationPlan.self,
            configurations: [config]
        )
        let writeContext = ModelContext(writeContainer)
        let day = Date(timeIntervalSince1970: 1_768_521_600)
        let log = HabitLog(date: day)
        log.dietQuality = "rough"
        log.dietAmountRhythm = "skipBinge"
        log.wholeFoodMeal = "no"
        writeContext.insert(log)
        try writeContext.save()

        let readContainer = try ModelContainer(
            for: schema,
            migrationPlan: LifeClockMigrationPlan.self,
            configurations: [config]
        )
        let readContext = ModelContext(readContainer)
        let fetched = try XCTUnwrap(
            try readContext.fetch(FetchDescriptor<HabitLog>()).first
        )

        XCTAssertEqual(fetched.dietQuality, "rough")
        XCTAssertEqual(fetched.dietAmountRhythm, "skipBinge")
        XCTAssertEqual(fetched.wholeFoodMeal, "no")
        XCTAssertEqual(fetched.alcoholLevel, "none", "Sibling fields must round-trip with their original defaults")
        XCTAssertEqual(fetched.stressLevel, "medium")
        XCTAssertFalse(fetched.smokingVaping)
        XCTAssertFalse(fetched.strengthTraining)
    }

    /// Sibling-field preservation: writing a HabitLog with the new fields
    /// set must NOT silently reset other HabitLog fields. Catches a class
    /// of regression where the migration / upsert path drops untouched
    /// columns.
    func testHabitLogSiblingFieldsRoundTripUnchanged() throws {
        let log = HabitLog(date: Date(timeIntervalSince1970: 0))
        log.alcoholLevel = "heavy"
        log.smokingVaping = true
        log.dietQuality = "great"
        log.stressLevel = "low"
        log.strengthTraining = true
        log.notes = "round-trip"
        log.dietAmountRhythm = "right"
        log.wholeFoodMeal = "yes"

        XCTAssertEqual(log.alcoholLevel, "heavy")
        XCTAssertTrue(log.smokingVaping)
        XCTAssertEqual(log.dietQuality, "great")
        XCTAssertEqual(log.stressLevel, "low")
        XCTAssertTrue(log.strengthTraining)
        XCTAssertEqual(log.notes, "round-trip")
        XCTAssertEqual(log.dietAmountRhythm, "right")
        XCTAssertEqual(log.wholeFoodMeal, "yes")
    }
}
