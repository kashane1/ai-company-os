import XCTest
import SwiftData
import UserNotifications
@testable import LifeClock

/// Spy implementation of the notifications service used to assert
/// schedule/cancel routing without touching `UNUserNotificationCenter`.
fileprivate actor MockNotificationsService: NotificationsServiceProtocol {
    // `installForegroundDelegate` is `nonisolated` on the protocol so it
    // must read/write outside actor isolation. A simple counter wrapped
    // in a class lets the test verify the call without crossing the
    // actor boundary.
    final class InstallTracker: @unchecked Sendable {
        private var _count = 0
        private let lock = NSLock()
        func increment() {
            lock.lock(); defer { lock.unlock() }
            _count += 1
        }
        var count: Int {
            lock.lock(); defer { lock.unlock() }
            return _count
        }
    }
    nonisolated let installTracker = InstallTracker()

    var stubAuthorizationStatus: UNAuthorizationStatus = .authorized
    var requestAuthorizationCount = 0
    var lastSetSchedule: (enabled: Bool, hour: Int, tone: ToneMode, suppressUntil: Date?)?
    var setScheduleCount = 0
    var cancelAllCount = 0

    func setStubAuthorizationStatus(_ status: UNAuthorizationStatus) {
        stubAuthorizationStatus = status
    }

    func requestAuthorization() async -> Bool {
        requestAuthorizationCount += 1
        return stubAuthorizationStatus == .authorized
    }

    func currentAuthorizationStatus() async -> UNAuthorizationStatus {
        stubAuthorizationStatus
    }

    nonisolated func installForegroundDelegate() {
        installTracker.increment()
    }

    func setSchedule(
        enabled: Bool,
        hour: Int,
        tone: ToneMode,
        suppressUntil: Date?,
        calendar: Calendar
    ) async {
        setScheduleCount += 1
        lastSetSchedule = (enabled, hour, tone, suppressUntil)
    }

    func cancelAll() async {
        cancelAllCount += 1
    }
}

@MainActor
final class LifeClockStoreTests: XCTestCase {
    private let fixedDate = Date(timeIntervalSince1970: 1_800_000_000)

    private func makeStore(seed: UInt64 = 42, simulateNoData: Bool = false) throws -> LifeClockStore {
        let container = try LifeClockContainer.make(inMemory: true)
        return LifeClockStore(
            healthService: MockHealthKitService(seed: seed, simulateNoData: simulateNoData),
            modelContext: container.mainContext,
            engineClock: .fixed(fixedDate)
        )
    }

    private func makeStoreWithNotifications(seed: UInt64 = 42)
        throws -> (store: LifeClockStore, notifications: MockNotificationsService)
    {
        let container = try LifeClockContainer.make(inMemory: true)
        let mock = MockNotificationsService()
        let store = LifeClockStore(
            healthService: MockHealthKitService(seed: seed),
            modelContext: container.mainContext,
            engineClock: .fixed(fixedDate),
            notificationsService: mock
        )
        return (store, mock)
    }

    func testBootstrapPopulatesEstimateAndQuests() async throws {
        let store = try makeStore()

        // First-launch path: no profile yet.
        await store.bootstrap()
        XCTAssertNil(store.profile, "bootstrap should not seed a profile when none persisted — onboarding does that")
    }

    func testCompleteOnboardingPersistsProfile() async throws {
        let store = try makeStore()
        let profile = UserProfile(birthDate: Date(timeIntervalSince1970: 631_152_000), biologicalSex: "female")
        store.completeOnboarding(profile: profile, tone: .gentle, disclaimerAccepted: true)

        XCTAssertNotNil(store.profile)
        XCTAssertTrue(store.hasCompletedOnboarding)
        XCTAssertEqual(store.toneMode, .gentle)

        // Refresh now has a profile to anchor on.
        await store.refreshFromHealthKit()
        XCTAssertNotNil(store.todayEstimate)
        XCTAssertGreaterThanOrEqual(store.todayQuests.count, 1)
        XCTAssertLessThanOrEqual(store.todayQuests.count, 3)
    }

    func testSetBodyMetricsPersistsCanonicalMetricValues() async throws {
        let store = try makeStore()
        let profile = UserProfile(birthDate: Date(timeIntervalSince1970: 631_152_000), biologicalSex: "female")
        store.completeOnboarding(profile: profile, tone: .coach, disclaimerAccepted: true)

        store.setBodyMetrics(heightCm: 180.34, weightKg: 81.65)

        XCTAssertEqual(store.profile?.heightCm, 180.34)
        XCTAssertEqual(store.profile?.weightKg, 81.65)

        store.setBodyMetrics(heightCm: nil, weightKg: nil)
        XCTAssertNil(store.profile?.heightCm)
        XCTAssertNil(store.profile?.weightKg)
    }

    func testColdRestartLoadsPersistedProfile() async throws {
        let container = try LifeClockContainer.make(inMemory: true)
        let context = container.mainContext

        // Session 1: complete onboarding.
        do {
            let store = LifeClockStore(
                healthService: MockHealthKitService(),
                modelContext: context,
                engineClock: .fixed(fixedDate)
            )
            store.completeOnboarding(
                profile: UserProfile(birthDate: Date(timeIntervalSince1970: 631_152_000), biologicalSex: "male"),
                tone: .coach,
                disclaimerAccepted: true
            )
        }

        // Session 2: fresh store reading from the same persistent container.
        let store2 = LifeClockStore(
            healthService: MockHealthKitService(),
            modelContext: context,
            engineClock: .fixed(fixedDate)
        )
        await store2.bootstrap()
        XCTAssertNotNil(store2.profile, "second session should restore the persisted profile")
        XCTAssertTrue(store2.hasCompletedOnboarding)
    }

    func testQuestCompletionAddsLedgerEntryStampedAtPinnedClock() async throws {
        let store = try makeStore(seed: 7)
        let profile = UserProfile(birthDate: Date(timeIntervalSince1970: 631_152_000), biologicalSex: "female")
        store.completeOnboarding(profile: profile, tone: .coach, disclaimerAccepted: true)
        await store.refreshFromHealthKit()

        let initialLedger = store.ledger.count
        guard let first = store.todayQuests.first else {
            XCTFail("expected at least one quest")
            return
        }
        store.toggleQuestCompletion(first)
        XCTAssertEqual(first.completedAt, fixedDate, "completedAt should use the injected clock, not Date()")
        XCTAssertEqual(store.ledger.count, initialLedger + 1)
        XCTAssertEqual(store.supportMoment?.title, "Nice work.")
    }

    func testQuestUndoRemovesLedgerEntryAndCompletionState() async throws {
        let store = try makeStore(seed: 7)
        let profile = UserProfile(birthDate: Date(timeIntervalSince1970: 631_152_000), biologicalSex: "female")
        store.completeOnboarding(profile: profile, tone: .coach, disclaimerAccepted: true)
        await store.refreshFromHealthKit()

        guard let first = store.todayQuests.first else {
            XCTFail("expected at least one action")
            return
        }

        store.toggleQuestCompletion(first)
        XCTAssertEqual(store.ledger.count, 1)

        store.toggleQuestCompletion(first)
        XCTAssertNil(first.completedAt)
        XCTAssertTrue(store.ledger.isEmpty, "undo should remove the manual progress entry it created")
        XCTAssertEqual(store.supportMoment?.title, "Action removed.")
    }

    func testCompletedPlanRestoresAcrossColdRestart() async throws {
        let container = try LifeClockContainer.make(inMemory: true)
        let context = container.mainContext
        let mockHealth = MockHealthKitService(seed: 11)

        let completedTitle: String
        do {
            let store = LifeClockStore(
                healthService: mockHealth,
                modelContext: context,
                engineClock: .fixed(fixedDate)
            )
            let profile = UserProfile(birthDate: Date(timeIntervalSince1970: 631_152_000), biologicalSex: "female")
            store.completeOnboarding(profile: profile, tone: .coach, disclaimerAccepted: true)
            await store.refreshFromHealthKit()
            guard let first = store.todayQuests.first else {
                XCTFail("expected at least one action")
                return
            }
            completedTitle = first.title
            store.toggleQuestCompletion(first)
            XCTAssertEqual(store.completedPlanCount, 1)
        }

        let store2 = LifeClockStore(
            healthService: mockHealth,
            modelContext: context,
            engineClock: .fixed(fixedDate)
        )
        await store2.bootstrap()

        XCTAssertEqual(store2.completedPlanCount, 1, "completed actions should survive refresh and cold restart")
        XCTAssertTrue(
            store2.todayQuests.contains { $0.title == completedTitle && $0.completedAt == fixedDate },
            "the regenerated plan should restore completion state for the matching action"
        )
    }

    /// Regression guard for todo 026: completion state must persist when a
    /// quest's display title changes between sessions. Identity is the slug,
    /// not the title.
    func testQuestCompletionSurvivesTitleRename() async throws {
        let container = try LifeClockContainer.make(inMemory: true)
        let context = container.mainContext
        // Sleep quest is always emitted (movement quest can be nil when steps already met).
        let slug = "sleep.consistency.v1"

        // Session 1: persist a Quest manually with the engine's slug, complete it.
        let store = LifeClockStore(
            healthService: MockHealthKitService(seed: 7),
            modelContext: context,
            engineClock: .fixed(fixedDate)
        )
        let profile = UserProfile(birthDate: Date(timeIntervalSince1970: 631_152_000), biologicalSex: "female")
        store.completeOnboarding(profile: profile, tone: .coach, disclaimerAccepted: true)
        await store.refreshFromHealthKit()
        guard let sleepQuest = store.todayQuests.first(where: { $0.slug == slug }) else {
            XCTFail("expected an emitted quest with slug \(slug); got slugs \(store.todayQuests.map(\.slug))")
            return
        }
        store.toggleQuestCompletion(sleepQuest)
        XCTAssertEqual(store.completedPlanCount, 1)

        // Simulate a copy edit: the persisted Quest row keeps the slug but
        // the display title diverges from a future engine emission.
        let descriptor = FetchDescriptor<Quest>(predicate: #Predicate { $0.slug == slug })
        guard let stored = try context.fetch(descriptor).first else {
            XCTFail("expected the persisted Quest to exist after completion")
            return
        }
        stored.title = "Old original title (different from current engine output)"
        try context.save()

        // Session 2: fresh store; engine emits the slug with current title;
        // applyPersistedCompletions should still restore completedAt.
        let store2 = LifeClockStore(
            healthService: MockHealthKitService(seed: 7),
            modelContext: context,
            engineClock: .fixed(fixedDate)
        )
        await store2.bootstrap()
        XCTAssertEqual(store2.completedPlanCount, 1, "title drift must not orphan slug-keyed completion state")
        XCTAssertTrue(
            store2.todayQuests.contains { $0.slug == slug && $0.completedAt != nil },
            "regenerated quest with the original slug should still show completedAt"
        )
    }

    /// Phase 3.A: legacy "memento_mori" rawValue (from before the case was
    /// removed) decodes to .coach, never crashes.
    func testToneModeFromStoredLegacyValueFallsBack() {
        XCTAssertEqual(ToneMode.fromStored("gentle"), .gentle)
        XCTAssertEqual(ToneMode.fromStored("coach"), .coach)
        XCTAssertEqual(ToneMode.fromStored("memento_mori"), .coach,
                       "legacy stored rawValue must decode to .coach without crashing")
        XCTAssertEqual(ToneMode.fromStored(""), .coach)
        XCTAssertEqual(ToneMode.fromStored("garbage"), .coach)
    }

    func testSetTodayHabitsUpsertsByDate() async throws {
        let store = try makeStore()
        let profile = UserProfile(birthDate: Date(timeIntervalSince1970: 631_152_000), biologicalSex: "female")
        store.completeOnboarding(profile: profile, tone: .coach, disclaimerAccepted: true)

        let habits1 = HabitLog(date: fixedDate)
        habits1.alcoholLevel = "heavy"
        await store.setTodayHabits(habits1)
        XCTAssertEqual(store.todayHabits?.alcoholLevel, "heavy")

        // Second call with same date should upsert, not create a duplicate.
        let habits2 = HabitLog(date: fixedDate)
        habits2.alcoholLevel = "none"
        habits2.smokingVaping = true
        await store.setTodayHabits(habits2)
        XCTAssertEqual(store.todayHabits?.alcoholLevel, "none")
        XCTAssertEqual(store.todayHabits?.smokingVaping, true)
    }

    func testSetPalettePersistsAndRestoresAcrossColdRestart() async throws {
        let container = try LifeClockContainer.make(inMemory: true)
        let context = container.mainContext

        // Session 1: onboard, switch palette to aurora-cool.
        do {
            let store = LifeClockStore(
                healthService: MockHealthKitService(),
                modelContext: context,
                engineClock: .fixed(fixedDate)
            )
            store.completeOnboarding(
                profile: UserProfile(birthDate: Date(timeIntervalSince1970: 631_152_000), biologicalSex: "female"),
                tone: .coach,
                disclaimerAccepted: true
            )
            store.setPalette(.auroraCool)
            XCTAssertEqual(store.palette, .auroraCool)
            XCTAssertEqual(store.profile?.paletteId, "aurora-cool")
        }

        // Session 2: fresh store on the same container — palette must restore.
        let store2 = LifeClockStore(
            healthService: MockHealthKitService(),
            modelContext: context,
            engineClock: .fixed(fixedDate)
        )
        await store2.bootstrap()
        XCTAssertEqual(store2.palette, .auroraCool, "palette must survive cold restart")
    }

    func testBootstrapFallsBackToDefaultNavyForUnknownPaletteId() async throws {
        let container = try LifeClockContainer.make(inMemory: true)
        let context = container.mainContext

        // Session 1: onboard, then tamper paletteId on the persisted row.
        let profile = UserProfile(birthDate: Date(timeIntervalSince1970: 631_152_000), biologicalSex: "male")
        do {
            let store = LifeClockStore(
                healthService: MockHealthKitService(),
                modelContext: context,
                engineClock: .fixed(fixedDate)
            )
            store.completeOnboarding(profile: profile, tone: .coach, disclaimerAccepted: true)
            profile.paletteId = "ghost"
            try? context.save()
        }

        // Session 2: fresh store must fall back to default-navy without crashing.
        let store2 = LifeClockStore(
            healthService: MockHealthKitService(),
            modelContext: context,
            engineClock: .fixed(fixedDate)
        )
        await store2.bootstrap()
        XCTAssertEqual(store2.palette, .defaultNavy, "unknown paletteId must fall back to default-navy")
    }

    func testResetForOnboardingRestoresDefaultPalette() async throws {
        let store = try makeStore()
        let profile = UserProfile(birthDate: Date(timeIntervalSince1970: 631_152_000), biologicalSex: "female")
        store.completeOnboarding(profile: profile, tone: .coach, disclaimerAccepted: true)
        store.setPalette(.sunsetWarm)
        XCTAssertEqual(store.palette, .sunsetWarm)

        store.resetForOnboarding()
        XCTAssertEqual(store.palette, .defaultNavy, "reset must restore the default palette so a new onboarding starts clean")
    }

    // MARK: - Daily reminder notifications

    func testSetDailyReminderClampsAndSchedules() async throws {
        let (store, mock) = try makeStoreWithNotifications()
        let profile = UserProfile(birthDate: Date(timeIntervalSince1970: 631_152_000), biologicalSex: "female")
        store.completeOnboarding(profile: profile, tone: .coach, disclaimerAccepted: true)
        await store.bootstrap()  // sets notificationAuthorizationStatus from mock = .authorized

        // Out-of-range hour should be clamped to 22.
        await store.setDailyReminder(enabled: true, hour: 25)
        XCTAssertEqual(profile.dailyReminderEnabled, true)
        XCTAssertEqual(profile.dailyReminderHour, 22, "hour must clamp to 22 (max quiet-hour bound)")

        let lastSchedule = await mock.lastSetSchedule
        XCTAssertEqual(lastSchedule?.enabled, true)
        XCTAssertEqual(lastSchedule?.hour, 22)
        XCTAssertEqual(lastSchedule?.tone, .coach)

        // Hour below quiet-window must clamp to 8.
        await store.setDailyReminder(enabled: true, hour: 3)
        XCTAssertEqual(profile.dailyReminderHour, 8, "hour must clamp to 8 (min quiet-hour bound)")
    }

    /// Regression: morning-log must suppress today's reminder fire.
    /// fixedDate is 2027-01-15 ~21:20 UTC — late evening in UTC. The
    /// dailyReminderHour 20 is interpreted in the device calendar
    /// (engineClock.calendar = .lifeClockUTC), so today's 20:00 fire
    /// has already passed at fixed time → no suppression-one-shot
    /// needed. Use a smaller hour (well before fixed-time) to exercise
    /// the suppression path. We verify the wiring by setting hour to a
    /// value still in the future relative to fixedDate.
    func testSetTodayHabitsRecordsSuppressionAndReconciles() async throws {
        // Use an EARLY-day fixed date so reminderHour > now.
        let earlyMorning = Date(timeIntervalSince1970: 1_736_924_400) // 2025-01-15 07:00 UTC
        let container = try LifeClockContainer.make(inMemory: true)
        let mock = MockNotificationsService()
        let store = LifeClockStore(
            healthService: MockHealthKitService(),
            modelContext: container.mainContext,
            engineClock: .fixed(earlyMorning),
            notificationsService: mock
        )
        let profile = UserProfile(birthDate: Date(timeIntervalSince1970: 631_152_000), biologicalSex: "female")
        store.completeOnboarding(profile: profile, tone: .coach, disclaimerAccepted: true)
        await store.bootstrap()
        await store.setDailyReminder(enabled: true, hour: 20)

        // Before logging: no suppression — schedule is plain repeating.
        var lastSchedule = await mock.lastSetSchedule
        XCTAssertNil(lastSchedule?.suppressUntil, "before logging, schedule must be plain repeating (no suppressUntil)")

        // Log habits at 7 AM (well before 8 PM reminder).
        let habits = HabitLog(date: earlyMorning)
        habits.dietQuality = "great"
        await store.setTodayHabits(habits)

        // After logging: suppressUntil must be set to tomorrow's 20:00.
        XCTAssertNotNil(profile.lastSuppressedDate, "setTodayHabits must record lastSuppressedDate")
        lastSchedule = await mock.lastSetSchedule
        XCTAssertNotNil(lastSchedule?.suppressUntil, "morning-log must trigger suppressUntil — closes #026 bug")
    }

    func testEveningLogDoesNotTriggerSuppressionPath() async throws {
        // fixedDate is 2027-01-15 ~21:20 UTC — past 20:00. Today's
        // reminder hour has already lapsed; reconcile should install
        // the plain repeating trigger (no suppressUntil) because iOS
        // will naturally fire next at tomorrow 20:00.
        let (store, mock) = try makeStoreWithNotifications()
        let profile = UserProfile(birthDate: Date(timeIntervalSince1970: 631_152_000), biologicalSex: "female")
        store.completeOnboarding(profile: profile, tone: .coach, disclaimerAccepted: true)
        await store.bootstrap()
        await store.setDailyReminder(enabled: true, hour: 20)

        let habits = HabitLog(date: fixedDate)
        habits.dietQuality = "great"
        await store.setTodayHabits(habits)

        let lastSchedule = await mock.lastSetSchedule
        XCTAssertNil(lastSchedule?.suppressUntil, "evening log (after reminder hour) must not need a one-shot suppression")
    }

    func testReconcileCancelsAllWhenAnyDisablingPathFires() async throws {
        let (store, mock) = try makeStoreWithNotifications()
        let profile = UserProfile(birthDate: Date(timeIntervalSince1970: 631_152_000), biologicalSex: "female")
        store.completeOnboarding(profile: profile, tone: .coach, disclaimerAccepted: true)
        await store.bootstrap()
        await store.setDailyReminder(enabled: true, hour: 20)

        // Path 1: hideClock=true must drop the schedule.
        var beforeCount = await mock.cancelAllCount
        await store.setHideClock(true)
        var afterCount = await mock.cancelAllCount
        XCTAssertGreaterThan(afterCount, beforeCount, "setHideClock(true) must reconcile to cancelAll")

        // Restore so subsequent checks start clean.
        await store.setHideClock(false)

        // Path 2: explicit disable.
        beforeCount = await mock.cancelAllCount
        await store.setDailyReminder(enabled: false, hour: 20)
        afterCount = await mock.cancelAllCount
        XCTAssertGreaterThan(afterCount, beforeCount, "setDailyReminder(enabled: false) must reconcile to cancelAll")

        // Path 3: auth flips to .denied via refresh.
        await store.setDailyReminder(enabled: true, hour: 20)
        await mock.setStubAuthorizationStatus(.denied)
        beforeCount = await mock.cancelAllCount
        await store.refreshNotificationAuthorization()
        afterCount = await mock.cancelAllCount
        XCTAssertGreaterThan(afterCount, beforeCount, "auth=.denied refresh must reconcile to cancelAll")
        XCTAssertEqual(profile.dailyReminderEnabled, true,
                       "user intent (toggle on) must be preserved even when iOS auth flips")
    }

    func testSetDailyReminderNoOpsWithoutProfile() async throws {
        let (store, mock) = try makeStoreWithNotifications()
        XCTAssertNil(store.profile, "precondition: no profile yet")

        let setBefore = await mock.setScheduleCount
        let cancelBefore = await mock.cancelAllCount
        await store.setDailyReminder(enabled: true, hour: 20)
        let setAfter = await mock.setScheduleCount
        let cancelAfter = await mock.cancelAllCount

        XCTAssertEqual(setAfter, setBefore, "no-profile path must not schedule")
        XCTAssertEqual(cancelAfter, cancelBefore, "no-profile path must not cancel either — full no-op")
    }

    /// Regression guard — a future refactor that drops the
    /// `installForegroundDelegate()` call from `LifeClockApp.init` would
    /// silently regress foreground-banner behavior. We simulate the same
    /// install pattern here to pin the contract.
    func testInstallForegroundDelegateIsCallable() async throws {
        let mock = MockNotificationsService()
        XCTAssertEqual(mock.installTracker.count, 0)
        mock.installForegroundDelegate()
        XCTAssertEqual(mock.installTracker.count, 1)
    }

    func testCompleteOnboardingRejectsUnacceptedDisclaimer() async throws {
        let store = try makeStore()
        let profile = UserProfile(birthDate: Date(timeIntervalSince1970: 631_152_000), biologicalSex: "female")

        let accepted = store.completeOnboarding(profile: profile, tone: .coach, disclaimerAccepted: false)
        XCTAssertFalse(accepted, "store must refuse to mark onboarding complete without disclaimer acceptance")
        XCTAssertNil(store.profile, "no profile should be persisted on a refused acceptance")
        XCTAssertFalse(store.hasCompletedOnboarding)
    }

    func testClearTodayHabitsRemovesPersistedLog() async throws {
        let store = try makeStore()
        let profile = UserProfile(birthDate: Date(timeIntervalSince1970: 631_152_000), biologicalSex: "female")
        store.completeOnboarding(profile: profile, tone: .coach, disclaimerAccepted: true)

        let habits = HabitLog(date: fixedDate)
        habits.alcoholLevel = "heavy"
        await store.setTodayHabits(habits)
        XCTAssertNotNil(store.todayHabits)

        await store.clearTodayHabits()
        XCTAssertNil(store.todayHabits, "clearTodayHabits must drop the cached log")

        // And on a fresh store reading the same container, the row is gone.
        await store.bootstrap()
        XCTAssertNil(store.todayHabits, "clearTodayHabits must delete the persisted row, not just the cache")
    }

    func testResetForOnboardingClearsAllPersistedData() async throws {
        let store = try makeStore()
        let profile = UserProfile(birthDate: Date(timeIntervalSince1970: 631_152_000), biologicalSex: "female")
        store.completeOnboarding(profile: profile, tone: .coach, disclaimerAccepted: true)
        XCTAssertNotNil(store.profile)

        store.resetForOnboarding()
        XCTAssertNil(store.profile)
        XCTAssertFalse(store.hasCompletedOnboarding)
    }

    // MARK: - Wrap-up sequencing

    /// Regression guard for the polish session
    /// `polish-2026-05-06-wrapup-sequencing-foreground-cycles`.
    ///
    /// Before the fix, `markWrapUpShown` cleared `pendingWrapUp = nil` but
    /// did not recompute, so a queued sibling (weekly after yesterday on a
    /// Monday return) was silently dropped until the next foreground cycle.
    /// This test pins the in-session sequencing contract: yesterday wins
    /// first, dismissing it triggers a recompute, weekly fires next.
    func testMarkWrapUpShownSequencesSiblingsInSameSession() async throws {
        // 2027-01-18 is a Monday (UTC). firstWeekday=Monday → both pending.
        // Match EngineClock.fixed's UTC calendar so day-keys align with
        // what WrapUpCoordinator queries.
        let monday = Date(timeIntervalSince1970: 1_768_780_800)
        var calendar = Calendar(identifier: .gregorian)
        calendar.timeZone = TimeZone(identifier: "UTC")!
        let yesterday = calendar.date(byAdding: .day, value: -1, to: monday)!
        let weekStart = calendar.date(byAdding: .day, value: -7, to: monday)!
        let onboarded = calendar.date(byAdding: .day, value: -30, to: monday)!

        let container = try LifeClockContainer.make(inMemory: true)
        let context = container.mainContext

        // Seed a returning user, yesterday snapshot with data, prior-week
        // report. Mirrors what the seed harness writes for
        // `LIFECLOCK_SEED_STREAK > 0`.
        let profile = UserProfile(
            birthDate: Date(timeIntervalSince1970: 631_152_000),
            biologicalSex: "female",
            toneMode: ToneMode.coach.rawValue
        )
        profile.onboardingCompletedAt = onboarded
        context.insert(profile)

        let yesterdaySnapshot = DailyHealthSnapshot(date: calendar.startOfDay(for: yesterday))
        yesterdaySnapshot.stepCount = 8_400
        yesterdaySnapshot.exerciseMinutes = 32
        yesterdaySnapshot.sleepHours = 7.4
        yesterdaySnapshot.activeEnergyKcal = 410
        yesterdaySnapshot.sourceCompleteness = 0.8
        context.insert(yesterdaySnapshot)

        let weekEnd = calendar.date(byAdding: .day, value: 6, to: weekStart)!
        let report = WeeklyReport(weekStart: weekStart, weekEnd: weekEnd)
        context.insert(report)
        try? context.save()

        let store = LifeClockStore(
            healthService: MockHealthKitService(seed: 7),
            modelContext: context,
            engineClock: .fixed(monday)
        )
        await store.bootstrap()

        guard case .yesterday = store.pendingWrapUp else {
            XCTFail("expected yesterday wrap-up to win first, got \(String(describing: store.pendingWrapUp))")
            return
        }

        store.markWrapUpShown(store.pendingWrapUp!)

        // Sequencing contract: weekly takes the slot in the SAME launch,
        // without waiting for a scenePhase active transition.
        guard case .weekly(let resolved) = store.pendingWrapUp else {
            XCTFail(
                "expected weekly wrap-up to sequence in after yesterday dismissal, got \(String(describing: store.pendingWrapUp))"
            )
            return
        }
        XCTAssertEqual(
            calendar.startOfDay(for: resolved),
            calendar.startOfDay(for: weekStart)
        )

        // And dismissing weekly clears the slot — no third sibling lurking.
        store.markWrapUpShown(store.pendingWrapUp!)
        XCTAssertNil(store.pendingWrapUp, "no further siblings expected")
    }
}
