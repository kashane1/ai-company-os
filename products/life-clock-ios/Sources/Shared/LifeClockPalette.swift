import SwiftUI

/// User-selectable color palette. Mirrors the `ToneMode` enum-rawValue
/// pattern: persisted as a `String` on `UserProfile.paletteId`, restored
/// via `LifeClockPalette(rawValue:)` with a fallback to `.defaultNavy`.
///
/// Per-palette fields are deliberately limited to `displayName` and
/// `accent`. The negative-delta color is constant (`Color.orange` on
/// `DesignTokens.Palette`) — the founder-pack rule "never alarming red"
/// is enforced structurally by the absence of a `negative` field here,
/// not by per-palette discipline.
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

    /// Primary tint. Applied at the app root via `.tint(_:)` and
    /// propagated to all SwiftUI controls (Buttons, Toggles, Pickers,
    /// NavigationStack chevrons, TabView selection, links).
    var accent: Color {
        switch self {
        case .defaultNavy:
            // Matches AccentColor.colorset (R 0.137, G 0.282, B 0.612 → #23489C).
            Color(red: 0.137, green: 0.282, blue: 0.612)
        case .auroraCool:
            // Cooler indigo — picks up the icon's blue chrome side.
            Color(red: 0.231, green: 0.357, blue: 0.749)
        case .sunsetWarm:
            // Warm amber. Dark-mode contrast is acceptable; light-mode
            // text contrast is borderline — track in follow-up.
            Color(red: 0.85, green: 0.42, blue: 0.20)
        }
    }
}
