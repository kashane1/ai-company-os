import Foundation

/// User-facing tone for headline / drivers / plan copy.
///
/// Phase 3.A collapse: `.mementoMori` was removed because keyed properties
/// had collapsed to identical strings between `.coach` and `.mementoMori`
/// after the 2026-04-30 audit copy refresh. The mortality framing the
/// original case represented was abandoned during the audit;
/// `displayName` had already been renamed to "Direct".
///
/// Legacy `UserProfile.toneMode == "memento_mori"` rows fall back to
/// `.coach` via `fromStored(_:)`; persisted values are written back as
/// `.coach` on the next `setToneMode(_:)`.
enum ToneMode: String, CaseIterable, Identifiable {
    case gentle
    case coach

    var id: String { rawValue }

    /// Decode a stored rawValue with explicit fallback. Use this everywhere
    /// the value is read off `UserProfile.toneMode`.
    static func fromStored(_ raw: String) -> ToneMode {
        ToneMode(rawValue: raw) ?? .coach
    }

    var displayName: String {
        switch self {
        case .gentle: return "Gentle"
        case .coach: return "Coach"
        }
    }

    var description: String {
        switch self {
        case .gentle:
            return "Keeps the focus on steady progress and supportive guidance."
        case .coach:
            return "Balanced guidance with clear progress language and supportive accountability."
        }
    }

    /// Copy keys vary by tone. Today screen uses these.
    var todayHeadline: String {
        switch self {
        case .gentle: return "Today"
        case .coach: return "Today's progress"
        }
    }

    var deltaPositivePrefix: String {
        switch self {
        case .gentle: return "Progress gained"
        case .coach: return "Progress today"
        }
    }

    var deltaNegativePrefix: String {
        switch self {
        case .gentle: return "Needs attention"
        case .coach: return "Progress at risk"
        }
    }

    // MARK: - Tab titles

    var weeklyTitle: String {
        switch self {
        case .gentle: return "This week"
        case .coach: return "Weekly"
        }
    }

    // MARK: - Empty / preamble copy

    var weeklyEmptyState: String {
        switch self {
        case .gentle:
            return "Come back after a few days — patterns appear with time."
        case .coach:
            return "Your weekly view will appear after a few days of data."
        }
    }

    // MARK: - Wrap-up copy

    var yesterdayWrapUpHeading: String {
        switch self {
        case .gentle: return "Yesterday"
        case .coach: return "Yesterday's wrap-up"
        }
    }

    var weeklyWrapUpHeading: String {
        switch self {
        case .gentle: return "Last week"
        case .coach: return "Weekly wrap-up"
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
        }
    }

    /// Body copy when the day netted zero minutes.
    var wrapUpZeroBody: String {
        switch self {
        case .gentle: return "Yesterday held steady. Even floors matter."
        case .coach: return "Net zero. Holding steady is a real outcome."
        }
    }

    var wrapUpDismissCTA: String {
        switch self {
        case .gentle: return "Got it"
        case .coach: return "Continue"
        }
    }

    /// Label on the chip that appears next to a metric the user has
    /// corrected. Same word in both modes — "Adjusted" reads as a neutral
    /// status, not a judgment.
    var adjustedChipLabel: String {
        switch self {
        case .gentle: return "Adjusted"
        case .coach: return "Adjusted"
        }
    }

    /// Card shown in History when the user has been away long enough that
    /// the wrap-up moment was suppressed. Sits where the Yesterday card
    /// would be.
    var historyLongAbsenceHeading: String {
        switch self {
        case .gentle: return "Welcome back"
        case .coach: return "Picking up where you left off"
        }
    }

    var historyLongAbsenceBody: String {
        switch self {
        case .gentle:
            return "We didn't have enough data from yesterday for a wrap-up. Today's a fresh start."
        case .coach:
            return "Yesterday didn't have enough data to summarize. Make today count."
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
        }
    }
}
