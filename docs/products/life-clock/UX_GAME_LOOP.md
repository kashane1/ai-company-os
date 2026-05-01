> Source: Life Clock Founder Pack (2026-04-27). Normalized for platform use.
> Updated 2026-05-01 to reflect the tab-bar consolidation refactor
> (`feat/life-clock-tab-consolidation`): Time Ledger and Quests are no
> longer top-level destinations — their content lives inside Today.

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

Time is emotionally legible and directly connected to the concept.

The 2026-04-30 UX pass and the 2026-05-01 IA refactor both reframed Life Clock away from gamified task completion and toward daily reflection + behavior awareness. Plan sections use behavioral-mirror copy ("One small thing to notice or do."), not points-board copy.

## Main surfaces

The bottom tab bar is **3 tabs**: Today, History, Profile.

### Today screen

Today is the daily ritual surface — score, why, plan, check-in. Sections render in this order:

1. **Life Clock headline** — today's signed delta + projected healthspan card.
2. **Support moment card** (conditional) — surfaced after a check-in or notable event.
3. **Why it changed** — top 3 drivers + a one-line plain-language interpretation generated from the day's signed delta and the top driver title (`ToneMode.todayInterpretationPositive(driverTitle:)` / `Negative(driverTitle:)` / `PreData()`).
4. **Today's Plan** — a small set of supportive actions (the data still flows from `QuestEngine`). Per-row "Potential +N min" labels were dropped in the IA refactor; the section subhead reads "One small thing to notice or do."
5. **Quick check-in** card and toolbar entry.
6. **Diet streak banner** (conditional, ≥2 days).

The momentum card was removed in the IA refactor — its retrospective summary belongs in History.

Example copy:

"+42 minutes today"

"Today is moving you forward, mostly because of steps."

### History tab

Owns retrospection: yesterday wrap-up card, weekly summary, daily history list (90 days for Pro, 7 days for free), drill-down per-day detail with override editing.

### Profile tab

Tone-mode picker, palette picker, paywall entry, daily reminder settings, Safety Net.

## Tone modes

The mortality-forward third tone mode (`mementoMori`) was removed in the 2026-04-30 UX pass. Two tones remain:

### Gentle

Steady-progress and future-self framing. No death-date language.

### Coach

Default. Direct but supportive progress language.

## Onboarding flow

1. Value screen: "Earn time back with better habits."
2. Safety screen: "Your clock is an estimate, not fate."
3. Baseline profile.
4. Tone mode.
5. Apple Health education and authorization.
6. First Life Clock reveal.

## UX risk

The biggest UX risk is creating anxiety. The default should be motivating, not punishing.

Every negative delta should be paired with an actionable next step or a softer interpretation line.
