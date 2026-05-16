import Foundation

/// Centralized copy catalog for the onboarding reveal escalator + paywall.
/// All strings keyed by `(tone, softened-register?)` and, where relevant,
/// by `(habitFailureMode, leverGuess, topLever, leverMatch)`.
///
/// **Why this file exists:** prior to the 2026-05-14 onboarding revamp,
/// reveal copy lived inline on each view and only `RevealEscalatorGentleCopy`
/// handled the softened-register branch. Adding tone × failure-mode ×
/// lever-match variants inline would have ballooned every view. Pulling
/// the copy here means the views stay layout-focused and the strings are
/// reviewable in one place.
///
/// **Tone discipline (binding):** every variant must be agency-framed —
/// no doom verbs, no medical-claim language, no streak-shame. The
/// `firmDirect` register is allowed to be short and pointed; it is NOT
/// allowed to be cruel. See `CLAUDE_HANDOFF.md` for the gate.
enum RevealCopy {

    // MARK: - "What we don't do" (between analyzing → archetypeReveal)
    //
    // Credibility beat. Pre-empts the doom-app suspicion right at the
    // moment a user is bracing for it. Tone-aware; softened-register users
    // see the same lines (the message is the same regardless of how
    // stressed/lonely they reported).

    static func whatWeDontDoTitle(tone: ToneMode) -> String {
        switch tone {
        case .gentle:     return "A few things you won't see here."
        case .coach:      return "What this isn't."
        case .firmDirect: return "What we don't do."
        }
    }

    static func whatWeDontDoBullets(tone: ToneMode) -> [String] {
        switch tone {
        case .gentle:
            return [
                "No looming death clock.",
                "No calorie counting.",
                "No daily weigh-ins.",
                "No streak shame if you miss a day.",
                "No guilt trips.",
                "No verdicts on who you are.",
                "No data leaves your phone.",
                "No unwanted notifications.",
            ]
        case .coach:
            return [
                "No looming death clock.",
                "No calorie counting.",
                "No daily weigh-ins.",
                "No streak shame.",
                "No guilt trips.",
                "No verdicts on you as a person.",
                "No data leaves your phone.",
                "No unwanted notifications.",
            ]
        case .firmDirect:
            return [
                "No looming death clock.",
                "No calorie counting.",
                "No daily weigh-ins.",
                "No streak shame.",
                "No guilt trips.",
                "No verdicts.",
                "No data leaves your phone.",
                "No unwanted notifications.",
            ]
        }
    }

    static func whatWeDontDoFooter(tone: ToneMode) -> String {
        switch tone {
        case .gentle:
            return "The clock moves with you, not at you."
        case .coach:
            return "The clock moves with you, not at you."
        case .firmDirect:
            return "The clock moves with you. Not at you."
        }
    }

    // MARK: - Archetype reveal — lever-guess payoff
    //
    // Shown on `archetypeReveal` once a user has answered `leverGuess`. If
    // their guess matches the engine's top lever, the prefix reads as
    // confirmation; if it doesn't, the prefix surprises without shaming.
    // `topLever.unanswered` (engine couldn't pick a clear top lever)
    // falls through to a neutral line that doesn't claim a winner.

    static func leverPayoffPrefix(
        tone: ToneMode,
        guess: LifeClockLever,
        top: LifeClockLever
    ) -> String {
        // Engine couldn't pick a clear winner — most often when the user
        // is roughly average across every input. Don't claim a match
        // either way; just acknowledge the question.
        if top == .unanswered || guess == .unanswered {
            switch tone {
            case .gentle:     return "You guessed your lever might be"
            case .coach:      return "You guessed"
            case .firmDirect: return "You guessed:"
            }
        }
        if guess == top {
            switch tone {
            case .gentle:     return "You called it —"
            case .coach:      return "You called it —"
            case .firmDirect: return "Called it."
            }
        }
        switch tone {
        case .gentle:     return "Most people guess differently here —"
        case .coach:      return "Most people guess wrong here —"
        case .firmDirect: return "Most guess wrong here."
        }
    }

    /// Body line under the prefix. `top == .unanswered` ⇒ neutral
    /// fallback that names what the clock will watch instead.
    static func leverPayoffBody(
        tone: ToneMode,
        top: LifeClockLever
    ) -> String {
        if top == .unanswered {
            switch tone {
            case .gentle:
                return "Your inputs read fairly balanced — the clock will watch which lever earns the most time as you log days."
            case .coach:
                return "Your inputs read balanced. The clock learns the top lever from your daily data."
            case .firmDirect:
                return "Inputs read balanced. Log days. The clock finds it."
            }
        }
        let name = top.displayName.lowercased()
        switch tone {
        case .gentle:
            return "The clock says your highest-leverage lever right now is \(name)."
        case .coach:
            return "The clock says your top lever right now is \(name)."
        case .firmDirect:
            return "Top lever: \(name)."
        }
    }

    // MARK: - Uncertainty chip (below archetype meters)
    //
    // Surfaces the "confidence shipped, not hidden" principle as a tappable
    // chip the user can pop open. Same line is quoted in the paywall body.

    static func uncertaintyChip(tone: ToneMode) -> String {
        switch tone {
        case .gentle:     return "First read — sharpens as the clock learns your patterns."
        case .coach:      return "First read. Sharpens as the clock learns your patterns."
        case .firmDirect: return "First read. Gets sharper with data."
        }
    }

    static func uncertaintyDetail(tone: ToneMode) -> String {
        switch tone {
        case .gentle:
            return "The clock starts with what you told us today, plus population data. Apple Health and your daily check-ins refine it from day one — the longer you use it, the more your number reflects your actual patterns, not averages."
        case .coach:
            return "The first read uses your answers plus population data. Apple Health and daily check-ins refine it — patterns over weeks beat any single-day estimate."
        case .firmDirect:
            return "Inputs plus population data set the first read. Apple Health and daily check-ins do the rest. Patterns beat single days."
        }
    }

    // MARK: - Healthspan reveal (replaces lifeGridRemaining + bigNumberPenalty)
    //
    // The big projected-healthspan number with a row of pinned sliders
    // showing where the user's answers placed them. Softened register is
    // honored — stressed + lonely users see a gentler title.

    static func healthspanRevealTitle(tone: ToneMode, softened: Bool) -> String {
        if softened {
            switch tone {
            case .gentle:     return "Here's what you've shared so far."
            case .coach:      return "Here's where your answers place you."
            case .firmDirect: return "Here's your read."
            }
        }
        switch tone {
        case .gentle:     return "Here's the clock you've drawn."
        case .coach:      return "Here's what you told the clock."
        case .firmDirect: return "Your read."
        }
    }

    static func healthspanRevealCaption(tone: ToneMode) -> String {
        switch tone {
        case .gentle:
            return "These sliders show where your answers placed you. They're read-only here — the dial on the next screen lets you fine-tune the final number."
        case .coach:
            return "Sliders show your answers. Read-only here; the next screen has the dial that adjusts the final number."
        case .firmDirect:
            return "Your positions. Next screen: the dial."
        }
    }

    // MARK: - Recovery preview (slider-based replacement)
    //
    // Big number that ticks up as the user drags their top lever.
    // Headline tone-aware; sub-line names what they're holding.

    static func recoveryPreviewHeadline(tone: ToneMode) -> String {
        switch tone {
        case .gentle:     return "Move one lever. Watch your clock respond."
        case .coach:      return "Move your top lever. Watch the clock respond."
        case .firmDirect: return "Pull the lever. Watch the clock."
        }
    }

    static func recoveryPreviewSubline(tone: ToneMode, lever: LifeClockLever) -> String {
        let name = lever == .unanswered ? "your lever" : lever.displayName.lowercased()
        switch tone {
        case .gentle:     return "Drag \(name) toward better and the years rise. Small lifts compound."
        case .coach:      return "Drag \(name) up. The number reflects what's available if you make this a pattern."
        case .firmDirect: return "Drag \(name) up. Years follow."
        }
    }

    // MARK: - Receipt (between healthKitAuth → paywall)
    //
    // "Here's what you taught the clock about you." Confirms the inputs
    // the user has invested in. Tone-aware footer adds an
    // anti-shame coaching line keyed off habit failure mode.

    static func receiptTitle(tone: ToneMode, signalCount: Int) -> String {
        switch tone {
        case .gentle:
            return "You shared \(signalCount) signals with the clock."
        case .coach:
            return "You taught the clock \(signalCount) things about you."
        case .firmDirect:
            return "\(signalCount) signals logged."
        }
    }

    static func receiptFooter(tone: ToneMode, failureMode: HabitFailureMode) -> String {
        // Tone × failure-mode matrix. `.unanswered` falls through to the
        // neutral "it's listening now" line so the screen still works for
        // users who skipped the question.
        switch (tone, failureMode) {
        case (.gentle, .forget):
            return "Gentle nudges, no scolding. Today is a soft place to start."
        case (.coach, .forget):
            return "We'll keep the clock visible so it's hard to forget."
        case (.firmDirect, .forget):
            return "Clock stays visible. You won't forget."

        case (.gentle, .loseMotivation):
            return "Motivation comes and goes. The clock holds steady."
        case (.coach, .loseMotivation):
            return "Motivation is a wave. The clock is the lighthouse."
        case (.firmDirect, .loseMotivation):
            return "Motivation dips. The clock doesn't."

        case (.gentle, .overdoAndStop):
            return "Steady wins. No reset weeks ahead — just rhythm."
        case (.coach, .overdoAndStop):
            return "Steady rhythm beats reset cycles. The clock rewards consistency."
        case (.firmDirect, .overdoAndStop):
            return "No reset week. Rhythm beats sprint."

        case (.gentle, .noProgressVisible):
            return "Progress will be visible from day one — small, real, yours."
        case (.coach, .noProgressVisible):
            return "Progress is the headline here. Every day, every lever."
        case (.firmDirect, .noProgressVisible):
            return "Progress shows up daily. No mystery."

        case (.gentle, .chaos):
            return "Logging takes seconds. Even on chaotic days."
        case (.coach, .chaos):
            return "Chaotic days are fine. The clock asks for seconds, not hours."
        case (.firmDirect, .chaos):
            return "Chaos doesn't beat the clock. Seconds a day."

        case (_, .unanswered):
            switch tone {
            case .gentle:     return "It's listening now. Tomorrow it starts learning."
            case .coach:      return "It's listening. Tomorrow it starts learning your patterns."
            case .firmDirect: return "It's listening. Tomorrow: learning."
            }
        }
    }

    // MARK: - Paywall — personalized headline keyed off habitFailureMode
    //
    // Replaces the static "Earn time, every day." Same App Store-safe
    // shape (no scarcity, no countdown); just a headline keyed off what
    // the user actually told us is hardest for them.

    static func paywallHeadline(tone: ToneMode, failureMode: HabitFailureMode) -> String {
        switch failureMode {
        case .forget:
            switch tone {
            case .gentle:     return "Stay easy to remember."
            case .coach:      return "Never lose the thread."
            case .firmDirect: return "Never lose the thread."
            }
        case .loseMotivation:
            switch tone {
            case .gentle:     return "Keep the clock close, even on flat days."
            case .coach:      return "Keep the clock visible when motivation isn't."
            case .firmDirect: return "Clock visible. Motivation optional."
            }
        case .overdoAndStop:
            switch tone {
            case .gentle:     return "A steadier rhythm — no reset weeks ahead."
            case .coach:      return "A steady rhythm, not another reset."
            case .firmDirect: return "Rhythm, not reset."
            }
        case .noProgressVisible:
            switch tone {
            case .gentle:     return "See the pattern, not just the day."
            case .coach:      return "See the pattern, not just the day."
            case .firmDirect: return "See the pattern. Not just the day."
            }
        case .chaos:
            switch tone {
            case .gentle:     return "Quick check-ins. Weekly clarity."
            case .coach:      return "Quick logging. Weekly clarity."
            case .firmDirect: return "Quick. Clear. Weekly."
            }
        case .unanswered:
            switch tone {
            case .gentle:     return "Keep your clock sharpening."
            case .coach:      return "Keep your clock sharpening."
            case .firmDirect: return "Keep the clock sharpening."
            }
        }
    }

    /// Paywall body — names the user's top lever inline so the value
    /// claim is personal. Falls back to neutral copy when `top` is
    /// `.unanswered`.
    static func paywallBody(tone: ToneMode, top: LifeClockLever) -> String {
        if top == .unanswered {
            switch tone {
            case .gentle:
                return "This is your first read. Pro keeps watching the patterns that actually move your clock, with full history and weekly drivers."
            case .coach:
                return "First read. Pro keeps watching the patterns that move your clock — full history, weekly drivers, correction power."
            case .firmDirect:
                return "First read. Pro: full history, weekly drivers, correction power."
            }
        }
        let name = top.displayName.lowercased()
        switch tone {
        case .gentle:
            return "This is your first read. Pro keeps watching the patterns around your \(name) so you see what's actually moving your clock."
        case .coach:
            return "First read. Pro keeps watching the patterns around your \(name) — full history, weekly drivers, correction power."
        case .firmDirect:
            return "First read. Pro watches your \(name). Full history. Drivers. Corrections."
        }
    }

    /// HealthKit auth screen — title + body. Reframes the permission ask
    /// as *uncovering* tracking already happening, not asking the user to
    /// start something new. Same tone discipline.

    static func healthKitAuthTitle(tone: ToneMode) -> String {
        switch tone {
        case .gentle:     return "You've been tracking for years."
        case .coach:      return "You've been tracking for years."
        case .firmDirect: return "You've already been tracking."
        }
    }

    static func healthKitAuthBody(tone: ToneMode) -> String {
        switch tone {
        case .gentle:
            return "Your iPhone already collects steps, sleep, and movement. Connect Apple Health once and your clock turns that into a daily read. You can change this any time in Settings."
        case .coach:
            return "Your iPhone collects steps, sleep, and movement already. Connect Apple Health once — your clock turns it into a daily read. Change any time in Settings."
        case .firmDirect:
            return "Your iPhone has been collecting steps, sleep, and movement. Connect once. The clock reads it. Change in Settings."
        }
    }

    // MARK: - Soft-skip secondary CTA (paywall)

    static func paywallSoftSkipLabel(tone: ToneMode) -> String {
        switch tone {
        case .gentle:     return "Continue with the free clock"
        case .coach:      return "Continue with the free clock"
        case .firmDirect: return "Skip — free clock for now"
        }
    }

    static func paywallSoftSkipCaption(tone: ToneMode) -> String {
        switch tone {
        case .gentle:
            return "Daily clock + 7-day view. Pro adds full history, weekly drivers, and corrections."
        case .coach:
            return "Daily clock + 7-day view. Pro adds full history, weekly drivers, and corrections."
        case .firmDirect:
            return "Daily clock + 7-day view. Pro: full history, drivers, corrections."
        }
    }
}
