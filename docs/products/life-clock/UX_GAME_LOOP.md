> Source: Life Clock Founder Pack (2026-04-27). Updated 2026-05-01 to
> reflect (a) the tab-bar consolidation refactor
> (`feat/life-clock-tab-consolidation`): Time Ledger and Quests are no
> longer top-level destinations — their content lives inside Today; and
> (b) the reveal-onboarding rebuild that replaced the 7-step flow with a
> ~33-screen Brainrot-modeled coordinator and reintroduced the
> `firmDirect` tone register.

# UX and Game Loop

## Core loop

1. Open Today.
2. See today's delta + the Life Clock.
3. Read "Why it changed" — top drivers + a one-line plain-language interpretation.
4. Tap into Today's Plan — pick one supportive action.
5. Save a daily check-in.
6. Return tomorrow for updated trajectory.

## The game mechanic

The core game currency is **time**.

Not points. Not coins. Not XP.

Time stays emotionally legible, but the current UX direction is calmer and less game-loud than the original founder pack framing.

The 2026-04-30 UX pass and the 2026-05-01 IA refactor both reframed Life Clock away from gamified task completion and toward daily reflection + behavior awareness. Plan sections use behavioral-mirror copy ("One small thing to notice or do."), not points-board copy.

## Main surfaces

The bottom tab bar is **4 tabs**: Today, History, **Future**, Profile. (`Sources/App/AppTab.swift`.) The Future tab was added after the 2026-05-01 IA consolidation; it owns long-horizon trajectory and the Pro-gated What-If Simulator.

### Today screen

Today is the daily ritual surface — score, why, plan, check-in. Sections render in this order (see `Sources/Features/Today/TodayView.swift` lines 105–119 for the canonical order):

1. **Life Clock headline** — today's signed delta + projected healthspan card (`headline`, `mascotHero`, `clockCard`).
2. **Trajectory peek + rescue line** — the small projection callout (`trajectoryPeek`) and the soft-interpretation line shown when the delta is negative (`rescueLine`).
3. **Support moment card** (conditional) — surfaced after a check-in or notable event (`supportMomentCard`).
4. **Why it changed** — top 3 drivers + a one-line plain-language interpretation generated from the day's signed delta and the top driver title (`driversCard`).
5. **Today's Plan** — a small set of supportive actions (the data still flows from `QuestEngine`). Per-row "Potential +N min" labels were dropped in the IA refactor; the section subhead reads "One small thing to notice or do." (`questsCard`.)
6. **Reflection card** — short tone-aware reflection prompt (`ReflectionCard`).
7. **Quick check-in** card and toolbar entry (`quickLogCard`).
8. **Monthly logging banner** (conditional) — calendar-month logged-days count + milestone copy. Replaced the earlier diet-streak banner per vision Decided constraint 2026-05-06 ("monthly count, no streak"; `DietStreakCalculator` was dropped along with the rolling-streak concept).
9. **Disclaimer banner** — global non-medical disclaimer (`DisclaimerBanner`).

The momentum card was removed in the IA refactor — its retrospective summary belongs in History.

Example copy:

"Progress today"

"Today is moving you forward, mostly because of steps."

### History tab

Owns retrospection: yesterday wrap-up card, weekly summary (net delta + drivers + lever cards), daily history list (90 days for Pro, **3 days for free** with a paywall-fogged peek of older rows; `HistoryView.freeRowLimit = 3` in `Sources/Features/History/HistoryView.swift`), drill-down per-day detail with override editing (Pro-only). Today is excluded from the list per `polish-2026-05-10-history-excludes-today.md`; a day-1 empty state ships per `polish-2026-05-11-history-day1-empty-state-tones.md`.

The weekly wrap-up sheet (`WrapUpSheet`, in-app, pull-only on cold-launch via `WrapUpCoordinator`) is a separate retrospection surface — never pushed to the lock screen. See vision Decided constraint 2026-05-09 (wrap-ups are pull, not push).

### Future tab

Owns long-horizon trajectory and Pro-gated What-If exploration: `TrajectoryChart` (past + projection), `WhatIfSlider` (Pro-only thumb that lets the user simulate "what if I slept more / smoked less / walked more"), `LongFormNarrative`, and state-aware copy across day0 / coldLaunch1to3 / warmingUp4to13 / full14plus (see `Sources/Features/Future/FutureView.swift`).

### Profile tab

Tone-mode picker, appearance/palette picker, Body metrics, Daily reminder section (8…22 hour clamp), Apple Health permission state, Subscription section (purchase/restore/manage), Completion badges, SafetyNet entry, Privacy (delete-all-data), About. See `polish-2026-05-09-profile-section-sweep.md` for the canonical section ordering.

## Tone modes

The original `mementoMori` tone was removed in the 2026-04-30 UX pass. Phase 3.B (2026-05-01) reintroduced a firm/direct register as `firmDirect` to support the Brainrot-style onboarding voice carrying into daily use. Three tones now ship:

### Gentle

Steady-progress and future-self framing. No death-date language.

### Coach

Default. Direct but supportive progress language.

### Firm / Direct

Short, specific, no hedging. The clock keeps score. Carries the
Brainrot-onboarding voice into daily use.

## Onboarding flow

The 2026-05-01 reveal-onboarding rebuild replaced the previous 7-step flow with a ~33-screen Brainrot-modeled coordinator. High-level beats:

1. Lead-ins (cold open, app previews, welcome, meet your clock, reactive slider).
2. Personalize intro + goal pick.
3. Baseline (DOB, sex, body composition, smoking, alcohol, activity, sleep, diet).
4. Sensitive consent (skip path available).
5. Tone selection.
6. Prior attempts.
7. Analyzing (fake-progress) → archetype reveal.
8. Concrete-this-year, life-grid (full and remaining).
9. Engine reveal + ±5 yr healthspan dial (one-time, bounded).
10. Recovery preview.
11. HealthKit auth.
12. Single-tier paywall.

See `docs/plans/2026-05-01-feat-life-clock-reveal-onboarding-anchor-dial-plan.md` for the full design.

## UX risk

The biggest UX risk is creating anxiety. The default should be motivating, not punishing.

Every negative delta should be paired with an actionable next step or a softer interpretation line.
