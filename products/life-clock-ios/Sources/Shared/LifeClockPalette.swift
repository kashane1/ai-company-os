import SwiftUI

/// The orange-not-red invariant ("never alarming red", founder pack)
/// is enforced by the absence of a `negative` field — the negative-delta
/// color stays as a constant on `DesignTokens.Palette`.
enum LifeClockPalette: String, CaseIterable, Identifiable {
    case defaultNavy = "default-navy"
    case auroraCool  = "aurora-cool"
    case sunsetWarm  = "sunset-warm"

    var id: String { rawValue }

    var displayName: String {
        switch self {
        case .defaultNavy: "Default Navy"
        case .auroraCool:  "Aurora Cool"
        case .sunsetWarm:  "Sunset Warm"
        }
    }

    var accent: Color {
        switch self {
        case .defaultNavy:
            Color(red: 0.137, green: 0.282, blue: 0.612)
        case .auroraCool:
            // Picks up the icon's blue chrome side.
            Color(red: 0.231, green: 0.357, blue: 0.749)
        case .sunsetWarm:
            // Light-mode text contrast borderline — track contrast in follow-up.
            Color(red: 0.85, green: 0.42, blue: 0.20)
        }
    }
}
