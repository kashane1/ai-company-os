import XCTest
import SwiftData
@testable import LifeClock

/// Schema migration safety check: a freshly-built `UserProfile` /
/// `DailyHealthSnapshot` from the V1 schema (now extended with the
/// History feature's wrap-up tracking + persistence-tracking fields)
/// must default the new fields to `nil`. This pins the SwiftData
/// lightweight-migration contract: existing V1 stores will get nil
/// values for the new properties, the wrap-up coordinator and refresh
/// short-circuit will treat that as "never shown / never recomputed",
/// and behavior remains correct for upgrade users.
///
/// See `docs/solutions/integration-issues/swiftdata-mandatory-attribute-migration-landmine.md`
/// for the underlying landmine these tests guard against.
@MainActor
final class SchemaWrapUpFieldDefaultsTests: XCTestCase {
    func testUserProfileWrapUpFieldsDefaultToNil() throws {
        let profile = UserProfile(birthDate: Date(timeIntervalSince1970: 0))
        XCTAssertNil(profile.lastShownYesterdayWrapUpDay)
        XCTAssertNil(profile.lastShownWeeklyWrapUpWeek)
    }

    func testDailyHealthSnapshotLastRecomputedAtDefaultsToNil() throws {
        let snapshot = DailyHealthSnapshot(date: Date(timeIntervalSince1970: 0))
        XCTAssertNil(snapshot.lastRecomputedAt)
    }

    /// Round-trip the new fields through an in-memory SwiftData container
    /// to confirm SwiftData persists and restores them. Catches
    /// type-encoding regressions (Date? in particular, which SwiftData has
    /// historically mis-handled in some early iOS 17 builds).
    func testWrapUpFieldsRoundTripThroughSwiftData() throws {
        let container = try LifeClockContainer.make(inMemory: true)
        let context = container.mainContext

        let profile = UserProfile(birthDate: Date(timeIntervalSince1970: 0))
        let yesterdayMarker = Date(timeIntervalSince1970: 1_768_521_600)
        let weeklyMarker = Date(timeIntervalSince1970: 1_768_780_800)
        profile.lastShownYesterdayWrapUpDay = yesterdayMarker
        profile.lastShownWeeklyWrapUpWeek = weeklyMarker
        context.insert(profile)

        let snapshotDate = Date(timeIntervalSince1970: 1_768_521_600)
        let snapshot = DailyHealthSnapshot(date: snapshotDate)
        snapshot.stepCount = 8_000
        snapshot.lastRecomputedAt = Date(timeIntervalSince1970: 1_768_521_900)
        context.insert(snapshot)

        try context.save()

        let fetchedProfile = try XCTUnwrap(
            try context.fetch(FetchDescriptor<UserProfile>()).first
        )
        XCTAssertEqual(fetchedProfile.lastShownYesterdayWrapUpDay, yesterdayMarker)
        XCTAssertEqual(fetchedProfile.lastShownWeeklyWrapUpWeek, weeklyMarker)

        let fetchedSnapshot = try XCTUnwrap(
            try context.fetch(FetchDescriptor<DailyHealthSnapshot>()).first
        )
        let recomputedAt = try XCTUnwrap(fetchedSnapshot.lastRecomputedAt)
        XCTAssertEqual(recomputedAt.timeIntervalSince1970, 1_768_521_900, accuracy: 0.001)
    }
}
