# Paste-ready Codex Build Prompt

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
