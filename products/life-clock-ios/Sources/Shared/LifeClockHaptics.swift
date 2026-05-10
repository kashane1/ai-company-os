import SwiftUI

/// Central policy for Life Clock's tactile language.
///
/// Keep this small and boring: haptics should underline agency and confirmation,
/// not become a second emotional voice competing with tone copy.
enum LifeClockHaptics {
    static let morningWake: SensoryFeedback = .impact(weight: .light)
    static let firstReveal: SensoryFeedback = .impact(weight: .light)
    static let monthlyMilestone: SensoryFeedback = .success
    static let purchaseSuccess: SensoryFeedback = .success
    static let questCompletion: SensoryFeedback = .success

    static func wrapUp(signedMinutes: Int) -> SensoryFeedback {
        if signedMinutes > 0 { return .success }
        if signedMinutes < 0 { return .impact(weight: .light) }
        return .selection
    }
}
