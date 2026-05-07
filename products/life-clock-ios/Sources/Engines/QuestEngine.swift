import Foundation

/// Generates 1–3 daily quests deterministic given inputs and the engine clock.
///
/// Rules:
///   - Always returns 1, 2, or 3 quests. Never zero, never four+.
///   - Adapts to missing data: if no HealthKit snapshot, returns manual-log
///     friendly quests instead of step/HR-anchored ones.
///   - Diet quality is a first-class quest category alongside movement and
///     sleep — it surfaces in the third slot most days. Nutrition quests
///     are coarse, encouraging, and never reference calories, macros, gram
///     targets, named diets, or "clean food" / "bad food" framing.
///   - Never recommends medication, supplements, or specific clinical targets.
struct QuestEngine {
    /// Three categories the daily plan rotates through. The picker enforces
    /// one selection per category — a user cannot stack three movement
    /// quests. Sleep and recovery share a slot because they're the same
    /// "wind down / reset" lever; nutrition and habit share the third slot
    /// because they're both food/intake-shaped.
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
    }

    let clock: EngineClock

    init(clock: EngineClock = .live) {
        self.clock = clock
    }

    func generateDailyQuests(
        profile: UserProfile,
        snapshot: DailyHealthSnapshot?,
        recentSnapshots: [DailyHealthSnapshot] = [],
        habits: HabitLog?
    ) -> [Quest] {
        let today = clock.calendar.startOfDay(for: clock.now())
        var quests: [Quest] = []

        for category in Category.allCases {
            let variants = availableQuests(
                for: category,
                profile: profile,
                snapshot: snapshot,
                recentSnapshots: recentSnapshots,
                habits: habits,
                today: today
            )
            // Movement variant pool returns empty when the day's step goal
            // is already met — that slot drops out, matching prior behavior.
            if let pick = variants.first {
                quests.append(pick)
            }
        }

        if quests.isEmpty {
            quests.append(consistencyFallback(today: today))
        }

        return Array(quests.prefix(3))
    }

    /// Returns the alternate quests the user can pick from for a single
    /// category. The first element is the engine's smart default given
    /// today's inputs (history-aware step target, habit-derived recovery
    /// pick, etc.); the rest are sibling variants the picker offers as
    /// swap options. Always 0–3 quests; never duplicates the default
    /// slug. Movement returns empty when today's step goal is already
    /// met, which is how that slot drops out of the daily plan.
    func availableQuests(
        for category: Category,
        profile: UserProfile,
        snapshot: DailyHealthSnapshot?,
        recentSnapshots: [DailyHealthSnapshot] = [],
        habits: HabitLog?,
        today: Date? = nil
    ) -> [Quest] {
        let day = today ?? clock.calendar.startOfDay(for: clock.now())
        switch category {
        case .movement:
            return movementVariants(today: day, snapshot: snapshot, recentSnapshots: recentSnapshots)
        case .sleepRecovery:
            return sleepRecoveryVariants(today: day, profile: profile, snapshot: snapshot, habits: habits)
        case .nutritionHabit:
            return nutritionHabitVariants(today: day, habits: habits)
        }
    }

    // MARK: - Variant pools

    private func movementVariants(today: Date, snapshot: DailyHealthSnapshot?, recentSnapshots: [DailyHealthSnapshot]) -> [Quest] {
        let target = movementStepTarget(recentSnapshots: recentSnapshots)
        let progress = Double(snapshot?.stepCount ?? 0)

        // Goal already met → drop the slot entirely.
        if let steps = snapshot?.stepCount, steps >= Int(target) {
            return []
        }

        // Surface the personalization signal in copy: when we have ≥5 logged
        // days the target is the user's own p50 + 10% (clamped 5k–20k); when
        // we don't, the 7500 default is admittedly arbitrary and the quest
        // should not pretend otherwise. This makes the picker read as
        // "we're tuning to you" instead of "stock 7500 for everyone."
        let loggedDays = recentSnapshots.compactMap { $0.stepCount }.filter { $0 > 0 }.count
        let isPersonalized = loggedDays >= 5
        let stepsDetail: String
        if snapshot?.stepCount == nil {
            stepsDetail = "Take a 10-minute walk after a meal today."
        } else if isPersonalized {
            stepsDetail = "Get to \(Int(target)) steps — tuned from your last \(loggedDays) days. A short post-dinner walk usually closes the gap."
        } else {
            stepsDetail = "Get to \(Int(target)) steps. A short post-dinner walk usually closes the gap. (We'll tune this once we have a week of your data.)"
        }
        let stepsQuest = Quest(
            slug: "movement.steps-target.v1",
            date: today,
            title: "Move a little more",
            detail: stepsDetail,
            category: "movement",
            target: target,
            rewardEstimateMinutes: 18
        )
        stepsQuest.progress = progress

        let walkQuest = Quest(
            slug: "movement.walk-after-meal.v1",
            date: today,
            title: "Post-meal 10-minute walk",
            detail: "A short walk after one meal today. Helps how that meal lands on your clock.",
            category: "movement",
            target: 0,
            rewardEstimateMinutes: 12
        )

        let stairsQuest = Quest(
            slug: "movement.stairs-instead.v1",
            date: today,
            title: "Take the stairs today",
            detail: "Skip elevators where you can. Small repeated effort beats one heroic workout.",
            category: "movement",
            target: 0,
            rewardEstimateMinutes: 10
        )

        return [stepsQuest, walkQuest, stairsQuest]
    }

    private func sleepRecoveryVariants(today: Date, profile: UserProfile, snapshot: DailyHealthSnapshot?, habits: HabitLog?) -> [Quest] {
        let consistencyQuest = Quest(
            slug: "sleep.consistency.v1",
            date: today,
            title: "Protect tomorrow's sleep",
            detail: "Be in bed within an hour of your usual time. Consistency matters more than total hours.",
            category: "sleep",
            target: profile.sleepGoalHours,
            rewardEstimateMinutes: 18
        )
        consistencyQuest.progress = snapshot?.sleepHours ?? 0

        let windDownQuest = Quest(
            slug: "sleep.wind-down.v1",
            date: today,
            title: "30-minute wind-down",
            detail: "Dim lights and step away from screens 30 minutes before bed. The brain needs a runway.",
            category: "sleep",
            target: 0,
            rewardEstimateMinutes: 14
        )

        let hydrationQuest = Quest(
            slug: "recovery.hydration-early-night.v1",
            date: today,
            title: "Hydration + early night",
            detail: "Aim for water before sleep. Tomorrow's clock recovers fastest with rest.",
            category: "recovery",
            target: 0,
            rewardEstimateMinutes: 10
        )

        // Heavy alcohol day → recovery moves to the front.
        if habits?.alcoholLevel.lowercased() == "heavy" {
            return [hydrationQuest, consistencyQuest, windDownQuest]
        }
        return [consistencyQuest, windDownQuest, hydrationQuest]
    }

    private func nutritionHabitVariants(today: Date, habits: HabitLog?) -> [Quest] {
        // Heavy-alcohol day: the recovery quest in the sleep/recovery slot
        // IS the message for the day. Surfacing a nutrition quest alongside
        // dilutes that single, gentle nudge — the prior single-slot engine
        // chose recovery and stopped, and the picker keeps that semantics.
        if habits?.alcoholLevel.lowercased() == "heavy" {
            return []
        }
        let dietRoughQuest = Quest(
            slug: "nutrition.one-better-meal.v1",
            date: today,
            title: "One better meal tomorrow",
            detail: "A rough food day is feedback, not failure. One simple, whole-food meal moves things back.",
            category: "nutrition",
            target: 0,
            rewardEstimateMinutes: 12
        )

        let logDietQuest = Quest(
            slug: "nutrition.log-diet-quality.v1",
            date: today,
            title: "Log your diet quality tonight",
            detail: "Great, okay, or rough — coarse is fine. Logging is what makes food visible on your clock.",
            category: "nutrition",
            target: 0,
            rewardEstimateMinutes: 8
        )

        let rotatedQuest = rotatingNutritionQuest(today: today)
        let proteinQuest = Quest(
            slug: "nutrition.add-protein.v1",
            date: today,
            title: "Add protein to your next meal",
            detail: "Eggs, beans, fish, chicken, tofu — pick one. No measuring required.",
            category: "nutrition",
            target: 0,
            rewardEstimateMinutes: 12
        )
        let wholeFoodQuest = Quest(
            slug: "nutrition.whole-food-meal.v1",
            date: today,
            title: "Add one whole-food meal",
            detail: "A piece of fruit, a handful of nuts, a real cooked meal — anything unprocessed counts.",
            category: "nutrition",
            target: 0,
            rewardEstimateMinutes: 12
        )

        // Smart-default ordering: most-relevant pick first; the other two
        // are swap options. Dedupe: when the day's rotated quest collides
        // with the static protein quest (the rotating pool also contains
        // add-protein), substitute whole-food so the picker always offers
        // three distinct slugs.
        let alt = (rotatedQuest.slug == proteinQuest.slug) ? wholeFoodQuest : proteinQuest
        if habits?.dietQuality.lowercased() == "rough" {
            return [dietRoughQuest, rotatedQuest, alt]
        }
        if habits?.dietQuality == nil || habits?.dietQuality.lowercased() == "unknown" {
            return [logDietQuest, rotatedQuest, alt]
        }
        return [rotatedQuest, alt, dietRoughQuest]
    }

    private func rotatingNutritionQuest(today: Date) -> Quest {
        // Deterministic rotation by day-of-year parity. Six gentle nutrition
        // nudges; none reference calories, macros, or named diets.
        let dayOfYear = clock.calendar.ordinality(of: .day, in: .year, for: today) ?? 0
        let pool: [(slug: String, title: String, detail: String, reward: Int)] = [
            ("nutrition.whole-food-meal.v1", "Add one whole-food meal", "A piece of fruit, a handful of nuts, a real cooked meal — anything unprocessed counts.", 12),
            ("nutrition.walk-after-dinner.v1", "Walk 10 minutes after dinner", "A short post-dinner walk smooths how today's meals affect your clock.", 14),
            ("nutrition.water-with-meal.v1", "Choose water with one meal", "Skip the sweetened drink at one meal today. That's the whole focus.", 10),
            ("nutrition.add-protein.v1", "Add protein to your next meal", "Eggs, beans, fish, chicken, tofu — pick one. No measuring required.", 12),
            ("nutrition.eat-meal-slowly.v1", "Eat one meal slowly", "Phone down, fork down between bites. Slower meals tend to be smaller meals without trying.", 10),
            ("nutrition.less-processed.v1", "Make one meal less processed", "Swap one packaged item for something whole. One meal, not your whole day.", 12),
        ]
        let pick = pool[dayOfYear % pool.count]
        return Quest(
            slug: pick.slug,
            date: today,
            title: pick.title,
            detail: pick.detail,
            category: "nutrition",
            target: 0,
            rewardEstimateMinutes: pick.reward
        )
    }

    /// Rolling-median step target. Uses the user's last ~14 days of logged
    /// steps (any snapshots passed in; caller controls the window) and
    /// returns p50 × 1.10, rounded to the nearest 500. Floored at 5,000
    /// (no demoralizingly tiny goals) and capped at 20,000 (no Strava-bro
    /// targets for casual users). Falls back to the historical 7,500
    /// default when we have fewer than 5 days of data, since p50 on a
    /// thin sample is noise.
    static let defaultStepTarget: Double = 7_500
    private func movementStepTarget(recentSnapshots: [DailyHealthSnapshot]) -> Double {
        let logged = recentSnapshots.compactMap { $0.stepCount }.filter { $0 > 0 }
        guard logged.count >= 5 else { return Self.defaultStepTarget }
        let sorted = logged.sorted()
        let p50 = Double(sorted[sorted.count / 2])
        let scaled = (p50 * 1.10 / 500).rounded() * 500
        return min(20_000, max(5_000, scaled))
    }

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
