import Foundation

/// User-facing tone for headline / drivers / plan copy.
///
/// History: `.mementoMori` was removed in Phase 3.A (2026-04-30) after a
/// copy audit collapsed most of its keyed properties into `.coach`.
/// Phase 3.B (2026-05-01) reintroduced a firm/direct register as
/// `.firmDirect` to support the Brainrot-style onboarding voice carrying
/// into daily use. The 2026-05-01 IA refactor (tab consolidation)
/// removed `ledgerTitle`, `ledgerEmptyState`, `questsTitle`, and
/// `questsPreamble` because the views that consumed them
/// (`TimeLedgerView`, `QuestsView`) were folded into Today.
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
        case .coach: return "Progress"
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

    var weeklyTitle: String {
        switch self {
        case .gentle: return "This week"
        case .coach: return "Weekly"
        case .firmDirect: return "Last 7"
        }
    }

    // MARK: - Empty / preamble copy

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

    // MARK: - Today interpretation copy

    /// Plain-language line shown under the "Why it changed" headline on
    /// Today, framing the day's signed delta in terms of the top driver.
    /// Takes a primitive `String?` — `ToneMode` is `Foundation`-only and
    /// must not import the SwiftData entity types. The view derives the
    /// driver title from `store.todayDrivers.first?.title`.
    func todayInterpretationPositive(driverTitle: String?) -> String {
        if let title = driverTitle, !title.isEmpty {
            switch self {
            case .gentle:
                return "Today is helping your healthspan — \(title) is supporting you."
            case .coach:
                return "Today is moving you forward, mostly because of \(title)."
            case .firmDirect:
                return "Today scored. \(title) carried it."
            }
        } else {
            switch self {
            case .gentle: return "Today is helping your healthspan."
            case .coach: return "Today is moving you forward."
            case .firmDirect: return "Today scored."
            }
        }
    }

    func todayInterpretationNegative(driverTitle: String?) -> String {
        if let title = driverTitle, !title.isEmpty {
            // 2026-05-07 vision-bad-day-three-tones audit (V2): the movement
            // driver names sub-2.5k-step days as "<n> steps — sedentary day"
            // and sub-5k-step days as "<n> steps — light day". Inlining the
            // raw title into the interpretation template stacks two em-dashes
            // for gentle ("...healthspan — <n> steps — sedentary day is the
            // main drag.") and reads as cruel-adjacent for firmDirect
            // ("Today's in the red. <n> steps — sedentary day is the cost.").
            // Strip the qualifier in the interpretation slot only; the driver
            // list (`today.driver.movement`) keeps the full title.
            let cleanedTitle = Self.interpretationTitle(from: title)
            switch self {
            case .gentle:
                return "Today is pulling against your healthspan — \(cleanedTitle) is the main drag."
            case .coach:
                return "Today is working against you, mostly because of \(cleanedTitle)."
            case .firmDirect:
                return "Today's in the red. \(cleanedTitle) is the cost."
            }
        } else {
            switch self {
            case .gentle: return "Today is pulling against your healthspan."
            case .coach: return "Today is working against you."
            case .firmDirect: return "Today's in the red."
            }
        }
    }

    /// Strips the movement-driver qualifier suffix (" — sedentary day",
    /// " — light day") so the interpretation sentence reads cleanly.
    /// Other driver titles ("4.7h sleep — too short", "Heavy alcohol logged")
    /// pass through unchanged — only the movement qualifiers cause the
    /// em-dash stack flagged by the bad-day audit.
    private static func interpretationTitle(from rawTitle: String) -> String {
        var trimmed = rawTitle
        for suffix in [" — sedentary day", " — light day"] {
            if trimmed.hasSuffix(suffix) {
                trimmed.removeLast(suffix.count)
                break
            }
        }
        return trimmed
    }

    /// Used when no estimate is available yet (cold launch, pre-data).
    /// Static — no driver to interpolate.
    func todayInterpretationPreData() -> String {
        switch self {
        case .gentle: return "Not enough data yet — this fills in as today goes on."
        case .coach: return "Not enough data yet. Check back as today's signals come in."
        case .firmDirect: return "No data yet. Check back."
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

    /// Heading on the Today screen's Reflection card. The body of the
    /// card is the rotating daily prompt from `ReflectionPrompts`.
    var reflectionHeading: String {
        switch self {
        case .gentle: return "Notice today"
        case .coach: return "What stood out today"
        case .firmDirect: return "Today, in one line"
        }
    }

    /// Card shown in History when the user has been away long enough that
    /// the wrap-up moment was suppressed. Sits where the Yesterday card
    /// would be.
    var historyLongAbsenceHeading: String {
        switch self {
        case .gentle: return "Welcome back"
        case .coach: return "Picking up where you left off"
        case .firmDirect: return "Back at it"
        }
    }

    var historyLongAbsenceBody: String {
        switch self {
        case .gentle:
            return "Today's a fresh start — nothing to make up for."
        case .coach:
            return "Today is a clean line. Show up; the rest follows."
        case .firmDirect:
            return "Clock resets to now. Log today."
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

    // MARK: - Quest completion payoff (vision Q14, 2026-05-09)

    /// Support-card payoff line shown briefly after a quest is checked
    /// complete on Today. Today-focused — describes what the user just
    /// saw happen on the clock, since under persist-banked the clock
    /// visibly moved by `minutes`. Source: vision Q14 + plan
    /// `2026-05-09-feat-life-clock-quest-completion-payoff-plan.md`
    /// Q-plan-4 resolution.
    func questCompletionPayoff(minutes: Int) -> String {
        let formatted = TimeDeltaFormatter.format(minutes: minutes)
        switch self {
        case .gentle: return "Your clock just moved \(formatted)."
        case .coach: return "\(formatted) on the clock."
        case .firmDirect: return "\(formatted). On the clock."
        }
    }

    // MARK: - Monthly logging banner (vision Q7, 2026-05-06)

    /// Secondary line on the monthly logging banner when the day is NOT a
    /// milestone day. Kept short and neutral — the count is the headline.
    var monthlyLoggingNeutralLine: String {
        switch self {
        case .gentle: return "Steady logging. Quality follows."
        case .coach: return "Logging is the win — quality follows."
        case .firmDirect: return "Log the day. The rest follows."
        }
    }

    /// Milestone copy slot. `daysLogged` is the count this month so far;
    /// `monthName` is the long form (e.g. "May"). Copy MUST NOT shame
    /// the user for the count — it just names the moment.
    func monthlyLoggingMilestoneLine(
        _ milestone: MonthlyLogging.Milestone,
        daysLogged: Int,
        monthName: String
    ) -> String {
        let phrase = daysLogged == 1 ? "1 day" : "\(daysLogged) days"
        switch (self, milestone) {
        case (.gentle, .start):
            return "A fresh \(monthName). Every day you log is yours."
        case (.coach, .start):
            return "\(monthName) starts now. Every logged day counts."
        case (.firmDirect, .start):
            return "\(monthName). Day one. Log it."

        case (.gentle, .quarter):
            return "First quarter of \(monthName). \(phrase) so far."
        case (.coach, .quarter):
            return "First quarter done. \(phrase) in."
        case (.firmDirect, .quarter):
            return "Quarter through. \(phrase) banked."

        case (.gentle, .half):
            return "Halfway through \(monthName). \(phrase) so far."
        case (.coach, .half):
            return "Halfway through \(monthName). \(phrase) logged."
        case (.firmDirect, .half):
            return "Halfway. \(phrase) banked."

        case (.gentle, .threeQuarter):
            return "Final stretch of \(monthName). \(phrase) so far."
        case (.coach, .threeQuarter):
            return "Final quarter. \(phrase) banked."
        case (.firmDirect, .threeQuarter):
            return "Last quarter. \(phrase) banked."
        }
    }

    // MARK: - Today drivers + plan card headings

    /// Heading on the Today drivers card. Sits above either the empty
    /// state or the per-driver list. The interpretation line below it is
    /// already tone-aware via `todayInterpretation*`. Sign-neutral by
    /// design — coach and firmDirect read fine on a bad day; gentle's
    /// previous "What helped today" misread when every visible driver
    /// was negative (caught 2026-05-07 vision-bad-day-three-tones recon).
    var todayDriversHeading: String {
        switch self {
        case .gentle: return "What shaped today"
        case .coach: return "Why it changed"
        case .firmDirect: return "What moved the needle"
        }
    }

    /// Empty-state body when there are no drivers yet (no HealthKit
    /// connection AND no manual check-in for today).
    var todayDriversEmptyState: String {
        switch self {
        case .gentle:
            return "No data yet. Connect Apple Health or save a quick check-in to start seeing patterns."
        case .coach:
            return "No health data yet. Connect Apple Health or save a daily check-in to start seeing patterns."
        case .firmDirect:
            return "No data yet. Connect Apple Health or log a check-in. Then we can talk."
        }
    }

    /// Heading on the Today plan card.
    var todayPlanHeading: String {
        switch self {
        case .gentle: return "Gentle nudges"
        case .coach: return "Today's Plan"
        case .firmDirect: return "Today's orders"
        }
    }

    /// One-line caption under the plan heading.
    var todayPlanSubline: String {
        switch self {
        case .gentle: return "One small thing to notice or do."
        case .coach: return "One small thing to notice or do."
        case .firmDirect: return "Pick one. Do it."
        }
    }

    /// PlanEditorSheet — navigation-bar title.
    var planEditorTitle: String {
        switch self {
        case .gentle: return "Today's plan"
        case .coach: return "Edit today's plan"
        case .firmDirect: return "Pick today's plan"
        }
    }

    /// PlanEditorSheet — caption under the title. Communicates the
    /// one-pick-per-category rule + the one-shot semantics.
    var planEditorSubtitle: String {
        switch self {
        case .gentle: return "Swap any line for another. One pick per area, just for today."
        case .coach: return "One pick per category. Resets tomorrow."
        case .firmDirect: return "One pick per slot. Today only. Resets at midnight."
        }
    }

    /// PlanEditorSheet — destructive button that drops user picks and
    /// returns the engine defaults.
    var planEditorResetCTA: String {
        switch self {
        case .gentle: return "Use today's defaults"
        case .coach: return "Reset to defaults"
        case .firmDirect: return "Drop my picks"
        }
    }

    // MARK: - History weekly card headings

    /// Label above the weekly net-delta number.
    var historyWeeklyNetLabel: String {
        switch self {
        case .gentle: return "This week, in time"
        case .coach: return "Net this week"
        case .firmDirect: return "Last 7 days, banked"
        }
    }

    /// Heading on the weekly drivers card (replaces "What shaped the week").
    var historyWeeklyDriversHeading: String {
        switch self {
        case .gentle: return "What helped, what didn't"
        case .coach: return "What shaped the week"
        case .firmDirect: return "What moved the week"
        }
    }

    /// Placeholder when the weekly report has no positive drivers (engine
    /// stores "—" in that case). Renders in the secondary color rather than
    /// the green positive color so an empty week reads as quiet, not as a
    /// red-flagged absence.
    var historyTopPositiveEmpty: String {
        switch self {
        case .gentle: return "Nothing stood out yet"
        case .coach: return "No clear positive yet"
        case .firmDirect: return "Nothing on the board"
        }
    }

    /// Placeholder when the weekly report has no negative drivers. A
    /// useful signal in itself ("nothing pulled you down this week"); the
    /// em-dash the engine emits doesn't carry that meaning to a new user.
    var historyTopDragEmpty: String {
        switch self {
        case .gentle: return "Nothing held you back"
        case .coach: return "No drag this week"
        case .firmDirect: return "No drag."
        }
    }

    /// Heading on the weekly "next best lever" card.
    var historyNextLeverHeading: String {
        switch self {
        case .gentle: return "One thing to try next"
        case .coach: return "Next best lever"
        case .firmDirect: return "Pull this lever next"
        }
    }

    /// Caption under the next-best-lever value.
    var historyNextLeverCaption: String {
        switch self {
        case .gentle:
            return "Small, repeatable wins compound. Don't try to fix everything."
        case .coach:
            return "Small, repeatable wins compound. Don't try to fix everything."
        case .firmDirect:
            return "Compound the small ones. Don't chase everything."
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
