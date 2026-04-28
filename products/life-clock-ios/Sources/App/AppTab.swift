import Foundation
import SwiftUI

enum AppTab: String, CaseIterable, Identifiable {
    case today
    case ledger
    case quests
    case weekly
    case profile

    var id: String { rawValue }

    var title: String {
        switch self {
        case .today: return "Today"
        case .ledger: return "Ledger"
        case .quests: return "Quests"
        case .weekly: return "Weekly"
        case .profile: return "Profile"
        }
    }

    var systemImage: String {
        switch self {
        case .today: return "clock.fill"
        case .ledger: return "list.bullet.rectangle.portrait"
        case .quests: return "checkmark.circle"
        case .weekly: return "chart.line.uptrend.xyaxis"
        case .profile: return "person.crop.circle"
        }
    }
}
