import Foundation

/// Presentation logic for the engine-reveal screen — owns the year→minute
/// mapping that drives the LifeClockMascotView's hands while the user drags
/// the ±5-year dial.
///
/// **Why a presenter, not inline:** the mascot's contract is a pure
/// `minutesDelta: Int` input (matches `ClockHandView`'s 6°/min convention).
/// Years-of-projected-healthspan is a different unit; one of these constants
/// must do the translation, and putting it in one named place keeps the
/// magic numbers out of the view body and out of the mascot primitive.
///
/// **Mapping:** 1 year ≈ `minutesPerYear` (6) minutes, hard-clamped to
/// `[minMinutes, maxMinutes]` (±60). The clamp keeps the visible sweep
/// inside one rotation — the headline number text is the source of truth
/// past the cap.
enum EngineRevealPresenter {
    static let minutesPerYear: Int = 6
    static let minMinutes: Int = -60
    static let maxMinutes: Int = 60

    /// Maps the engine reveal screen's `(displayedYears, baselineYears)` pair
    /// to a clamped integer minute delta suitable for `LifeClockMascotView`.
    static func mascotDelta(displayedYears: Double, baselineYears: Double) -> Int {
        let raw = Int(((displayedYears - baselineYears) * Double(minutesPerYear)).rounded())
        return min(max(raw, minMinutes), maxMinutes)
    }
}
