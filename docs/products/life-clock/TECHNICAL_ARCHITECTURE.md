> Source: Life Clock Founder Pack (2026-04-27). Updated to reflect the current iOS implementation on 2026-04-30.

# Technical Architecture

## Recommended stack

- SwiftUI
- SwiftData
- HealthKit
- StoreKit 2
- UserNotifications
- WidgetKit later
- ActivityKit only if a live quest/timer feature emerges
- App Intents later for quick logging
- Cloud backend only after local MVP proves value

## Architecture stance

Local-first. Health data stays on device. Derived app data is persisted with SwiftData and explicitly does not iCloud-sync.

Current implementation:

- `LifeClockStore` is the app-level observable state coordinator.
- `LifeClockSchemaV1` is a versioned SwiftData schema from day one.
- `HealthKitServiceProtocol` hides the live-vs-mock data source boundary.
- `SubscriptionStore` is the single source of truth for Pro entitlement state.
- `NotificationsService` schedules local-only daily reminders; there is no push backend.

## Core models

### UserProfile

- id
- birthDate
- biologicalSex
- heightCm optional
- weightKg optional
- smokingStatus
- alcoholFrequency
- dietQualityBaseline
- stressBaseline
- strengthFrequencyPerWeek
- sleepGoalHours
- toneMode
- paletteId
- dailyReminderEnabled
- dailyReminderHour
- lastSuppressedDate optional
- onboardingCompletedAt optional
- disclaimerAcceptedAt optional
- hideClock

### DailyHealthSnapshot

- date
- stepCount optional
- distanceMeters optional
- exerciseMinutes optional
- activeEnergyKcal optional
- sleepHours optional
- sleepConsistencyScore optional
- restingHeartRate optional
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
- projectedAgeYears
- projectedDate optional
- healthspanScore
- dailyTimeDeltaMinutes
- confidenceRaw
- explanation

### TimeLedgerEntry

- id
- date
- title
- deltaMinutes
- source
- confidenceRaw
- driverType
- questSlug optional

### Quest

- id
- slug
- date
- title
- detail
- category
- target
- progress
- rewardEstimateMinutes
- completedAt optional

### WeeklyReport

- weekStart
- weekEnd
- netTimeDeltaMinutes
- topPositiveDriver
- topNegativeDriver
- nextBestLever
- confidenceRaw

## Services

### HealthKitServiceProtocol

- requestAuthorization
- dailySnapshot
- recentSnapshots
- authorizationKnown
- isHealthDataAvailable

### ClockEngine

- calculateBaseline
- calculateDailyDelta
- calculateWeeklyTrend

### QuestEngine

- generateDailyQuests
- adaptToMissingData
- avoid unsafe medical advice

### SubscriptionStore

- product loading
- entitlement refresh
- purchase
- restore

### NotificationsService

- local-notification authorization
- daily reminder scheduling
- same-day reminder suppression after a check-in
- tone-aware reminder copy

## Testing priorities

- deterministic `ClockEngine` coverage
- confidence and aggregation behavior
- missing-data behavior
- quest generation and persistence behavior
- StoreKit entitlement and restore behavior
- HealthKit mock-path coverage
- cold-start restoration and reset behavior
- end-to-end app flow coverage with the mock health path

## V1 engineering rule

Do not add a backend until the local daily loop proves retention.
