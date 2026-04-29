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
        case .mementoMori: return "Memento Mori"
        }
    }

    var description: String {
        switch self {
        case .gentle:
            return "Healthspan score, time earned, future-self framing. No mortality language."
        case .coach:
            return "Default. Uses the Life Clock but stays motivating, not punishing."
        case .mementoMori:
            return "Direct mortality framing. Still avoids medical certainty."
        }
    }

    /// Copy keys vary by tone. Today screen uses these.
    var todayHeadline: String {
        switch self {
        case .gentle: return "Healthspan today"
        case .coach: return "Your Life Clock today"
        case .mementoMori: return "Your time today"
        }
    }

    var deltaPositivePrefix: String {
        switch self {
        case .gentle: return "Time earned"
        case .coach: return "Clock moved"
        case .mementoMori: return "Earned back"
        }
    }

    var deltaNegativePrefix: String {
        switch self {
        case .gentle: return "Time at risk"
        case .coach: return "Clock pulled back"
        case .mementoMori: return "Time lost"
        }
    }

    // MARK: - Tab titles

    var ledgerTitle: String {
        switch self {
        case .gentle: return "Time earned"
        case .coach: return "Time Ledger"
        case .mementoMori: return "Ledger"
        }
    }

    var questsTitle: String {
        switch self {
        case .gentle: return "Today's small wins"
        case .coach: return "Quests"
        case .mementoMori: return "Today's quests"
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
            return "Your ledger fills up with the small wins of each day."
        case .coach:
            return "No entries yet — your ledger fills up as data flows in."
        case .mementoMori:
            return "No entries yet. The clock waits for data."
        }
    }

    var questsPreamble: String {
        switch self {
        case .gentle:
            return "Pick one small thing. Showing up is the win."
        case .coach:
            return "1–3 quests per day. Pick one to do well."
        case .mementoMori:
            return "Today's levers. Use them."
        }
    }

    var weeklyEmptyState: String {
        switch self {
        case .gentle:
            return "Come back after a few days — patterns appear with time."
        case .coach:
            return "Weekly report will appear after a week of data."
        case .mementoMori:
            return "A week's data tells the truth a day cannot."
        }
    }
}
