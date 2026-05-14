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
    enum HealthDataState: Equatable {
        case unavailable
        case awaitingAuthorization
        case availableToday
        case historicalOnly
        case noRecentData
    }

    var profile: UserProfile?
    var todayEstimate: LifeClockEstimate?
    var todayDrivers: [TimeLedgerEntry] = []
    var todayQuests: [Quest] = []
    /// One-shot per-day picks the user made via the Plan editor. Pro-only
    /// to write; cleared automatically when the in-memory dayKey doesn't
    /// match today. Persisted via UserDefaults so a relaunch within the
    /// same day preserves the user's picks.
    private(set) var todayPlanOverrides: TodayPlanOverrides = .empty
    /// In-memory mirror of recent ledger entries. The persisted source of
    /// truth is `TimeLedgerEntry` in SwiftData; this array is maintained
    /// on every write path (`toggleQuestCompletion`, `refreshFromHealthKit`,
    /// `bootstrap`) for fast access by `LifeClockStoreTests` /
    /// `LifeClockE2ETests` and as a hedge against re-introducing a debug
    /// surface. No production view reads it directly — Today reads
    /// `todayDrivers` (top 3, derived) and History reads through
    /// `snapshot(for:)` / `DayDetailView`. A future cleanup can refactor
    /// it to private + a `recentLedger(limit:)` accessor.
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
    var monthlyLogging: MonthlyLogging = .zero
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

    /// Today's saved reflection, if one exists. Re-published by
    /// `reloadTodayReflection()` after `bootstrap()` and after each
    /// `saveReflection(...)`. Reads through `todayReflection` instead
    /// of an inline `@Query` to keep the store-mediated invariant
    /// (one `@Query` site app-wide; everything else through the store).
    private(set) var todayReflection: DailyReflection?

    // MARK: - Future tab projection state (V1.7.0)
    //
    // Store-owned per the plan §Phase 4 architecture-strategist review
    // finding: trajectory cache + slider scrub coordination must NOT
    // leak into View `@State`. Views read these properties; the store
    // owns invalidation contracts. All access `@MainActor`.

    /// User-applied slider overrides during a what-if scrub. Empty
    /// `[:]` = personal-current values (slider at rest). Phase 4
    /// `WhatIfSlider.onOverridesChange` writes here; `FutureView`
    /// reads via @Observable to redraw the chart.
    var sliderOverrides: [HealthspanEngine.Dimension: Double] = [:]

    /// Memoized 14-day baseline aggregates captured on scrub-start.
    /// Reused for every `onChange` tick during a scrub so we don't
    /// re-fetch SwiftData per tick. Cleared 250ms after touch-end
    /// (debounced — rapid re-grabs within the window reuse it).
    /// Nil = not scrubbing or cache cleared.
    var cachedBaselineAggregates: [HealthspanEngine.Dimension: Double]?

    /// True while any slider is actively scrubbing. Drives the
    /// `.animation(nil, value:)` gate on the chart and the
    /// pending-refresh queue. Multi-touch supported via the counter
    /// (`activeScrubCount`); `isProjectionScrubbing` is true iff > 0.
    var isProjectionScrubbing: Bool { activeScrubCount > 0 }

    /// Count of in-flight slider scrubs. Multi-touch lets two fingers
    /// scrub independently; we hold the aggregate cache + animation
    /// gate until ALL release.
    private(set) var activeScrubCount: Int = 0

    /// Refresh ticks that arrived during a scrub. Cleared on flush;
    /// counter (not bool) so we can observe whether anything queued
    /// without losing edge cases.
    private(set) var pendingRefreshCount: Int = 0

    /// Monotonically-incrementing token. Bumped on every scrub-end so
    /// any pending debounced clear that fires AFTER a new scrub-start
    /// is a no-op (token mismatch ⇒ ignore).
    private var scrubEndToken: Int = 0

    /// Cross-tab navigation. The TodayView trajectory peek writes
    /// `.future` here; MainTabView binds its `TabView` selection to
    /// this property so any view can drive tab changes via the store.
    var selectedTab: AppTab = .today

    /// Personal-current healthspan projection — the same value the
    /// Future tab headline uses, recomputed in the store on every
    /// write path that can change it (HK refresh save, QuickLog,
    /// override apply/revert). Today's trajectory peek reads this
    /// instead of re-fetching + re-aggregating per render. Nil until
    /// the first refresh after a baseline is set.
    private(set) var currentHealthspanProjection: HealthspanEngine.Projection?

    private func emit(_ intent: SupportMomentPresenter.Intent) {
        supportMoment = supportPresenter.moment(for: intent, tone: toneMode)
    }

    var completedPlanCount: Int {
        todayQuests.filter { $0.completedAt != nil }.count
    }

    var hasCheckInToday: Bool {
        todayHabits != nil
    }

    /// Coarse UI-facing health state. The app never claims to know
    /// "denied" vs "empty" — only whether we can currently see signal.
    var healthDataState: HealthDataState {
        guard healthDataAvailable else { return .unavailable }
        guard healthAuthorizationKnown else { return .awaitingAuthorization }
        if hasTodaySignal { return .availableToday }
        if fetchRecentSnapshots(limit: 14).contains(where: { $0.sourceCompleteness > 0 }) {
            return .historicalOnly
        }
        return .noRecentData
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
    /// Strong reference to the context's container. Without this, callers
    /// that construct the container as a local in a helper (and only return
    /// the store wrapping `container.mainContext`) see the container
    /// deallocate when the helper returns. On iOS 26.4 simulator,
    /// `ModelContext` does not retain its `ModelContainer`, and the next
    /// `insert` / `save` traps with `EXC_BREAKPOINT` from inside SwiftData.
    /// Production (`LifeClockApp`) is unaffected because the App struct
    /// keeps the container in `let container: ModelContainer` for the
    /// app's lifetime; the failure mode bites tests only. Holding the
    /// container here defends every caller without changing the existing
    /// `init(modelContext:)` signature.
    @ObservationIgnored private let modelContainer: ModelContainer
    @ObservationIgnored private let monthlyLoggingCalculator: MonthlyLoggingCalculator
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
        self.modelContainer = modelContext.container
        self.clock = engineClock
        self.clockEngine = ClockEngine(clock: engineClock)
        self.questEngine = QuestEngine(clock: engineClock)
        self.monthlyLoggingCalculator = MonthlyLoggingCalculator(calendar: engineClock.calendar)
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
            // Restore one-shot plan picks if they're for today.
            loadTodayPlanOverrides()
            // Restore prior ledger entries (most recent first, capped at 50).
            ledger = fetchRecentLedger(limit: 50)
            // Restore today's reflection if the user wrote one earlier.
            reloadTodayReflection()
        }
        // V1.5.0: backfill `Quest.genre` for any persisted Quests that
        // landed before the field existed. Idempotent — subsequent runs
        // find no `genre == ""` rows and short-circuit. Safe to call on
        // every launch. Migration must complete before this runs;
        // SwiftData's ModelContainer init makes that the case.
        bootstrapQuestGenres()
        // V1.6.0 (Phase 5a): flip legacy `useQuestPoolEngine = false`
        // rows forward. Idempotent: subsequent launches find the flag
        // already true and short-circuit. Existing user upgrades hit
        // this once on the launch immediately after the V1.6.0 ship.
        bootstrapQuestPoolEngineFlag()
        // V1.7.0 (Phase 2): backfill `baselineHealthspanYears` for
        // existing onboarded users so the Future tab has its anchor
        // without re-running onboarding. Idempotent — once set the
        // method is a no-op. Sanity-checked.
        bootstrapV170Baseline()
        // `force: true` so a cold restart within the 5-minute fresh-snapshot
        // window still emits today's quest slate and applies persisted
        // completions. Otherwise the short-circuit at the top of
        // `refreshFromHealthKit` returns before `applyPersistedCompletions`
        // runs, leaving `todayQuests` empty on relaunch.
        await refreshFromHealthKit(force: true)
        notificationAuthorizationStatus = await notificationsService.currentAuthorizationStatus()
        await reconcileNotifications()
    }

    // MARK: - Quest genre backfill (V1.5.0)
    //
    // Maps legacy `Quest.slug` values to their corresponding `Genre.rawValue`.
    // Source of truth: the migration table in
    // docs/plans/2026-05-08-feat-quest-pool-affinity-engine-plan.md
    // (Migration Mapping section).
    //
    // The fallback `consistency.open-app-tomorrow.v1` slug intentionally
    // has no genre — it's out-of-pool engine machinery. Affinity
    // computation ignores events whose `genre` doesn't map to a known
    // `Genre`, so leaving it empty is safe.
    private static let slugGenreMap: [String: String] = [
        "movement.steps-target.v1":         "activity",
        "movement.walk-after-meal.v1":      "activity",
        "movement.stairs-instead.v1":       "activity",
        "sleep.consistency.v1":             "sleep",
        "sleep.wind-down.v1":               "sleep",
        "recovery.hydration-early-night.v1": "sleep",
        "nutrition.one-better-meal.v1":     "diet",
        "nutrition.log-diet-quality.v1":    "diet",
        "nutrition.whole-food-meal.v1":     "diet",
        // Reclassified per master plan: this slug's primary action is
        // the walk, not the meal — re-homes from "diet" to "activity".
        "nutrition.walk-after-dinner.v1":   "activity",
        "nutrition.water-with-meal.v1":     "diet",
        "nutrition.add-protein.v1":         "diet",
        "nutrition.eat-meal-slowly.v1":     "diet",
        "nutrition.less-processed.v1":      "diet",
    ]

    // MARK: - Phase 3c/3d helpers

    /// Phase 3d task 16 + 3c task 15: daily-cycle hook. On the first
    /// foreground of a new local-calendar day, run the EOD resolver
    /// (G23 invariant: BEFORE today's affinity read so yesterday's
    /// passed_over / abandoned events are visible to today's
    /// AffinityEngine.computeAffinities call). Then increment
    /// distinctOpenDays and update lastForegroundDay.
    ///
    /// DST safety (G25): `Calendar.current.startOfDay(for:)` correctly
    /// handles 25-hour and 23-hour days — single fire on either.
    /// Cross-midnight edge: if a user opens at 23:59 and again at
    /// 00:01, the second call sees a new dayStart and fires the
    /// daily-cycle hook (correct — yesterday is now over).
    private func runDailyCycleIfNewDay(profile: UserProfile, now: Date, dayStart: Date) {
        // Cheap guard: if it's still the same calendar day as the last
        // foreground, no work to do. Idempotent under repeated calls
        // within the same day.
        if let last = profile.lastForegroundDay, last >= dayStart {
            return
        }
        // Run EOD resolver first. Phase 5b: legacy path is gone, so this
        // always runs — every user is on the pool engine.
        try? QuestSelector.resolveEndOfDay(context: modelContext, today: now)
        // Then increment counter + update last-foreground marker.
        profile.distinctOpenDays += 1
        profile.lastForegroundDay = dayStart
        try? modelContext.save()
    }

    /// Bounded fetch of QuestEvent rows for AffinityEngine input.
    /// Phase 3 ships non-cached — incremental cache via
    /// `UserProfile.affinityState: Data` is deferred per master plan
    /// Out-of-Scope §1.
    ///
    /// Defensive `fetchLimit = 5000` (perf review on PR #32): year-3
    /// users at ~30k events would otherwise materialize ~6MB on
    /// every emit. EMA at α=0.2 has effective half-life ≈ 3 events
    /// per signal — events older than the most recent ~5000 contribute
    /// well under 0.001 to the result, so the cap is semantically safe.
    /// Sorted descending by date so the cap retains the freshest signal.
    private func fetchAllQuestEvents() -> [QuestEvent] {
        var descriptor = FetchDescriptor<QuestEvent>(
            sortBy: [SortDescriptor(\.date, order: .reverse)]
        )
        descriptor.fetchLimit = 5000
        return (try? modelContext.fetch(descriptor)) ?? []
    }

    /// Lazy QuestPool from Bundle.main. Cached after first load so
    /// subsequent calls within the session are O(1). Loader failure
    /// in production = fatalError per the Phase 2 design (a missing
    /// or malformed pool JSON is a build defect, not a runtime
    /// fallback). Tests bypass this method entirely by injecting a
    /// pool directly through `QuestEngine.generateDailyQuests(pool:)`.
    private var cachedQuestPool: QuestPool?
    private func lazyLoadedQuestPool() -> QuestPool? {
        if let cached = cachedQuestPool { return cached }
        do {
            let pool = try QuestPool.loadFromBundle(Bundle.main)
            cachedQuestPool = pool
            return pool
        } catch {
            // Phase 4 ships authored pool JSON. Until then, the
            // production files are empty arrays — the loader returns
            // an empty pool, not an error. A real load failure here
            // (corrupted bundle, malformed JSON) is genuinely fatal
            // since it indicates a build / signing defect.
            assertionFailure("QuestPool.loadFromBundle failed: \(error)")
            return nil
        }
    }

    // MARK: - Quest event emission (Phase 3c)
    //
    // Four hook points emit QuestEvent rows that AffinityEngine reads:
    //   shown     — engine emits today's slate (one per slug + alternates)
    //   picked    — user adds a slug to today's plan
    //   replaced  — user swaps slug A → slug B (logs replaced(A) + picked(B))
    //   completed — user ticks a quest done
    //
    // Phase 5b: every user is on the pool engine, so the emit helpers no
    // longer gate on `useQuestPoolEngine`. The pre-onboarding `profile ==
    // nil` short-circuit remains — there's nothing to attribute events to
    // before onboarding completes.

    /// Idempotent shown emission per (date, slug). Phase 3 plan task 10
    /// + master plan G14. Re-emit on the same day is a no-op.
    private func emitShown(slug: String, genre: String, date: Date) {
        guard profile != nil else { return }
        let dayStart = clock.calendar.startOfDay(for: date)
        let shownKind = QuestEventKind.shown.rawValue
        let predicate = #Predicate<QuestEvent> { event in
            event.date == dayStart && event.slug == slug && event.kind == shownKind
        }
        if let existing = try? modelContext.fetch(FetchDescriptor<QuestEvent>(predicate: predicate)),
           !existing.isEmpty {
            return
        }
        let event = QuestEvent(date: dayStart, slug: slug, genre: genre, kind: shownKind)
        modelContext.insert(event)
    }

    /// Idempotent picked emission per (date, slug). The plan editor
    /// guarantees one pick per category per day, so duplicate picks on
    /// the same slug shouldn't normally happen — but the dedup is
    /// defensive against double-fire.
    private func emitPicked(slug: String, genre: String, date: Date) {
        guard profile != nil else { return }
        let dayStart = clock.calendar.startOfDay(for: date)
        let pickedKind = QuestEventKind.picked.rawValue
        let predicate = #Predicate<QuestEvent> { event in
            event.date == dayStart && event.slug == slug && event.kind == pickedKind
        }
        if let existing = try? modelContext.fetch(FetchDescriptor<QuestEvent>(predicate: predicate)),
           !existing.isEmpty {
            return
        }
        let event = QuestEvent(date: dayStart, slug: slug, genre: genre, kind: pickedKind)
        modelContext.insert(event)
    }

    /// Replaced emissions are NOT deduped (master plan G7). Every swap
    /// of the same slug logs a separate row — A→B→A→B yields four
    /// `replaced` rows. EMA absorbs the noise; net-zero is the right
    /// signal because back-and-forth indicates indecision, not strong
    /// rejection.
    private func emitReplaced(slug: String, genre: String, date: Date) {
        guard profile != nil else { return }
        let dayStart = clock.calendar.startOfDay(for: date)
        let event = QuestEvent(date: dayStart, slug: slug, genre: genre, kind: QuestEventKind.replaced.rawValue)
        modelContext.insert(event)
    }

    /// Idempotent completed emission per (date, slug).
    private func emitCompleted(slug: String, genre: String, date: Date) {
        guard profile != nil else { return }
        let dayStart = clock.calendar.startOfDay(for: date)
        let completedKind = QuestEventKind.completed.rawValue
        let predicate = #Predicate<QuestEvent> { event in
            event.date == dayStart && event.slug == slug && event.kind == completedKind
        }
        if let existing = try? modelContext.fetch(FetchDescriptor<QuestEvent>(predicate: predicate)),
           !existing.isEmpty {
            return
        }
        let event = QuestEvent(date: dayStart, slug: slug, genre: genre, kind: completedKind)
        modelContext.insert(event)
    }

    /// Removes the `completed` event for (date, slug). Called when the
    /// user un-ticks a quest. Symmetric with the ledger-entry cleanup
    /// in `toggleQuestCompletion`'s un-tick branch — affinity must
    /// reflect the user's final intent, not their initial click.
    /// Code-review feedback on PR #32 (data-integrity #7): keeping
    /// the row would let a stray tap permanently shift affinity in a
    /// direction the user didn't intend.
    private func removeCompleted(slug: String, date: Date) {
        guard profile != nil else { return }
        let dayStart = clock.calendar.startOfDay(for: date)
        let completedKind = QuestEventKind.completed.rawValue
        let predicate = #Predicate<QuestEvent> { event in
            event.date == dayStart && event.slug == slug && event.kind == completedKind
        }
        guard let matches = try? modelContext.fetch(FetchDescriptor<QuestEvent>(predicate: predicate)) else {
            return
        }
        for event in matches {
            modelContext.delete(event)
        }
    }

    /// Single source of truth for slug→genre lookup. Architecture
    /// review on PR #32 flagged duplicated lookup logic across
    /// `eventGenre(for:)` and inline `slugGenreMap[slug]` calls.
    /// Both paths now go through `genreFor(slug:)` (with optional
    /// quest-row override when the row already carries non-empty
    /// genre — applies to events emitted from a persisted Quest).
    private static func genreFor(slug: String) -> String {
        slugGenreMap[slug] ?? ""
    }

    /// Genre lookup for events emitted from a Quest row. Prefers the
    /// row's own `genre` (which may be more specific than the slug
    /// map for slugs added post-Phase-3) and falls through to
    /// `slugGenreMap` otherwise.
    private func eventGenre(for quest: Quest) -> String {
        if !quest.genre.isEmpty { return quest.genre }
        return Self.genreFor(slug: quest.slug)
    }

    /// Idempotent. Walks all `Quest` rows with `genre == ""`, populates
    /// `genre` from the slug→genre map, saves the context. Safe to
    /// re-run — subsequent calls find no unbackfilled rows.
    /// Phase 3 of the quest-pool affinity engine (todo 049 #2).
    /// `internal` (not `private`) so unit tests can exercise the
    /// idempotency contract directly via `@testable import`.
    func bootstrapQuestGenres() {
        let descriptor = FetchDescriptor<Quest>(
            predicate: #Predicate { $0.genre == "" }
        )
        guard let unbackfilled = try? modelContext.fetch(descriptor), !unbackfilled.isEmpty else {
            return
        }
        var changed = false
        for quest in unbackfilled {
            if let genre = Self.slugGenreMap[quest.slug] {
                quest.genre = genre
                changed = true
            }
            // Slugs not in the map (e.g. consistency.open-app-tomorrow.v1)
            // stay with genre == "" — this is intentional, not a bug.
        }
        if changed {
            try? modelContext.save()
        }
    }

    // MARK: - Phase 5a flag-flip backfill (V1.6.0)
    //
    // Property-default changes in SwiftData only affect new instantiations.
    // Existing UserProfile rows persisted under V1.5.0 stay at their stored
    // value (false). To meet plan §5a's "existing user upgrades flip on
    // next launch" criterion, this backfill flips false → true once after
    // the V1.6.0 ship and short-circuits thereafter.
    //
    // Idempotency contract:
    //   * On first post-V1.6.0 launch: flips the persisted false → true.
    //   * On every subsequent launch: profile.useQuestPoolEngine is already
    //     true (either via the flip above or via a fresh-install default),
    //     and the guard short-circuits.
    //
    // `internal` (not `private`) so unit tests can exercise the
    // idempotency contract directly via `@testable import`.
    func bootstrapQuestPoolEngineFlag() {
        guard let profile, !profile.useQuestPoolEngine else { return }
        profile.useQuestPoolEngine = true
        try? modelContext.save()
    }

    // MARK: - V1.7.0 baseline backfill (Future tab anchor)
    //
    // Existing onboarded users (V1.6 stores upgraded to V1.7) have no
    // `baselineHealthspanYears` set — `applyAnchorAdjustment` ran
    // before the field existed. This idempotent hook runs on every
    // cold launch (and at the end of `applyAnchorAdjustment` to heal
    // upgraded-mid-onboarding users) until the baseline is set.
    //
    // Precedent: `bootstrapQuestPoolEngineFlag` (V1.6.0 Phase 5a).
    //
    // Sanity check (P1 review finding): wrap `ClockEngine.calculateBaseline`
    // in `(candidate).isFinite && > currentAge`. On failure (NaN, corrupt
    // profile, age sentinel) leave the field nil so the next launch
    // retries — don't ship a poison baseline.
    //
    // `internal` so unit tests can drive the bootstrap directly.
    func bootstrapV170Baseline() {
        guard let profile,
              profile.onboardingCompletedAt != nil,
              profile.anchorAdjustedAt != nil,
              let adjustment = profile.personalAdjustmentYears,
              profile.baselineHealthspanYears == nil else { return }
        let engineYears = clockEngine.calculateBaseline(profile: profile).projectedAgeYears
        let candidate = engineYears + adjustment
        // Sanity check — reject NaN/Inf, or any value at/below the
        // user's current age (impossible by construction; would be a
        // corrupt profile). Floor for projection enforced separately
        // in HealthspanEngine.
        let currentAge = Double(AgeGate.ageInYears(
            birthDate: profile.birthDate,
            asOf: clock.now(),
            calendar: clock.calendar
        ))
        guard candidate.isFinite, candidate > currentAge else { return }
        profile.baselineHealthspanYears = candidate
        profile.baselineCapturedAt = profile.anchorAdjustedAt
        try? modelContext.save()
    }

    // MARK: - HealthKit-driven recompute

    func refreshFromHealthKit(force: Bool = false) async {
        guard let profile else { return }
        // V1.7.0 Phase 4 coalesce: if a slider scrub is in flight,
        // queue the refresh instead of running it now. `endScrub`
        // flushes via `force: true` on touch-end. `force: true`
        // callers bypass the queue (e.g. scrub-end flush itself,
        // significant time change).
        if !force, queueRefreshIfScrubbing() {
            return
        }
        let now = clock.now()
        let dayStart = clock.calendar.startOfDay(for: now)

        // Phase 3c/3d: daily-cycle hook fires BEFORE the short-circuit so
        // the new-day branch always runs even when the snapshot is fresh.
        // Order is load-bearing per Phase 3 plan G23: EOD resolver runs
        // first, then distinctOpenDays increments. Today's affinity
        // computation later in this method then sees yesterday's
        // freshly-resolved passed_over / abandoned events.
        runDailyCycleIfNewDay(profile: profile, now: now, dayStart: dayStart)

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
            baseline.confidenceRaw = Confidence.low.rawValue
            baseline.explanation = "Waiting for Apple Health signal before claiming a daily minute change."
            todayDrivers = []
            hasTodaySignal = false
        }
        todayEstimate = baseline
        let recentSnapshots = fetchRecentSnapshots(limit: 14)
        // Phase 3c: feed events + pool into the engine when the flag
        // is on so the selector path can run. fetchAllQuestEvents()
        // returns [] until any event is emitted (flag-off → empty).
        // Pool resolution is lazy-loaded from Bundle.main on first call.
        // Phase 5b: legacy path retired — always fetch events + pool.
        let events = fetchAllQuestEvents()
        let pool = lazyLoadedQuestPool()
        todayQuests = questEngine.generateDailyQuests(
            profile: profile,
            snapshot: snapshot,
            recentSnapshots: recentSnapshots,
            habits: todayHabits,
            events: events,
            pool: pool
        )
        applyPersistedCompletions(to: &todayQuests, for: dayStart)
        applyTodayPlanOverrides()
        // Phase 3c task 11: emit `shown` events for every slug in the
        // emitted slate (flag-gated inside emitShown). Idempotent —
        // safe to call on every refresh.
        for quest in todayQuests {
            emitShown(slug: quest.slug, genre: eventGenre(for: quest), date: dayStart)
        }

        let weekSnapshots = await healthService.recentSnapshots(endingAt: now, count: 7)
        let weekHabits = fetchHabitsBack(7)
        weekly = clockEngine.calculateWeeklyTrend(snapshots: weekSnapshots, habits: weekHabits, profile: profile)
        // Only persist when there's at least one snapshot — the engine's
        // empty-input branch returns a placeholder keyed at `now`, which
        // would beat real prior-week reports in pendingWeekly's
        // most-recent selection and trigger a "this-week" wrap-up on the
        // morning the user has no data yet.
        if let weekly, !weekSnapshots.isEmpty {
            persistWeeklyReport(weekly)
        }

        // 60 days back covers any current month plus the prior one's tail
        // for safe boundary handling near month-rollover.
        monthlyLogging = monthlyLoggingCalculator.compute(habits: fetchHabitsBack(60), asOf: now)
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

    // MARK: - Today's plan overrides (Pro)

    /// Stable UserDefaults key for one-shot plan overrides.
    private static let todayPlanOverridesKey = "lifeclock.todayPlanOverrides"

    /// Variants the user can choose from for a single category, given the
    /// latest known snapshot + history + habits. The picker UI calls this
    /// to render swap options. Reads from persisted state — no async I/O.
    func planVariants(for category: QuestEngine.Category) -> [Quest] {
        guard let profile, let pool = lazyLoadedQuestPool() else { return [] }
        let now = clock.now()
        let dayStart = clock.calendar.startOfDay(for: now)
        return questEngine.availableQuests(
            for: category,
            profile: profile,
            pool: pool,
            events: fetchAllQuestEvents(),
            recentSnapshots: fetchRecentSnapshots(limit: 14),
            habits: todayHabits,
            today: dayStart
        )
    }

    /// Apply a user pick to today's plan. Pro-only — throws `.notEntitled`
    /// for free users (the picker UI surfaces a paywall instead).
    func selectPlanQuest(slug: String, in category: QuestEngine.Category) throws {
        guard entitlements?.isPro == true else {
            throw OverrideService.OverrideError.notEntitled
        }
        let now = clock.now()
        let key = TodayPlanOverrides.dayKey(for: now, calendar: clock.calendar)
        if todayPlanOverrides.dayKey != key {
            todayPlanOverrides = TodayPlanOverrides(dayKey: key, picks: [:])
        }
        // Phase 3c task 12: emit `replaced` for the slug being swapped
        // OUT (if any) and `picked` for the slug being added.
        // Replaced is per-event, NOT deduped, so A→B→A→B yields four
        // `replaced` rows (master plan G7 — back-and-forth signals
        // indecision). Picked IS deduped per (date, slug).
        let dayStart = clock.calendar.startOfDay(for: now)
        let priorSlug = todayPlanOverrides.picks[category.rawValue]
            ?? todayQuests.first(where: { Self.engineCategory(of: $0) == category })?.slug
        if let priorSlug, priorSlug != slug {
            emitReplaced(slug: priorSlug, genre: Self.genreFor(slug: priorSlug), date: dayStart)
        }
        emitPicked(slug: slug, genre: Self.genreFor(slug: slug), date: dayStart)

        todayPlanOverrides.picks[category.rawValue] = slug
        persistTodayPlanOverrides()
        applyTodayPlanOverrides()
        // Code-review feedback on PR #32 (data-integrity #8): the
        // emit helpers insert into modelContext; persistTodayPlanOverrides
        // saves UserDefaults, NOT modelContext. Without an explicit
        // save here, picked/replaced events would rely on SwiftData's
        // autosave — which has no guaranteed cadence. A force-quit
        // between insert and the next save would lose them.
        try? modelContext.save()
    }

    /// Drop all of today's user picks; the engine's smart defaults take
    /// over again. Free for all users — clearing your own choice never
    /// requires Pro.
    func clearTodayPlanOverrides() {
        todayPlanOverrides = .empty
        persistTodayPlanOverrides()
        applyTodayPlanOverrides()
    }

    private func loadTodayPlanOverrides() {
        guard let data = UserDefaults.standard.data(forKey: Self.todayPlanOverridesKey),
              let decoded = try? JSONDecoder().decode(TodayPlanOverrides.self, from: data)
        else { return }
        let key = TodayPlanOverrides.dayKey(for: clock.now(), calendar: clock.calendar)
        // Stale (yesterday's picks) → drop them. One-shot per the v1 spec.
        todayPlanOverrides = (decoded.dayKey == key) ? decoded : .empty
        if todayPlanOverrides.isEmpty {
            UserDefaults.standard.removeObject(forKey: Self.todayPlanOverridesKey)
        }
    }

    private func persistTodayPlanOverrides() {
        if todayPlanOverrides.isEmpty {
            UserDefaults.standard.removeObject(forKey: Self.todayPlanOverridesKey)
            return
        }
        if let data = try? JSONEncoder().encode(todayPlanOverrides) {
            UserDefaults.standard.set(data, forKey: Self.todayPlanOverridesKey)
        }
    }

    /// Re-applies user picks on top of the engine-generated `todayQuests`.
    /// Each pick replaces the same-category quest if one exists, or appends
    /// a new one (Movement may be empty when the day's step goal is met;
    /// the user can override it back in by picking a different movement
    /// variant). Idempotent — safe to call after every refresh.
    private func applyTodayPlanOverrides() {
        let key = TodayPlanOverrides.dayKey(for: clock.now(), calendar: clock.calendar)
        guard todayPlanOverrides.dayKey == key, !todayPlanOverrides.isEmpty else { return }
        for category in QuestEngine.Category.allCases {
            guard let slug = todayPlanOverrides.picks[category.rawValue] else { continue }
            let variants = planVariants(for: category)
            guard let pick = variants.first(where: { $0.slug == slug }) else { continue }
            if let idx = todayQuests.firstIndex(where: { Self.engineCategory(of: $0) == category }) {
                todayQuests[idx] = pick
            } else {
                todayQuests.append(pick)
            }
        }
        // Persisted completion state needs to survive the swap.
        applyPersistedCompletions(to: &todayQuests, for: clock.calendar.startOfDay(for: clock.now()))
    }

    /// Map a `Quest`'s loose category string to the picker's structured
    /// `QuestEngine.Category`. Sleep + recovery share a slot; nutrition +
    /// habit share a slot — see QuestEngine.Category for rationale.
    ///
    /// Pool-driven quests (Phase 5b+) carry `Genre.rawValue` in `category`
    /// — `"activity"`, `"sleep"`, `"diet"` — so accept those too. Without
    /// the genre aliases, `applyTodayPlanOverrides` could not find the
    /// engine-generated quest to replace and would APPEND the user's pick
    /// instead, duplicating items in today's plan.
    static func engineCategory(of quest: Quest) -> QuestEngine.Category? {
        if let genre = Genre(rawValue: quest.genre.lowercased()),
           let category = QuestEngine.Category(genre: genre) {
            return category
        }
        switch quest.category.lowercased() {
        case "activity", "movement": return .movement
        case "sleep", "recovery": return .sleepRecovery
        case "diet", "nutrition", "habit": return .nutritionHabit
        default: return nil
        }
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
        // V1.7.0: any Pro override mutates the per-day snapshot, which
        // shifts both the History cumulative summary and the Future
        // headline projection. Invalidate + recompute alongside the
        // existing derived-state refresh.
        invalidateCumulativeCache()
        refreshCurrentHealthspanProjection()
    }

    /// Public read accessor used by the day-detail view. Returns nil when
    /// no snapshot has been persisted for the day yet.
    func snapshot(for dayStart: Date) -> DailyHealthSnapshot? {
        fetchSnapshot(for: dayStart)
    }

    /// Returns the most recent N persisted snapshots for the History list.
    ///
    /// History is yesterday-and-earlier — today's row lives on Today. When
    /// `includingToday` is false (default), any snapshot whose date is in
    /// the current day per the injected clock is dropped. The fetch limit
    /// is widened by 1 internally so callers still see N rows when a
    /// today-snapshot exists.
    func recentSnapshots(limit: Int, includingToday: Bool = false) -> [DailyHealthSnapshot] {
        if includingToday {
            return fetchRecentSnapshots(limit: limit)
        }
        let raw = fetchRecentSnapshots(limit: limit + 1)
        let todayStart = clock.calendar.startOfDay(for: clock.now())
        let filtered = raw.filter { !clock.calendar.isDate($0.date, inSameDayAs: todayStart) }
        return Array(filtered.prefix(limit))
    }

    /// Signed daily delta for an arbitrary persisted snapshot. Mirrors
    /// `recomputeYesterdayDelta` so History rows show the same number the
    /// engine would assign that day. Returns nil when no profile is loaded.
    func dailyDelta(for snapshot: DailyHealthSnapshot) -> Int? {
        guard let profile else { return nil }
        let habits = fetchHabits(for: snapshot.date)
        let result = clockEngine.calculateDailyDelta(
            snapshot: snapshot,
            habits: habits,
            profile: profile
        )
        return result.deltaMinutes
    }

    // MARK: - Future tab scrub coordination (V1.7.0 — Phase 4 perf gates)
    //
    // Per the plan §Phase 4 slider-scrub interaction spec:
    //   * Memoize 14-day baseline aggregates on scrub-start.
    //   * Hold for 250ms post touch-end (debounced clear) — rapid
    //     re-grabs reuse the cache.
    //   * Coalesce queued daily-refresh ticks during a scrub.
    //   * Disable redraw animation while scrubbing.
    //
    // All entry points `@MainActor`-bound; the store as a whole is
    // @MainActor so no actor-hop is required. The 250ms debounce
    // uses `Task.sleep` with a monotonically-incrementing token to
    // discard stale clears (rapid re-grab within the window means
    // a new beginScrub bumps the token and the prior endScrub's
    // debounced clear becomes a no-op).

    /// Called by `WhatIfSlider.onEditingChanged(true)`. Captures the
    /// current 14-day aggregates if no scrub is already active.
    /// Increments the active-scrub counter so multi-touch is handled.
    func beginScrub() {
        activeScrubCount += 1
        if cachedBaselineAggregates == nil {
            cachedBaselineAggregates = HealthspanEngine.aggregates(
                snapshots: recentSnapshots(limit: 14),
                habits: recentHabits(limit: 14)
            )
        }
    }

    /// Called by `WhatIfSlider.onEditingChanged(false)`. Decrements
    /// the counter; when it reaches zero, kicks off the 250ms
    /// debounced clear of `cachedBaselineAggregates` AND flushes the
    /// pending-refresh queue. Token-stable: a re-begin within 250ms
    /// invalidates the in-flight clear via `scrubEndToken`.
    func endScrub() {
        activeScrubCount = max(0, activeScrubCount - 1)
        guard activeScrubCount == 0 else { return }
        scrubEndToken += 1
        let token = scrubEndToken
        // Flush any refresh that queued during the scrub. Exactly one
        // refresh + crossfade per the plan's coalesce rule.
        if pendingRefreshCount > 0 {
            pendingRefreshCount = 0
            Task { @MainActor in
                await refreshFromHealthKit(force: true)
            }
        }
        Task { @MainActor in
            try? await Task.sleep(nanoseconds: 250_000_000)  // 250ms
            guard token == scrubEndToken else { return }     // re-grab; ignore
            cachedBaselineAggregates = nil
        }
    }

    /// Called by `WhatIfSlider` on each `onChange`. Cheap setter; the
    /// view binds to `store.sliderOverrides` via @Observable.
    func setSliderOverride(_ dim: HealthspanEngine.Dimension, value: Double?) {
        if let value {
            sliderOverrides[dim] = value
        } else {
            sliderOverrides.removeValue(forKey: dim)
        }
    }

    /// Called by `WhatIfSlider.onEditingChanged(false)` after the
    /// snap-back. Clears all overrides in one shot — chart returns
    /// to personal-current.
    func clearSliderOverrides() {
        sliderOverrides = [:]
    }

    /// Called by HK refresh when a scrub is in flight. Returns true if
    /// the caller should defer (queued) or false if it should proceed
    /// normally. `flushPendingRefresh` runs the deferred refresh on
    /// scrub-end.
    func queueRefreshIfScrubbing() -> Bool {
        guard isProjectionScrubbing else { return false }
        pendingRefreshCount += 1
        return true
    }

    /// Returns the N most-recent persisted habit logs, optionally
    /// excluding today. Mirrors `recentSnapshots(limit:includingToday:)`.
    /// V1.7.0: Phase 3 trajectory chart + Phase 4 slider personal-
    /// current anchors both need a 14-day habit window aligned to the
    /// same convention as the snapshot accessor.
    func recentHabits(limit: Int, includingToday: Bool = false) -> [HabitLog] {
        var descriptor = FetchDescriptor<HabitLog>(
            sortBy: [SortDescriptor(\.date, order: .reverse)]
        )
        descriptor.fetchLimit = includingToday ? limit : limit + 1
        let raw = (try? modelContext.fetch(descriptor)) ?? []
        if includingToday {
            return Array(raw.prefix(limit))
        }
        let todayStart = clock.calendar.startOfDay(for: clock.now())
        let filtered = raw.filter { !clock.calendar.isDate($0.date, inSameDayAs: todayStart) }
        return Array(filtered.prefix(limit))
    }

    // MARK: - Cumulative since install (V1.7.0 — History summary section)
    //
    // Plan §Phase 1. Walks DailyHealthSnapshot + HabitLog from
    // `max(profile.onboardingCompletedAt, now - 3.years)` to yesterday,
    // accumulates per-driver-type contribution, and caches the result in
    // `CumulativeSummaryCache` (single-row @Model). Cache is invalidated
    // by `refreshFromHealthKit` on any snapshot upsert + by a
    // content-hash mismatch on every read (catches retroactive deletes).
    //
    // All operations `@MainActor`-only (the entire store is). HK refresh
    // is also @MainActor per existing pattern, so invalidation inside its
    // save block is race-free against History tab reads.
    //
    // Performance gate: first call O(N) over the window (one batched
    // FetchDescriptor per entity, grouped into [Date: HabitLog] for the
    // walk). Subsequent calls same-day O(1).

    /// Walks the install→yesterday window, returns hero number + top-3
    /// contributors. Returns nil when no profile loaded.
    func cumulativeDeltaSinceInstall() -> CumulativeSummary? {
        guard let profile,
              let onboardingCompletedAt = profile.onboardingCompletedAt else {
            return nil
        }
        let now = clock.now()
        let calendar = clock.calendar
        let today = calendar.startOfDay(for: now)
        guard let yesterday = calendar.date(byAdding: .day, value: -1, to: today) else {
            return nil
        }

        // Window start: max(onboardingCompletedAt, now - 3.years).
        // Per P1 review: bound first-walk cost; 3-year cap with a
        // "since {Year}" copy affordance when truncation applies.
        let threeYearsAgo = calendar.date(byAdding: .year, value: -3, to: today) ?? today
        let installDay = calendar.startOfDay(for: onboardingCompletedAt)
        let windowStart = max(installDay, calendar.startOfDay(for: threeYearsAgo))
        let truncated = windowStart > installDay

        // Day 0 short-circuit: no walk needed. Returns an empty
        // summary with daysSinceInstall == 0 so the view renders the
        // Day-0 hero copy.
        if windowStart > yesterday {
            return CumulativeSummary(
                totalDeltaMinutes: 0,
                windowStart: windowStart,
                lastIncludedDate: windowStart,
                daysSinceInstall: 0,
                topContributors: [],
                snapshotsWithData: 0,
                truncatedTo3Years: truncated
            )
        }

        let daysSinceInstall = max(
            0,
            calendar.dateComponents([.day], from: installDay, to: today).day ?? 0
        )

        // Cache check.
        let contentVersion = currentCumulativeContentVersion(
            windowStart: windowStart,
            windowEnd: yesterday
        )
        if let cache = fetchCumulativeCache(),
           cache.lastIncludedDate == yesterday,
           cache.contentVersion == contentVersion,
           cache.windowStart == windowStart {
            let cachedContribs = decodeContributors(cache.topContributorsData)
            return CumulativeSummary(
                totalDeltaMinutes: cache.totalDeltaMinutes,
                windowStart: cache.windowStart,
                lastIncludedDate: cache.lastIncludedDate,
                daysSinceInstall: daysSinceInstall,
                topContributors: cachedContribs.contributors,
                snapshotsWithData: cachedContribs.snapshotsWithData,
                truncatedTo3Years: truncated
            )
        }

        // Cache miss — recompute the full window.
        let snapshots = fetchSnapshotsInRange(start: windowStart, end: yesterday)
        let habits = fetchHabitsInRange(start: windowStart, end: yesterday)
        let habitsByDay: [Date: HabitLog] = habits.reduce(into: [:]) { dict, habit in
            dict[calendar.startOfDay(for: habit.date)] = habit
        }

        var totalDelta = 0
        var dimTotals: [CumulativeContributor.Dimension: Int] = [:]
        var dimDayCounts: [CumulativeContributor.Dimension: Int] = [:]
        var snapshotsWithData = 0

        for snapshot in snapshots {
            let dayStart = calendar.startOfDay(for: snapshot.date)
            let habit = habitsByDay[dayStart]
            let result = clockEngine.calculateDailyDelta(
                snapshot: snapshot,
                habits: habit,
                profile: profile
            )
            totalDelta += result.deltaMinutes
            if result.deltaMinutes != 0 || !result.drivers.isEmpty {
                snapshotsWithData += 1
            }
            // Aggregate per-driver-type net + day-count.
            for driver in result.drivers {
                let dim = CumulativeContributor.Dimension(driverString: driver.driverType)
                dimTotals[dim, default: 0] += driver.deltaMinutes
                dimDayCounts[dim, default: 0] += 1
            }
        }

        // Top-3 by absolute net delta. Filter out `.other` from the
        // panel — it's an "unrecognized driver" bucket, not user-facing.
        let contributors: [CumulativeContributor] = dimTotals
            .filter { $0.key != .other && $0.value != 0 }
            .map { dim, net in
                CumulativeContributor(
                    dimension: dim,
                    netDeltaMinutes: net,
                    topDayCount: dimDayCounts[dim] ?? 0
                )
            }
            .sorted { abs($0.netDeltaMinutes) > abs($1.netDeltaMinutes) }
            .prefix(3)
            .map { $0 }

        // Persist to cache.
        let cache = fetchCumulativeCache() ?? {
            let new = CumulativeSummaryCache()
            modelContext.insert(new)
            return new
        }()
        cache.lastIncludedDate = yesterday
        cache.contentVersion = contentVersion
        cache.totalDeltaMinutes = totalDelta
        cache.windowStart = windowStart
        cache.topContributorsData = encodeContributors(
            contributors: contributors,
            snapshotsWithData: snapshotsWithData
        )
        try? modelContext.save()

        return CumulativeSummary(
            totalDeltaMinutes: totalDelta,
            windowStart: windowStart,
            lastIncludedDate: yesterday,
            daysSinceInstall: daysSinceInstall,
            topContributors: contributors,
            snapshotsWithData: snapshotsWithData,
            truncatedTo3Years: truncated
        )
    }

    /// Invalidate the cumulative cache. Called by `refreshFromHealthKit`
    /// inside its save block on any snapshot upsert so the next History
    /// tab open recomputes — eliminates the read-then-write race
    /// between background HK refresh and foreground History reads.
    /// Also called from `setTodayHabits` and the override write paths
    /// so retroactive habit edits invalidate the cache at the source
    /// (defense in depth — the contentVersion mismatch path catches it
    /// on next read regardless).
    /// (Both are @MainActor in this store, but explicit invalidation
    /// keeps the contract clear and survives a future actor split.)
    fileprivate func invalidateCumulativeCache() {
        guard let cache = fetchCumulativeCache() else { return }
        // Force contentVersion mismatch on next read; cheap.
        cache.contentVersion = -1
    }

    /// Recompute `currentHealthspanProjection` from the latest persisted
    /// snapshots + habits + profile baseline. Called from the same write
    /// paths as `invalidateCumulativeCache()` so the TodayView trajectory
    /// peek stays current without re-aggregating per render.
    fileprivate func refreshCurrentHealthspanProjection() {
        guard let profile, let baseline = profile.baselineHealthspanYears else {
            currentHealthspanProjection = nil
            return
        }
        let snapshots = recentSnapshots(limit: 14)
        let habits = recentHabits(limit: 14)
        let currentAge = Double(AgeGate.ageInYears(
            birthDate: profile.birthDate,
            asOf: clock.now(),
            calendar: clock.calendar
        ))
        currentHealthspanProjection = HealthspanEngine.currentProjection(
            snapshots: snapshots,
            habits: habits,
            baseline: baseline,
            currentAge: currentAge,
            clock: clock
        )
    }

    private func fetchCumulativeCache() -> CumulativeSummaryCache? {
        let descriptor = FetchDescriptor<CumulativeSummaryCache>()
        return try? modelContext.fetch(descriptor).first
    }

    /// Content-hash for cache validity. Bumps automatically when any
    /// HabitLog or DailyHealthSnapshot in the window is added or
    /// deleted. Reuses `fetchCount` so we never materialize the rows
    /// just to count them.
    private func currentCumulativeContentVersion(windowStart: Date, windowEnd: Date) -> Int {
        let snapshotDescriptor = FetchDescriptor<DailyHealthSnapshot>(
            predicate: #Predicate { $0.date >= windowStart && $0.date <= windowEnd }
        )
        let habitDescriptor = FetchDescriptor<HabitLog>(
            predicate: #Predicate { $0.date >= windowStart && $0.date <= windowEnd }
        )
        let snapshotCount = (try? modelContext.fetchCount(snapshotDescriptor)) ?? 0
        let habitCount = (try? modelContext.fetchCount(habitDescriptor)) ?? 0
        return snapshotCount * 1_000_000 + habitCount
    }

    private func fetchSnapshotsInRange(start: Date, end: Date) -> [DailyHealthSnapshot] {
        let descriptor = FetchDescriptor<DailyHealthSnapshot>(
            predicate: #Predicate { $0.date >= start && $0.date <= end },
            sortBy: [SortDescriptor(\.date, order: .forward)]
        )
        return (try? modelContext.fetch(descriptor)) ?? []
    }

    private func fetchHabitsInRange(start: Date, end: Date) -> [HabitLog] {
        let descriptor = FetchDescriptor<HabitLog>(
            predicate: #Predicate { $0.date >= start && $0.date <= end },
            sortBy: [SortDescriptor(\.date, order: .forward)]
        )
        return (try? modelContext.fetch(descriptor)) ?? []
    }

    private struct EncodedContributors: Codable {
        let contributors: [CumulativeContributor]
        let snapshotsWithData: Int
    }

    private func encodeContributors(
        contributors: [CumulativeContributor],
        snapshotsWithData: Int
    ) -> Data {
        let payload = EncodedContributors(
            contributors: contributors,
            snapshotsWithData: snapshotsWithData
        )
        return (try? JSONEncoder().encode(payload)) ?? Data()
    }

    private func decodeContributors(_ data: Data) -> (
        contributors: [CumulativeContributor],
        snapshotsWithData: Int
    ) {
        guard !data.isEmpty,
              let decoded = try? JSONDecoder().decode(EncodedContributors.self, from: data) else {
            return ([], 0)
        }
        return (decoded.contributors, decoded.snapshotsWithData)
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
        // Recompute so a queued sibling (e.g. weekly wrap-up after the user
        // dismissed yesterday on a Monday return) sequences in within the
        // same launch instead of waiting for the next foreground transition.
        // Coordinator's monotonic guards prevent re-presenting what we just
        // marked shown.
        recomputePendingWrapUp(profile: profile, now: now)
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
        todayEstimate = clockEngine.calculateBaseline(profile: profile)
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
    ///
    /// V1.7.0 (Future tab plan §Phase 2): also captures
    /// `baselineHealthspanYears` (engine + dial) and `baselineCapturedAt`
    /// in the same save. Sanity-checked. On failure, the baseline
    /// fields stay nil and `bootstrapV170Baseline` retries on next
    /// cold launch.
    func applyAnchorAdjustment(years: Double) {
        guard let profile else { return }
        // Idempotency: never re-apply if already adjusted.
        guard profile.anchorAdjustedAt == nil else { return }
        let now = clock.now()
        profile.personalAdjustmentYears = years
        profile.anchorAdjustedAt = now
        // Atomic baseline capture. Same save block as the anchor pair —
        // if the save fails, all four fields revert.
        let engineYears = clockEngine.calculateBaseline(profile: profile).projectedAgeYears
        let candidate = engineYears + years
        let currentAge = Double(AgeGate.ageInYears(
            birthDate: profile.birthDate,
            asOf: now,
            calendar: clock.calendar
        ))
        if candidate.isFinite, candidate > currentAge {
            profile.baselineHealthspanYears = candidate
            profile.baselineCapturedAt = now
        }
        // If the candidate failed the sanity check, leave the baseline
        // fields nil — `bootstrapV170Baseline()` will retry on the next
        // cold launch with a (hopefully repaired) profile.
        do {
            try modelContext.save()
        } catch {
            // Roll memory back to match disk so the dial screen reappears
            // on next launch and the user can retry cleanly.
            profile.personalAdjustmentYears = nil
            profile.anchorAdjustedAt = nil
            profile.baselineHealthspanYears = nil
            profile.baselineCapturedAt = nil
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

    func setBodyMetrics(heightCm: Double?, weightKg: Double?) {
        profile?.heightCm = heightCm
        profile?.weightKg = weightKg
        try? modelContext.save()
        if let profile {
            todayEstimate = clockEngine.calculateBaseline(profile: profile)
        }
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
            // Phase 3c task 13: emit `completed` event. Idempotent per
            // (date, slug) so re-tick after un-tick + re-tick is a
            // single event. Flag-gated inside emitCompleted.
            emitCompleted(
                slug: quest.slug,
                genre: eventGenre(for: stored),
                date: clock.calendar.startOfDay(for: now)
            )
            emit(.questCompleted(rewardMinutes: quest.rewardEstimateMinutes))
        } else {
            quest.completedAt = nil
            stored.completedAt = nil
            if let entry = fetchLatestQuestLedgerEntry(for: quest, on: clock.calendar.startOfDay(for: now)) {
                modelContext.delete(entry)
                ledger.removeAll { $0.id == entry.id }
            }
            // Phase 3c data-correctness: un-tick removes the matching
            // `completed` event so affinity reflects the user's final
            // intent. Code-review feedback on PR #32 (data-integrity
            // #7) — without this, a stray tap permanently shifts
            // affinity in a direction the user un-did.
            removeCompleted(slug: quest.slug, date: clock.calendar.startOfDay(for: now))
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
            existing.dietAmountRhythm = habits.dietAmountRhythm
            existing.wholeFoodMeal = habits.wholeFoodMeal
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
        // V1.7.0: retroactive habit edits invalidate the cumulative
        // cache + projection peek. `refreshFromHealthKit` below ALSO
        // does this on its snapshot save path, but invalidating here
        // closes the window between save() and the HK refresh.
        invalidateCumulativeCache()
        try? modelContext.save()
        refreshCurrentHealthspanProjection()
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
        // Cap source rows to days at or after the user finished onboarding.
        // Without this, a Pro upgrade triggers the 10-year HealthKit backfill
        // (`HistoricalImportCoordinator`), and the badge engine treats those
        // pre-LifeClock days as "Rich signal days," instantly unlocking
        // tier-100 badges. The badge titles ("Captured a day with strong
        // data completeness") imply days WHILE USING the app, not history
        // imported from before. Reproduced 2026-05-09 — see
        // docs/products/life-clock/polish-2026-05-09-badge-overcount-fix.md.
        let onboardingDay: Date? = profile?.onboardingCompletedAt.map { dayKey(for: $0) }
        let filterByOnboarding: (Date) -> Bool = { date in
            guard let onboardingDay else { return false }
            return date >= onboardingDay
        }
        let habits = fetchAllHabits().filter { filterByOnboarding(dayKey(for: $0.date)) }
        let quests = fetchAllQuests().filter { filterByOnboarding(dayKey(for: $0.date)) }
        let snapshots = fetchAllSnapshots().filter { filterByOnboarding(dayKey(for: $0.date)) }
        let reports = fetchAllWeeklyReports().filter { filterByOnboarding(dayKey(for: $0.weekStart)) }
        let completedQuests = quests.filter { $0.completedAt != nil }
        let completedQuestDays = Set(completedQuests.map { dayKey(for: $0.date) })
        let completedByDay = Dictionary(grouping: completedQuests, by: { dayKey(for: $0.date) })

        return CompletionBadgeProgress(
            onboardedAt: profile?.onboardingCompletedAt,
            completedQuestCount: completedQuests.count,
            completedQuestDays: completedQuestDays.count,
            threeQuestDays: completedByDay.values.filter { $0.count >= 3 }.count,
            checkInDays: Set(habits.map { dayKey(for: $0.date) }).count,
            monthlyLogDays: monthlyLogging.daysLogged,
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

    // MARK: - Reflection (Phase 3 of the 2026-05-01 IA refactor)

    /// Persist today's reflection. Upserts on the local-day key. Safe
    /// against double-tap on Save: this method is `@MainActor`-isolated
    /// (the whole store is) so concurrent calls serialize, and the
    /// fetch-then-mutate-or-insert pattern is idempotent within a
    /// single day.
    func saveReflection(prompt: String, response: String) {
        let key = DayKey.from(date: clock.now(), calendar: clock.calendar)
        let row: DailyReflection
        if let existing = fetchReflection(for: key) {
            existing.response = response
            existing.prompt = prompt   // re-stamp in case prompt rotated
            row = existing
        } else {
            let new = DailyReflection(dayKey: key, prompt: prompt, response: response)
            modelContext.insert(new)
            row = new
        }
        try? modelContext.save()
        // Set directly rather than re-fetch — `row` is the live model
        // attached to this context after `insert`/`save`.
        todayReflection = row
    }

    /// Reflection for an arbitrary day. Used by History `DayDetailView`
    /// to surface saved reflections in the past-day archive.
    func reflection(for date: Date) -> DailyReflection? {
        let key = DayKey.from(date: date, calendar: clock.calendar)
        return fetchReflection(for: key)
    }

    /// Delete today's reflection if one exists. No-op when nothing is
    /// saved. Lets a user un-save something they wrote and regretted.
    func deleteTodayReflection() {
        let key = DayKey.from(date: clock.now(), calendar: clock.calendar)
        guard let existing = fetchReflection(for: key) else { return }
        modelContext.delete(existing)
        try? modelContext.save()
        todayReflection = nil
    }

    private func reloadTodayReflection() {
        let key = DayKey.from(date: clock.now(), calendar: clock.calendar)
        todayReflection = fetchReflection(for: key)
    }

    private func fetchReflection(for key: Int) -> DailyReflection? {
        var descriptor = FetchDescriptor<DailyReflection>(
            predicate: #Predicate { $0.dayKey == key }
        )
        descriptor.fetchLimit = 1
        return (try? modelContext.fetch(descriptor))?.first
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

    /// Upsert the freshly-computed weekly report keyed on `weekStart`.
    /// `calculateWeeklyTrend` returns a transient `WeeklyReport` value; if a
    /// row already exists for that week, copy fields onto it (avoids
    /// `@Attribute(.unique)` violation), else insert. Pending weekly
    /// wrap-up presentation reads through `fetchRecentWeeklyReports`, so
    /// without this the weekly wrap-up is unreachable in production.
    private func persistWeeklyReport(_ report: WeeklyReport) {
        let weekStart = clock.calendar.startOfDay(for: report.weekStart)
        let descriptor = FetchDescriptor<WeeklyReport>(
            predicate: #Predicate { $0.weekStart == weekStart }
        )
        if let existing = (try? modelContext.fetch(descriptor))?.first {
            existing.weekEnd = report.weekEnd
            existing.netTimeDeltaMinutes = report.netTimeDeltaMinutes
            existing.topPositiveDriver = report.topPositiveDriver
            existing.topNegativeDriver = report.topNegativeDriver
            existing.nextBestLever = report.nextBestLever
            existing.confidenceRaw = report.confidenceRaw
        } else {
            modelContext.insert(report)
        }
        try? modelContext.save()
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
        // V1.7.0: invalidate the cumulative cache inside the same save
        // block. Future History tab reads recompute against the new
        // snapshot row. Also recompute the store-owned trajectory peek
        // so the Today screen reads cheaply on next render.
        invalidateCumulativeCache()
        try? modelContext.save()
        refreshCurrentHealthspanProjection()
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

        // Same-day completions remain visible even when the engine's
        // anti-repeat selector rotates past their slug on the next
        // refresh (e.g. cold restart after a morning completion).
        // Append any persisted completion for today that the slate
        // didn't already surface, so a checkmark on the user's
        // just-completed action survives plan regeneration until
        // tomorrow's slate.
        let emittedSlugs = Set(quests.map(\.slug))
        let missingCompletions = storedRows.filter { stored in
            stored.completedAt != nil
                && !stored.slug.isEmpty
                && !emittedSlugs.contains(stored.slug)
        }
        quests.append(contentsOf: missingCompletions)
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
    func upsertQuest(_ quest: Quest) -> Quest {
        // Resolve the incoming genre at the boundary so the same value
        // is applied symmetrically on both insert and update. If the
        // caller passed an empty default (legacy engine path or the
        // consistency fallback), look up a known genre by slug; only
        // use the fallback "" if the slug isn't in the map either.
        // This eliminates the insert/update-branch asymmetry flagged
        // by the data-integrity review on PR #31.
        let resolvedGenre: String = {
            if !quest.genre.isEmpty { return quest.genre }
            return Self.slugGenreMap[quest.slug] ?? ""
        }()

        let stored = fetchStoredQuest(slug: quest.slug, on: quest.date) ?? {
            let new = Quest(
                id: quest.id,
                slug: quest.slug,
                date: quest.date,
                title: quest.title,
                detail: quest.detail,
                category: quest.category,
                target: quest.target,
                rewardEstimateMinutes: quest.rewardEstimateMinutes,
                genre: resolvedGenre
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
        // Phase 3 V1.5.0: propagate `genre` on update (todo 049 #1).
        // GUARDED against the empty-default sentinel — otherwise the
        // legacy QuestEngine emit path and the consistency-fallback
        // path would clobber a previously-backfilled non-empty genre.
        if !resolvedGenre.isEmpty {
            stored.genre = resolvedGenre
        }
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
