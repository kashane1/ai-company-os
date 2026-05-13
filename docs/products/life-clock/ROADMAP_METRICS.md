> Source: Life Clock Founder Pack (2026-04-27). Normalized for platform use.

# Roadmap and Metrics

> **Instrumentation status (2026-05-13):** Analytics and crash-reporting are intentionally absent pre-TestFlight (see `PHASE_STATUS.md`). Telemetry events exist for the onboarding funnel (`OnboardingTelemetry` protocol) with `privacy: .private` on all values, but no aggregator is wired. The metrics below describe the *target* funnel; computing them requires post-TestFlight analytics work. **Sequencing source of truth is `PHASE_STATUS.md`, not this roadmap.**

## Phase 1: MVP (shipped 2026-04 → 2026-05; pre-TestFlight)

Goal: prove the daily loop.

Shipped surfaces:

- Onboarding — reveal escalator + healthspan dial (~29 screens, `OnboardingScreen.swift`)
- Apple Health live reads (steps, exercise minutes, active energy, resting heart rate, sleep, body mass)
- Baseline survey + sensitive-consent block (PSS-10, UCLA-3, parental ages; vision Q9 Decided 2026-05-12)
- Clock estimate (`ClockEngine` additive minutes) + healthspan projection (`HealthspanEngine` years; Future tab)
- Today (Life Clock + drivers + Today's Plan + monthly logging banner + ReflectionCard + DisclaimerBanner)
- History (yesterday wrap-up, weekly cards, day detail + override; foggy stack beyond 3 days for Free)
- Future tab (TrajectoryChart + What-If Simulator, Pro-gated)
- WrapUp (yesterday + weekly in-app sheets, pull-only on cold-launch; vision Decided 2026-05-09)
- SafetyNet (mental-health crisis resources)
- QuickLog (manual habit logging)
- Paywall (3-tier StoreKit 2: monthly / annual / lifetime; annual-first; no trial in v1)
- Under-13 hard block in onboarding
- Notifications — one daily reminder, opt-in, 8…22 hour clamp, evening canonical (vision Decided 2026-05-09); wrap-ups pull-not-push

## Phase 2: Apple-native depth (post-TestFlight)

Goal: make the app feel native and sticky.

Features (in priority order):

- Widgets / Lock Screen surfaces (v1.2 — no WidgetKit target in v1)
- Apple Watch companion
- HealthKit advanced metrics — concrete next candidates: HRV, VO2 max, blood pressure
- Trend-vs-prior-week comparison in History weekly cards (the only remaining Phase 2 trend gap per `PHASE_STATUS.md`)

## Phase 3: AI assistance

Goal: add interpretation without medical overclaiming.

Features:

- meal photo estimate
- personalized Today's Plan action explanations
- weekly coach summary
- habit suggestions

## Phase 4: deeper longevity

Goal: expand for power users.

Features:

- blood pressure and glucose tracking
- lab upload
- clinician-reviewed content if needed
- deeper reports

## North star metric

**Weekly active users who complete at least 3 Today's Plan actions per week.** (Surface label is "Today's Plan," not "quests"; user-facing "quests" was dropped in the 2026-05-01 IA refactor.) Requires analytics instrumentation — post-TestFlight.

## Activation metrics

- onboarding completion rate
- HealthKit permission rate
- first clock reveal rate
- first Today's Plan action completion rate
- first QuickLog entry rate

## Retention metrics

- D1, D7, D30 retention
- weekly WrapUpSheet impressions (in-app sheet, cold-launch-triggered — not a "report opens" metric since there's no separate report surface)
- Today's Plan actions completed per active user
- Monthly logging count distribution (calendar-month logged-days; vision Decided constraint 2026-05-06: "monthly count, no streak" — rolling-streak metrics rejected)
- History day-detail opens (Pro)

## Monetization metrics

- free-to-paid conversion (no trial in v1 — `Products.storekit` has `introductoryOffer: null`; free-to-trial only applies once App Store Connect introductory pricing for `pro.annual` lands per `PHASE_STATUS.md`)
- annual vs monthly vs lifetime mix
- paywall view → subscribe
- refund rate
- renewal rate

## Health data metrics

- average connected data types
- missing data patterns
- confidence score distribution
- manual habit logging frequency

## Emotional safety metrics

- tone mode selected
- app deletions after first clock reveal
- negative feedback mentioning anxiety/fear
- support requests about accuracy
