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

    /// Pro-signal copy rendered AFTER the weekly wrap-up animation lands.
    /// Yesterday wrap-ups never show this (daily reflection ≠ upsell moment;
    /// see [`wrap-up-spec.md`](../../../../docs/products/life-clock/wrap-up-spec.md)).
    /// The copy quotes the Free/Pro rule from MONETIZATION.md ("Pro = depth")
    /// in each tone's voice — does not invent a fourth voice.
    var weeklyWrapUpProSignalTitle: String {
        switch self {
        case .gentle: return "See a little more with Pro"
        case .coach: return "Go deeper this week with Pro"
        case .firmDirect: return "Pro: the drivers and the lever"
        }
    }

    var weeklyWrapUpProSignalBody: String {
        switch self {
        case .gentle:
            return "Pro adds the three drivers behind the week and one gentle nudge for next week."
        case .coach:
            return "Pro shows the three drivers and the one habit to lever next week."
        case .firmDirect:
            return "Pro: drivers, and the one lever. Now."
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

    /// Mirror of `LifeClockStore.HealthDataState` for the History day-1
    /// empty-state copy. Kept here (not imported) so `ToneMode` remains
    /// `Foundation`-only and free of SwiftData entity coupling.
    enum HistoryEmptyHealthState {
        case unavailable
        case awaitingAuthorization
        case historicalOnly
        case noRecentData
        case availableToday
    }

    /// Body copy for the History tab's day-1 empty-state card, when the
    /// user has no prior snapshots (today is excluded from History as of
    /// the 2026-05-10 store-boundary fix). Tone-keyed because new users
    /// hit this card hardest — previously masked by today appearing as a
    /// historical row.
    ///
    /// Register guardrails (per polish-2026-05-11 success criteria):
    /// - gentle: no platitudes ("every day counts", "small things matter")
    /// - coach:  no presumption-of-adherence ("keep showing up")
    /// - firmDirect: no mortality lexicon ("owed", "tally", "in the red",
    ///   "cost") — this card is a setup state, not a scorekeeping moment.
    func historyEmptyStateBody(for state: HistoryEmptyHealthState) -> String {
        switch (self, state) {
        case (.gentle, .unavailable):
            return "Apple Health isn't available on this device. A quick daily check-in is what History uses here."
        case (.coach, .unavailable):
            return "Apple Health isn't available on this device. Daily check-ins build History instead."
        case (.firmDirect, .unavailable):
            return "No Apple Health on this device. Daily check-ins build History instead."

        case (.gentle, .awaitingAuthorization):
            return "Connect Apple Health when you're ready — History fills in after a few days of steps, sleep, or workouts."
        case (.coach, .awaitingAuthorization):
            return "History fills in after a few days of Apple Health signal. You can connect from Profile."
        case (.firmDirect, .awaitingAuthorization):
            return "Connect Apple Health from Profile. History needs a few days of signal."

        case (.gentle, .historicalOnly):
            return "Today's Apple Health signal isn't through yet. Earlier days are still here."
        case (.coach, .historicalOnly):
            return "Today's Apple Health data hasn't arrived. Earlier days remain on file."
        case (.firmDirect, .historicalOnly):
            return "No Apple Health for today yet. Earlier days are intact."

        case (.gentle, .noRecentData):
            return "Apple Health isn't sharing anything yet — History waits for real signal before showing patterns."
        case (.coach, .noRecentData):
            return "No recent Apple Health signal. History waits for real data before showing a trend."
        case (.firmDirect, .noRecentData):
            return "No Apple Health signal. History stays empty until there's real data."

        case (.gentle, .availableToday):
            return "History fills in after a few days. Today is the first one."
        case (.coach, .availableToday):
            return "A few more days of signal and patterns start to appear here."
        case (.firmDirect, .availableToday):
            return "A few more days. Then History has something to say."
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

    // MARK: - QuickLog narration (vision Q11, 2026-05-11)

    /// QuickLogSheet — top-of-sheet headline. The picker affordances + the
    /// section labels below are intentionally NOT tone-keyed (see file
    /// doc-comment on QuickLogSheet). Only the narration shifts.
    var quickLogIntroHeadline: String {
        switch self {
        case .gentle:     return "A few quick signals help your Life Clock listen better."
        case .coach:      return "A few quick signals help your Life Clock stay honest."
        case .firmDirect: return "Log the day. The clock can't read what you don't tell it."
        }
    }

    /// QuickLogSheet — subheadline directly under the headline. Same
    /// anti-shame anchor across modes ("no calorie counting") with the
    /// register shifting around it.
    var quickLogIntroSubheadline: String {
        switch self {
        case .gentle:     return "No calorie counting. Nothing to prove."
        case .coach:      return "No calorie counting. No judgment."
        case .firmDirect: return "No calorie counting. Just signals."
        }
    }

    /// QuickLogSheet — caption under the Rhythm picker (adult users only).
    /// Coupled with the intro subheadline; if the intro pair gets keyed,
    /// this should too — otherwise the surface develops a register split
    /// mid-screen.
    var quickLogRhythmCaption: String {
        switch self {
        case .gentle:     return "No calories, no judgment — just the shape of the day."
        case .coach:      return "No calories, no judgment. Just rhythm."
        case .firmDirect: return "No calorie math. Just the rhythm."
        }
    }

    /// QuickLogSheet — footer below the "Clear today's check-in" destructive
    /// button. Explains what clearing does. The destructive button label
    /// itself is intentionally neutral (iOS HIG verb-noun pattern).
    var quickLogClearFooter: String {
        switch self {
        case .gentle:
            return "Clears today's check-in. Your clock will lean on Apple Health for the rest of today."
        case .coach:
            return "Removes today's manual signals. Your Life Clock will recompute from HealthKit signals only."
        case .firmDirect:
            return "Wipes today's manual log. Clock runs on Health data only."
        }
    }

    /// QuickLogSheet — confirmation toolbar CTA. Couples tone register with
    /// a state-branch: the label differs depending on whether the user is
    /// saving for the first time today (`hasExistingHabits: false`) or
    /// updating an existing log. Original literal `"Update Life Clock"`
    /// read slightly odd on first save (the clock is not being *updated*
    /// from a prior value).
    func quickLogSaveCTA(hasExistingHabits: Bool) -> String {
        switch (self, hasExistingHabits) {
        case (.gentle, false):     return "Save today's signals"
        case (.gentle, true):      return "Update today's signals"
        case (.coach, false):      return "Save check-in"
        case (.coach, true):       return "Update Life Clock"
        case (.firmDirect, false): return "Log it"
        case (.firmDirect, true):  return "Update the log"
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

    // MARK: - Future tab + History summary (V1.7.0, 2026-05-11)
    //
    // Authored copy per docs/products/life-clock/future-tab-tone-pools-spec.md.
    // The pool-with-discrete-N transparency line + free narrative
    // templates live in `ReflectionPrompts.swift` (where pool selection
    // already has the rotation harness). All other slots are direct
    // properties below.

    /// Future tab subtext under the projection number on warmingUp/full.
    var futureHeadlineSubtext: String {
        switch self {
        case .gentle: return "Updated daily from your last 14 days."
        case .coach: return "Updated daily. Last 14 days of signal."
        case .firmDirect: return "14-day rolling. Updated daily."
        }
    }

    /// Day 0 (install day) line — no chart, no slider, baseline-only.
    var futureDay0Line: String {
        switch self {
        case .gentle:
            return "Your projection arrives tomorrow. For today, your starting baseline is enough."
        case .coach:
            return "Projection starts tomorrow. Today: log your first day."
        case .firmDirect:
            return "Day zero. Projection turns on tomorrow."
        }
    }

    /// Day 1–3 cold-launch line — baseline + this line; no chart, no slider.
    var futureColdLaunchLine: String {
        switch self {
        case .gentle:
            return "Your projection will sharpen as you log days. We're listening."
        case .coach:
            return "Projection sharpens with each day. Three days in, the chart turns on."
        case .firmDirect:
            return "Sharpens with each day. Chart unlocks at day 4."
        }
    }

    /// Pro long-form narrative subhead. `dateText` formatted as "MMM d"
    /// at the call site via DateFormatter.localizedString.
    func futureWeeklyNarrativeSubhead(dateText: String) -> String {
        switch self {
        case .gentle: return "Reflection from Sunday, \(dateText)"
        case .coach: return "Reflection — week ending \(dateText)"
        case .firmDirect: return "Week ending \(dateText)"
        }
    }

    /// Footnote under the Future headline projection: anchors the user
    /// to their starting baseline.
    func futureBaselineFootnote(formatted: String) -> String {
        switch self {
        case .gentle: return "you started at \(formatted)"
        case .coach: return "Baseline: \(formatted)"
        case .firmDirect: return "Started: \(formatted)"
        }
    }

    /// Signed-delta sentence on the Future headline (e.g. "+3y 2m
    /// earned since you started"). `sign` is the prefix glyph the
    /// caller already chose (e.g. "+" or "−"); `magnitude` is the
    /// formatted years+months string.
    func futureSignedDelta(sign: String, magnitude: String, positive: Bool) -> String {
        switch self {
        case .gentle:
            return positive
                ? "\(sign)\(magnitude) earned since you started"
                : "\(sign)\(magnitude) lost since you started"
        case .coach:
            return "\(sign)\(magnitude) vs your starting baseline"
        case .firmDirect:
            return positive
                ? "\(sign)\(magnitude) banked"
                : "\(sign)\(magnitude) drag"
        }
    }

    // MARK: - History summary (V1.7.0)

    /// Day 0 hero copy on the install-summary section.
    var historySummaryDay0Hero: String {
        switch self {
        case .gentle: return "Your ledger starts today. Check back tomorrow."
        case .coach: return "Ledger begins today. First entry tomorrow."
        case .firmDirect: return "Ledger opens today."
        }
    }

    /// Heading for the top-3 contributors panel (Day 7+).
    var historyTopContributorsHeading: String {
        switch self {
        case .gentle: return "What's been moving your ledger"
        case .coach: return "Top contributors"
        case .firmDirect: return "Top 3"
        }
    }

    /// Day 7+ but <3 days of HK/QuickLog data — typically HK denied
    /// entire week. Distinct from Day-0 zero-state.
    var historySummaryNoSignal: String {
        switch self {
        case .gentle:
            return "No signal yet. Once Apple Health or your check-ins start filling in, your ledger will too."
        case .coach:
            return "No signal yet. Connect Apple Health or use QuickLog to start the ledger."
        case .firmDirect:
            return "No signal. Connect HK or use QuickLog."
        }
    }

    /// Prefix for the cumulative-summary anchor sentence
    /// ("banked since {anchor}"). Carries the valence — the ± glyph on
    /// the hero number stays neutral per the plan / SpecFlow gap #14.
    func historySummaryAnchorPrefix(positive: Bool) -> String {
        switch self {
        case .gentle: return positive ? "banked since" : "lost since"
        case .coach: return positive ? "net since" : "behind since"
        case .firmDirect: return positive ? "+ since" : "− since"
        }
    }

    /// Today screen trajectory-peek affordance. Routes to the Future
    /// tab on tap. `formatted` is the years+months projection (e.g.
    /// "87y 2m"). Hidden when day-state is day0 / coldLaunch1to3.
    func todayTrajectoryPeek(formatted: String) -> String {
        switch self {
        case .gentle: return "Your projection ahead: \(formatted) →"
        case .coach: return "Trajectory: \(formatted) →"
        case .firmDirect: return "Tally: \(formatted) →"
        }
    }

    /// VoiceOver label for the Today trajectory peek. The noun half of
    /// `todayTrajectoryPeek(formatted:)` with the number and arrow
    /// stripped, so VoiceOver reads "<label>. <value>. Button." cleanly
    /// instead of pronouncing "87y 2m right arrow" as "eight seven y
    /// two m right arrow." Pair with `TimeDeltaFormatter.formatProjectionA11y`
    /// for the value half.
    var todayTrajectoryPeekA11yLabel: String {
        switch self {
        case .gentle: return "Your projection ahead"
        case .coach: return "Trajectory"
        case .firmDirect: return "Tally"
        }
    }
}

// MARK: - Future tab neutral strings (single neutral string, no per-tone variants)
//
// Clamp-and-explain pattern: when projection hits the cap or floor we
// surface a single neutral string inline rather than per-tone variants.
// The honesty is in the data — we don't need three tones to say the
// same factual thing. See plan §Phase 3.
enum FutureNeutralCopy {
    static let capReached: String = "Projection capped at 105 years."
    static let floorReached: String = "Projection at minimum."
    static let nearCapCompression: String = "Near projection ceiling — chart compressed."
}
