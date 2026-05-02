import Foundation

/// Pool of reflection prompts surfaced one-at-a-time on the Today
/// screen's Reflection card. Selection is deterministic by day-of-year
/// so the prompt is stable across renders within a single calendar day
/// and rotates predictably across days.
///
/// IMPORTANT: do NOT use `Calendar.Component.dayOfYear` — that case is
/// `@available(iOS 18, ...)` and the Life Clock deployment target is
/// iOS 17. Use `Calendar.ordinality(of: .day, in: .year, for:)` which
/// is iOS 8+ and computes the same value (1...365 / 1...366).
enum ReflectionPrompts {
    static let pool: [String] = [
        "What's one decision today that future-you would thank you for?",
        "Where did you choose the harder, healthier option?",
        "What pulled you off your plan today?",
        "What's one small thing you'd do differently tomorrow?",
        "What did you notice about how your body felt today?",
        "What's one habit that's quietly helping you?",
        "What's getting in the way of the day you wanted?",
        "What surprised you about today?",
        "What would tomorrow look like if today was a fresh start?",
        "What's one moment from today you want to remember?",
        "What did you learn about yourself today?",
        "What's one thing you can let go of?",
        "What are you grateful for in your body today?",
        "What's one signal your body is sending you?",
        "What would the next steady version of you do right now?",
    ]

    /// Returns the prompt for the calendar day containing `date`.
    /// Deterministic: same `(date, calendar)` always returns the same
    /// prompt. Cheap enough to recompute on every render — the work is
    /// `Calendar.ordinality(...)` plus an array index over 15 elements.
    static func prompt(for date: Date, calendar: Calendar = .current) -> String {
        let dayOfYear = calendar.ordinality(of: .day, in: .year, for: date) ?? 1
        return pool[(dayOfYear - 1) % pool.count]
    }
}
