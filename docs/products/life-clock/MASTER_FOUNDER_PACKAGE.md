# Life Clock Founder Package

Prepared for: Founder

Version: 1.0

Date: April 27, 2026

Working title: Life Clock

## Executive Summary

## Working title

**Life Clock** is the working title. It is not final. Other brand candidates include TimeBack, Long Game, DayBank, Clockwise, and Healthspan Quest.

## Concept

Life Clock is an iPhone-first Health & Fitness app where daily behavior moves a user's projected life trajectory. Instead of presenting a fixed death date, the app turns healthspan into a game: sleep, movement, workouts, nutrition, stress, alcohol, smoking, and consistency can add or subtract time from a visible clock.

## Wedge

**Earn time back with better daily habits.**

This is more defensible and App Store-safe than "predict your death date." The app can still have a dramatic clock, but the product promise should be agency-based: your trajectory changes as your behavior changes.

## Why this is worth building

There is direct demand for the concept. Death Clock: The Life Lab is a Health & Fitness app with approximately 15K ratings at 4.8 and membership IAPs ranging roughly from $39.99 to $99.99, plus higher-ticket baseline options [S1]. That validates user curiosity and willingness to pay, but it also means a generic "death clock" app is no longer novel.

The opening is to build a more elegant, less medically risky, more game-like, Apple-native version focused on daily behavior change.

## Category recommendation

Primary App Store category: **Health & Fitness**.

Secondary positioning: **Lifestyle / habit formation / quantified self**.

Do not use Games as the primary category. The game mechanic is the retention layer; the buyer intent is health improvement.

## Founder recommendation

Build this as a **HealthKit-powered longevity game**, not a clinical longevity app and not a literal death prediction oracle.

## MVP promise

"Connect Apple Health. See today's time delta. Complete daily quests to earn time back."

## MVP loop

1. User completes a short baseline.
2. User grants progressive Apple Health permissions.
3. App calculates a starting Life Clock and confidence level.
4. Each day, passive HealthKit data and quick manual inputs update the clock.
5. The app shows what moved the clock most.
6. The app gives 1-3 quests to improve tomorrow.
7. Weekly report summarizes time earned, time lost, and best next lever.

## What v1 should not do

- Do not claim to know the user's real death date.
- Do not provide diagnosis or treatment advice.
- Do not interpret bloodwork in v1.
- Do not build a calorie database in v1.
- Do not sell ads or use HealthKit data for advertising.
- Do not require every HealthKit permission on first launch.
- Do not make the app emotionally punitive by default.

## Initial monetization

Use freemium with an annual-first subscription.

Recommended initial pricing:

- Free: starting Life Clock, basic Apple Health import, 3 daily quests, 7-day trend.
- Pro Annual: $39.99-$59.99/year.
- Pro Monthly: $7.99-$9.99/month.
- Lifetime: $99.99-$149.99.

Avoid weekly pricing. RevenueCat's 2026 benchmark highlights materially stronger retention for yearly plans versus weekly/monthly plans, and Health & Fitness is a category where annual plans can support better long-term economics [S2].

---

## Business Plan

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

The free version must be useful enough to build trust:

- baseline Life Clock
- Apple Health step/workout/sleep import
- daily time delta
- limited daily quests
- 7-day history

### Paid value

Pro should unlock depth, not basic dignity:

- full time ledger
- advanced health data sources
- weekly reports
- custom quests
- advanced trend breakdown
- widgets / Lock Screen surfaces
- AI meal/photo summaries later
- export/delete controls

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

---

## Product Strategy

## Positioning statement

For health-curious iPhone users who want stronger motivation to improve their daily habits, Life Clock is a HealthKit-powered longevity game that translates sleep, movement, workouts, nutrition, stress, and risk habits into a visible time trajectory.

## Category

Primary: **Health & Fitness**

Subcategory language: longevity, healthspan, habit game, Apple Health tracker, self-improvement.

## Core wedge

**Earn time back with better daily habits.**

## What this app is

- A daily healthspan game.
- A personal time ledger.
- A habit tracker with consequences.
- A HealthKit-powered coaching surface.
- A dramatic but agency-centered behavior-change product.

## What this app is not

- Not a medical device.
- Not a diagnosis tool.
- Not a real death-date oracle.
- Not a doctor replacement.
- Not a calorie tracker.
- Not a full longevity clinic.
- Not an ad-supported health-data business.

## Product principles

### 1. Agency over fear

The app can be emotionally intense, but it should make the user feel they can act.

### 2. Trajectory over prophecy

The clock reflects a current estimate, not fate.

### 3. Confidence is part of the product

If data is sparse, say so. Unknown data should reduce confidence rather than invent precision.

### 4. Passive first, manual second

Use Apple Health where possible. Manual input should be quick, coarse, and optional.

### 5. Health data is sacred

No ads. No sale of HealthKit data. No marketing/data mining use. Clear privacy policy and permission education are mandatory [S3][S6].

### 6. Daily loop before clinical depth

The app should prove daily behavior change before adding bloodwork, AI health concierge, or advanced risk models.

### 7. The game mechanic is time, not points

Points are abstract. Time is primal.

## App personality

Default tone: motivating, elegant, direct, slightly dramatic.

Optional tone modes:

- Gentle: healthspan only, no death language.
- Coach: balanced default.
- Memento Mori: more direct mortality framing.

## Core product sentence

"Today's habits moved your Life Clock by +42 minutes. Here's why, and here's how to improve tomorrow."

---

## Product Requirements Document

## Product purpose

Help users understand how daily habits affect their healthspan trajectory and motivate them to improve through time-based feedback and quests.

## MVP user story

As a health-curious iPhone user, I want to connect Apple Health and see how today's sleep, movement, workouts, and habits changed my projected time, so that I can make better choices tomorrow.

## Core screens

### 1. Onboarding

Purpose: establish trust, explain the app, collect baseline, and request health permissions progressively.

Must include:

- value framing
- non-medical disclaimer
- baseline profile
- progressive HealthKit education
- tone mode selection
- initial Life Clock reveal

### 2. Today

Purpose: show the main clock and today's movement.

Must include:

- Life Clock / projected date or healthspan meter
- today's time delta
- confidence level
- top drivers
- daily quests
- manual quick log button

### 3. Time Ledger

Purpose: explain what moved the clock.

Must include:

- chronological entries
- source icons: HealthKit, manual, estimate
- positive/negative time deltas
- confidence notes

### 4. Quests

Purpose: give the user 1-3 achievable actions.

Must include:

- daily movement quest
- sleep/consistency quest
- risk-habit quest
- weekly strength quest where relevant

### 5. Weekly Report

Purpose: show progress and the best next lever.

Must include:

- time earned/lost this week
- biggest positive driver
- biggest drag
- next best habit lever
- trend vs prior week

### 6. Profile / Settings

Purpose: manage baseline data, tone, permissions, privacy, and subscription.

Must include:

- baseline profile
- connected data sources
- Health permission state
- tone mode
- privacy/export/delete
- paywall/restore purchases

## MVP feature list

### Must have

- Local-first user profile
- Baseline survey
- HealthKit authorization flow
- Step count import
- Exercise minutes / workouts import
- Sleep import
- Weight/BMI import if authorized
- Manual habits: smoking/vaping, alcohol, diet quality, stress, strength training
- Clock estimate
- Daily time delta
- Time ledger
- Daily quests
- Weekly report
- Pro paywall
- Privacy policy and ToS support pages

### Should have

- Widgets or Lock Screen quick glance
- Manual quick logging from Today screen
- Habit streaks
- Tone modes
- Confidence indicator
- Export/delete data

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

### Quests

- User receives 1-3 daily quests.
- Quests are based on available data and stated goals.
- Completed quests produce visible time-ledger feedback.

### Paywall

- User gets value before paywall pressure.
- Restore purchases works.
- Free user can continue basic logging.

---

## Health Data Strategy

## Strategy

Do not ask for everything at once. Use progressive permission prompts and explain why each HealthKit data type matters.

Apple HealthKit requires fine-grained authorization, and users can grant or deny each data type separately [S3][S4]. Denied read access can appear as missing data from the app's perspective [S3]. The product must treat missing data as normal.

## MVP HealthKit data

### Tier 1: core passive signals

These should be requested early because they power the basic loop:

- step count
- walking/running distance
- workouts
- exercise minutes / active energy
- sleep analysis
- height
- weight/body mass
- BMI if available
- resting heart rate if available
- heart rate if available
- VO2 max if available

Apple's HealthKit quantity identifiers include activity, body measurements, vital signs, sleep/mindfulness, nutrition, alcohol, mobility and other categories [S5].

## Manual baseline inputs

HealthKit will not cover everything. The app needs a short baseline survey:

- age/date of birth
- biological sex for population baseline if the user consents
- smoking/vaping status
- alcohol frequency
- typical diet quality
- typical stress level
- strength training frequency
- sleep schedule goal
- current chronic condition disclaimer / optional skip
- family history optional later, not MVP-critical

## Daily manual inputs

Manual input must be coarse and fast:

- alcohol today: none / light / heavy
- smoking/vaping today: no / yes
- diet today: great / okay / rough
- stress today: low / medium / high
- strength training: yes / no
- mindful minutes: imported or manual

## Pro / later data

Add these after trust is built:

- HRV
- respiratory rate
- blood oxygen
- blood pressure
- blood glucose
- body fat percentage
- waist circumference
- nutrition macros
- caffeine
- number of alcoholic drinks
- medications / supplements adherence
- lab upload

## Confidence model by data source

| Source | Confidence | Product behavior |
|---|---:|---|
| Apple Health passive data | High | Use directly, show source |
| Apple Watch metrics | High | Use if enough recent samples exist |
| Manual daily input | Medium | Use but label as self-reported |
| Baseline survey | Medium-low | Use as a starting estimate |
| Meal photo estimate | Medium | Later, show as estimate only |
| Missing data | Unknown | Lower confidence, do not over-penalize |

## Permission request sequence

1. Explain value in onboarding.
2. Request steps, workouts, sleep, height, weight.
3. Show first clock even if data is incomplete.
4. Later ask for heart rate / VO2 max when explaining advanced precision.
5. Later ask for nutrition or alcohol only when the feature needs it.

## Critical UX rule

Never block the app behind full HealthKit access.

---

## Clock Model

## Model principle

The Life Clock should be a transparent rules engine in v1, not a black-box medical AI.

The app should say:

"This is a healthspan trajectory estimate based on your current data, not a medical prediction."

## Baseline

Use public population life expectancy as context. CDC FastStats lists U.S. life expectancy at birth as 79.0 years for both sexes, 76.5 for males, and 81.4 for females, based on Mortality in the United States, 2024 [S8].

This should be used carefully:

- as a population anchor
- not as a personal guarantee
- not as a clinical life table substitute

## Score components

### Baseline profile score

Inputs:

- age
- sex if provided
- height/weight/BMI
- smoking status
- alcohol frequency
- general activity level
- sleep baseline

### Daily behavior score

Inputs:

- steps
- exercise minutes
- workouts
- sleep duration and consistency
- strength training
- diet quality
- alcohol
- smoking/vaping
- stress/mindfulness

### Weekly trend score

Inputs:

- seven-day movement trend
- seven-day sleep consistency
- workout frequency
- risk habit frequency
- weight trend if available and appropriate

## Time delta examples

These examples are product-tuning placeholders, not clinical claims:

- Hit movement target: +10 to +30 minutes
- Completed workout: +15 to +45 minutes
- Sleep within target range: +10 to +25 minutes
- Strength training completed: +20 to +40 minutes
- Heavy alcohol day: negative delta
- Smoking logged: negative delta
- Very sedentary day: negative delta
- Missing data: lower confidence, not automatic penalty

## CDC activity anchor

CDC adult guidelines recommend at least 150 minutes of moderate-intensity physical activity weekly plus 2 days of muscle-strengthening activity [S9]. Use this as a quest anchor, not as a personal medical prescription.

## Confidence calculation

Each daily score should have confidence:

- High: enough passive HealthKit data plus recent baseline.
- Medium: some passive data plus manual inputs.
- Low: mostly manual or sparse data.

The UI should show:

- "Confidence: High"
- "Based on Apple Health steps, workouts, and sleep"
- "Missing: heart rate, VO2 max"

## Smoothing

The clock should not swing wildly day by day. Use smoothing:

- daily time delta for immediate feedback
- weekly trend for actual Life Clock movement
- significant warning before big negative changes

## Safety boundaries

Do not say:

- "You will die on this date."
- "This habit added 3.2 years to your life."
- "Guaranteed lifespan improvement."
- "You need medication/supplements."

Safer wording:

- "Your current trajectory moved by..."
- "Estimated time delta."
- "Based on available data."
- "This is not medical advice."
- "Talk to a clinician for medical decisions."

---

## UX and Game Loop

## Core loop

1. Open Today.
2. See clock movement.
3. Understand top drivers.
4. Complete one quest.
5. Log one optional habit.
6. Return tomorrow for updated trajectory.

## The game mechanic

The core game currency is **time**.

Not points. Not coins. Not XP.

Time is emotionally legible and directly connected to the concept.

## Main surfaces

### Today screen

Primary elements:

- Life Clock
- Today's delta
- confidence label
- top 3 drivers
- daily quests
- quick log

Example copy:

"+42 minutes today"

"Your strongest drivers were steps, sleep, and no alcohol logged."

### Time Ledger

Purpose: make the estimate explainable.

Example entries:

- +18 min - 9,800 steps - Apple Health
- +14 min - 43 exercise minutes - Apple Health
- +10 min - 7h 38m sleep - Apple Health
- -12 min - high stress logged - Self-report

### Quests

Quest types:

- movement quest
- sleep consistency quest
- strength quest
- nutrition quality quest
- risk reduction quest
- recovery/stress quest

Example quests:

- Walk 7,500 steps today.
- Take a 10-minute walk after dinner.
- Log no alcohol today.
- Complete 2 strength sessions this week.
- Be in bed by your target window.

### Weekly report

Example sections:

- Time earned this week
- Time lost this week
- Best driver
- Biggest drag
- Next best lever
- Confidence changes

## Tone modes

### Gentle

No death-date language. Uses healthspan score, time earned, and future-self framing.

### Coach

Default. Uses Life Clock but avoids harsh language.

### Memento Mori

More dramatic. Uses direct countdown language, but still avoids medical certainty.

## Onboarding flow

1. Value screen: "Earn time back with better habits."
2. Safety screen: "Your clock is an estimate, not fate."
3. Baseline profile.
4. Tone mode.
5. Apple Health education.
6. Permission request.
7. First Life Clock reveal.
8. First quest.

## UX risk

The biggest UX risk is creating anxiety. The default should be motivating, not punishing.

Every negative delta should be paired with an actionable next step.

---

## Monetization Strategy

## Recommendation

Use a Health & Fitness freemium subscription model with annual-first pricing and optional lifetime.

RevenueCat's 2026 subscription benchmarks emphasize that yearly subscriptions retain materially better than weekly and monthly subscriptions, while weekly plans have very weak long-term retention [S2]. This product should avoid weekly pricing.

## Pricing

### Free

- starting Life Clock
- basic HealthKit import
- today's time delta
- 3 daily quests
- 7-day trend
- basic manual habits

### Pro Annual

Recommended: **$39.99-$59.99/year**

Unlocks:

- full time ledger
- advanced HealthKit metrics
- weekly reports
- custom quests
- deeper trend breakdown
- widgets / Lock Screen surfaces
- tone modes
- export/delete controls
- AI meal/photo summaries later

### Pro Monthly

Recommended: **$7.99-$9.99/month**

Useful for trial-conversion users who resist annual pricing.

### Lifetime

Recommended: **$99.99-$149.99**

Good for indie trust and anti-subscription users.

## Paywall timing

Do not show a hard paywall before first value.

Best conversion moments:

1. After first Life Clock reveal.
2. After the user taps locked detailed driver breakdown.
3. After the first weekly report preview.
4. When the user wants advanced HealthKit metrics.
5. When the user wants widget/Lock Screen surfaces.

## Trial stance

Use a 7-day trial on annual if the app has enough immediate value. Avoid a confusing 3-day trial unless analytics later prove it.

## What not to monetize in v1

- basic Apple Health import
- basic clock
- privacy/export/delete
- safety disclaimers
- basic logging

## Business logic

The clock is the activation hook. The weekly report is the retention hook. Pro should unlock deeper clarity and personalization, not block the emotional core.

---

## App Store and ASO Strategy

## Category

Primary category: **Health & Fitness**

Do not use Games as primary. The game layer improves engagement, but user intent and monetization fit Health & Fitness.

## Naming strategy

Avoid launching as "Death Clock" because a direct competitor already uses that territory strongly [S1]. Also, the phrase can create unnecessary anxiety and App Review sensitivity.

## Name candidates

1. TimeBack
2. Life Clock
3. Long Game
4. DayBank
5. Clockwise Health
6. Healthspan Quest
7. Extra Time
8. Future You
9. Longevity Ledger
10. Memento Health

## Subtitle options

- Earn time with better habits
- Your healthspan habit game
- Apple Health longevity tracker
- Turn healthy habits into time
- See how habits move your life

## App Store description angle

Lead with agency, not death.

Example:

"Life Clock turns your Apple Health data and daily habits into a simple time-based game. See what moved your healthspan trajectory today, complete small quests, and build a longer, stronger future one day at a time."

## First screenshots

1. **See your Life Clock**
2. **Earn time with healthy habits**
3. **Apple Health updates your progress**
4. **Find what is costing you time**
5. **Complete daily longevity quests**
6. **Track your healthspan trend**

## Keyword themes

- longevity
- healthspan
- habit tracker
- Apple Health
- life expectancy
- wellness
- sleep tracker
- fitness tracker
- self improvement
- health score

## App Review posture

Marketing must match the UI. Do not claim medical accuracy or diagnosis. Keep the app clearly in wellness / fitness / behavior-change territory.

---

## Privacy, Compliance, and Trust Guardrails

## Core stance

Health data is sacred. The app should be local-first, privacy-first, and transparent.

Apple HealthKit documentation says health data is sensitive, users control permissions per data type, and apps must clearly disclose how HealthKit data is used [S3][S4]. Apple's App Review Guidelines also restrict health, fitness, and medical data use for advertising, marketing, or data mining and require disclosure of specific health data collected [S6].

## Required rules

### Do

- Provide a privacy policy.
- Explain every HealthKit permission in plain language.
- Request only data that powers a visible feature.
- Use progressive permission prompts.
- Store as much as possible locally.
- Let users delete their data.
- Clearly label estimates.
- Use confidence levels.
- Include a medical disclaimer.

### Do not

- Do not use HealthKit data for ads.
- Do not sell HealthKit data.
- Do not share HealthKit data with non-health/fitness third parties without express permission.
- Do not imply denial of HealthKit permission when data is absent.
- Do not write false or inaccurate data into HealthKit.
- Do not present the clock as medical truth.
- Do not recommend medication/supplements in v1.

## App Store privacy details

Apple requires apps to provide App Privacy details in App Store Connect describing data collection, linkage, tracking, and use [S7]. This product should aim for:

- no third-party tracking
- no ads
- minimum analytics
- clear separation between product analytics and health data

## Medical disclaimer draft

"Life Clock provides wellness and habit insights for informational purposes only. It is not medical advice, diagnosis, treatment, or a guarantee of lifespan. Your Life Clock is an estimate based on available data and should not be used for medical decisions. Talk to a qualified clinician about health concerns."

## Emotional safety

Because the product uses mortality framing, the app must support tone control and avoid punitive language.

Required:

- gentle mode
- non-medical framing
- actionable next steps after negative deltas
- no doom notifications
- no manipulative fear-based paywall

## Data handling recommendation

V1 should be local-first with SwiftData. If a backend is added later, store only derived app records unless raw health data storage is absolutely necessary and reviewed carefully.

---

## GTM and Launch Plan

## Positioning ladder

Functional: see how today's habits moved your clock.

Emotional: earn time back.

Identity: become the kind of person who plays the long game.

## Launch wedge

Do not market as a scary death calculator first. Market as a healthspan game with a dramatic clock.

Top message:

**Earn time back with better habits.**

Supporting messages:

- See what moved your Life Clock today.
- Apple Health turns into daily quests.
- Build a longer, stronger future one day at a time.
- Your clock is not fate. It is feedback.

## Initial channels

1. TikTok/Reels short-form hooks.
2. Reddit quantified-self and habit communities.
3. Indie hacker / build-in-public content.
4. Apple Watch / HealthKit creator content.
5. SEO landing page around healthspan habit tracking.
6. TestFlight beta with self-improvement users.

## Creative hooks

- "I built an app that tells me if today cost or earned me time."
- "Your step count is boring. What if it changed your life clock?"
- "This is not a death prediction. It is a habit mirror."
- "Apple Health, but with consequences."
- "I earned 42 minutes back today."

## 90-day launch plan

### Days 1-15: validation and design

- finalize name
- make landing page
- create Figma prototype or SwiftUI prototype
- interview 10 target users
- test copy: death-clock vs life-clock vs time-earned framing

### Days 16-45: MVP build

- SwiftUI app shell
- HealthKit read integration
- baseline onboarding
- clock model v1
- Today screen
- ledger
- quests
- weekly report
- paywall

### Days 46-65: beta

- TestFlight with 50-100 users
- measure activation
- collect emotional safety feedback
- adjust model and tone
- tune paywall timing

### Days 66-90: launch

- App Store assets
- landing page
- 20 short videos
- influencer outreach
- launch to one primary audience
- review conversion and retention

## Success test

The app is worth continuing if users come back after the first shock moment and complete quests for at least one week.

---

## Roadmap and Metrics

## Phase 1: MVP

Goal: prove the daily loop.

Features:

- onboarding
- HealthKit core import
- baseline survey
- clock estimate
- Today screen
- time ledger
- quests
- weekly report
- paywall

## Phase 2: Apple-native depth

Goal: make the app feel native and sticky.

Features:

- widgets
- Lock Screen widget
- Apple Watch glance later
- HealthKit advanced metrics
- notification timing
- better trends

## Phase 3: AI assistance

Goal: add interpretation without medical overclaiming.

Features:

- meal photo estimate
- personalized quest explanations
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

**Weekly active users who complete at least 3 quests.**

## Activation metrics

- onboarding completion rate
- HealthKit permission rate
- first clock reveal rate
- first quest completion rate
- first manual log rate

## Retention metrics

- D1, D7, D30 retention
- weekly report opens
- quests completed per active user
- 7-day streak rate
- time ledger views

## Monetization metrics

- free-to-trial conversion
- trial-to-paid conversion
- annual vs monthly mix
- paywall view to subscribe
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

---

## Technical Architecture

## Recommended stack

- SwiftUI
- SwiftData
- HealthKit
- StoreKit 2
- WidgetKit later
- ActivityKit only if a live quest/timer feature emerges
- App Intents later for quick logging
- Cloud backend only after local MVP proves value

## Architecture stance

Local-first. Health data should stay on device where possible. Derived app data can be stored in SwiftData.

## Core models

### UserProfile

- id
- dateOfBirth / age bucket
- sex optional
- height
- weight
- toneMode
- onboardingCompletedAt
- disclaimerAcceptedAt

### HealthPermissionState

- dataType
- requestedAt
- status: unknown / connected / unavailable
- lastReadAt

### DailyHealthSnapshot

- date
- stepCount
- distance
- exerciseMinutes
- activeEnergy
- workouts
- sleepDuration
- sleepConsistency
- restingHeartRate
- heartRate
- vo2Max
- sourceCompleteness

### HabitLog

- date
- alcoholLevel
- smokingVaping
- dietQuality
- stressLevel
- strengthTraining
- notes

### LifeClockEstimate

- date
- projectedAge
- projectedDate optional
- healthspanScore
- dailyTimeDeltaMinutes
- confidence
- explanation

### TimeLedgerEntry

- id
- date
- title
- deltaMinutes
- source
- confidence
- driverType

### Quest

- id
- date
- title
- category
- target
- progress
- rewardEstimateMinutes
- completedAt

### WeeklyReport

- weekStart
- weekEnd
- netTimeDelta
- topPositiveDriver
- topNegativeDriver
- nextBestLever
- confidence

## Services

### HealthKitService

- requestAuthorization
- fetchDailySnapshot
- observeUpdates later
- handle unavailable data gracefully

### ClockEngine

- calculateBaseline
- calculateDailyDelta
- calculateWeeklyTrend
- assignConfidence
- generateLedgerEntries

### QuestEngine

- generateDailyQuests
- adaptToMissingData
- avoid unsafe medical advice

### PaywallService

- StoreKit products
- entitlement state
- restore purchases

## Testing priorities

- ClockEngine deterministic tests
- confidence model tests
- missing data behavior
- quest generation tests
- paywall entitlement tests
- HealthKit service mocked tests

## V1 engineering rule

Do not add a backend until the local daily loop proves retention.

---

## Paste-ready Codex Build Prompt

Start in planning mode, then implement phase by phase.

We are building a new iPhone-first Health & Fitness app with the working title **Life Clock**.

## Product framing

Life Clock is a HealthKit-powered longevity game. It shows how daily habits move a user's projected healthspan trajectory, then gives small quests to earn time back.

The wedge is:

**Earn time back with better daily habits.**

This is not:

- a medical device
- a diagnosis app
- a literal death-date oracle
- a calorie tracker
- a social app
- a clinical longevity concierge

Core rules:

- agency over fear
- trajectory over prophecy
- confidence labels everywhere
- passive HealthKit data first
- manual input must be quick and coarse
- no ads
- no HealthKit data sale or advertising use
- local-first MVP

## Read first

Read the founder pack files in order:

1. README.md
2. 00_EXECUTIVE_SUMMARY.md
3. 03_PRD.md
4. 04_HEALTH_DATA_STRATEGY.md
5. 05_CLOCK_MODEL.md
6. 09_PRIVACY_COMPLIANCE.md
7. 12_TECHNICAL_ARCHITECTURE.md

## Mission for first pass

Create the first real iOS MVP skeleton.

Do not overbuild. Do not add backend. Do not add AI. Do not add lab interpretation. Do not add a full calorie tracker.

## Scope

Implement:

1. SwiftUI app shell
2. onboarding flow
3. local SwiftData models
4. HealthKit permission wrapper with mockable service boundary
5. Today screen with placeholder/sample clock
6. Time Ledger screen
7. Daily Quests screen
8. Profile/Settings screen
9. ClockEngine v1 as deterministic pure Swift logic
10. QuestEngine v1 as deterministic pure Swift logic
11. focused unit tests for ClockEngine and QuestEngine

## UX requirements

- premium Apple-native feel
- emotionally safe language
- clear medical disclaimer
- confidence labels
- no paywall before first value
- missing HealthKit data must not break app

## Validation

Run relevant iOS tests. Report exact commands and results.

## Final report

Return:

1. Implementation plan used
2. Files created
3. Files modified
4. Product behavior implemented
5. Tests added
6. Validation commands and results
7. Known gaps
8. Next best MVP slice

---

## Open Questions

## Brand

1. Should the app lean into mortality with a name like Life Clock, or soften into TimeBack / Long Game?
2. Should the default UI show a projected date, projected age, or only a healthspan score?
3. Should "death clock mode" be an opt-in tone rather than the default?

## Product

4. How intense should negative feedback be?
5. Should users be able to hide the clock and only see time earned?
6. What is the minimum manual logging that feels useful but not annoying?
7. Should diet be a daily quality score in v1, or should photo meals launch early?

## Model

8. What public actuarial/lifestyle research should be used after MVP?
9. How much should one day affect the clock versus weekly trend smoothing?
10. How should the app communicate uncertainty without feeling weak?

## Compliance

11. Should a clinician review the copy before App Store submission?
12. Should the app be 13+, 17+, or general wellness depending on tone?
13. How should the app handle self-harm adjacent language or anxious users?

## Monetization

14. Should Pro launch at $39.99 or $59.99/year?
15. Should lifetime be available at launch?
16. Should the first paywall appear after initial reveal or after first weekly report?

## Technical

17. Should v1 be entirely local-first with no account?
18. Should derived data ever sync?
19. What HealthKit data types are requested on first launch versus later?

---

## Sources

- **[S1] Death Clock: The Life Lab - App Store**: https://apps.apple.com/us/app/death-clock-ai-health/id6499554412
  - Direct competitor benchmark: Health & Fitness category, iPhone app, 15K ratings at 4.8, Apple Health/wearables positioning, membership IAPs. Accessed Apr. 27, 2026.
- **[S2] RevenueCat State of Subscription Apps 2026**: https://www.revenuecat.com/state-of-subscription-apps-2026-productivity/
  - Subscription benchmark: yearly plans retain materially better than weekly/monthly; Health & Fitness yearly renewal retention cited as strong. Accessed Apr. 27, 2026.
- **[S3] Apple HealthKit - Protecting user privacy**: https://developer.apple.com/documentation/healthkit/protecting-user-privacy
  - HealthKit privacy requirements, fine-grained permissions, usage descriptions, no HealthKit data for ads/data mining/sale. Accessed Apr. 27, 2026.
- **[S4] Apple HealthKit - Authorizing access to health data**: https://developer.apple.com/documentation/healthkit/authorizing-access-to-health-data
  - HealthKit authorization should be requested per data type and can be progressive instead of all at once. Accessed Apr. 27, 2026.
- **[S5] Apple HealthKit - HKQuantityTypeIdentifier**: https://developer.apple.com/documentation/healthkit/hkquantitytypeidentifier
  - Reference for activity, body measurement, vital sign, sleep, nutrition, alcohol, mobility and other HealthKit quantity types. Accessed Apr. 27, 2026.
- **[S6] Apple App Review Guidelines**: https://developer.apple.com/appstore/resources/approval/guidelines.html
  - Health, fitness and medical data restrictions; disclosure requirements; restrictions on advertising/data mining and inaccurate HealthKit writes. Accessed Apr. 27, 2026.
- **[S7] Apple App privacy details on the App Store**: https://developer.apple.com/app-store/app-privacy-details/
  - Privacy nutrition label / App Store Connect disclosure requirements. Accessed Apr. 27, 2026.
- **[S8] CDC FastStats - Life Expectancy**: https://www.cdc.gov/nchs/fastats/life-expectancy.htm
  - U.S. life expectancy at birth: both sexes 79.0, males 76.5, females 81.4 from Mortality in the United States, 2024. Accessed Apr. 27, 2026.
- **[S9] CDC Adult Activity Guidelines**: https://www.cdc.gov/physical-activity-basics/guidelines/adults.html
  - Adults need at least 150 minutes moderate activity weekly and 2 days of muscle-strengthening activity. Accessed Apr. 27, 2026.

---

