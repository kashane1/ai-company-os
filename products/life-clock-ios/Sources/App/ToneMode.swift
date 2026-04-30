import Foundation

enum ToneMode: String, CaseIterable, Identifiable {
    case gentle
    case coach
    case mementoMori = "memento_mori"

    var id: String { rawValue }

    var displayName: String {
        switch self {
        case .gentle: return "Gentle"
        case .coach: return "Coach"
        case .mementoMori: return "Direct"
        }
    }

    var description: String {
        switch self {
        case .gentle:
            return "Keeps the focus on steady progress and supportive guidance."
        case .coach:
            return "Balanced guidance with clear progress language and supportive accountability."
        case .mementoMori:
            return "More direct about risk and long-term consequences, without fatalism."
        }
    }

    /// Copy keys vary by tone. Today screen uses these.
    var todayHeadline: String {
        switch self {
        case .gentle: return "Today"
        case .coach: return "Today's progress"
        case .mementoMori: return "Today's progress"
        }
    }

    var deltaPositivePrefix: String {
        switch self {
        case .gentle: return "Progress gained"
        case .coach: return "Progress today"
        case .mementoMori: return "Progress today"
        }
    }

    var deltaNegativePrefix: String {
        switch self {
        case .gentle: return "Needs attention"
        case .coach: return "Progress at risk"
        case .mementoMori: return "At risk today"
        }
    }

    // MARK: - Tab titles

    var ledgerTitle: String {
        switch self {
        case .gentle: return "Progress"
        case .coach: return "Progress"
        case .mementoMori: return "Progress"
        }
    }

    var questsTitle: String {
        switch self {
        case .gentle: return "Next steps"
        case .coach: return "Plan"
        case .mementoMori: return "Plan"
        }
    }

    var weeklyTitle: String {
        switch self {
        case .gentle: return "This week"
        case .coach: return "Weekly"
        case .mementoMori: return "Week in review"
        }
    }

    // MARK: - Empty / preamble copy

    var ledgerEmptyState: String {
        switch self {
        case .gentle:
            return "Your progress log fills up as you check in and data comes in."
        case .coach:
            return "No progress entries yet. Check in once and the story starts to build."
        case .mementoMori:
            return "No progress entries yet. A clearer picture starts with today's first check-in."
        }
    }

    var questsPreamble: String {
        switch self {
        case .gentle:
            return "Pick one supportive action. Showing up is a real win."
        case .coach:
            return "Choose one supportive action for today. Small steps count."
        case .mementoMori:
            return "Choose one action worth following through on today."
        }
    }

    var weeklyEmptyState: String {
        switch self {
        case .gentle:
            return "Come back after a few days — patterns appear with time."
        case .coach:
            return "Your weekly view will appear after a few days of data."
        case .mementoMori:
            return "A week's data reveals patterns a single day can't."
        }
    }
}
