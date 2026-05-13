> Source: Life Clock Founder Pack (2026-04-27). Normalized for platform use.

# Business Plan

## 1. Problem

Most people understand that health habits matter, but they struggle to connect today's behavior to a future consequence that feels immediate. A step count is abstract. A sleep score is temporary. A calorie target is easy to ignore.

Mortality, healthspan, and time are emotionally legible. The product opportunity is to translate daily behavior into the most intuitive unit possible: **time**.

## 2. Customer

### Primary ICP

Health-curious iPhone users, roughly 25-45, who already have some interest in self-improvement but are not deeply optimized biohackers. They likely own an Apple Watch or use iPhone Health data, and they respond to gamified feedback.

### Secondary ICP

- Habit tracker users who need stronger motivation.
- Fitness users who want healthspan framing, not gym-only tracking.
- Quantified-self users who like Apple Health dashboards but want interpretation.
- Mortality-curious users attracted by the shock value of a clock.

### Not the initial ICP

- Patients needing clinical care.
- Advanced longevity biohackers who expect lab interpretation.
- Users who want a full diet/macro tracker.
- Users who want a medical-grade life expectancy model.

## 3. Market logic

The category sits between four proven markets:

1. Health & Fitness subscriptions.
2. Habit tracking.
3. Gamified self-care.
4. Longevity / preventive health.

The key is to avoid competing directly with any one incumbent on their own terms. Do not beat MyFitnessPal at calorie logging. Do not beat Oura/WHOOP at wearable hardware. Do not beat clinical longevity clinics at lab interpretation. Own the app-level emotional loop: **what did today do to my time?**

## 4. Competitive landscape

### Direct competitor

Death Clock: The Life Lab validates the category but also creates a differentiation problem. It is positioned around AI, medical science, bloodwork, AI concierge, Apple Health/wearables, and a death date prediction [S1].

### Differentiation path

Life Clock should not try to out-clinic Death Clock. Instead, it should be:

- more game-like
- more habit-loop focused
- more transparent
- more Apple-native
- more emotionally safe
- more local-first/privacy-first
- less dependent on expensive lab workflows

## 5. Business model

Start with a free consumer core that creates habit and trust, then monetize advanced insights and personalization.

### Free value

See [`MONETIZATION.md`](MONETIZATION.md) § Free for the canonical list. Summary: starting Life Clock, basic Apple Health import (steps / exercise / active energy / resting HR / sleep / body mass), today's delta + drivers, 1-3 Today's Plan actions, recent History view (foggy-stack beyond ~3 days), Yesterday + Weekly wrap-up sheets (in-app, pull-only), QuickLog, tone modes, and the SafetyNet entry. Free should always answer "what happened today?" — the rule from `MONETIZATION.md` § Free vs Pro Rule.

### Paid value

Pro unlocks depth, archive, and correction power — never basic understanding. Shipped Pro (v1) per `MONETIZATION.md` § Pro Annual:

- **Full daily history** — every past day drillable in History
- **Weekly drivers + next-best lever** — `HistoryView.weeklySection` Pro cards + richer WrapUp content
- **Correction power** — override imported Apple Health values you know are wrong (`OverrideService`)
- **Custom Today's Plan** — Plan Editor selects which 1-3 actions you see
- **Deeper trend breakdown** — Future tab's What-If Simulator (`WhatIfSlider`, Pro-only)

Post-v1 candidates (do not promise on the paywall as shipped Pro):

- Advanced HealthKit metrics (v1.1)
- Widgets / Lock Screen surfaces (v1.2)
- AI meal/photo summaries (v2+)

## 6. Moat

The moat is not the calculation formula. The moat is habit, trust, data history, and emotional attachment to the clock.

If users build a 90-day personal history of time earned/lost, the app becomes increasingly personal.

## 7. Founder-level risk

The app can become creepy, medically risky, or gimmicky if framed wrong.

Mitigation:

- healthspan framing over death-date certainty
- confidence labels
- source transparency
- tone controls
- no clinical claims
- no HealthKit data monetization
