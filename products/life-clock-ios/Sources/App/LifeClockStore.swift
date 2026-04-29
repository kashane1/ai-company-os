import Foundation
import Observation
import SwiftData

/// App-level observable state. Mediates `ModelContext` for persistence and
/// orchestrates the engines + HealthKit service.
///
/// Side effects belong in `bootstrap()`, not `init`.
///
/// `@MainActor` because the store mutates UI-bound properties after async
/// awaits and because `ModelContext` is not `Sendable`.
@MainActor
@Observable
final class LifeClockStore {
    var profile: UserProfile?
    var todayEstimate: LifeClockEstimate?
    var todayDrivers: [TimeLedgerEntry] = []
    var todayQuests: [Quest] = []
    var ledger: [TimeLedgerEntry] = []
    var weekly: WeeklyReport?
    var hasCompletedOnboarding: Bool = false
    var toneMode: ToneMode = .coach
    var healthAuthorizationKnown: Bool = false
    var healthDataAvailable: Bool = true
    var todayHabits: HabitLog?
    var lastHealthAuthError: String?
    var hasTodaySignal: Bool = false
    var dietStreaks: DietStreaks = .zero

    /// True iff the user has a profile and reports DOB making them ≥18 as of
    /// today's clock. Drives the age-gate on QuickLog smoking/alcohol pickers.
    var isAdultUser: Bool {
        guard let profile else { return false }
        return AgeGate.isAdult(
            birthDate: profile.birthDate,
            asOf: clock.now(),
            calendar: clock.calendar
        )
    }

    @ObservationIgnored private let healthService: HealthKitServiceProtocol
    @ObservationIgnored let clock: EngineClock
    @ObservationIgnored private let clockEngine: ClockEngine
    @ObservationIgnored private let questEngine: QuestEngine
    @ObservationIgnored private let modelContext: ModelContext
    @ObservationIgnored private let streakCalculator: DietStreakCalculator

    init(
        healthService: HealthKitServiceProtocol,
        modelContext: ModelContext,
        engineClock: EngineClock = .live
    ) {
        self.healthService = healthService
        self.modelContext = modelContext
        self.clock = engineClock
        self.clockEngine = ClockEngine(clock: engineClock)
        self.questEngine = QuestEngine(clock: engineClock)
        self.streakCalculator = DietStreakCalculator(calendar: engineClock.calendar)
        self.healthAuthorizationKnown = healthService.authorizationKnown
        self.healthDataAvailable = healthService.isHealthDataAvailable
    }

    // MARK: - Bootstrap

    func bootstrap() async {
        // Restore from persistence if a profile exists; otherwise this is a
        // first launch and OnboardingView is showing instead of MainTabView.
        if profile == nil {
            profile = fetchFirst(UserProfile.self)
            if let profile {
                hasCompletedOnboarding = true
                if let mode = ToneMode(rawValue: profile.toneMode) {
                    toneMode = mode
                }
            }
            // Restore today's habits if logged earlier.
            todayHabits = fetchHabits(for: clock.calendar.startOfDay(for: clock.now()))
            // Restore prior ledger entries (most recent first, capped at 50).
            ledger = fetchRecentLedger(limit: 50)
        }
        await refreshFromHealthKit()
    }

    // MARK: - HealthKit-driven recompute

    func refreshFromHealthKit() async {
        guard let profile else { return }
        let now = clock.now()
        let snapshot = await healthService.dailySnapshot(for: now)

        let baseline = clockEngine.calculateBaseline(profile: profile)
        if let snapshot {
            let result = clockEngine.calculateDailyDelta(snapshot: snapshot, habits: todayHabits, profile: profile)
            baseline.dailyTimeDeltaMinutes = result.deltaMinutes
            baseline.confidenceRaw = result.confidence.rawValue
            todayDrivers = result.drivers
            // Merge drivers into the persisted ledger (older entries already
            // there from prior days). Drivers are recomputed each refresh —
            // we don't persist them; they'd be duplicated on every relaunch.
            ledger = (result.drivers + ledger.filter { !clock.calendar.isDate($0.date, inSameDayAs: now) })
                .sorted { $0.date > $1.date }
            hasTodaySignal = snapshot.stepCount != nil
                || snapshot.exerciseMinutes != nil
                || snapshot.sleepHours != nil
                || snapshot.restingHeartRate != nil
        } else {
            todayDrivers = []
            hasTodaySignal = false
        }
        todayEstimate = baseline
        todayQuests = questEngine.generateDailyQuests(profile: profile, snapshot: snapshot, habits: todayHabits)

        let weekSnapshots = await healthService.recentSnapshots(endingAt: now, count: 7)
        weekly = clockEngine.calculateWeeklyTrend(snapshots: weekSnapshots, habits: [], profile: profile)

        dietStreaks = streakCalculator.compute(habits: fetchHabitsBack(60), asOf: now)
    }

    // MARK: - HealthKit authorization

    func requestHealthAuthorization() async {
        guard healthDataAvailable else {
            lastHealthAuthError = "Apple Health is not available on this device."
            return
        }
        do {
            try await healthService.requestAuthorization()
            lastHealthAuthError = nil
            healthAuthorizationKnown = true
            await refreshFromHealthKit()
        } catch HealthKitError.unavailable {
            lastHealthAuthError = "Apple Health is not available on this device."
        } catch {
            lastHealthAuthError = "Apple Health request failed: \(error.localizedDescription)"
            healthAuthorizationKnown = healthService.authorizationKnown
        }
    }

    // MARK: - Mutations driven by the UI

    func completeOnboarding(profile: UserProfile, tone: ToneMode) {
        let now = clock.now()
        profile.toneMode = tone.rawValue
        profile.disclaimerAcceptedAt = now
        profile.onboardingCompletedAt = now
        modelContext.insert(profile)
        try? modelContext.save()
        self.profile = profile
        self.toneMode = tone
        hasCompletedOnboarding = true
    }

    func setToneMode(_ tone: ToneMode) {
        toneMode = tone
        profile?.toneMode = tone.rawValue
        try? modelContext.save()
    }

    /// Persist the user's "hide the clock" preference. Today screen reads
    /// `profile?.hideClock` to decide whether to render the projected-age
    /// card or the safer "time earned today" alternative. Resolves Q5 +
    /// part of the safety-net offering for Q13.
    func setHideClock(_ hidden: Bool) async {
        profile?.hideClock = hidden
        try? modelContext.save()
    }

    func toggleQuestCompletion(_ quest: Quest) {
        let now = clock.now()
        if quest.completedAt == nil {
            quest.completedAt = now
            // Persist the quest if it isn't already tracked.
            if quest.modelContext == nil {
                modelContext.insert(quest)
            }
            let entry = TimeLedgerEntry(
                date: now,
                title: "Completed quest: \(quest.title)",
                deltaMinutes: quest.rewardEstimateMinutes,
                source: "manual",
                confidenceRaw: Confidence.medium.rawValue,
                driverType: "quest"
            )
            modelContext.insert(entry)
            ledger.insert(entry, at: 0)
        } else {
            quest.completedAt = nil
        }
        try? modelContext.save()
    }

    func setTodayHabits(_ habits: HabitLog) async {
        // Upsert by date — only one HabitLog per day.
        let dayStart = clock.calendar.startOfDay(for: habits.date)
        habits.date = dayStart
        if let existing = fetchHabits(for: dayStart) {
            existing.alcoholLevel = habits.alcoholLevel
            existing.smokingVaping = habits.smokingVaping
            existing.dietQuality = habits.dietQuality
            existing.stressLevel = habits.stressLevel
            existing.strengthTraining = habits.strengthTraining
            existing.notes = habits.notes
            todayHabits = existing
        } else {
            modelContext.insert(habits)
            todayHabits = habits
        }
        try? modelContext.save()
        await refreshFromHealthKit()
    }

    func resetForOnboarding() {
        deleteAllPersistedData()
        profile = nil
        todayHabits = nil
        ledger = []
        todayEstimate = nil
        todayDrivers = []
        todayQuests = []
        weekly = nil
        hasCompletedOnboarding = false
    }

    // MARK: - Persistence helpers

    private func fetchFirst<T: PersistentModel>(_ type: T.Type) -> T? {
        let descriptor = FetchDescriptor<T>()
        return try? modelContext.fetch(descriptor).first
    }

    private func fetchHabits(for dayStart: Date) -> HabitLog? {
        let descriptor = FetchDescriptor<HabitLog>(
            predicate: #Predicate { $0.date == dayStart }
        )
        return try? modelContext.fetch(descriptor).first
    }

    private func fetchHabitsBack(_ days: Int) -> [HabitLog] {
        guard
            let earliest = clock.calendar.date(byAdding: .day, value: -days, to: clock.now())
        else { return [] }
        let descriptor = FetchDescriptor<HabitLog>(
            predicate: #Predicate { $0.date >= earliest },
            sortBy: [SortDescriptor(\.date, order: .reverse)]
        )
        return (try? modelContext.fetch(descriptor)) ?? []
    }

    private func fetchRecentLedger(limit: Int) -> [TimeLedgerEntry] {
        var descriptor = FetchDescriptor<TimeLedgerEntry>(
            sortBy: [SortDescriptor(\.date, order: .reverse)]
        )
        descriptor.fetchLimit = limit
        return (try? modelContext.fetch(descriptor)) ?? []
    }

    private func deleteAllPersistedData() {
        try? modelContext.delete(model: UserProfile.self)
        try? modelContext.delete(model: HabitLog.self)
        try? modelContext.delete(model: Quest.self)
        try? modelContext.delete(model: TimeLedgerEntry.self)
        try? modelContext.delete(model: LifeClockEstimate.self)
        try? modelContext.delete(model: WeeklyReport.self)
        try? modelContext.delete(model: DailyHealthSnapshot.self)
        try? modelContext.save()
    }
}
