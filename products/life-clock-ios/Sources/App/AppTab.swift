import Foundation
import SwiftUI

enum AppTab: String {
    case today
    case ledger
    case quests
    case history
    case profile

    var title: String {
        switch self {
        case .today: return "Today"
        case .ledger: return "Progress"
        case .quests: return "Plan"
        case .history: return "History"
        case .profile: return "Profile"
        }
    }

    var systemImage: String {
        switch self {
        case .today: return "clock.fill"
        case .ledger: return "list.bullet.rectangle.portrait"
        case .quests: return "checkmark.circle"
        case .history: return "clock.arrow.circlepath"
        case .profile: return "person.crop.circle"
        }
    }
}
