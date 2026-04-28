import Foundation
import Observation

/// App-level observable state. Seeded from the injected `HealthKitServiceProtocol`
/// at bootstrap. Production v1 wires `MockHealthKitService`.
///
/// Side effects belong in `bootstrap()`, not `init` — `@State`-held stores get
/// re-initialized on every parent rebuild, and side effects in `init` leak.
@Observable
final class LifeClockStore {
    var profile: UserProfile?
    var todayEstimate: LifeClockEstimate?
    var todayDriversToday: [TimeLedgerEntry] = []
    var todayQuests: [Quest] = []
    var ledger: [TimeLedgerEntry] = []
    var weekly: WeeklyReport?
    var hasCompletedOnboarding: Bool = false
    var toneMode: ToneMode = .coach
    var permissions: [String: String] = [:] // dataType → status string

    @ObservationIgnored private let healthService: HealthKitServiceProtocol
    @ObservationIgnored private let clockEngine: ClockEngine
    @ObservationIgnored private let questEngine: QuestEngine
    @ObservationIgnored private let calendar: Calendar

    init(
        healthService: HealthKitServiceProtocol = MockHealthKitService(),
        engineClock: EngineClock = .live
    ) {
        self.healthService = healthService
        self.clockEngine = ClockEngine(clock: engineClock)
        self.questEngine = QuestEngine(clock: engineClock)
        self.calendar = engineClock.calendar
    }

    // MARK: - Bootstrap

    func bootstrap() async {
        // Seed a sample profile if onboarding hasn't run. v1 has no persistence,
        // so this fires every cold start — acknowledged in README.
        if profile == nil {
            let sample = UserProfile(
                birthDate: Calendar.lifeClockUTC.date(from: DateComponents(year: 1990, month: 6, day: 12))
                    ?? Date(timeIntervalSince1970: 0),
                biologicalSex: "unspecified",
                toneMode: toneMode.rawValue
            )
            sample.smokingStatus = "none"
            sample.alcoholFrequency = "rare"
            sample.sleepGoalHours = 7.5
            sample.strengthFrequencyPerWeek = 2
            profile = sample
        }

        guard let profile else { return }

        let now = Date()
        let snapshot = await healthService.dailySnapshot(for: now)

        let baseline = clockEngine.calculateBaseline(profile: profile)
        if let snapshot {
            let result = clockEngine.calculateDailyDelta(snapshot: snapshot, habits: nil, profile: profile)
            baseline.dailyTimeDeltaMinutes = result.deltaMinutes
            baseline.confidenceRaw = result.confidence.rawValue
            todayDriversToday = result.drivers
            ledger = result.drivers.sorted { $0.deltaMinutes > $1.deltaMinutes }
        }
        todayEstimate = baseline
        todayQuests = questEngine.generateDailyQuests(profile: profile, snapshot: snapshot, habits: nil)

        let weekSnapshots = await healthService.recentSnapshots(endingAt: now, count: 7)
        weekly = clockEngine.calculateWeeklyTrend(snapshots: weekSnapshots, habits: [], profile: profile)
    }

    // MARK: - Mutations driven by the UI

    func completeOnboarding(profile: UserProfile, tone: ToneMode) {
        self.profile = profile
        self.toneMode = tone
        profile.toneMode = tone.rawValue
        profile.disclaimerAcceptedAt = Date()
        profile.onboardingCompletedAt = Date()
        hasCompletedOnboarding = true
    }

    func setToneMode(_ tone: ToneMode) {
        toneMode = tone
        profile?.toneMode = tone.rawValue
    }

    func toggleQuestCompletion(_ quest: Quest) {
        if quest.completedAt == nil {
            quest.completedAt = Date()
            ledger.insert(
                TimeLedgerEntry(
                    date: Date(),
                    title: "Completed quest: \(quest.title)",
                    deltaMinutes: quest.rewardEstimateMinutes,
                    source: "manual",
                    confidenceRaw: Confidence.medium.rawValue,
                    driverType: "quest"
                ),
                at: 0
            )
        } else {
            quest.completedAt = nil
        }
    }

    func resetForOnboarding() {
        profile = nil
        hasCompletedOnboarding = false
    }
}
