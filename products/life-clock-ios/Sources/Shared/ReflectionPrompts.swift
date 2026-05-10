import Foundation

/// Per-tone pools of reflection prompts surfaced one-at-a-time on the
/// Today screen's Reflection card. Selection is deterministic by
/// day-of-year so the prompt is stable across renders within a single
/// calendar day and rotates predictably across days.
///
/// Tones match the voice register defined in `ToneMode`:
/// - `gentle` — soft, curious, body-aware
/// - `coach` — motivational, action-oriented, supportive accountability
/// - `firmDirect` — blunt, no hedging, the clock keeps score
///
/// IMPORTANT: do NOT use `Calendar.Component.dayOfYear` — that case is
/// `@available(iOS 18, ...)` and the Life Clock deployment target is
/// iOS 17. Use `Calendar.ordinality(of: .day, in: .year, for:)` which
/// is iOS 8+ and computes the same value (1...365 / 1...366).
enum ReflectionPrompts {
    // 2026-05-10 vision-bad-day-gentle-coach-pools audit: cycled the
    // rotation across all 12 gentle entries against the −1h 37m bad-day
    // stack and softened two that collapsed into toothless platitude
    // ("Where did you give yourself a little kindness today?" presupposed
    // it happened on a clearly-rough day; "What are you grateful for in
    // your body today?" obligated gratitude on a day the user just saw
    // pulling against their healthspan). Rewrites stay warm and
    // body-aware — they invite rather than presuppose. The remaining ten
    // are unchanged.
    static let gentlePool: [String] = [
        "What did you notice about how your body felt today?",
        "What's one moment from today you want to hold onto?",
        "Where could you offer yourself a little kindness tonight?",
        "What's one signal your body is sending you?",
        "What's one thing your body did for you today?",
        "What's one habit that's quietly helping you?",
        "What pulled you gently off course today?",
        "What surprised you about today?",
        "What's one small thing tomorrow could hold?",
        "What did today teach you about your own pace?",
        "What's one thing you can let go of tonight?",
        "Where did your body ask for rest today?",
    ]

    // 2026-05-10 vision-bad-day-gentle-coach-pools audit: same cycle, three
    // coach entries failed the bad-day reading. "Where did you choose the
    // harder, healthier option?" and "Where did you stick to the plan…?"
    // both presupposed adherence on a −1h 37m day. "What did you avoid
    // today that you can't keep avoiding?" crossed register into
    // firmDirect ("can't keep avoiding" mirrors firmDirect's "move you
    // keep stalling on"). Rewrites keep coach's forward, action-oriented
    // posture without presupposing or accusing. The remaining nine are
    // unchanged.
    static let coachPool: [String] = [
        "What's one decision today that future-you would thank you for?",
        "What's one harder, healthier option open to you tomorrow?",
        "What's one small thing you'd do differently tomorrow?",
        "What's getting in the way of the day you wanted?",
        "What did you learn about yourself today?",
        "What would tomorrow look like if today was a fresh start?",
        "What's one habit moving the needle right now?",
        "What's a plan you want to hold to tomorrow?",
        "What's the one move that would make tomorrow easier?",
        "What's something you've been putting off that would help tomorrow?",
        "What would the next steady version of you do right now?",
        "What's one win from today, however small?",
    ]

    // 2026-05-07 vision-bad-day-three-tones audit (V1) softened the three
    // most accusatory prompts that stacked on top of "Today's reckoning /
    // Owed today / -1h 37m" on a clearly-negative day. Register stays
    // pointed; accusation goes. Held three slots: "lie you told yourself"
    // → "story you told yourself"; "smallest hard thing you ducked" →
    // "smallest hard thing you'll face tonight"; "excuse you're tired of
    // hearing yourself make" → "move you keep stalling on". The remaining
    // nine prompts are unchanged — firmDirect still keeps score.
    static let firmDirectPool: [String] = [
        "What did you do today that bought time on the clock?",
        "What did you do today that cost you?",
        "What's the story you told yourself today?",
        "What's the smallest hard thing you'll face tonight?",
        "What would you change if today were on the record?",
        "What did the clock just say about your choices?",
        "What's the next move — and are you actually going to make it?",
        "Where did you settle today?",
        "What's the move you keep stalling on?",
        "What did you put off that you keep putting off?",
        "Who do you want to be tomorrow — and what does that cost tonight?",
        "What's the one decision today you'd want back?",
    ]

    /// Returns the prompt for the calendar day containing `date`, drawn
    /// from the pool that matches `tone`. Deterministic: same
    /// `(date, calendar, tone)` always returns the same prompt. Cheap
    /// enough to recompute on every render — the work is
    /// `Calendar.ordinality(...)` plus an array index over ~12 elements.
    static func prompt(
        for date: Date,
        tone: ToneMode,
        calendar: Calendar = .current
    ) -> String {
        let pool = self.pool(for: tone)
        let dayOfYear = calendar.ordinality(of: .day, in: .year, for: date) ?? 1
        return pool[(dayOfYear - 1) % pool.count]
    }

    static func pool(for tone: ToneMode) -> [String] {
        switch tone {
        case .gentle: return gentlePool
        case .coach: return coachPool
        case .firmDirect: return firmDirectPool
        }
    }
}
