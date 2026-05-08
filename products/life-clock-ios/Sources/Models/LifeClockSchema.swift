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
    // 1.1.0 (2026-05-01): additive fields for the reveal-onboarding rebuild
    // (cardio, family longevity, stress/loneliness, goal, archetype, healthspan
    // dial). All optional or with property-level defaults — lightweight
    // migration applies on existing V1 stores. See
    // docs/plans/2026-05-01-feat-life-clock-reveal-onboarding-anchor-dial-plan.md
    // Phase 1a for the rationale.
    //
    // 1.2.0 (2026-05-02): additive HabitLog fields for the diet rhythm axis
    // and whole-food anchor. Both non-optional with meaningful neutral
    // defaults (`"right"` / `"unknown"`) to match the existing convention
    // (dietQuality="okay", alcoholLevel="none"). See
    // docs/plans/2026-05-02-feat-life-clock-diet-rhythm-and-copy-pass-plan.md.
    //
    // 1.3.0 (2026-05-02): additive DailyReflection entity (per-day user
    // reflection captured on the Today screen). Brand-new entity, no
    // legacy rows; @Attribute(.unique) on dayKey is safe at migration.
    // See docs/plans/2026-05-01-refactor-life-clock-tab-consolidation-plan.md
    // Phase 3 + 2026-05-02 review-fix changelog.
    //
    // 1.4.0 (2026-05-08): Phase 2 of the quest-pool affinity engine.
    // Additive new `QuestEvent` entity (four-event lifecycle: shown / picked
    // / replaced / completed — selection-side tracking that the new affinity
    // engine reads in Phase 3). Additive `Quest.genre` field with
    // property-level default `""`, populated at bootstrap from a slug→genre
    // map; `Quest.category` is intentionally preserved for rollback safety
    // and to keep `WeeklyReport.topPositiveDriver` strings consistent. See
    // docs/plans/2026-05-08-feat-quest-pool-affinity-engine-plan.md.
    //
    // 1.5.0 (2026-05-08): Phase 3 of the quest-pool affinity engine.
    // Three additive UserProfile fields, all property-level-defaulted:
    //   - `distinctOpenDays: Int = 0` — drives the cold-start discovery
    //     dampening factor in QuestSelector.
    //   - `lastForegroundDay: Date? = nil` — start-of-day for the most
    //     recent local-day foreground; used to detect "first foreground
    //     of new day" and increment distinctOpenDays.
    //   - `useQuestPoolEngine: Bool = false` — feature flag for the
    //     selector path. False default; flipped by Phase 5a after the
    //     production pool ships.
    // Plus an `#Index` on QuestEvent's (date, slug, kind) triple — without
    // it, the idempotent-emit dedup lookup grows linearly with retention.
    // See docs/plans/2026-05-08-feat-quest-pool-phase-3-engines-plan.md.
    static var versionIdentifier = Schema.Version(1, 5, 0)

    static var models: [any PersistentModel.Type] {
        [
            UserProfile.self,
            DailyHealthSnapshot.self,
            HabitLog.self,
            LifeClockEstimate.self,
            TimeLedgerEntry.self,
            Quest.self,
            WeeklyReport.self,
            DailyReflection.self,
            QuestEvent.self,
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

        // MARK: - Reveal-onboarding rebuild (additive 2026-05-01)
        //
        // All optional or with property-level defaults so SwiftData lightweight
        // migration applies them silently to existing V1 stores. Driven by the
        // brainstorm + plan at docs/brainstorms/ + docs/plans/. These feed
        // ClockEngine.lifestyleAdjustmentYears (Phase 1b) and the new dial
        // (Phase 5). None of them iCloud-sync — `cloudKitDatabase: .none` at
        // the container level applies globally.

        /// Cardio minutes per week (PA Guidelines 2018; Lee et al. 2014).
        /// Distinct from `strengthFrequencyPerWeek` — cardio has its own
        /// mortality-reduction curve. 0 default = unanswered ⇒ engine treats
        /// as the worst bucket. Phase 4 question collects this explicitly.
        var cardioMinsPerWeek: Int = 0

        /// Parental longevity (Sebastiani et al. 2012; Atzmon et al. 2010).
        /// Genetic-anchor signal. All four fields nil = "prefer not to say"
        /// ⇒ engine applies zero adjustment. Sensitive copy required at
        /// collection time (see Phase 4 consent priming).
        var parentMotherAlive: Bool? = nil
        var parentMotherAgeAtDeath: Int? = nil
        var parentFatherAlive: Bool? = nil
        var parentFatherAgeAtDeath: Int? = nil

        /// Cohen 1988 PSS-10 (perceived stress, 0–40 range) and UCLA-3
        /// loneliness scale (3–9 range). Special-category data under
        /// GDPR Art. 9 — captured only after explicit consent priming.
        /// Telemetry MUST bucket these before logging (low/medium/high) —
        /// raw values never enter the public log channel.
        var perceivedStressScore: Int? = nil
        var lonelinessScore: Int? = nil

        /// `OnboardingGoal` raw value. Personalizes the recovery animation
        /// cycling words and softens framing for `.justCurious`.
        var primaryGoal: String? = nil

        /// `Archetype` raw value computed at the end of the analyzing phase.
        /// `.marathoner` / `.sprinter` / `.sleeper` / `.outlier` per the
        /// pace-based taxonomy chosen in the brainstorm.
        var archetype: String? = nil

        /// One-time healthspan dial adjustment in years (bounded ±5). The
        /// engine reads this ONLY when `anchorAdjustedAt != nil` — atomic
        /// gate makes the pair race-free under partial-write failure.
        /// Once set, the dial UI never reappears for the lifetime of the
        /// install.
        var personalAdjustmentYears: Double? = nil
        var anchorAdjustedAt: Date? = nil

        /// Distinguishes users who completed the new (post-rebuild) onboarding
        /// from existing users on the legacy 7-step flow. Existing users with
        /// `currentProfile != nil` AND `anchorAdjustedAt == nil` get a one-time
        /// recalibration prompt rather than a full restart of onboarding.
        var onboardingV2CompletedAt: Date? = nil

        // MARK: - Quest-pool affinity engine (additive 2026-05-08, V1.5.0)
        //
        // Property-level defaults are mandatory (NSCocoaErrorDomain 134110
        // landmine, see docs/solutions/integration-issues/swiftdata-mandatory-attribute-migration-landmine.md).
        // Defaults are chosen so a freshly-migrated profile reads as
        // "first day, no engagement" — discovery damp = 0.3 and the
        // legacy QuestEngine path runs.

        /// Number of distinct local-calendar days this install has been
        /// foregrounded. Drives the cold-start discovery dampening
        /// factor in QuestSelector — `0.3 + 0.7 × min(d/7, 1)`.
        /// Incremented on first foreground per local day in
        /// `LifeClockStore.refresh()`.
        var distinctOpenDays: Int = 0

        /// Start-of-day for the most recent local-calendar day on which
        /// this install was foregrounded. `nil` until first launch
        /// completes. Used to gate the daily-cycle EOD resolver and the
        /// `distinctOpenDays` increment.
        var lastForegroundDay: Date? = nil

        /// Feature flag for the quest-pool selector path. When true,
        /// `QuestEngine.generateDailyQuests` routes through QuestSelector
        /// + the JSON-loaded pool. When false (default), the legacy
        /// inlined Quest path runs unchanged. Flipped by Phase 5a after
        /// the production pool ships and bakes ≥1 week.
        var useQuestPoolEngine: Bool = false

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

        // MARK: - Overrides (additive 2026-05-01, Pro override flow)
        //
        // Stored as encoded `Data` rather than Swift dictionaries because
        // SwiftData's representation of `[String: Double]` on `@Model` types
        // has been inconsistent across iOS minor releases. `Data = Data()`
        // default keeps lightweight migration safe.
        //
        // Decode/encode through `SnapshotOverrideMap` — never touch the raw
        // bytes from view code.

        /// Encoded `SnapshotOverrideMap` of user-applied corrections. Pro
        /// only. The engine reads through `effectiveValue(for:)` which
        /// returns the override when present, else the raw HK field.
        var overridesData: Data = Data()

        /// Encoded `SnapshotOverrideMap` capturing the HealthKit values at
        /// the moment each override was first written. Used by Revert to
        /// restore the original. Write-once-per-field — never overwrite
        /// when HK later returns updated data.
        var originalHealthKitValuesData: Data = Data()

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

        // MARK: - Diet rhythm axis (additive 2026-05-02, V1.2.0)
        //
        // Property-level defaults are mandatory (NSCocoaErrorDomain 134110
        // landmine). Defaults match the existing meaningful-neutral
        // convention: `"right"` is the engine's zero-delta case for
        // rhythm; `"unknown"` is the same neutral token QuestEngine
        // already uses for unset diet. Engine treats both defaults as
        // zero contribution.

        /// "right" | "overate" | "undereate" | "skipBinge" | "irregular"
        var dietAmountRhythm: String = "right"

        /// "yes" | "almost" | "no" | "unknown"
        var wholeFoodMeal: String = "unknown"

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

        // 1.4.0 (2026-05-08): additive `genre` field for the quest-pool
        // affinity engine. Populated at bootstrap from a slug→genre map
        // (LifeClockStore.bootstrapQuestGenres). Property-level default
        // `""` keeps lightweight migration safe; engine code treats `""`
        // as "needs backfill" and falls back to mapping by `category`.
        // `category` is intentionally preserved (not rewritten in place)
        // for rollback safety and cross-table vocabulary alignment with
        // WeeklyReport driver strings. See
        // docs/plans/2026-05-08-feat-quest-pool-affinity-engine-plan.md.
        var genre: String = ""

        init(
            id: UUID = UUID(),
            slug: String,
            date: Date,
            title: String,
            detail: String,
            category: String,
            target: Double,
            rewardEstimateMinutes: Int,
            genre: String = ""
        ) {
            self.id = id
            self.slug = slug
            self.date = date
            self.title = title
            self.detail = detail
            self.category = category
            self.target = target
            self.rewardEstimateMinutes = rewardEstimateMinutes
            self.genre = genre
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

    /// User-written daily reflection in response to the rotating prompt
    /// surfaced on Today. One row per local calendar day, keyed by
    /// `dayKey` (yyyyMMdd Int) which is timezone-stable — `Date`-based
    /// startOfDay keys would shift under timezone changes and create
    /// phantom rows.
    ///
    /// `dayKey` is `@Attribute(.unique)` so the database guarantees
    /// one-row-per-day even if a future code path bypasses the
    /// `LifeClockStore.saveReflection(...)` upsert. The entity is brand
    /// new in V1.2.0, so no legacy rows can collide on the unique
    /// constraint at migration time.
    @Model
    final class DailyReflection {
        @Attribute(.unique) var dayKey: Int = 0
        var prompt: String = ""
        var response: String = ""

        init(dayKey: Int, prompt: String, response: String) {
            self.dayKey = dayKey
            self.prompt = prompt
            self.response = response
        }
    }

    /// 1.4.0 (2026-05-08): per-event tracking for the quest-pool affinity
    /// engine. One row per (date, slug, kind) — the `shown / picked /
    /// replaced / completed` lifecycle. Phase 3's AffinityEngine reads this
    /// table to compute per-genre EMA preferences; the end-of-day resolver
    /// fills `resolvedKind` for unresolved rows on the next foreground past
    /// midnight (gates `picked` → "abandoned" and `shown` → "passed_over").
    ///
    /// Brand-new entity, no legacy rows. `id` is `@Attribute(.unique)` —
    /// safe at migration time because the table starts empty.
    ///
    /// Hard rule (NSCocoaErrorDomain 134110 landmine): every non-optional
    /// stored property carries a property-level default. The default-init
    /// pattern matches `TimeLedgerEntry`. See
    /// docs/solutions/integration-issues/swiftdata-mandatory-attribute-migration-landmine.md
    /// and docs/plans/2026-05-08-feat-quest-pool-affinity-engine-plan.md.
    @Model
    final class QuestEvent {
        @Attribute(.unique) var id: UUID = UUID()
        /// Calendar-day this event belongs to (start-of-day in the user's
        /// local timezone at emit). Never re-bucketed on timezone shift —
        /// see plan G8 for rationale.
        var date: Date = Date(timeIntervalSince1970: 0)
        var slug: String = ""
        /// Denormalized genre string ("activity" / "diet" / "sleep") so
        /// affinity computation can fetch + group without cross-table
        /// joins to PoolQuest. Set by the emit path from the in-memory
        /// pool entry's `genre.rawValue`.
        var genre: String = ""
        /// "shown" | "picked" | "replaced" | "completed". String-typed to
        /// match the existing `driverType` convention on TimeLedgerEntry.
        var kind: String = ""
        /// End-of-day resolver fills these. Unresolved `shown` rows roll
        /// forward as "passed_over"; unresolved `picked` rows as
        /// "abandoned". Both nil for `completed` and `replaced` (already
        /// terminal at emit).
        var resolvedAt: Date? = nil
        var resolvedKind: String? = nil

        init(
            id: UUID = UUID(),
            date: Date,
            slug: String,
            genre: String,
            kind: String
        ) {
            self.id = id
            self.date = date
            self.slug = slug
            self.genre = genre
            self.kind = kind
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
typealias DailyReflection = LifeClockSchemaV1.DailyReflection
typealias QuestEvent = LifeClockSchemaV1.QuestEvent

enum LifeClockMigrationPlan: SchemaMigrationPlan {
    static var schemas: [any VersionedSchema.Type] {
        [LifeClockSchemaV1.self]
    }

    /// Empty for V1. When V2 lands, add a `MigrationStage.lightweight` (for
    /// renames/optional adds) or `.custom` (for data transforms). Write a
    /// snapshot test of V1 → V2 *before* shipping V2.
    ///
    /// Note: V1 internal version bumps (1.1.0 → 1.4.0) are all
    /// lightweight-eligible because every change has been additive with
    /// property-level defaults. The single VersionedSchema absorbs them
    /// without an explicit MigrationStage — see SwiftData lightweight
    /// migration semantics.
    static var stages: [MigrationStage] { [] }
}
