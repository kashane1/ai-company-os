# Technical Architecture

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
