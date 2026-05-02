import Foundation

/// User-facing tone for headline / progress / quest copy.
///
/// History: a `.mementoMori` case was removed in Phase 3.A (2026-04-30)
/// after a copy audit collapsed most of its keyed properties into the
/// `.coach` strings. Phase 3.B (2026-05-01) reintroduces a firm/direct
/// register as `.firmDirect` to support the Brainrot-style onboarding
/// voice carrying into daily use.
///
/// Legacy `UserProfile.toneMode == "memento_mori"` rows fall back to
/// `.coach` via `fromStored(_:)`; persisted values are written back as
/// `.coach` on the next `setToneMode(_:)`.
enum ToneMode: String, CaseIterable, Identifiable {
    case gentle
    case coach
    case firmDirect = "firm_direct"

    var id: String { rawValue }

    /// Decode a stored rawValue with explicit fallback. Use this everywhere
    /// the value is read off `UserProfile.toneMode`.
    static func fromStored(_ raw: String) -> ToneMode {
        ToneMode(rawValue: raw) ?? .coach
    }

    var displayName: String {
        switch self {
        case .gentle: return "Calm / Gentle"
        case .coach: return "Default / Average"
        case .firmDirect: return "Firm / Direct"
        }
    }

    var description: String {
        switch self {
        case .gentle:
            return "Keeps the focus on steady progress and supportive guidance."
        case .coach:
            return "Balanced guidance with clear progress language and supportive accountability."
        case .firmDirect:
            return "Short, specific, no hedging. The clock keeps score."
        }
    }

    /// Copy keys vary by tone. Today screen uses these.
    var todayHeadline: String {
        switch self {
        case .gentle: return "Today"
        case .coach: return "Today's progress"
        case .firmDirect: return "Today's reckoning"
        }
    }

    var deltaPositivePrefix: String {
        switch self {
        case .gentle: return "Progress gained"
        case .coach: return "Progress today"
        case .firmDirect: return "Banked"
        }
    }

    var deltaNegativePrefix: String {
        switch self {
        case .gentle: return "Needs attention"
        case .coach: return "Progress at risk"
        case .firmDirect: return "Owed"
        }
    }

    // MARK: - Tab titles

    /// Inlined to "Progress" everywhere (was identical across all tones
    /// even before Phase 3.A). Kept as a property so call sites do not
    /// need to change; collapse to a literal in a future cleanup if a
    /// tone-aware variant never reappears.
    var ledgerTitle: String { "Progress" }

    var questsTitle: String {
        switch self {
        case .gentle: return "Next steps"
        case .coach: return "Plan"
        case .firmDirect: return "Today's moves"
        }
    }

    var weeklyTitle: String {
        switch self {
        case .gentle: return "This week"
        case .coach: return "Weekly"
        case .firmDirect: return "Last 7"
        }
    }

    // MARK: - Empty / preamble copy

    var ledgerEmptyState: String {
        switch self {
        case .gentle:
            return "Your progress log fills up as you check in and data comes in."
        case .coach:
            return "No progress entries yet. Check in once and the story starts to build."
        case .firmDirect:
            return "Nothing logged. Check in. The clock can't score what it can't see."
        }
    }

    var questsPreamble: String {
        switch self {
        case .gentle:
            return "Pick one supportive action. Showing up is a real win."
        case .coach:
            return "Choose one supportive action for today. Small steps count."
        case .firmDirect:
            return "Pick one. Do it today. Skip the rest."
        }
    }

    var weeklyEmptyState: String {
        switch self {
        case .gentle:
            return "Come back after a few days — patterns appear with time."
        case .coach:
            return "Your weekly view will appear after a few days of data."
        case .firmDirect:
            return "Not enough days yet. Show up. Come back."
        }
    }

    // MARK: - Wrap-up copy

    var yesterdayWrapUpHeading: String {
        switch self {
        case .gentle: return "Yesterday"
        case .coach: return "Yesterday's wrap-up"
        case .firmDirect: return "Yesterday's tally"
        }
    }

    var weeklyWrapUpHeading: String {
        switch self {
        case .gentle: return "Last week"
        case .coach: return "Weekly wrap-up"
        case .firmDirect: return "Last 7 days"
        }
    }

    /// Body copy shown beneath the clock animation when the day netted
    /// positive minutes.
    func wrapUpPositiveBody(minutes: Int) -> String {
        let formatted = TimeDeltaFormatter.format(minutes: minutes)
        switch self {
        case .gentle:
            return "You moved \(formatted) forward. Small days add up."
        case .coach:
            return "\(formatted) gained. Keep stacking days like this."
        case .firmDirect:
            return "+\(formatted). Banked."
        }
    }

    /// Body copy when the day netted negative minutes — supportive, not
    /// punitive (per UX_GAME_LOOP.md "every negative delta should be paired
    /// with an actionable next step or a softer explanation").
    func wrapUpNegativeBody(minutes: Int) -> String {
        let formatted = TimeDeltaFormatter.format(minutes: minutes)
        switch self {
        case .gentle:
            return "Yesterday cost \(formatted). Today is a fresh start."
        case .coach:
            return "\(formatted) yesterday. One day doesn't define the trend."
        case .firmDirect:
            return "-\(formatted). Owe today's self."
        }
    }

    /// Body copy when the day netted zero minutes.
    var wrapUpZeroBody: String {
        switch self {
        case .gentle: return "Yesterday held steady. Even floors matter."
        case .coach: return "Net zero. Holding steady is a real outcome."
        case .firmDirect: return "Net zero. No ground gained, none lost."
        }
    }

    var wrapUpDismissCTA: String {
        switch self {
        case .gentle: return "Got it"
        case .coach: return "Continue"
        case .firmDirect: return "Next"
        }
    }

    /// Label on the chip that appears next to a metric the user has
    /// corrected. Same word in both modes — "Adjusted" reads as a neutral
    /// status, not a judgment.
    var adjustedChipLabel: String {
        switch self {
        case .gentle: return "Adjusted"
        case .coach: return "Adjusted"
        case .firmDirect: return "Adjusted"
        }
    }

    /// Card shown in History when the user has been away long enough that
    /// the wrap-up moment was suppressed. Sits where the Yesterday card
    /// would be.
    var historyLongAbsenceHeading: String {
        switch self {
        case .gentle: return "Welcome back"
        case .coach: return "Picking up where you left off"
        case .firmDirect: return "You were gone"
        }
    }

    var historyLongAbsenceBody: String {
        switch self {
        case .gentle:
            return "We didn't have enough data from yesterday for a wrap-up. Today's a fresh start."
        case .coach:
            return "Yesterday didn't have enough data to summarize. Make today count."
        case .firmDirect:
            return "No data for yesterday. Clock starts again now."
        }
    }

    /// "Patterns, not perfection" line shown on Today when the user logged
    /// a rough day driven by diet signals (V1.2.0 diet rhythm pass).
    /// Method name follows the existing <surface><Aspect> convention
    /// (compare: wrapUpPositiveBody, wrapUpNegativeBody, todayInterpretation).
    /// The trigger lives in the caller (`RescueLine` view); this method is
    /// unconditional once invoked.
    func todayRescueBody() -> String {
        switch self {
        case .gentle:
            return "Rough day? Log it and move on. Tomorrow still counts."
        case .coach:
            return "You don't need a perfect diet. You need a repeatable one."
        case .firmDirect:
            return "Your Life Clock responds to patterns, not perfection."
        }
    }

    /// Inline error message in `OverrideSheet` when the user attempts an
    /// override without Pro entitlement. Doubles as the downgrade notice —
    /// surfaces at the moment of friction rather than as a separate banner.
    /// Honors the "existing overrides stay active" grace period.
    var overrideNotEntitledMessage: String {
        switch self {
        case .gentle:
            return "New adjustments are paused — Pro only. Your existing adjustments stay active. Re-subscribe in Profile to keep editing."
        case .coach:
            return "New adjustments require Pro. Existing adjustments remain in effect. Re-subscribe in Profile to resume editing."
        case .firmDirect:
            return "Adjustments are Pro. Existing ones stay. Re-subscribe to edit."
        }
    }
}
