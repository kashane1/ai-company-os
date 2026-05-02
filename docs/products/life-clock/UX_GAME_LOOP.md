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

The bottom tab bar is **3 tabs**: Today, History, Profile.

### Today screen

Today is the daily ritual surface — score, why, plan, check-in. Sections render in this order:

1. **Life Clock headline** — today's signed delta + projected healthspan card.
2. **Support moment card** (conditional) — surfaced after a check-in or notable event.
3. **Why it changed** — top 3 drivers + a one-line plain-language interpretation generated from the day's signed delta and the top driver title.
4. **Today's Plan** — a small set of supportive actions (the data still flows from `QuestEngine`). Per-row "Potential +N min" labels were dropped in the IA refactor; the section subhead reads "One small thing to notice or do."
5. **Quick check-in** card and toolbar entry.
6. **Diet streak banner** (conditional, ≥2 days).

The momentum card was removed in the IA refactor — its retrospective summary belongs in History.

Example copy:

"Progress today"

"Today is moving you forward, mostly because of steps."

### History tab

Owns retrospection: yesterday wrap-up card, weekly summary, daily history list (90 days for Pro, 7 days for free), drill-down per-day detail with override editing.

### Profile tab

Tone-mode picker, palette picker, paywall entry, daily reminder settings, Safety Net.

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
