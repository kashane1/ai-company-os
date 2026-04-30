import Foundation
import Observation
import SwiftData
import UserNotifications

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
    var palette: LifeClockPalette = .defaultNavy
    var notificationAuthorizationStatus: UNAuthorizationStatus = .notDetermined
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
    @ObservationIgnored private let notificationsService: NotificationsServiceProtocol

    init(
        healthService: HealthKitServiceProtocol,
        modelContext: ModelContext,
        engineClock: EngineClock = .live,
        notificationsService: NotificationsServiceProtocol = NotificationsService()
    ) {
        self.healthService = healthService
        self.modelContext = modelContext
        self.clock = engineClock
        self.clockEngine = ClockEngine(clock: engineClock)
        self.questEngine = QuestEngine(clock: engineClock)
        self.streakCalculator = DietStreakCalculator(calendar: engineClock.calendar)
        self.notificationsService = notificationsService
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
                if let restored = LifeClockPalette(rawValue: profile.paletteId) {
                    palette = restored
                }
            }
            // Restore today's habits if logged earlier.
            todayHabits = fetchHabits(for: clock.calendar.startOfDay(for: clock.now()))
            // Restore prior ledger entries (most recent first, capped at 50).
            ledger = fetchRecentLedger(limit: 50)
        }
        await refreshFromHealthKit()
        notificationAuthorizationStatus = await notificationsService.currentAuthorizationStatus()
        await reconcileNotifications()
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

    /// Persist the onboarding result. `disclaimerAccepted` MUST be true —
    /// the UI gates the Continue button on the disclaimer toggle, but a
    /// second client (App Intents, Shortcuts, future deep links) must not
    /// be able to bypass acceptance. Returns `true` on success.
    @discardableResult
    func completeOnboarding(profile: UserProfile, tone: ToneMode, disclaimerAccepted: Bool) -> Bool {
        guard disclaimerAccepted else { return false }
        let now = clock.now()
        profile.toneMode = tone.rawValue
        profile.disclaimerAcceptedAt = now
        profile.onboardingCompletedAt = now
        modelContext.insert(profile)
        try? modelContext.save()
        self.profile = profile
        self.toneMode = tone
        hasCompletedOnboarding = true
        return true
    }

    func setToneMode(_ tone: ToneMode) {
        toneMode = tone
        profile?.toneMode = tone.rawValue
        try? modelContext.save()
        // Notification copy varies by tone; reconcile is idempotent.
        Task { await reconcileNotifications() }
    }

    func setPalette(_ palette: LifeClockPalette) {
        self.palette = palette
        profile?.paletteId = palette.rawValue
        try? modelContext.save()
    }

    /// Persist the user's daily-reminder preference. Refuses if no profile
    /// exists (mirrors the disclaimer-guard pattern). Hour is clamped to
    /// the 8…22 quiet-hour window — defense in depth: the picker should
    /// also enforce this, but a future App Intent or Shortcut could
    /// bypass the UI.
    func setDailyReminder(enabled: Bool, hour: Int) async {
        guard let profile else { return }
        let clamped = max(8, min(22, hour))
        profile.dailyReminderEnabled = enabled
        profile.dailyReminderHour = clamped
        // Skip reconcile if the persist failed — avoids a state desync
        // where the in-memory mutation diverges from disk.
        do {
            try modelContext.save()
        } catch {
            return
        }
        await reconcileNotifications()
    }

    func requestNotificationAuthorization() async -> Bool {
        let granted = await notificationsService.requestAuthorization()
        notificationAuthorizationStatus = await notificationsService.currentAuthorizationStatus()
        await reconcileNotifications()
        return granted
    }

    /// Called from `LifeClockApp` on `scenePhase == .active` so that
    /// changes to notification permission made in iOS Settings (without
    /// relaunching) are picked up.
    func refreshNotificationAuthorization() async {
        notificationAuthorizationStatus = await notificationsService.currentAuthorizationStatus()
        await reconcileNotifications()
    }

    /// Single chokepoint for notification scheduling. All mutators that
    /// affect the schedule (`bootstrap`, `setTodayHabits`, `setToneMode`,
    /// `setHideClock`, `setDailyReminder`, `resetForOnboarding`) call this
    /// after their state mutation. One guard expression, no drift across
    /// mutators.
    ///
    /// Suppression rule (closes the morning-log bug): if the user logged
    /// today AND the reminder hour hasn't passed yet, install a one-shot
    /// trigger for tomorrow's hour instead of the daily-repeating trigger.
    /// The next reconcile (next launch, next mutator, next scenePhase
    /// active) restores the repeating shape once we're past today.
    private func reconcileNotifications() async {
        guard let profile,
              profile.dailyReminderEnabled,
              !profile.hideClock,
              notificationAuthorizationStatus == .authorized
        else {
            await notificationsService.cancelAll()
            return
        }
        let suppressUntil = nextFireSkippingTodayIfLogged(profile: profile)
        await notificationsService.setSchedule(
            enabled: true,
            hour: profile.dailyReminderHour,
            tone: toneMode,
            suppressUntil: suppressUntil,
            calendar: clock.calendar
        )
    }

    /// Returns tomorrow's reminder fire-time if the user has logged today
    /// AND today's reminder hour hasn't passed yet; nil otherwise (caller
    /// installs the normal daily-repeating trigger).
    private func nextFireSkippingTodayIfLogged(profile: UserProfile) -> Date? {
        guard let lastSuppressed = profile.lastSuppressedDate else { return nil }
        let now = clock.now()
        let calendar = clock.calendar
        let todayStart = calendar.startOfDay(for: now)
        guard calendar.isDate(lastSuppressed, inSameDayAs: todayStart) else { return nil }

        // If today's reminder hour has already passed, the repeating
        // trigger naturally fires tomorrow — no suppression needed.
        guard
            let todayFire = calendar.date(
                bySettingHour: profile.dailyReminderHour,
                minute: 0,
                second: 0,
                of: now
            ),
            todayFire > now
        else {
            return nil
        }

        // Install one-shot at tomorrow's hour to skip today's fire.
        return calendar.date(byAdding: .day, value: 1, to: todayFire)
    }

    /// Persist the user's "hide the clock" preference. Today screen reads
    /// `profile?.hideClock` to decide whether to render the projected-age
    /// card or the safer "time earned today" alternative. Resolves Q5 +
    /// part of the safety-net offering for Q13.
    func setHideClock(_ hidden: Bool) async {
        profile?.hideClock = hidden
        do {
            try modelContext.save()
        } catch {
            return
        }
        await reconcileNotifications()
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

    /// Delete today's `HabitLog` if it exists. Recovers from a mis-tap in
    /// QuickLog so the engine isn't stuck with phantom signals (e.g. a
    /// "heavy alcohol" entry the user didn't mean to save). No-op if no log
    /// is present for today.
    func clearTodayHabits() async {
        let dayStart = clock.calendar.startOfDay(for: clock.now())
        guard let existing = fetchHabits(for: dayStart) else { return }
        modelContext.delete(existing)
        try? modelContext.save()
        todayHabits = nil
        await refreshFromHealthKit()
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
        // Mark today as logged so reconcile suppresses today's fire.
        // Closes the morning-log bug (#026): if user logs at 9 AM with
        // a 8 PM reminder, the cancel-then-reconcile cycle previously
        // re-installed today's fire because iOS computed the next match
        // as today 8 PM. Reconcile now reads `lastSuppressedDate` and
        // installs a one-shot for tomorrow instead.
        profile?.lastSuppressedDate = clock.calendar.startOfDay(for: clock.now())
        try? modelContext.save()
        await refreshFromHealthKit()
        await reconcileNotifications()
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
        palette = .defaultNavy
        hasCompletedOnboarding = false
        Task { await reconcileNotifications() }
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
