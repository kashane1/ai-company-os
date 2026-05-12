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

    // MARK: - Future tab warming-up transparency line (V1.7.0)
    //
    // Day 4–13 transparency: N-aware copy, pre-authored per N per tone.
    // Pool-with-discrete-N rather than templated `String(format:)` so
    // each tone-N combination can carry tone-distinct phrasing. Per
    // `docs/products/life-clock/future-tab-tone-pools-spec.md`.
    //
    // Indexing: clamps N to 4..13 then subtracts 4 for array offset.
    // Out-of-range N returns the closest in-range string (defense for
    // an unexpected dayState computation; the day-state machine should
    // not call this with N outside [4,13]).
    private static let warmingUpGentle: [String] = [
        "4 days in. Your projection is taking shape — the picture sharpens through day 14.",
        "5 days of signal. Still warming up; full confidence at day 14.",
        "6 days logged. The trajectory is forming.",
        "One week in. Your projection still has room to settle.",
        "8 days of data. The chart is finding its footing.",
        "9 days in. Five more days reach full confidence.",
        "10 days. Almost the full window.",
        "11 days. Confidence is climbing.",
        "12 days. Two days from full read.",
        "13 days. Tomorrow your full 14-day window kicks in.",
    ]

    private static let warmingUpCoach: [String] = [
        "4 of 14 days logged. Projection sharpens through day 14.",
        "5 of 14. Building toward full confidence.",
        "6 of 14. Trajectory taking shape.",
        "Week one done. Halfway to full read.",
        "8 of 14. Signal is clarifying.",
        "9 of 14. Five days to full window.",
        "10 of 14. Closing in.",
        "11 of 14. Three more days.",
        "12 of 14. Two more days.",
        "13 of 14. Full window opens tomorrow.",
    ]

    private static let warmingUpFirmDirect: [String] = [
        "4/14 days. Full read at 14.",
        "5/14. Building.",
        "6/14.",
        "7/14. Halfway.",
        "8/14.",
        "9/14. Five days out.",
        "10/14.",
        "11/14. Three days.",
        "12/14. Two days.",
        "13/14. Tomorrow.",
    ]

    static func futureWarmingUpTransparency(daysOfData: Int, tone: ToneMode) -> String {
        let clamped = max(4, min(13, daysOfData))
        let index = clamped - 4
        switch tone {
        case .gentle: return warmingUpGentle[index]
        case .coach: return warmingUpCoach[index]
        case .firmDirect: return warmingUpFirmDirect[index]
        }
    }
}
