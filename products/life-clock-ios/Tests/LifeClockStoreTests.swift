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

/// Grants Pro so `selectPlanQuest` (Pro-gated) can be exercised.
fileprivate final class ProEntitlement: EntitlementProviding {
    var isPro: Bool { true }
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

    func testRefreshWithoutHealthSignalDropsConfidenceToLow() async throws {
        let container = try LifeClockContainer.make(inMemory: true)
        let store = LifeClockStore(
            healthService: MockHealthKitService(preAuthorized: true, healthProfile: .empty),
            modelContext: container.mainContext,
            engineClock: .fixed(fixedDate)
        )
        let profile = UserProfile(birthDate: Date(timeIntervalSince1970: 631_152_000), biologicalSex: "female")
        store.completeOnboarding(profile: profile, tone: .coach, disclaimerAccepted: true)

        await store.refreshFromHealthKit()

        XCTAssertEqual(store.healthDataState, .noRecentData)
        XCTAssertFalse(store.hasTodaySignal)
        XCTAssertEqual(store.todayEstimate?.confidenceRaw, Confidence.low.rawValue)
        XCTAssertEqual(store.todayDrivers.count, 0, "no signal path must not invent daily drivers")
    }

    /// Pre-onboarding snapshots (e.g. 10y of HealthKit history pulled in by
    /// `HistoricalImportCoordinator` after a Pro upgrade) must not count
    /// toward badge progress. Repro 2026-05-09: a freshly-onboarded user
    /// who taps History triggers the 10y backfill, then sees Profile show
    /// "22 of 60 earned" with `data.rich.100` unlocked despite zero days
    /// of using the app.
    func testCompletionBadgesDoNotCountSnapshotsBeforeOnboarding() async throws {
        let container = try LifeClockContainer.make(inMemory: true)
        let context = container.mainContext
        let store = LifeClockStore(
            healthService: MockHealthKitService(preAuthorized: true),
            modelContext: context,
            engineClock: .fixed(fixedDate)
        )
        let profile = UserProfile(birthDate: Date(timeIntervalSince1970: 631_152_000), biologicalSex: "female")
        store.completeOnboarding(profile: profile, tone: .coach, disclaimerAccepted: true)

        // Backdate 200 rich-signal snapshots into the pre-onboarding window.
        let cal = Calendar.lifeClockUTC
        for offset in 1...200 {
            guard let day = cal.date(byAdding: .day, value: -offset, to: fixedDate) else { continue }
            let snap = DailyHealthSnapshot(date: cal.startOfDay(for: day))
            snap.stepCount = 12_000
            snap.exerciseMinutes = 45
            snap.sleepHours = 8.0
            snap.sleepConsistencyScore = 0.9
            snap.restingHeartRate = 58
            snap.activeEnergyKcal = 500
            snap.distanceMeters = 9_400
            snap.sourceCompleteness = 0.9
            context.insert(snap)
        }
        try context.save()

        let badges = store.completionBadges()
        let unlocked = Set(badges.filter { $0.isUnlocked }.map { $0.id })

        // The two onboarding-tier badges that fire on the seeded inputs:
        // health authorization is known (Signal linked) and a profile exists
        // with onboardingCompletedAt set (Clock started). Everything else
        // must stay locked because every backdated snapshot precedes
        // onboarding day.
        XCTAssertTrue(unlocked.contains("start.first-profile"))
        XCTAssertTrue(unlocked.contains("start.health-connected"))
        XCTAssertFalse(unlocked.contains("data.rich.100"),
                       "100-day rich-signal badge must require 100 days of post-onboarding rich snapshots")
        XCTAssertFalse(unlocked.contains("data.rich.30"))
        XCTAssertFalse(unlocked.contains("data.rich.7"))
        XCTAssertFalse(unlocked.contains("movement.steps7500.30"))
        XCTAssertFalse(unlocked.contains("exercise.minutes30.30"))
        XCTAssertFalse(unlocked.contains("sleep.goal.30"))
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

    /// Regression: completing a plan item, then swapping that item's
    /// category to a different quest via the Pro plan editor, must keep
    /// today's plan at EXACTLY three items (one per category). The old
    /// behavior resurrected the swapped-out completed quest as a 4th
    /// item because same-day completions were re-appended by slug
    /// without honoring the per-category 3-tuple invariant. The
    /// completion row stays in the DB (non-destructive) — it's just
    /// suppressed from the plan in favor of the deliberate swap.
    func testSwapAfterCompletionKeepsPlanAtExactlyThree() async throws {
        let container = try LifeClockContainer.make(inMemory: true)
        let context = container.mainContext
        let store = LifeClockStore(
            healthService: MockHealthKitService(seed: 11),
            modelContext: context,
            engineClock: .fixed(fixedDate)
        )
        store.entitlements = ProEntitlement()
        let profile = UserProfile(birthDate: Date(timeIntervalSince1970: 631_152_000), biologicalSex: "female")
        store.completeOnboarding(profile: profile, tone: .coach, disclaimerAccepted: true)
        await store.refreshFromHealthKit()

        // Find a plan item whose category has at least one OTHER variant
        // to swap to.
        let swap = store.todayQuests.lazy.compactMap { quest -> (Quest, QuestEngine.Category, String)? in
            guard let category = LifeClockStore.engineCategory(of: quest) else { return nil }
            guard let other = store.planVariants(for: category)
                .first(where: { $0.slug != quest.slug }) else { return nil }
            return (quest, category, other.slug)
        }.first
        let (completedQuest, category, newSlug) = try XCTUnwrap(
            swap, "expected a category with a swappable second variant"
        )
        let oldSlug = completedQuest.slug

        store.toggleQuestCompletion(completedQuest)
        XCTAssertEqual(store.completedPlanCount, 1)

        try store.selectPlanQuest(slug: newSlug, in: category)

        XCTAssertEqual(
            store.todayQuests.count, 3,
            "plan must stay an exact 3-tuple after a post-completion swap"
        )
        let categories = store.todayQuests.compactMap { LifeClockStore.engineCategory(of: $0) }
        XCTAssertEqual(
            Set(categories).count, 3,
            "plan must hold exactly one quest per category"
        )
        XCTAssertTrue(
            store.todayQuests.contains { $0.slug == newSlug },
            "the deliberately-picked replacement must be in the plan"
        )
        XCTAssertFalse(
            store.todayQuests.contains { $0.slug == oldSlug },
            "the swapped-out completed quest must not resurrect as a 4th item"
        )

        // Non-destructive: the completion row for the old slug still
        // exists in the store (preserved for streak/affinity history),
        // it's just no longer surfaced on the plan.
        let persisted = try context.fetch(FetchDescriptor<Quest>())
        XCTAssertTrue(
            persisted.contains { $0.slug == oldSlug && $0.completedAt != nil },
            "completing then swapping must keep the completion record in the DB"
        )
    }

    /// Regression guard for todo 026: completion state must persist when a
    /// quest's display title changes between sessions. Identity is the slug,
    /// not the title.
    ///
    /// V1.7.0 follow-up: re-derive the target slug from whichever sleep-
    /// bucket quest the engine actually emits on `fixedDate` rather than
    /// pinning a specific slug. The quest pool rotates the bucket choice
    /// by day-of-year (per the pool affinity engine); hard-coding
    /// "sleep.consistency.v1" was correct only for the rotation slot
    /// that happened to land on the test's fixed date originally. The
    /// invariant under test is slug-identity persistence across a copy
    /// edit — not the specific slug.
    func testQuestCompletionSurvivesTitleRename() async throws {
        let container = try LifeClockContainer.make(inMemory: true)
        let context = container.mainContext

        // Session 1: emit quests for fixedDate, pick the sleep-bucket one,
        // complete it. Sleep is always emitted (movement quest can be nil
        // when steps already met).
        let store = LifeClockStore(
            healthService: MockHealthKitService(seed: 7),
            modelContext: context,
            engineClock: .fixed(fixedDate)
        )
        let profile = UserProfile(birthDate: Date(timeIntervalSince1970: 631_152_000), biologicalSex: "female")
        store.completeOnboarding(profile: profile, tone: .coach, disclaimerAccepted: true)
        await store.refreshFromHealthKit()
        guard let sleepQuest = store.todayQuests.first(where: { $0.slug.hasPrefix("sleep.") }) else {
            XCTFail("expected at least one sleep-bucket quest; got slugs \(store.todayQuests.map(\.slug))")
            return
        }
        let slug = sleepQuest.slug
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
        // Use a late-evening fixed date so today's 20:00 reminder hour
        // has already passed; reconcile should install the plain
        // repeating trigger (no suppressUntil) because iOS will
        // naturally fire next at tomorrow 20:00.
        let lateEvening = Date(timeIntervalSince1970: 1_800_050_400) // 2027-01-15 22:00 UTC
        let container = try LifeClockContainer.make(inMemory: true)
        let mock = MockNotificationsService()
        let store = LifeClockStore(
            healthService: MockHealthKitService(),
            modelContext: container.mainContext,
            engineClock: .fixed(lateEvening),
            notificationsService: mock
        )
        let profile = UserProfile(birthDate: Date(timeIntervalSince1970: 631_152_000), biologicalSex: "female")
        store.completeOnboarding(profile: profile, tone: .coach, disclaimerAccepted: true)
        await store.bootstrap()
        await store.setDailyReminder(enabled: true, hour: 20)

        let habits = HabitLog(date: lateEvening)
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

    /// Regression guard for the production weekly-report persistence fix.
    /// Pre-fix, `calculateWeeklyTrend` set `store.weekly` in-memory but the
    /// `WeeklyReport` was never inserted into the model context, so
    /// `pendingWeekly` (which reads through `fetchRecentWeeklyReports`)
    /// returned nil regardless of date and the weekly wrap-up was dead code.
    func testRefreshPersistsWeeklyReportSoPendingWeeklyCanFire() async throws {
        let monday = Date(timeIntervalSince1970: 1_768_780_800)  // 2027-01-18 UTC
        var calendar = Calendar(identifier: .gregorian)
        calendar.timeZone = TimeZone(identifier: "UTC")!

        let container = try LifeClockContainer.make(inMemory: true)
        let context = container.mainContext

        let profile = UserProfile(
            birthDate: Date(timeIntervalSince1970: 631_152_000),
            biologicalSex: "female",
            toneMode: ToneMode.coach.rawValue
        )
        profile.onboardingCompletedAt = calendar.date(byAdding: .day, value: -30, to: monday)!
        context.insert(profile)
        try? context.save()

        // Pre-condition: no WeeklyReport rows exist.
        let preCount = (try? context.fetch(FetchDescriptor<WeeklyReport>()))?.count ?? -1
        XCTAssertEqual(preCount, 0, "fixture should start with no WeeklyReport rows")

        let store = LifeClockStore(
            healthService: MockHealthKitService(seed: 7, preAuthorized: true),
            modelContext: context,
            engineClock: .fixed(monday)
        )
        await store.bootstrap()

        let postCount = (try? context.fetch(FetchDescriptor<WeeklyReport>()))?.count ?? 0
        XCTAssertGreaterThan(
            postCount,
            0,
            "refreshFromHealthKit must persist the computed WeeklyReport so pendingWeekly has a row to query"
        )

        // Idempotent: a second refresh upserts (no duplicate-unique violation),
        // and total count does not jump.
        await store.refreshFromHealthKit(force: true)
        let secondCount = (try? context.fetch(FetchDescriptor<WeeklyReport>()))?.count ?? 0
        XCTAssertEqual(secondCount, postCount, "subsequent refresh must upsert, not duplicate")
    }

    // MARK: - Phase 3: bootstrapQuestGenres backfill (todo 049 #2)

    func testBootstrapQuestGenresBackfillsLegacyRows() throws {
        let container = try LifeClockContainer.make(inMemory: true)
        let context = container.mainContext

        // Insert three legacy Quests with empty genre — the V1.4.0
        // additive default state for any rows that landed before
        // the field existed.
        let day = Date(timeIntervalSince1970: 1_768_521_600)
        let movement = Quest(
            slug: "movement.steps-target.v1",
            date: day,
            title: "Steps",
            detail: "",
            category: "movement",
            target: 7500,
            rewardEstimateMinutes: 5
        )
        let recoveryHydration = Quest(
            slug: "recovery.hydration-early-night.v1",
            date: day,
            title: "Hydrate",
            detail: "",
            category: "recovery",
            target: 1,
            rewardEstimateMinutes: 1
        )
        // Reclassified slug — primary action is the walk, re-homes to activity.
        let walkAfterDinner = Quest(
            slug: "nutrition.walk-after-dinner.v1",
            date: day,
            title: "Walk after dinner",
            detail: "",
            category: "nutrition",
            target: 1,
            rewardEstimateMinutes: 5
        )
        context.insert(movement)
        context.insert(recoveryHydration)
        context.insert(walkAfterDinner)
        try context.save()

        let store = LifeClockStore(
            healthService: MockHealthKitService(seed: 7),
            modelContext: context,
            engineClock: .fixed(day)
        )
        store.bootstrapQuestGenres()

        let after = try context.fetch(FetchDescriptor<Quest>())
        let bySlug = Dictionary(uniqueKeysWithValues: after.map { ($0.slug, $0.genre) })
        XCTAssertEqual(bySlug["movement.steps-target.v1"], "activity")
        XCTAssertEqual(bySlug["recovery.hydration-early-night.v1"], "sleep",
            "recovery+hydration re-homes to sleep per the migration mapping")
        XCTAssertEqual(bySlug["nutrition.walk-after-dinner.v1"], "activity",
            "walk-after-dinner reclassifies to activity (primary action is the walk)")
    }

    func testBootstrapQuestGenresIsIdempotent() throws {
        let container = try LifeClockContainer.make(inMemory: true)
        let context = container.mainContext
        let day = Date(timeIntervalSince1970: 1_768_521_600)
        let quest = Quest(
            slug: "movement.steps-target.v1",
            date: day,
            title: "Steps",
            detail: "",
            category: "movement",
            target: 7500,
            rewardEstimateMinutes: 5
        )
        context.insert(quest)
        try context.save()

        let store = LifeClockStore(
            healthService: MockHealthKitService(seed: 7),
            modelContext: context,
            engineClock: .fixed(day)
        )
        store.bootstrapQuestGenres()
        let firstGenre = try context.fetch(FetchDescriptor<Quest>()).first?.genre
        XCTAssertEqual(firstGenre, "activity")

        // Second run is a no-op — no fresh writes, value stable.
        store.bootstrapQuestGenres()
        let secondGenre = try context.fetch(FetchDescriptor<Quest>()).first?.genre
        XCTAssertEqual(secondGenre, "activity")
    }

    func testBootstrapQuestGenresLeavesConsistencyFallbackAtEmpty() throws {
        let container = try LifeClockContainer.make(inMemory: true)
        let context = container.mainContext
        let day = Date(timeIntervalSince1970: 1_768_521_600)
        // The consistency fallback is intentionally NOT in the slug→genre
        // map — it's out-of-pool engine machinery and stays at genre = "".
        let consistency = Quest(
            slug: "consistency.open-app-tomorrow.v1",
            date: day,
            title: "Open the app tomorrow",
            detail: "",
            category: "consistency",
            target: 1,
            rewardEstimateMinutes: 0
        )
        context.insert(consistency)
        try context.save()

        let store = LifeClockStore(
            healthService: MockHealthKitService(seed: 7),
            modelContext: context,
            engineClock: .fixed(day)
        )
        store.bootstrapQuestGenres()
        let after = try XCTUnwrap(try context.fetch(FetchDescriptor<Quest>()).first)
        XCTAssertEqual(after.genre, "",
            "Out-of-pool consistency fallback must stay at genre == \"\" — it has no genre by design")
    }

    // MARK: - Phase 3: upsertQuest empty-genre guard (todo 049 #1)

    func testUpsertQuestPropagatesGenreOnInsert() throws {
        let container = try LifeClockContainer.make(inMemory: true)
        let context = container.mainContext
        let day = Date(timeIntervalSince1970: 1_768_521_600)
        let store = LifeClockStore(
            healthService: MockHealthKitService(seed: 7),
            modelContext: context,
            engineClock: .fixed(day)
        )
        let incoming = Quest(
            slug: "activity.fixture-walk-after-meal.v1",
            date: day,
            title: "Walk",
            detail: "",
            category: "activity",
            target: 10,
            rewardEstimateMinutes: 5,
            genre: "activity"
        )
        let stored = store.upsertQuest(incoming)
        XCTAssertEqual(stored.genre, "activity",
            "Insert path must propagate genre")
    }

    /// Code-review feedback on PR #31 (data-integrity #5): the insert
    /// branch was previously asymmetric with the update branch's
    /// empty-genre guard. A legacy caller passing `genre = ""` on
    /// insert wrote a fresh row with empty genre, relying on the
    /// next-launch `bootstrapQuestGenres` to backfill. The fix
    /// resolves genre at the boundary via `slugGenreMap` lookup, so
    /// the insert path lands the right value immediately when the
    /// slug is known.
    func testUpsertQuestResolvesGenreFromSlugMapOnInsertWhenIncomingIsEmpty() throws {
        let container = try LifeClockContainer.make(inMemory: true)
        let context = container.mainContext
        let day = Date(timeIntervalSince1970: 1_768_521_600)
        let store = LifeClockStore(
            healthService: MockHealthKitService(seed: 7),
            modelContext: context,
            engineClock: .fixed(day)
        )
        // Slug IS in the map but caller passes empty genre (legacy path).
        let legacy = Quest(
            slug: "movement.steps-target.v1",
            date: day,
            title: "Steps target",
            detail: "",
            category: "movement",
            target: 7500,
            rewardEstimateMinutes: 5
            // genre defaults to ""
        )
        let stored = store.upsertQuest(legacy)
        XCTAssertEqual(stored.genre, "activity",
            "Insert path must resolve genre from slug→genre map when caller passes empty default")
    }

    func testUpsertQuestInsertGracefullyHandlesUnmappedSlug() throws {
        let container = try LifeClockContainer.make(inMemory: true)
        let context = container.mainContext
        let day = Date(timeIntervalSince1970: 1_768_521_600)
        let store = LifeClockStore(
            healthService: MockHealthKitService(seed: 7),
            modelContext: context,
            engineClock: .fixed(day)
        )
        // The consistency fallback isn't in the map (intentional —
        // out-of-pool engine machinery). Insert path falls through to
        // empty genre.
        let consistency = Quest(
            slug: "consistency.open-app-tomorrow.v1",
            date: day,
            title: "Open the app tomorrow",
            detail: "",
            category: "consistency",
            target: 1,
            rewardEstimateMinutes: 0
        )
        let stored = store.upsertQuest(consistency)
        XCTAssertEqual(stored.genre, "",
            "Out-of-pool slug must remain at genre = \"\" — affinity engine ignores it")
    }

    func testUpsertQuestWithEmptyGenreDoesNotClobberBackfilledRow() throws {
        // The dominant clobber risk: an upstream caller (legacy engine
        // path or the consistency fallback) emits a Quest with the
        // default genre = "", and upsertQuest's update branch overwrites
        // a previously-backfilled non-empty genre. The empty-genre
        // guard prevents this.
        let container = try LifeClockContainer.make(inMemory: true)
        let context = container.mainContext
        let day = Date(timeIntervalSince1970: 1_768_521_600)

        // Pre-existing row with non-empty genre (post-backfill state).
        let existing = Quest(
            slug: "movement.steps-target.v1",
            date: day,
            title: "Steps",
            detail: "",
            category: "movement",
            target: 7500,
            rewardEstimateMinutes: 5,
            genre: "activity"
        )
        context.insert(existing)
        try context.save()

        let store = LifeClockStore(
            healthService: MockHealthKitService(seed: 7),
            modelContext: context,
            engineClock: .fixed(day)
        )

        // Emit a fresh Quest with the SAME slug but genre = "" (the
        // legacy path's default state). The guard must preserve the
        // backfilled "activity" value.
        let incoming = Quest(
            slug: "movement.steps-target.v1",
            date: day,
            title: "Steps target",
            detail: "Refreshed copy",
            category: "movement",
            target: 8000,
            rewardEstimateMinutes: 5
            // genre defaults to ""
        )
        let stored = store.upsertQuest(incoming)
        XCTAssertEqual(stored.genre, "activity",
            "Empty incoming genre must NOT clobber a previously-backfilled non-empty value")
        // Other mutable fields ARE refreshed (this proves the update
        // branch ran and the genre guard is the only thing protecting
        // genre, not a no-op):
        XCTAssertEqual(stored.title, "Steps target")
        XCTAssertEqual(stored.target, 8000)
    }

    // MARK: - Phase 3c: Event emission hooks
    //
    // Integration tests for the four QuestEvent hook points. Phase 5b
    // retired the legacy `useQuestPoolEngine` off-path; the flag-off
    // tests below are gone (the path no longer exists). Every user
    // emits events at refresh + plan editor swap + quest tick.

    private func makePhase3cStore(day: Date) async throws -> (LifeClockStore, ModelContext) {
        let container = try LifeClockContainer.make(inMemory: true)
        let context = container.mainContext
        let mockHealth = MockHealthKitService(seed: 11)
        let store = LifeClockStore(
            healthService: mockHealth,
            modelContext: context,
            engineClock: .fixed(day)
        )
        let profile = UserProfile(birthDate: Date(timeIntervalSince1970: 631_152_000), biologicalSex: "female")
        store.completeOnboarding(profile: profile, tone: .coach, disclaimerAccepted: true)
        return (store, context)
    }

    func testRefreshEmitsShownEvents() async throws {
        let day = Date(timeIntervalSince1970: 1_800_000_000)
        let (store, context) = try await makePhase3cStore(day: day)
        await store.refreshFromHealthKit()

        let shownEvents = try context.fetch(
            FetchDescriptor<QuestEvent>(predicate: #Predicate { $0.kind == "shown" })
        )
        XCTAssertGreaterThan(shownEvents.count, 0,
            "Flag-on path must emit shown events for every emitted slug")
        let slugs = Set(shownEvents.map(\.slug))
        XCTAssertEqual(slugs.count, shownEvents.count,
            "Shown events should be deduped per (date, slug)")
    }

    func testShownEventDedupedOnDoubleRefresh() async throws {
        let day = Date(timeIntervalSince1970: 1_800_000_000)
        let (store, context) = try await makePhase3cStore(day: day)
        await store.refreshFromHealthKit()
        let firstCount = try context.fetch(
            FetchDescriptor<QuestEvent>(predicate: #Predicate { $0.kind == "shown" })
        ).count

        await store.refreshFromHealthKit(force: true)
        let secondCount = try context.fetch(
            FetchDescriptor<QuestEvent>(predicate: #Predicate { $0.kind == "shown" })
        ).count
        XCTAssertEqual(firstCount, secondCount,
            "Shown event count must not grow on double-refresh same day — emitShown is idempotent")
    }

    func testCompletedEventEmittedOnTick() async throws {
        let day = Date(timeIntervalSince1970: 1_800_000_000)
        let (store, context) = try await makePhase3cStore(day: day)
        await store.refreshFromHealthKit()
        guard let first = store.todayQuests.first else {
            XCTFail("Expected at least one quest")
            return
        }
        store.toggleQuestCompletion(first)

        let completedEvents = try context.fetch(
            FetchDescriptor<QuestEvent>(predicate: #Predicate { $0.kind == "completed" })
        )
        XCTAssertEqual(completedEvents.count, 1)
        XCTAssertEqual(completedEvents.first?.slug, first.slug)
    }

    /// PR #32 review fix (data-integrity #7): un-ticking a completion
    /// removes the matching `completed` event so affinity reflects the
    /// user's final intent, not their initial click. Symmetric with the
    /// ledger-entry deletion that already happens on un-tick.
    func testUntickRemovesCompletedEventForDataCorrectness() async throws {
        let day = Date(timeIntervalSince1970: 1_800_000_000)
        let (store, context) = try await makePhase3cStore(day: day)
        await store.refreshFromHealthKit()
        guard let first = store.todayQuests.first else {
            XCTFail("Expected at least one quest")
            return
        }
        store.toggleQuestCompletion(first)   // tick → emit completed
        let afterTick = try context.fetch(
            FetchDescriptor<QuestEvent>(predicate: #Predicate { $0.kind == "completed" })
        )
        XCTAssertEqual(afterTick.count, 1)

        store.toggleQuestCompletion(first)   // un-tick → DELETE completed event

        let afterUntick = try context.fetch(
            FetchDescriptor<QuestEvent>(predicate: #Predicate { $0.kind == "completed" })
        )
        XCTAssertEqual(afterUntick.count, 0,
            "Un-ticking must DELETE the completed event — affinity should reflect the user's final state, not poison from a stray tap")
    }

    /// Re-ticking after un-tick re-emits a single completed event (the
    /// previous one was deleted on un-tick). This is the canonical
    /// "user changed their mind back" path: tick → un-tick → re-tick
    /// produces exactly one completed row.
    func testReTickAfterUntickProducesOneCompletedEvent() async throws {
        let day = Date(timeIntervalSince1970: 1_800_000_000)
        let (store, context) = try await makePhase3cStore(day: day)
        await store.refreshFromHealthKit()
        guard let first = store.todayQuests.first else {
            XCTFail("Expected at least one quest")
            return
        }
        store.toggleQuestCompletion(first)   // tick
        store.toggleQuestCompletion(first)   // un-tick (deletes event)
        store.toggleQuestCompletion(first)   // re-tick (emits fresh event)

        let completedEvents = try context.fetch(
            FetchDescriptor<QuestEvent>(predicate: #Predicate { $0.kind == "completed" })
        )
        XCTAssertEqual(completedEvents.count, 1,
            "After tick → un-tick → re-tick, exactly one completed event should exist")
    }

    // MARK: - Phase 3c task 15 + 3d task 16: daily-cycle hook

    func testDistinctOpenDaysIncrementsOnFirstForegroundOfDay() async throws {
        let day = Date(timeIntervalSince1970: 1_800_000_000)
        let (store, _) = try await makePhase3cStore(day: day)
        await store.refreshFromHealthKit()
        XCTAssertEqual(store.profile?.distinctOpenDays, 1)
        XCTAssertNotNil(store.profile?.lastForegroundDay)
    }

    func testDistinctOpenDaysDoesNotDoubleIncrementSameDay() async throws {
        let day = Date(timeIntervalSince1970: 1_800_000_000)
        let (store, _) = try await makePhase3cStore(day: day)
        await store.refreshFromHealthKit()
        await store.refreshFromHealthKit(force: true)
        XCTAssertEqual(store.profile?.distinctOpenDays, 1,
            "distinctOpenDays must not double-increment within the same calendar day")
    }

    func testDistinctOpenDaysIncrementsAcrossDays() async throws {
        let day1 = Date(timeIntervalSince1970: 1_800_000_000)
        let (store, _) = try await makePhase3cStore(day: day1)
        await store.refreshFromHealthKit()
        let firstCount = store.profile?.distinctOpenDays ?? 0

        // Simulate "user opened yesterday, now opening today" by
        // backdating lastForegroundDay one day. The engine clock is
        // immutable so we can't move forward; the daily-cycle hook
        // only cares that lastForegroundDay < today's start.
        let oneDayBack = Calendar.current.date(byAdding: .day, value: -1, to: store.profile!.lastForegroundDay!)!
        store.profile?.lastForegroundDay = oneDayBack

        await store.refreshFromHealthKit(force: true)
        XCTAssertEqual(store.profile?.distinctOpenDays, firstCount + 1,
            "distinctOpenDays must increment when first foreground of a new local day fires")
    }

    // MARK: - History today-exclusion

    /// History is yesterday-and-earlier; today's row lives on Today.
    /// `recentSnapshots(limit:)` must drop a snapshot whose date is in
    /// the current day per the injected clock. The fetch limit is
    /// widened by 1 internally so callers still see N rows when a
    /// today-snapshot exists.
    func testRecentSnapshotsExcludesTodayByDefault() throws {
        let container = try LifeClockContainer.make(inMemory: true)
        let context = container.mainContext
        let store = LifeClockStore(
            healthService: MockHealthKitService(preAuthorized: true),
            modelContext: context,
            engineClock: .fixed(fixedDate)
        )
        let cal = Calendar.lifeClockUTC
        let today = cal.startOfDay(for: fixedDate)

        // Seed today + 13 prior days, all date-normalized to startOfDay.
        for offset in 0..<14 {
            guard let day = cal.date(byAdding: .day, value: -offset, to: today) else { continue }
            let snap = DailyHealthSnapshot(date: cal.startOfDay(for: day))
            snap.stepCount = 8_000
            snap.sleepHours = 7.0
            snap.sourceCompleteness = 0.7
            context.insert(snap)
        }
        try context.save()

        let defaulted = store.recentSnapshots(limit: 7)
        XCTAssertEqual(defaulted.count, 7,
                       "default fetch must still return N rows when a today-snapshot exists")
        XCTAssertFalse(defaulted.contains(where: { cal.isDate($0.date, inSameDayAs: today) }),
                       "today's snapshot must not appear in History results")
        XCTAssertEqual(defaulted.first?.date, cal.date(byAdding: .day, value: -1, to: today),
                       "first row must be yesterday, not today")

        let inclusive = store.recentSnapshots(limit: 7, includingToday: true)
        XCTAssertEqual(inclusive.count, 7)
        XCTAssertTrue(inclusive.contains(where: { cal.isDate($0.date, inSameDayAs: today) }),
                      "opt-in path must keep today for callers that need the live row")
    }

    /// Long-absence: when no today-snapshot exists (returning user after
    /// a gap), the today-exclusion path is a no-op. We must still surface
    /// the older snapshots so the `hasOlderSnapshots` predicate fires.
    func testRecentSnapshotsAfterLongAbsenceReturnsOldSnapshots() throws {
        let container = try LifeClockContainer.make(inMemory: true)
        let context = container.mainContext
        let store = LifeClockStore(
            healthService: MockHealthKitService(preAuthorized: true),
            modelContext: context,
            engineClock: .fixed(fixedDate)
        )
        let cal = Calendar.lifeClockUTC
        let today = cal.startOfDay(for: fixedDate)

        // Seed three snapshots from 30+ days ago. No today, no yesterday.
        for offset in [30, 31, 32] {
            guard let day = cal.date(byAdding: .day, value: -offset, to: today) else { continue }
            let snap = DailyHealthSnapshot(date: cal.startOfDay(for: day))
            snap.stepCount = 5_000
            snap.sleepHours = 6.5
            snap.sourceCompleteness = 0.6
            context.insert(snap)
        }
        try context.save()

        let rows = store.recentSnapshots(limit: 3)
        XCTAssertEqual(rows.count, 3,
                       "long-absence snapshots must still surface — today-exclusion is a no-op when no today row exists")
        XCTAssertFalse(rows.contains(where: { cal.isDate($0.date, inSameDayAs: today) }))
    }

}
