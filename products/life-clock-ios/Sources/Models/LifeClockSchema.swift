import Foundation
import SwiftData

// MARK: - Schema versioning
//
// All SwiftData models live inside a VersionedSchema from day one. Moving
// from unversioned → versioned later requires a separate release; doing it
// up front is free.
//
// Hard rule: every non-optional stored property has a property-level default.
// Without that, lightweight migration silently fails on upgraded devices
// (NSCocoaErrorDomain 134110) and writes no-op invisibly. See
// docs/solutions/integration-issues/swiftdata-mandatory-attribute-migration-landmine.md.

enum LifeClockSchemaV1: VersionedSchema {
    static var versionIdentifier = Schema.Version(1, 0, 0)

    static var models: [any PersistentModel.Type] {
        [
            UserProfile.self,
            DailyHealthSnapshot.self,
            HabitLog.self,
            LifeClockEstimate.self,
            TimeLedgerEntry.self,
            Quest.self,
            WeeklyReport.self,
        ]
    }

    @Model
    final class UserProfile {
        @Attribute(.unique) var id: UUID = UUID()
        var birthDate: Date = Date(timeIntervalSince1970: 0)
        var biologicalSex: String = "unspecified"
        var heightCm: Double? = nil
        var weightKg: Double? = nil
        var smokingStatus: String = "none"
        var alcoholFrequency: String = "rare"
        var dietQualityBaseline: String = "okay"
        var stressBaseline: String = "medium"
        var strengthFrequencyPerWeek: Int = 0
        var sleepGoalHours: Double = 7.5
        var toneMode: String = "coach"
        var paletteId: String = "default-navy"
        var dailyReminderEnabled: Bool = false
        var dailyReminderHour: Int = 20
        /// Set to start-of-today (in the user's calendar) whenever the
        /// user logs habits. `reconcileNotifications` reads this to
        /// suppress today's reminder firing for users who logged before
        /// the reminder hour. Cleared overnight implicitly — once the
        /// next day starts, this date < today and the suppression check
        /// no longer applies.
        var lastSuppressedDate: Date? = nil
        var onboardingCompletedAt: Date? = nil
        var disclaimerAcceptedAt: Date? = nil
        /// When true, Today screen replaces "Projected healthspan" with
        /// "Time earned today" only. Resolves Open Question 5 + part of the
        /// safety-net offering for users who find the clock anxiety-inducing.
        var hideClock: Bool = false

        // MARK: - Wrap-up tracking (additive 2026-04-30, History feature)
        //
        // Both fields are optional with `nil` defaults so SwiftData lightweight
        // migration applies them silently to existing V1 stores. They are
        // consumed by `WrapUpCoordinator` and updated via `markYesterdayShown`
        // / `markWeeklyShown` after the wrap-up sheet is presented.

        /// Start-of-day for the most recent day on which the Yesterday Wrap-Up
        /// sheet was shown. Monotonic — never advanced backward.
        var lastShownYesterdayWrapUpDay: Date? = nil

        /// Start-of-day of the most recent week (firstWeekday-aligned) for
        /// which the Weekly Wrap-Up sheet was shown.
        var lastShownWeeklyWrapUpWeek: Date? = nil

        init(
            id: UUID = UUID(),
            birthDate: Date,
            biologicalSex: String = "unspecified",
            toneMode: String = "coach"
        ) {
            self.id = id
            self.birthDate = birthDate
            self.biologicalSex = biologicalSex
            self.toneMode = toneMode
        }
    }

    @Model
    final class DailyHealthSnapshot {
        @Attribute(.unique) var date: Date = Date(timeIntervalSince1970: 0)
        var stepCount: Int? = nil
        var distanceMeters: Double? = nil
        var exerciseMinutes: Int? = nil
        var activeEnergyKcal: Double? = nil
        var sleepHours: Double? = nil
        var sleepConsistencyScore: Double? = nil
        var restingHeartRate: Int? = nil
        var sourceCompleteness: Double = 0.0

        // MARK: - Persistence tracking (additive 2026-04-30, History feature)
        //
        // Optional with `nil` default for SwiftData lightweight migration on
        // existing V1 stores. `LifeClockStore.refreshFromHealthKit()` reads
        // this to short-circuit redundant HK fetches on rapid foreground
        // transitions (skips fetch when age < 300s).

        /// When the snapshot was last upserted from HealthKit (or by the
        /// override service, in a future phase). nil for never-persisted rows.
        var lastRecomputedAt: Date? = nil

        init(date: Date) {
            self.date = date
        }
    }

    @Model
    final class HabitLog {
        @Attribute(.unique) var date: Date = Date(timeIntervalSince1970: 0)
        var alcoholLevel: String = "none"
        var smokingVaping: Bool = false
        var dietQuality: String = "okay"
        var stressLevel: String = "medium"
        var strengthTraining: Bool = false
        var notes: String = ""

        init(date: Date) {
            self.date = date
        }
    }

    @Model
    final class LifeClockEstimate {
        @Attribute(.unique) var date: Date = Date(timeIntervalSince1970: 0)
        var projectedAgeYears: Double = 0
        var projectedDate: Date? = nil
        var healthspanScore: Double = 0
        var dailyTimeDeltaMinutes: Int = 0
        var confidenceRaw: String = "low"
        var explanation: String = ""

        init(date: Date) {
            self.date = date
        }
    }

    @Model
    final class TimeLedgerEntry {
        @Attribute(.unique) var id: UUID = UUID()
        var date: Date = Date(timeIntervalSince1970: 0)
        var title: String = ""
        var deltaMinutes: Int = 0
        var source: String = "estimate"
        var confidenceRaw: String = "low"
        var driverType: String = "other"
        // Quest slug for entries with driverType == "quest". Lets the undo
        // flow find the entry by stable slug instead of by display title,
        // which can drift across copy edits. Optional with property-level
        // default `nil` for safe lightweight migration; nil for non-quest
        // entries.
        var questSlug: String? = nil

        init(
            id: UUID = UUID(),
            date: Date,
            title: String,
            deltaMinutes: Int,
            source: String,
            confidenceRaw: String,
            driverType: String,
            questSlug: String? = nil
        ) {
            self.id = id
            self.date = date
            self.title = title
            self.deltaMinutes = deltaMinutes
            self.source = source
            self.confidenceRaw = confidenceRaw
            self.driverType = driverType
            self.questSlug = questSlug
        }
    }

    @Model
    final class Quest {
        @Attribute(.unique) var id: UUID = UUID()
        var date: Date = Date(timeIntervalSince1970: 0)
        // Stable identity for matching across daily regeneration. Format:
        // "<category>.<intent>[.v<n>]" — e.g. "nutrition.water-with-meal.v1".
        // Title is free-form display copy and may change without orphaning
        // persisted completion state. Property-level default required for
        // SwiftData lightweight migration. Intentionally NOT @Attribute(.unique)
        // in this version — existing rows would all default to "" and violate
        // uniqueness. Add .unique only after the bootstrap() backfill has
        // shipped on every install and a later schema version applies it.
        var slug: String = ""
        var title: String = ""
        var detail: String = ""
        var category: String = "movement"
        var target: Double = 0
        var progress: Double = 0
        var rewardEstimateMinutes: Int = 0
        var completedAt: Date? = nil

        init(
            id: UUID = UUID(),
            slug: String,
            date: Date,
            title: String,
            detail: String,
            category: String,
            target: Double,
            rewardEstimateMinutes: Int
        ) {
            self.id = id
            self.slug = slug
            self.date = date
            self.title = title
            self.detail = detail
            self.category = category
            self.target = target
            self.rewardEstimateMinutes = rewardEstimateMinutes
        }
    }

    @Model
    final class WeeklyReport {
        @Attribute(.unique) var weekStart: Date = Date(timeIntervalSince1970: 0)
        var weekEnd: Date = Date(timeIntervalSince1970: 0)
        var netTimeDeltaMinutes: Int = 0
        var topPositiveDriver: String = ""
        var topNegativeDriver: String = ""
        var nextBestLever: String = ""
        var confidenceRaw: String = "low"

        init(weekStart: Date, weekEnd: Date) {
            self.weekStart = weekStart
            self.weekEnd = weekEnd
        }
    }
}

// Production code references the typealiases — never the versioned form.
// When V2 lands, the typealiases get re-pointed inside a migration step.
typealias UserProfile = LifeClockSchemaV1.UserProfile
typealias DailyHealthSnapshot = LifeClockSchemaV1.DailyHealthSnapshot
typealias HabitLog = LifeClockSchemaV1.HabitLog
typealias LifeClockEstimate = LifeClockSchemaV1.LifeClockEstimate
typealias TimeLedgerEntry = LifeClockSchemaV1.TimeLedgerEntry
typealias Quest = LifeClockSchemaV1.Quest
typealias WeeklyReport = LifeClockSchemaV1.WeeklyReport

enum LifeClockMigrationPlan: SchemaMigrationPlan {
    static var schemas: [any VersionedSchema.Type] {
        [LifeClockSchemaV1.self]
    }

    /// Empty for V1. When V2 lands, add a `MigrationStage.lightweight` (for
    /// renames/optional adds) or `.custom` (for data transforms). Write a
    /// snapshot test of V1 → V2 *before* shipping V2.
    static var stages: [MigrationStage] { [] }
}
