> Source: Life Clock Founder Pack (2026-04-27). Normalized for platform use.

# Product Requirements Document

## Product purpose

Help users understand how daily habits affect their healthspan trajectory and motivate them to improve through time-based feedback and quests.

## MVP user story

As a health-curious iPhone user, I want to connect Apple Health and see how today's sleep, movement, workouts, and habits changed my projected time, so that I can make better choices tomorrow.

## Core surfaces

> **IA note (2026-05-01 refactor + 2026-05 Future tab add):** the app ships **4 tabs** — Today, History, Future, Profile (`Sources/App/AppTab.swift`). The earlier 5-screen taxonomy (Today / Time Ledger / Quests / Weekly Report / Profile) is superseded: Time Ledger is folded into Today's "Why it changed" drivers + History day detail; Quests are surfaced inside Today as "Today's Plan." Onboarding is a coordinator, not a tab.

### Onboarding (coordinator, not a tab)

Purpose: establish trust, explain the app, collect baseline, hard-block users under 13, and request health permissions in context.

Must include:

- value framing, non-medical disclaimer
- baseline profile (DOB with under-13 hard block, sex, body composition, smoking, alcohol, cardio, strength, sleep, diet)
- sensitive-consent block (PSS-10 stress, UCLA-3 loneliness; skip path available)
- tone mode selection (gentle / coach / firmDirect; inferred-softer rule per vision Decided 2026-05-12 Q9)
- HealthKit permission education + auth
- initial Life Clock reveal (reveal escalator) + healthspan dial (one-time, bounded ±5y)
- single-tier paywall priming after reveal

Live screen taxonomy lives in `Sources/Features/Onboarding/OnboardingScreen.swift` (29 cases). See `docs/plans/2026-05-01-feat-life-clock-reveal-onboarding-anchor-dial-plan.md` for the full design.

### 1. Today

Purpose: the daily ritual surface — score, why, plan, check-in.

Render order (see `TodayView.swift:105–119` for canonical order):

- Life Clock headline + projected healthspan card + mascot
- Trajectory peek + rescue line (soft interpretation when delta is negative)
- Support moment card (conditional, post-check-in)
- Why it changed — top 3 drivers + one-line plain-language interpretation (Time Ledger content lives here, not as a separate screen)
- Today's Plan — 1–3 supportive actions ("One small thing to notice or do."); Pro-gated Plan Editor for custom selection
- Reflection card
- Quick check-in card + toolbar entry
- Monthly logging banner (calendar-month count, no streak — vision Decided 2026-05-06)
- Confidence indicator
- DisclaimerBanner

### 2. History

Purpose: retrospection, archive, correction.

Must include:

- Yesterday wrap-up surface (in-app `WrapUpSheet`, fires pull-only on cold-launch; vision Decided 2026-05-09)
- Weekly summary cards (net delta Free; drivers + lever Pro)
- Daily history list — 90 days for Pro, **3 days for Free** (`HistoryView.freeRowLimit = 3`) with paywall-fogged peek of older rows
- Drill-down per-day detail (`DayDetailView`, Pro-only) with override editing (`OverrideService`)
- Day-1 empty state per `polish-2026-05-11-history-day1-empty-state-tones.md`

### 3. Future

Purpose: long-horizon trajectory + Pro-gated What-If exploration.

Must include:

- TrajectoryChart (past + projection)
- LongFormNarrative copy across day0 / coldLaunch1to3 / warmingUp4to13 / full14plus states
- What-If Simulator (`WhatIfSlider`, Pro-only thumb — Free preview, locked tap → paywall)
- Healthspan dial summary (reflects the one-time anchor from onboarding)

Math source: `HealthspanEngine` (separate from `ClockEngine`'s additive ledger); coefficients in `docs/products/life-clock/healthspan-coefficients.md`.

### 4. Profile

Purpose: manage tone/appearance, reminders, Apple Health permissions, subscription, privacy.

Must include (canonical section order from `polish-2026-05-09-profile-section-sweep.md`):

- Tone-mode picker (gentle / coach / firmDirect)
- Appearance / palette picker
- Body metrics (height, weight)
- Daily reminder (opt-in, single local notification, 8…22 hour clamp; vision Decided 2026-05-09)
- Apple Health permission state (honest "Not configured / Available / No data" copy — never "Denied")
- Subscription — purchase / restore / **manage subscription** (pending pro-value-backlog Prompt 1)
- Completion badges
- SafetyNet entry (`profile.safetyNet`)
- Privacy — Delete all data (Free)
- About

## MVP feature list

### Must have

- Local-first user profile
- Baseline survey
- HealthKit authorization flow
- Step count import
- Exercise minutes / workouts import
- Sleep import
- Weight/BMI import if authorized
- Manual habits via QuickLog: smoking/vaping, alcohol, diet (fuel / rhythm / whole food / extras), stress, strength training, recovery, nicotine
- Clock estimate (additive minutes via `ClockEngine`) + healthspan years projection (`HealthspanEngine`, Future tab)
- Daily time delta on Today; driver decomposition ("Why it changed")
- Day detail + override (History, Pro-only)
- Today's Plan (1–3 supportive actions; replaces the standalone "Quests" surface)
- Weekly + Yesterday wrap-up sheets (in-app, pull-only on cold-launch via `WrapUpCoordinator`); History weekly cards (net Free, drivers+lever Pro) — replaces the standalone "Weekly Report" surface
- Future tab with TrajectoryChart + What-If Simulator (Pro)
- SafetyNet (mental-health crisis resources surface)
- Pro paywall (StoreKit 2, 3 SKUs; annual-first)
- Under-13 hard block in onboarding
- Privacy policy and ToS support pages

### Should have

- Widgets or Lock Screen quick glance — **deferred to v1.2** (no WidgetKit target in v1)
- Manual quick logging from Today screen — **shipped** (QuickLog card + toolbar)
- ~~Habit streaks~~ — **dropped**. Vision Decided constraint 2026-05-06: "monthly count, no streak." The previous rolling streak (`DietStreakCalculator`) and its derivatives were removed. Replaced by Today's monthly-logging banner.
- Tone modes — **shipped** (gentle / coach / firmDirect; vision Decided 2026-05-04)
- Confidence indicator — **shipped** (`ConfidenceModel.assign(snapshot:)` + `ConfidenceBadge`)
- Delete data — **shipped** (Profile, Free); Export data — **deferred** (placeholder, no UI)

### Later

- Apple Watch companion
- Meal photo estimate
- HRV / resting heart rate / VO2 max deeper scoring
- Blood pressure / glucose if manually entered or authorized
- Lab upload and interpretation
- AI health coach

## Explicitly out of scope for MVP

- Clinical diagnosis
- Bloodwork interpretation
- Supplement/medication recommendations
- Insurance discounts
- Social features
- Ads
- Selling health data
- Full calorie database
- Backend accounts unless required for purchases/sync

## Acceptance criteria

### Onboarding

- User can complete onboarding without granting every HealthKit permission.
- App explains each permission before the system alert.
- User sees a clear disclaimer that the app is not medical advice.

### Health data import

- App requests only MVP data types first.
- App handles missing or denied data gracefully.
- App does not imply denial; it says data is unavailable or not connected.

### Clock model

- App produces a starting estimate with confidence.
- App shows daily deltas tied to specific inputs.
- App never claims certainty about death date.

### Today's Plan (formerly "Quests" — surface label is "Today's Plan" since 2026-05-01 IA refactor)

- User receives 1-3 daily Today's Plan actions.
- Actions are based on available data and stated goals.
- Felt-time payoff after action completion is still in design (vision Open Q14; see `polish-2026-05-09-quest-completion-payoff.md`).

### Paywall

- User gets value before paywall pressure.
- Restore purchases works.
- Free user can continue basic logging.
