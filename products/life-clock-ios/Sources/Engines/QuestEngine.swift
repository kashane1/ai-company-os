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
    let clock: EngineClock

    init(clock: EngineClock = .live) {
        self.clock = clock
    }

    func generateDailyQuests(
        profile: UserProfile,
        snapshot: DailyHealthSnapshot?,
        habits: HabitLog?
    ) -> [Quest] {
        let today = clock.calendar.startOfDay(for: clock.now())
        var quests: [Quest] = []

        if let movement = movementQuest(today: today, snapshot: snapshot) {
            quests.append(movement)
        }
        quests.append(sleepQuest(today: today, profile: profile, snapshot: snapshot))

        // Third slot — nutrition by default, recovery/risk when the day's
        // logged state calls for it. This is where the "diet is a primary
        // lever" framing lives.
        quests.append(habitOrNutritionQuest(today: today, habits: habits))

        if quests.isEmpty {
            quests.append(consistencyFallback(today: today))
        }

        return Array(quests.prefix(3))
    }

    // MARK: - Quest generators

    private func movementQuest(today: Date, snapshot: DailyHealthSnapshot?) -> Quest? {
        let target: Double = 7_500
        let progress = Double(snapshot?.stepCount ?? 0)
        let detail: String
        if let steps = snapshot?.stepCount, steps >= Int(target) {
            return nil // already done
        }
        if snapshot?.stepCount == nil {
            detail = "Take a 10-minute walk after a meal today."
        } else {
            detail = "Get to \(Int(target)) steps. A short post-dinner walk usually closes the gap."
        }
        let quest = Quest(
            date: today,
            title: "Move a little more",
            detail: detail,
            category: "movement",
            target: target,
            rewardEstimateMinutes: 18
        )
        quest.progress = progress
        return quest
    }

    private func sleepQuest(today: Date, profile: UserProfile, snapshot: DailyHealthSnapshot?) -> Quest {
        let detail = "Be in bed within an hour of your usual time. Consistency matters more than total hours."
        let quest = Quest(
            date: today,
            title: "Protect tomorrow's sleep",
            detail: detail,
            category: "sleep",
            target: profile.sleepGoalHours,
            rewardEstimateMinutes: 18
        )
        quest.progress = snapshot?.sleepHours ?? 0
        return quest
    }

    /// Picks the most relevant third quest from the user's logged state.
    ///
    /// Priority:
    ///   1. Heavy alcohol logged → recovery quest (gentle, never punitive).
    ///   2. Rough diet logged → nutrition-repair quest (one-meal nudge).
    ///   3. No diet logged yet → "log diet quality tonight" prompt.
    ///   4. Otherwise → rotating nutrition quest (deterministic, day-of-year
    ///      parity).
    private func habitOrNutritionQuest(today: Date, habits: HabitLog?) -> Quest {
        if habits?.alcoholLevel.lowercased() == "heavy" {
            return Quest(
                date: today,
                title: "Hydration + early night",
                detail: "Aim for water before sleep. Tomorrow's clock recovers fastest with rest.",
                category: "recovery",
                target: 0,
                rewardEstimateMinutes: 10
            )
        }

        if habits?.dietQuality.lowercased() == "rough" {
            return Quest(
                date: today,
                title: "One better meal tomorrow",
                detail: "A rough food day is feedback, not failure. One simple, whole-food meal moves things back.",
                category: "nutrition",
                target: 0,
                rewardEstimateMinutes: 12
            )
        }

        if habits?.dietQuality == nil || habits?.dietQuality.lowercased() == "unknown" {
            return Quest(
                date: today,
                title: "Log your diet quality tonight",
                detail: "Great, okay, or rough — coarse is fine. Logging is what makes food visible on your clock.",
                category: "nutrition",
                target: 0,
                rewardEstimateMinutes: 8
            )
        }

        return rotatingNutritionQuest(today: today)
    }

    private func rotatingNutritionQuest(today: Date) -> Quest {
        // Deterministic rotation by day-of-year parity. Six gentle nutrition
        // nudges; none reference calories, macros, or named diets.
        let dayOfYear = clock.calendar.ordinality(of: .day, in: .year, for: today) ?? 0
        let pool: [(title: String, detail: String, reward: Int)] = [
            ("Add one whole-food meal", "A piece of fruit, a handful of nuts, a real cooked meal — anything unprocessed counts.", 12),
            ("Walk 10 minutes after dinner", "A short post-dinner walk smooths how today's meals affect your clock.", 14),
            ("Choose water with one meal", "Skip the sweetened drink at one meal today. That's the whole focus.", 10),
            ("Add protein to your next meal", "Eggs, beans, fish, chicken, tofu — pick one. No measuring required.", 12),
            ("Eat one meal slowly", "Phone down, fork down between bites. Slower meals tend to be smaller meals without trying.", 10),
            ("Make one meal less processed", "Swap one packaged item for something whole. One meal, not your whole day.", 12),
        ]
        let pick = pool[dayOfYear % pool.count]
        return Quest(
            date: today,
            title: pick.title,
            detail: pick.detail,
            category: "nutrition",
            target: 0,
            rewardEstimateMinutes: pick.reward
        )
    }

    private func consistencyFallback(today: Date) -> Quest {
        Quest(
            date: today,
            title: "Open the app tomorrow",
            detail: "The clock improves most from showing up daily.",
            category: "consistency",
            target: 1,
            rewardEstimateMinutes: 0
        )
    }
}
