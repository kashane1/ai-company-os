import Foundation
import SwiftUI

enum AppTab: String {
    case today
    case history
    case future
    case profile

    var title: String {
        switch self {
        case .today: return "Today"
        case .history: return "History"
        case .future: return "Future"
        case .profile: return "Profile"
        }
    }

    var systemImage: String {
        switch self {
        case .today: return "clock.fill"
        case .history: return "clock.arrow.circlepath"
        case .future: return "chart.line.uptrend.xyaxis"
        case .profile: return "person.crop.circle"
        }
    }
}
