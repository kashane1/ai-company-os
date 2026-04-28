import Foundation

enum ToneMode: String, CaseIterable, Codable, Identifiable {
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
}
