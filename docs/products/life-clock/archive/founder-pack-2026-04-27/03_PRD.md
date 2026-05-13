# Product Requirements Document

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
