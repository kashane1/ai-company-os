import Foundation

/// Generates 1–3 daily quests deterministic given inputs and the engine clock.
///
/// Rules:
///   - Always returns 1, 2, or 3 quests. Never zero, never four+.
///   - Adapts to missing data: if no HealthKit snapshot, returns manual-log
///     friendly quests instead of step/HR-anchored ones.
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
        if let sleep = sleepQuest(today: today, profile: profile, snapshot: snapshot) {
            quests.append(sleep)
        }
        if let risk = riskReductionQuest(today: today, habits: habits) {
            quests.append(risk)
        }

        if quests.isEmpty {
            quests.append(consistencyFallback(today: today))
        }

        // Hard cap at 3.
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

    private func sleepQuest(today: Date, profile: UserProfile, snapshot: DailyHealthSnapshot?) -> Quest? {
        let target = profile.sleepGoalHours
        let detail = "Be in bed within an hour of your usual time. Consistency matters more than total hours."
        let quest = Quest(
            date: today,
            title: "Protect tomorrow's sleep",
            detail: detail,
            category: "sleep",
            target: target,
            rewardEstimateMinutes: 18
        )
        quest.progress = snapshot?.sleepHours ?? 0
        return quest
    }

    private func riskReductionQuest(today: Date, habits: HabitLog?) -> Quest? {
        // If user already logged a heavy alcohol day, suggest a recovery focus
        // — gentle, not punitive.
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
        // Default risk quest: a no-alcohol log for the day.
        return Quest(
            date: today,
            title: "Log no alcohol today",
            detail: "An alcohol-free day adds meaningful time over a week.",
            category: "risk",
            target: 0,
            rewardEstimateMinutes: 12
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
