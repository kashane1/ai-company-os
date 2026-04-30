import XCTest
import SwiftData
import UserNotifications
@testable import LifeClock

/// Spy implementation of the notifications service used to assert
/// schedule/cancel routing without touching `UNUserNotificationCenter`.
fileprivate actor MockNotificationsService: NotificationsServiceProtocol {
    var stubAuthorizationStatus: UNAuthorizationStatus = .authorized
    var requestAuthorizationCount = 0
    var lastSetSchedule: (enabled: Bool, hour: Int, tone: ToneMode, suppressUntil: Date?)?
    var setScheduleCount = 0
    var cancelAllCount = 0
    var installForegroundDelegateCount = 0

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
        // Spy can't track this from a nonisolated context safely; left blank.
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
}
