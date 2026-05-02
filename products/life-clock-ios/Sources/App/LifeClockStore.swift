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
    /// In-memory mirror of recent ledger entries. As of the 2026-05-01 IA
    /// refactor (tab bar collapse), no production view reads `ledger`
    /// directly — Today reads `todayDrivers` (top 3) and History reads
    /// `DayDetailView` data via `snapshot(for:)`. Kept exposed for tests
    /// (`LifeClockStoreTests`, `LifeClockE2ETests`) and future debug
    /// surfaces. Refactor to private + a `recentLedger(limit:)` accessor
    /// is a separate cleanup.
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
    /// Result of `WrapUpCoordinator.pendingWrapUp(...)` after the most recent
    /// refresh. Observed by `LifeClockApp` to drive sheet presentation.
    /// Cleared by `markWrapUpShown(_:)` after the sheet dismisses.
    var pendingWrapUp: WrapUpCoordinator.PendingWrapUp?
    /// Signed minute delta for yesterday, when a persisted snapshot exists.
    /// Drives the History tab's Yesterday card and the wrap-up sheet
    /// readout. Recomputed during each refresh.
    var yesterdayDeltaMinutes: Int?
    /// Signed weekly net for the most recent completed week, when a weekly
    /// report exists. Drives the weekly wrap-up sheet readout.
    var lastWeekDeltaMinutes: Int?
    private(set) var supportMoment: SupportMoment?
    private let supportPresenter = SupportMomentPresenter()

    private func emit(_ intent: SupportMomentPresenter.Intent) {
        supportMoment = supportPresenter.moment(for: intent)
    }

    var completedPlanCount: Int {
        todayQuests.filter { $0.completedAt != nil }.count
    }

    var hasCheckInToday: Bool {
        todayHabits != nil
    }

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
    /// Optional Pro-entitlement source. When nil (default at construction),
    /// override write attempts throw `.notEntitled`. `LifeClockApp` injects
    /// the live `SubscriptionStore` after construction. Tests can inject a
    /// mock conformance to exercise both Pro and non-Pro paths.
    ///
    /// Strong reference (not weak): `EntitlementProviding` conformers are
    /// owned by their app-level holders (`LifeClockApp` keeps
    /// `SubscriptionStore` in @State), not by this store. There's no
    /// retain cycle since the entitlement source has no reference back.
    @ObservationIgnored var entitlements: (any EntitlementProviding)?
    @ObservationIgnored private let clockEngine: ClockEngine
    @ObservationIgnored private let questEngine: QuestEngine
    @ObservationIgnored private let modelContext: ModelContext
    @ObservationIgnored private let streakCalculator: DietStreakCalculator
    @ObservationIgnored private let notificationsService: NotificationsServiceProtocol
    @ObservationIgnored private let wrapUpCoordinator: WrapUpCoordinator
    @ObservationIgnored private let completionBadgeEngine = CompletionBadgeEngine()
    @ObservationIgnored private(set) lazy var historicalImporter: HistoricalImportCoordinator =
        HistoricalImportCoordinator(
            healthService: healthService,
            modelContext: modelContext,
            clock: clock
        )

    /// Foreground refreshes that fall within this many seconds of the last
    /// snapshot persistence are skipped. Saves an HK fetch on each rapid
    /// background→foreground transition (typical user foregrounds 10-30×/day).
    @ObservationIgnored private static let refreshShortCircuitWindow: TimeInterval = 300

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
        self.wrapUpCoordinator = WrapUpCoordinator(clock: engineClock)
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
                toneMode = ToneMode.fromStored(profile.toneMode)
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

    func refreshFromHealthKit(force: Bool = false) async {
        guard let profile else { return }
        let now = clock.now()
        let dayStart = clock.calendar.startOfDay(for: now)

        // Short-circuit: if today's snapshot was just persisted, skip the HK
        // round-trip. `force: true` (e.g. on significantTimeChange or pull-to-
        // refresh) bypasses this.
        if !force,
           let existing = fetchSnapshot(for: dayStart),
           let last = existing.lastRecomputedAt,
           now.timeIntervalSince(last) < Self.refreshShortCircuitWindow {
            recomputePendingWrapUp(profile: profile, now: now)
            return
        }

        let snapshot = await healthService.dailySnapshot(for: now)

        // Persist (or update) today's snapshot row so wrap-ups have a
        // deterministic source across launches.
        if let snapshot {
            persistSnapshot(snapshot, dayStart: dayStart, recomputedAt: now)
        }

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
        applyPersistedCompletions(to: &todayQuests, for: dayStart)

        let weekSnapshots = await healthService.recentSnapshots(endingAt: now, count: 7)
        let weekHabits = fetchHabitsBack(7)
        weekly = clockEngine.calculateWeeklyTrend(snapshots: weekSnapshots, habits: weekHabits, profile: profile)

        dietStreaks = streakCalculator.compute(habits: fetchHabitsBack(60), asOf: now)
        recomputeYesterdayDelta(profile: profile, now: now)
        lastWeekDeltaMinutes = weekly?.netTimeDeltaMinutes
        recomputePendingWrapUp(profile: profile, now: now)
    }

    /// Compute yesterday's signed delta from the persisted snapshot, if one
    /// exists, by re-running `calculateDailyDelta` against the prior-day
    /// habit log. Idempotent and cheap.
    private func recomputeYesterdayDelta(profile: UserProfile, now: Date) {
        let cal = clock.calendar
        let today = cal.startOfDay(for: now)
        guard let yesterday = cal.date(byAdding: .day, value: -1, to: today),
              let snapshot = fetchSnapshot(for: yesterday) else {
            yesterdayDeltaMinutes = nil
            return
        }
        let yesterdayHabits = fetchHabits(for: yesterday)
        let result = clockEngine.calculateDailyDelta(
            snapshot: snapshot,
            habits: yesterdayHabits,
            profile: profile
        )
        yesterdayDeltaMinutes = result.deltaMinutes
    }

    // MARK: - Wrap-up presentation

    /// Maps current persisted state into DTOs and asks the coordinator
    /// whether a wrap-up should be presented. Idempotent — safe to call on
    /// every refresh and on every `scenePhase == .active` transition.
    private func recomputePendingWrapUp(profile: UserProfile, now: Date) {
        let profileSnapshot = WrapUpCoordinator.ProfileSnapshot(
            onboardingCompletedAt: profile.onboardingCompletedAt,
            lastShownYesterdayWrapUpDay: profile.lastShownYesterdayWrapUpDay,
            lastShownWeeklyWrapUpWeek: profile.lastShownWeeklyWrapUpWeek
        )
        let recentSnapshots = fetchRecentSnapshots(limit: 7).map(daySnapshot(from:))
        let recentWeeks = fetchRecentWeeklyReports(limit: 4).map(weekSnapshot(from:))
        pendingWrapUp = wrapUpCoordinator.pendingWrapUp(
            profile: profileSnapshot,
            snapshots: recentSnapshots,
            weeks: recentWeeks,
            now: now
        )
    }

    // MARK: - Overrides (Pro)

    /// Apply or update a Pro override and trigger a re-render. Returns the
    /// service's error on failure so the sheet can surface tone-aware copy.
    /// Throws `.notEntitled` when the injected entitlement source reports
    /// `isPro == false` (or when no entitlement source is wired).
    func applyOverride(
        field: SnapshotOverrideMap.Field,
        value: Double,
        on dayStart: Date
    ) throws {
        guard entitlements?.isPro == true else {
            throw OverrideService.OverrideError.notEntitled
        }
        let now = clock.now()
        let service = OverrideService(modelContext: modelContext)
        try service.applyOverride(field: field, value: value, on: dayStart, recomputedAt: now)
        refreshDerivedStateAfterOverride(dayStart: dayStart, now: now)
    }

    /// Remove a Pro override and restore the captured original HK value.
    /// Throws `.notEntitled` like `applyOverride`.
    func revertOverride(
        field: SnapshotOverrideMap.Field,
        on dayStart: Date
    ) throws {
        guard entitlements?.isPro == true else {
            throw OverrideService.OverrideError.notEntitled
        }
        let now = clock.now()
        let service = OverrideService(modelContext: modelContext)
        try service.revertOverride(field: field, on: dayStart, recomputedAt: now)
        refreshDerivedStateAfterOverride(dayStart: dayStart, now: now)
    }

    /// Re-derive view-bound state after an override change. Skips the
    /// per-day delta recompute when the edited day isn't yesterday (no
    /// yesterday card update needed) but always re-asks the coordinator
    /// in case a wrap-up sheet is currently open and the underlying delta
    /// should refresh.
    private func refreshDerivedStateAfterOverride(dayStart: Date, now: Date) {
        guard let profile else { return }
        let cal = clock.calendar
        let today = cal.startOfDay(for: now)
        if let yesterday = cal.date(byAdding: .day, value: -1, to: today),
           cal.isDate(dayStart, inSameDayAs: yesterday) {
            recomputeYesterdayDelta(profile: profile, now: now)
        }
        recomputePendingWrapUp(profile: profile, now: now)
    }

    /// Public read accessor used by the day-detail view. Returns nil when
    /// no snapshot has been persisted for the day yet.
    func snapshot(for dayStart: Date) -> DailyHealthSnapshot? {
        fetchSnapshot(for: dayStart)
    }

    /// Returns the most recent N persisted snapshots for the History list.
    func recentSnapshots(limit: Int) -> [DailyHealthSnapshot] {
        fetchRecentSnapshots(limit: limit)
    }

    /// Called by the wrap-up sheet on dismiss to advance the lastShown* keys
    /// and clear the pending state. Caller passes the same `PendingWrapUp`
    /// they presented so we advance the right key.
    func markWrapUpShown(_ wrapUp: WrapUpCoordinator.PendingWrapUp) {
        guard let profile else { return }
        let now = clock.now()
        let profileSnapshot = WrapUpCoordinator.ProfileSnapshot(
            onboardingCompletedAt: profile.onboardingCompletedAt,
            lastShownYesterdayWrapUpDay: profile.lastShownYesterdayWrapUpDay,
            lastShownWeeklyWrapUpWeek: profile.lastShownWeeklyWrapUpWeek
        )
        let advanced: WrapUpCoordinator.ProfileSnapshot
        switch wrapUp {
        case .yesterday:
            advanced = wrapUpCoordinator.markYesterdayShown(profile: profileSnapshot, now: now)
        case .weekly(let weekStart):
            advanced = wrapUpCoordinator.markWeeklyShown(profile: profileSnapshot, weekStart: weekStart)
        }
        profile.lastShownYesterdayWrapUpDay = advanced.lastShownYesterdayWrapUpDay
        profile.lastShownWeeklyWrapUpWeek = advanced.lastShownWeeklyWrapUpWeek
        try? modelContext.save()
        pendingWrapUp = nil
    }

    private func daySnapshot(from snapshot: DailyHealthSnapshot) -> WrapUpCoordinator.DaySnapshot {
        let hasMinimumData =
            (snapshot.stepCount ?? 0) > 0
            || (snapshot.exerciseMinutes ?? 0) > 0
            || (snapshot.sleepHours ?? 0) > 0
            || (snapshot.activeEnergyKcal ?? 0) > 0
        return WrapUpCoordinator.DaySnapshot(
            date: snapshot.date,
            hasMinimumData: hasMinimumData
        )
    }

    private func weekSnapshot(from report: WeeklyReport) -> WrapUpCoordinator.WeekSnapshot {
        WrapUpCoordinator.WeekSnapshot(weekStart: report.weekStart)
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
        emit(.onboardingComplete)
        return true
    }

    /// Apply the one-time healthspan dial adjustment. Writes both
    /// `personalAdjustmentYears` and `anchorAdjustedAt` together —
    /// the engine reads `personalAdjustmentYears` only when
    /// `anchorAdjustedAt != nil`, so the pair is logically atomic
    /// against partial-write failure. Replaces silent `try?` with
    /// explicit do/catch so a failed save doesn't leave memory dirty.
    /// Source: Phase 5 of the reveal-onboarding rebuild plan.
    func applyAnchorAdjustment(years: Double) {
        guard let profile else { return }
        // Idempotency: never re-apply if already adjusted.
        guard profile.anchorAdjustedAt == nil else { return }
        profile.personalAdjustmentYears = years
        profile.anchorAdjustedAt = clock.now()
        do {
            try modelContext.save()
        } catch {
            // Roll memory back to match disk so the dial screen reappears
            // on next launch and the user can retry cleanly.
            profile.personalAdjustmentYears = nil
            profile.anchorAdjustedAt = nil
        }
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
        let stored = upsertQuest(quest)
        if quest.completedAt == nil {
            quest.completedAt = now
            stored.completedAt = now
            let entry = TimeLedgerEntry(
                date: now,
                title: "Completed action: \(quest.title)",
                deltaMinutes: quest.rewardEstimateMinutes,
                source: "manual",
                confidenceRaw: Confidence.medium.rawValue,
                driverType: "quest",
                questSlug: quest.slug
            )
            modelContext.insert(entry)
            ledger.insert(entry, at: 0)
            emit(.questCompleted(rewardMinutes: quest.rewardEstimateMinutes))
        } else {
            quest.completedAt = nil
            stored.completedAt = nil
            if let entry = fetchLatestQuestLedgerEntry(for: quest, on: clock.calendar.startOfDay(for: now)) {
                modelContext.delete(entry)
                ledger.removeAll { $0.id == entry.id }
            }
            emit(.questUndone)
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
        let previousDelta = todayEstimate?.dailyTimeDeltaMinutes ?? 0
        let hadCheckIn = todayHabits != nil

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
        let updatedDelta = todayEstimate?.dailyTimeDeltaMinutes ?? previousDelta
        let deltaChange = updatedDelta - previousDelta

        emit(.checkInSaved(
            deltaMinutes: deltaChange,
            strengthLogged: habits.strengthTraining,
            hadPriorCheckIn: hadCheckIn
        ))
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
        supportMoment = nil
        Task { await reconcileNotifications() }
    }

    func dismissSupportMoment() {
        supportMoment = nil
    }

    // MARK: - Completion badges

    func completionBadges() -> [CompletionBadge] {
        completionBadgeEngine.badges(for: completionBadgeProgress())
    }

    private func completionBadgeProgress() -> CompletionBadgeProgress {
        let habits = fetchAllHabits()
        let quests = fetchAllQuests()
        let snapshots = fetchAllSnapshots()
        let reports = fetchAllWeeklyReports()
        let completedQuests = quests.filter { $0.completedAt != nil }
        let completedQuestDays = Set(completedQuests.map { dayKey(for: $0.date) })
        let completedByDay = Dictionary(grouping: completedQuests, by: { dayKey(for: $0.date) })

        return CompletionBadgeProgress(
            onboardedAt: profile?.onboardingCompletedAt,
            completedQuestCount: completedQuests.count,
            completedQuestDays: completedQuestDays.count,
            threeQuestDays: completedByDay.values.filter { $0.count >= 3 }.count,
            checkInDays: Set(habits.map { dayKey(for: $0.date) }).count,
            dietLoggingStreakDays: dietStreaks.loggingDays,
            supportiveDietDays: habits.filter { ["great", "okay"].contains($0.dietQuality.lowercased()) }.count,
            greatDietDays: habits.filter { $0.dietQuality.lowercased() == "great" }.count,
            lowRiskRecoveryDays: habits.filter { habit in
                habit.smokingVaping == false && habit.alcoholLevel.lowercased() != "heavy"
            }.count,
            strengthDays: habits.filter { $0.strengthTraining }.count,
            stepTargetDays: snapshots.filter { ($0.stepCount ?? 0) >= 7_500 }.count,
            tenThousandStepDays: snapshots.filter { ($0.stepCount ?? 0) >= 10_000 }.count,
            exerciseTargetDays: snapshots.filter { ($0.exerciseMinutes ?? 0) >= 30 }.count,
            sleepGoalDays: snapshots.filter { snapshot in
                guard let sleepHours = snapshot.sleepHours else { return false }
                return sleepHours >= (profile?.sleepGoalHours ?? 7.5)
            }.count,
            positiveWeekCount: reports.filter { $0.netTimeDeltaMinutes > 0 }.count,
            dataRichDays: snapshots.filter { $0.sourceCompleteness >= 0.75 }.count,
            healthConnected: healthAuthorizationKnown || snapshots.contains { $0.sourceCompleteness > 0 },
            reminderEnabled: profile?.dailyReminderEnabled == true
        )
    }

    private func dayKey(for date: Date) -> Date {
        clock.calendar.startOfDay(for: date)
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

    private func fetchSnapshot(for dayStart: Date) -> DailyHealthSnapshot? {
        let descriptor = FetchDescriptor<DailyHealthSnapshot>(
            predicate: #Predicate { $0.date == dayStart }
        )
        return try? modelContext.fetch(descriptor).first
    }

    private func fetchRecentSnapshots(limit: Int) -> [DailyHealthSnapshot] {
        var descriptor = FetchDescriptor<DailyHealthSnapshot>(
            sortBy: [SortDescriptor(\.date, order: .reverse)]
        )
        descriptor.fetchLimit = limit
        return (try? modelContext.fetch(descriptor)) ?? []
    }

    private func fetchRecentWeeklyReports(limit: Int) -> [WeeklyReport] {
        var descriptor = FetchDescriptor<WeeklyReport>(
            sortBy: [SortDescriptor(\.weekStart, order: .reverse)]
        )
        descriptor.fetchLimit = limit
        return (try? modelContext.fetch(descriptor)) ?? []
    }

    private func fetchAllSnapshots() -> [DailyHealthSnapshot] {
        let descriptor = FetchDescriptor<DailyHealthSnapshot>(
            sortBy: [SortDescriptor(\.date, order: .reverse)]
        )
        return (try? modelContext.fetch(descriptor)) ?? []
    }

    private func fetchAllWeeklyReports() -> [WeeklyReport] {
        let descriptor = FetchDescriptor<WeeklyReport>(
            sortBy: [SortDescriptor(\.weekStart, order: .reverse)]
        )
        return (try? modelContext.fetch(descriptor)) ?? []
    }

    /// Upsert today's snapshot. The HK service returns a transient
    /// `DailyHealthSnapshot` (not yet inserted into a context). If a row
    /// already exists for `dayStart`, update its fields in place; otherwise
    /// insert the transient instance after stamping `lastRecomputedAt`.
    private func persistSnapshot(
        _ snapshot: DailyHealthSnapshot,
        dayStart: Date,
        recomputedAt: Date
    ) {
        if let existing = fetchSnapshot(for: dayStart) {
            // Override-aware merge: HK refresh writes field-by-field, with
            // two guards:
            //   1. overridden fields are skipped entirely (user correction
            //      stays authoritative)
            //   2. nil HK values do NOT overwrite a previously-good raw
            //      value (HK occasionally returns nil for transient reasons
            //      — query timeouts, sync glitches; we don't want a flaky
            //      response to nuke yesterday's good data)
            let overrides = existing.overrideMap
            if !overrides.presentFields.contains(.stepCount), let v = snapshot.stepCount {
                existing.stepCount = v
            }
            if !overrides.presentFields.contains(.sleepHours), let v = snapshot.sleepHours {
                existing.sleepHours = v
            }
            if !overrides.presentFields.contains(.exerciseMinutes), let v = snapshot.exerciseMinutes {
                existing.exerciseMinutes = v
            }
            if !overrides.presentFields.contains(.activeEnergyKcal), let v = snapshot.activeEnergyKcal {
                existing.activeEnergyKcal = v
            }
            // Non-overridable fields update from HK only when HK delivered
            // a value. Same nil-guard reasoning as above.
            if let v = snapshot.distanceMeters { existing.distanceMeters = v }
            if let v = snapshot.sleepConsistencyScore { existing.sleepConsistencyScore = v }
            if let v = snapshot.restingHeartRate { existing.restingHeartRate = v }
            // sourceCompleteness is non-optional and meaningful even at 0 —
            // always update so it reflects the most recent fetch attempt.
            existing.sourceCompleteness = snapshot.sourceCompleteness
            existing.lastRecomputedAt = recomputedAt
        } else {
            snapshot.lastRecomputedAt = recomputedAt
            modelContext.insert(snapshot)
        }
        try? modelContext.save()
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

    private func fetchAllHabits() -> [HabitLog] {
        let descriptor = FetchDescriptor<HabitLog>(
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

    /// Apply persisted completion state to the engine-emitted quests for a
    /// given day. Matches by (date, slug) — title is free to drift across
    /// copy edits without orphaning completion state.
    ///
    /// Lazy backfill: persisted rows from pre-slug versions of the app have
    /// `slug == ""`. We promote them by matching on (category, title) against
    /// today's engine-emitted quests and writing the engine's slug onto the
    /// stored row, so subsequent days find them by slug. One-time per row.
    private func applyPersistedCompletions(to quests: inout [Quest], for dayStart: Date) {
        let storedRows = fetchQuests(on: dayStart)
        // `uniquingKeysWith: { first, _ in first }` defends against duplicate
        // keys (legacy data could in principle have two rows with the same
        // (category, title) for a given day; SwiftData doesn't enforce
        // uniqueness on those columns). First write wins; the second row
        // stays orphaned but does not crash the app.
        let storedBySlug = Dictionary(
            storedRows.compactMap { stored -> (String, Quest)? in
                stored.slug.isEmpty ? nil : (stored.slug, stored)
            },
            uniquingKeysWith: { first, _ in first }
        )
        let legacyByTitleCategory = Dictionary(
            storedRows.compactMap { stored -> (TitleCategoryKey, Quest)? in
                guard stored.slug.isEmpty else { return nil }
                return (TitleCategoryKey(category: stored.category, title: stored.title), stored)
            },
            uniquingKeysWith: { first, _ in first }
        )
        var didBackfill = false
        quests = quests.map { quest in
            if let stored = storedBySlug[quest.slug] {
                quest.completedAt = stored.completedAt
            } else if let legacy = legacyByTitleCategory[TitleCategoryKey(category: quest.category, title: quest.title)] {
                legacy.slug = quest.slug
                quest.completedAt = legacy.completedAt
                didBackfill = true
            }
            return quest
        }
        if didBackfill {
            try? modelContext.save()
        }
    }

    private struct TitleCategoryKey: Hashable {
        let category: String
        let title: String
    }

    /// Single source of truth for "find or insert a Quest persisted by slug."
    /// Replaces five overlapping helpers that matched by (date, title, category).
    /// Mutable display fields (title, detail, target, progress, reward) are
    /// copied from the engine-emitted instance so daily refresh stays accurate;
    /// completedAt is left to the caller.
    @discardableResult
    private func upsertQuest(_ quest: Quest) -> Quest {
        let stored = fetchStoredQuest(slug: quest.slug, on: quest.date) ?? {
            let new = Quest(
                id: quest.id,
                slug: quest.slug,
                date: quest.date,
                title: quest.title,
                detail: quest.detail,
                category: quest.category,
                target: quest.target,
                rewardEstimateMinutes: quest.rewardEstimateMinutes
            )
            new.progress = quest.progress
            modelContext.insert(new)
            return new
        }()
        stored.title = quest.title
        stored.detail = quest.detail
        stored.target = quest.target
        stored.progress = quest.progress
        stored.rewardEstimateMinutes = quest.rewardEstimateMinutes
        return stored
    }

    private func fetchQuests(on dayStart: Date) -> [Quest] {
        let descriptor = FetchDescriptor<Quest>(
            predicate: #Predicate { $0.date == dayStart }
        )
        return (try? modelContext.fetch(descriptor)) ?? []
    }

    private func fetchAllQuests() -> [Quest] {
        let descriptor = FetchDescriptor<Quest>(
            sortBy: [SortDescriptor(\.date, order: .reverse)]
        )
        return (try? modelContext.fetch(descriptor)) ?? []
    }

    private func fetchStoredQuest(slug: String, on dayStart: Date) -> Quest? {
        guard !slug.isEmpty else { return nil }
        let descriptor = FetchDescriptor<Quest>(
            predicate: #Predicate { stored in
                stored.date == dayStart && stored.slug == slug
            }
        )
        return try? modelContext.fetch(descriptor).first
    }

    private func fetchLatestQuestLedgerEntry(for quest: Quest, on dayStart: Date) -> TimeLedgerEntry? {
        let nextDay = clock.calendar.date(byAdding: .day, value: 1, to: dayStart) ?? dayStart
        let slug = quest.slug
        var descriptor = FetchDescriptor<TimeLedgerEntry>(
            predicate: #Predicate { entry in
                entry.date >= dayStart
                    && entry.date < nextDay
                    && entry.driverType == "quest"
                    && entry.questSlug == slug
            },
            sortBy: [SortDescriptor(\.date, order: .reverse)]
        )
        descriptor.fetchLimit = 1
        return try? modelContext.fetch(descriptor).first
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
