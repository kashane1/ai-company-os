import Foundation

/// Generates 1–3 daily quests deterministic given inputs and the engine clock.
///
/// Phase 5b (V1.6.0+): the legacy inlined-Quest path has been retired.
/// All quests now come from the 90-slug authored pool via `QuestSelector`.
/// `Category` survives as a UI-side categorization (plan-editor sections,
/// `TodayPlanOverrides` keying), with a 1:1 mapping to `Genre`.
///
/// Failure modes:
///   - Pool missing or empty: returns the deadlock fallback
///     (`consistency.open-app-tomorrow.v1`). In production the bundle
///     ships activity/diet/sleep JSONs with 30 slugs each, so this branch
///     is reachable only on a build defect.
///   - Selector returns empty for all genres: same fallback.
///   - All eligibility filters reject every slug for the user's profile:
///     same fallback. Authoring tests cover this for default cold-start
///     users; an edge-case combo could in principle still hit it.
struct QuestEngine {
    /// UI-side categorization for the plan editor and `TodayPlanOverrides`
    /// keys. Pre-Phase-5b each case had its own variant pool; post-5b each
    /// case maps 1:1 to a `Genre` and the pool selector drives the picks.
    enum Category: String, CaseIterable, Codable {
        case movement
        case sleepRecovery
        case nutritionHabit

        var displayTitle: String {
            switch self {
            case .movement: return "Movement"
            case .sleepRecovery: return "Sleep & Recovery"
            case .nutritionHabit: return "Nutrition & Habit"
            }
        }

        var genre: Genre {
            switch self {
            case .movement: return .activity
            case .sleepRecovery: return .sleep
            case .nutritionHabit: return .diet
            }
        }

        init?(genre: Genre) {
            switch genre {
            case .activity: self = .movement
            case .sleep: self = .sleepRecovery
            case .diet: self = .nutritionHabit
            }
        }
    }

    let clock: EngineClock

    init(clock: EngineClock = .live) {
        self.clock = clock
    }

    /// Generates today's slate. One quest per genre, picked by the
    /// selector. Snapshot/habits are accepted but unused — preserved in
    /// the signature so callers don't have to be rewritten.
    func generateDailyQuests(
        profile: UserProfile,
        snapshot: DailyHealthSnapshot? = nil,
        recentSnapshots: [DailyHealthSnapshot] = [],
        habits: HabitLog? = nil,
        events: [QuestEvent] = [],
        pool: QuestPool? = nil
    ) -> [Quest] {
        let today = clock.calendar.startOfDay(for: clock.now())
        guard let resolvedPool = pool, !resolvedPool.isEmpty else {
            // Build defect path: production always ships a non-empty pool.
            // Surface the deadlock fallback rather than a blank slate.
            return [consistencyFallback(today: today)]
        }
        return selectorPath(
            pool: resolvedPool,
            profile: profile,
            recentSnapshots: recentSnapshots,
            events: events,
            today: today
        )
    }

    /// Pool-driven alternates for a single category. The plan editor calls
    /// this to surface up-to-N swap options to the user. Returns Quest
    /// rows materialized from the genre's eligible pool entries, ordered
    /// by current selector score (highest first). Includes the slug the
    /// engine would otherwise pick first — callers identify it as item 0.
    func availableQuests(
        for category: Category,
        profile: UserProfile,
        pool: QuestPool,
        events: [QuestEvent] = [],
        recentSnapshots: [DailyHealthSnapshot] = [],
        habits: HabitLog? = nil,
        today: Date? = nil,
        limit: Int = 3
    ) -> [Quest] {
        let day = today ?? clock.calendar.startOfDay(for: clock.now())
        let affinity = AffinityEngine.computeAffinities(events: events)
        let needWeight = NeedWeightEngine.compute(profile: profile, recentSnapshots: recentSnapshots)
        let ranked = QuestSelector.rankEligibleByScore(
            pool: pool,
            genre: category.genre,
            affinity: affinity,
            needWeight: needWeight,
            profile: profile,
            today: day,
            events: events
        )
        let tone = ToneMode.fromStored(profile.toneMode)
        return ranked.prefix(limit).map { Self.materializeQuest($0, tone: tone, today: day) }
    }

    // MARK: - Internals

    private func selectorPath(
        pool: QuestPool,
        profile: UserProfile,
        recentSnapshots: [DailyHealthSnapshot],
        events: [QuestEvent],
        today: Date
    ) -> [Quest] {
        let affinity = AffinityEngine.computeAffinities(events: events)
        let needWeight = NeedWeightEngine.compute(profile: profile, recentSnapshots: recentSnapshots)
        let picked = QuestSelector.select(
            pool: pool,
            affinity: affinity,
            needWeight: needWeight,
            profile: profile,
            today: today,
            events: events
        )
        if picked.isEmpty {
            return [consistencyFallback(today: today)]
        }
        let tone = ToneMode.fromStored(profile.toneMode)
        return picked.map { Self.materializeQuest($0, tone: tone, today: today) }
    }

    /// Snapshot a `PoolQuest` into a `Quest` SwiftData row. Tone resolution
    /// happens at materialization time; views that need fresh tone should
    /// call `pool.copy(for:tone:)` directly. Falls back to coach copy
    /// then to intent text if the requested tone is missing — load-time
    /// validation in `PoolQuest.init(from:)` already requires all three
    /// tones, so the fallbacks are safety net only.
    static func materializeQuest(
        _ poolQuest: PoolQuest,
        tone: ToneMode,
        today: Date
    ) -> Quest {
        let copy = poolQuest.copy[tone]
            ?? poolQuest.copy[.coach]
            ?? ToneCopy(title: poolQuest.intent, detail: "")
        return Quest(
            slug: poolQuest.slug,
            date: today,
            title: copy.title,
            detail: copy.detail,
            category: poolQuest.genre.rawValue,
            target: poolQuest.target?.value ?? 1,
            rewardEstimateMinutes: 5,
            genre: poolQuest.genre.rawValue
        )
    }

    /// Deadlock fallback (master plan G16). Emitted only when the pool is
    /// missing/empty or the selector cannot satisfy the genre floor for
    /// any slot. Stable slug across days.
    private func consistencyFallback(today: Date) -> Quest {
        Quest(
            slug: "consistency.open-app-tomorrow.v1",
            date: today,
            title: "Open the app tomorrow",
            detail: "The clock improves most from showing up daily.",
            category: "consistency",
            target: 1,
            rewardEstimateMinutes: 0
        )
    }
}
