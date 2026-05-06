import Foundation

struct CompletionBadge: Identifiable, Equatable {
    enum Category: String, CaseIterable {
        case onboarding
        case dailyPlan
        case consistency
        case movement
        case exercise
        case sleep
        case nutrition
        case recovery
        case strength
        case weekly
        case data

        var displayName: String {
            switch self {
            case .onboarding: return "Getting started"
            case .dailyPlan: return "Daily plan"
            case .consistency: return "Consistency"
            case .movement: return "Movement"
            case .exercise: return "Exercise"
            case .sleep: return "Sleep"
            case .nutrition: return "Nutrition"
            case .recovery: return "Recovery"
            case .strength: return "Strength"
            case .weekly: return "Weekly wins"
            case .data: return "Data"
            }
        }
    }

    enum Tier: Int, Comparable {
        case starter = 0
        case bronze = 1
        case silver = 2
        case gold = 3
        case platinum = 4

        static func < (lhs: Tier, rhs: Tier) -> Bool {
            lhs.rawValue < rhs.rawValue
        }
    }

    let id: String
    let title: String
    let detail: String
    let systemImage: String
    let category: Category
    let tier: Tier
    let progress: Int
    let target: Int
    let unlockedAt: Date?

    var isUnlocked: Bool {
        progress >= target
    }

    var progressFraction: Double {
        guard target > 0 else { return isUnlocked ? 1 : 0 }
        return min(1, Double(progress) / Double(target))
    }

    var progressText: String {
        "\(min(progress, target))/\(target)"
    }
}

struct CompletionBadgeProgress {
    var onboardedAt: Date?
    var completedQuestCount: Int = 0
    var completedQuestDays: Int = 0
    var threeQuestDays: Int = 0
    var checkInDays: Int = 0
    /// Distinct days logged in the current calendar month. Replaced the old
    /// `dietLoggingStreakDays` (rolling-streak metric) on 2026-05-06 when
    /// vision Q7 resolved to "monthly count, no streak."
    var monthlyLogDays: Int = 0
    var supportiveDietDays: Int = 0
    var greatDietDays: Int = 0
    var lowRiskRecoveryDays: Int = 0
    var strengthDays: Int = 0
    var stepTargetDays: Int = 0
    var tenThousandStepDays: Int = 0
    var exerciseTargetDays: Int = 0
    var sleepGoalDays: Int = 0
    var positiveWeekCount: Int = 0
    var dataRichDays: Int = 0
    var healthConnected: Bool = false
    var reminderEnabled: Bool = false
}

struct CompletionBadgeEngine {
    private struct Definition {
        let id: String
        let title: String
        let detail: String
        let systemImage: String
        let category: CompletionBadge.Category
        let tier: CompletionBadge.Tier
        let target: Int
        let value: (CompletionBadgeProgress) -> Int
    }

    func badges(for progress: CompletionBadgeProgress) -> [CompletionBadge] {
        definitions.map { definition in
            let value = definition.value(progress)
            return CompletionBadge(
                id: definition.id,
                title: definition.title,
                detail: definition.detail,
                systemImage: definition.systemImage,
                category: definition.category,
                tier: definition.tier,
                progress: value,
                target: definition.target,
                unlockedAt: unlockedAt(for: definition, progress: progress)
            )
        }
        .sorted { lhs, rhs in
            if lhs.isUnlocked != rhs.isUnlocked {
                return lhs.isUnlocked && !rhs.isUnlocked
            }
            if lhs.category.displayName != rhs.category.displayName {
                return lhs.category.displayName < rhs.category.displayName
            }
            if lhs.tier != rhs.tier {
                return lhs.tier > rhs.tier
            }
            return lhs.title < rhs.title
        }
    }

    private func unlockedAt(for definition: Definition, progress: CompletionBadgeProgress) -> Date? {
        guard definition.value(progress) >= definition.target else { return nil }
        return progress.onboardedAt
    }

    private var definitions: [Definition] {
        return [
            Definition(
                id: "start.first-profile",
                title: "Clock started",
                detail: "Completed onboarding.",
                systemImage: "sparkles",
                category: .onboarding,
                tier: .starter,
                target: 1,
                value: { $0.onboardedAt == nil ? 0 : 1 }
            ),
            Definition(
                id: "start.health-connected",
                title: "Signal linked",
                detail: "Connected a health data source.",
                systemImage: "heart.text.square",
                category: .data,
                tier: .starter,
                target: 1,
                value: { $0.healthConnected ? 1 : 0 }
            ),
            Definition(
                id: "start.reminder-enabled",
                title: "Future nudge",
                detail: "Enabled the daily reminder.",
                systemImage: "bell.badge",
                category: .consistency,
                tier: .starter,
                target: 1,
                value: { $0.reminderEnabled ? 1 : 0 }
            ),
        ] + tiered(
            base: "plan.completed",
            title: "Action finisher",
            detail: "Completed planned actions.",
            image: "checkmark.circle.fill",
            category: .dailyPlan,
            thresholds: [(1, .starter), (10, .bronze), (25, .silver), (50, .gold), (100, .platinum)],
            value: \.completedQuestCount
        ) + tiered(
            base: "plan.days",
            title: "Showed up",
            detail: "Completed at least one planned action in a day.",
            image: "calendar.badge.checkmark",
            category: .dailyPlan,
            thresholds: [(1, .starter), (7, .bronze), (21, .silver), (50, .gold)],
            value: \.completedQuestDays
        ) + tiered(
            base: "plan.three",
            title: "Full plan clear",
            detail: "Completed three planned actions in a day.",
            image: "checklist.checked",
            category: .dailyPlan,
            thresholds: [(1, .bronze), (7, .silver), (21, .gold)],
            value: \.threeQuestDays
        ) + tiered(
            base: "checkin.days",
            title: "Daily check-in",
            detail: "Saved daily check-ins.",
            image: "square.and.pencil",
            category: .consistency,
            thresholds: [(1, .starter), (7, .bronze), (30, .silver), (100, .gold)],
            value: \.checkInDays
        ) + tiered(
            base: "movement.steps7500",
            title: "Step target",
            detail: "Hit 7,500 steps in a day.",
            image: "figure.walk",
            category: .movement,
            thresholds: [(1, .starter), (7, .bronze), (30, .silver), (100, .gold)],
            value: \.stepTargetDays
        ) + tiered(
            base: "movement.steps10000",
            title: "Big step day",
            detail: "Hit 10,000 steps in a day.",
            image: "shoeprints.fill",
            category: .movement,
            thresholds: [(1, .bronze), (7, .silver), (30, .gold)],
            value: \.tenThousandStepDays
        ) + tiered(
            base: "exercise.minutes30",
            title: "Exercise target",
            detail: "Logged 30 active minutes in a day.",
            image: "figure.run",
            category: .exercise,
            thresholds: [(1, .starter), (7, .bronze), (30, .silver), (100, .gold)],
            value: \.exerciseTargetDays
        ) + tiered(
            base: "sleep.goal",
            title: "Sleep protected",
            detail: "Met your sleep goal.",
            image: "moon.zzz.fill",
            category: .sleep,
            thresholds: [(1, .starter), (7, .bronze), (30, .silver), (100, .gold)],
            value: \.sleepGoalDays
        ) + tiered(
            base: "nutrition.supportive",
            title: "Supportive food day",
            detail: "Logged a great or okay food day.",
            image: "leaf.fill",
            category: .nutrition,
            thresholds: [(1, .starter), (7, .bronze), (30, .silver), (100, .gold)],
            value: \.supportiveDietDays
        ) + tiered(
            base: "nutrition.great",
            title: "Great food day",
            detail: "Logged a great food day.",
            image: "carrot.fill",
            category: .nutrition,
            thresholds: [(1, .bronze), (7, .silver), (30, .gold)],
            value: \.greatDietDays
        ) + tiered(
            base: "nutrition.month",
            title: "Days logged this month",
            detail: "Logged a diet day this month.",
            image: "calendar",
            category: .nutrition,
            thresholds: [(3, .bronze), (7, .silver), (14, .gold), (30, .platinum)],
            value: \.monthlyLogDays
        ) + tiered(
            base: "recovery.lowrisk",
            title: "Clean recovery day",
            detail: "Logged no nicotine and no heavy alcohol.",
            image: "heart.fill",
            category: .recovery,
            thresholds: [(1, .starter), (7, .bronze), (30, .silver), (100, .gold)],
            value: \.lowRiskRecoveryDays
        ) + tiered(
            base: "strength.days",
            title: "Strength done",
            detail: "Logged strength training.",
            image: "dumbbell.fill",
            category: .strength,
            thresholds: [(1, .starter), (8, .bronze), (24, .silver), (52, .gold)],
            value: \.strengthDays
        ) + tiered(
            base: "weekly.positive",
            title: "Positive week",
            detail: "Finished a week with net time gained.",
            image: "chart.line.uptrend.xyaxis",
            category: .weekly,
            thresholds: [(1, .bronze), (4, .silver), (12, .gold)],
            value: \.positiveWeekCount
        ) + tiered(
            base: "data.rich",
            title: "Rich signal day",
            detail: "Captured a day with strong data completeness.",
            image: "waveform.path.ecg",
            category: .data,
            thresholds: [(1, .starter), (7, .bronze), (30, .silver), (100, .gold)],
            value: \.dataRichDays
        )
    }

    private func tiered(
        base: String,
        title: String,
        detail: String,
        image: String,
        category: CompletionBadge.Category,
        thresholds: [(Int, CompletionBadge.Tier)],
        value: KeyPath<CompletionBadgeProgress, Int>
    ) -> [Definition] {
        thresholds.map { threshold, tier in
            Definition(
                id: "\(base).\(threshold)",
                title: threshold == 1 ? title : "\(title) \(threshold)",
                detail: detail,
                systemImage: image,
                category: category,
                tier: tier,
                target: threshold,
                value: { progress in progress[keyPath: value] }
            )
        }
    }
}
