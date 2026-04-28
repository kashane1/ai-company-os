import Foundation

// MARK: - Models
//
// v1 ships in-memory only — no SwiftData container, no persistence across cold
// starts. Models are plain `final class` reference types so the store can mutate
// them without `ModelContext`. When persistence lands (separate plan), these
// types switch to `@Model` and get wrapped in a `VersionedSchema` in the same
// PR that constructs a `ModelContainer`.
//
// Property-level defaults are kept on every stored property — they're good
// practice regardless of SwiftData and they make the SwiftData migration
// (when it lands) safe per the past learning at
// docs/solutions/integration-issues/swiftdata-mandatory-attribute-migration-landmine.md.

final class UserProfile {
    var id: UUID = UUID()
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
    var onboardingCompletedAt: Date? = nil
    var disclaimerAcceptedAt: Date? = nil

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

final class DailyHealthSnapshot {
    var date: Date = Date(timeIntervalSince1970: 0)
    var stepCount: Int? = nil
    var distanceMeters: Double? = nil
    var exerciseMinutes: Int? = nil
    var activeEnergyKcal: Double? = nil
    var sleepHours: Double? = nil
    var sleepConsistencyScore: Double? = nil
    var restingHeartRate: Int? = nil
    var sourceCompleteness: Double = 0.0

    init(date: Date) {
        self.date = date
    }
}

final class HabitLog {
    var date: Date = Date(timeIntervalSince1970: 0)
    var alcoholLevel: String = "none"      // none / light / heavy
    var smokingVaping: Bool = false
    var dietQuality: String = "okay"        // great / okay / rough
    var stressLevel: String = "medium"      // low / medium / high
    var strengthTraining: Bool = false
    var notes: String = ""

    init(date: Date) {
        self.date = date
    }
}

final class LifeClockEstimate {
    var date: Date = Date(timeIntervalSince1970: 0)
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

final class TimeLedgerEntry {
    var id: UUID = UUID()
    var date: Date = Date(timeIntervalSince1970: 0)
    var title: String = ""
    var deltaMinutes: Int = 0
    var source: String = "estimate" // healthkit / manual / estimate
    var confidenceRaw: String = "low"
    var driverType: String = "other"

    init(
        id: UUID = UUID(),
        date: Date,
        title: String,
        deltaMinutes: Int,
        source: String,
        confidenceRaw: String,
        driverType: String
    ) {
        self.id = id
        self.date = date
        self.title = title
        self.deltaMinutes = deltaMinutes
        self.source = source
        self.confidenceRaw = confidenceRaw
        self.driverType = driverType
    }
}

final class Quest {
    var id: UUID = UUID()
    var date: Date = Date(timeIntervalSince1970: 0)
    var title: String = ""
    var detail: String = ""
    var category: String = "movement"
    var target: Double = 0
    var progress: Double = 0
    var rewardEstimateMinutes: Int = 0
    var completedAt: Date? = nil

    init(
        id: UUID = UUID(),
        date: Date,
        title: String,
        detail: String,
        category: String,
        target: Double,
        rewardEstimateMinutes: Int
    ) {
        self.id = id
        self.date = date
        self.title = title
        self.detail = detail
        self.category = category
        self.target = target
        self.rewardEstimateMinutes = rewardEstimateMinutes
    }
}

final class WeeklyReport {
    var weekStart: Date = Date(timeIntervalSince1970: 0)
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
