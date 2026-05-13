> Source: Life Clock Founder Pack (2026-04-27). Normalized for platform use.

# Health Data Strategy

## Strategy

Do not ask for everything at once. Use progressive permission prompts and explain why each HealthKit data type matters.

Apple HealthKit requires fine-grained authorization, and users can grant or deny each data type separately [S3][S4]. Denied read access can appear as missing data from the app's perspective [S3]. The product must treat missing data as normal.

## MVP HealthKit data

### Tier 1: core passive signals (as shipped — six types)

`LiveHealthKitService.coreReadTypes` requests exactly these six types on first HealthKit authorization:

- step count (`HKQuantityType.stepCount`)
- exercise minutes (`HKQuantityType.appleExerciseTime`)
- active energy (`HKQuantityType.activeEnergyBurned`)
- resting heart rate (`HKQuantityType.restingHeartRate`)
- sleep analysis (`HKCategoryType.sleepAnalysis`)
- body mass / weight (`HKQuantityType.bodyMass`)

Apple's HealthKit quantity identifiers include activity, body measurements, vital signs, sleep/mindfulness, nutrition, alcohol, mobility and other categories [S5].

### Not currently read from HealthKit (despite founder-pack v0 listing them as Tier-1)

These were anticipated in the original founder pack but are **not requested** by the live `LiveHealthKitService` and have no call site in `Sources/`:

- walking/running distance
- workouts (`HKWorkoutType`)
- height — collected manually in onboarding (`UserProfile.heightCm`), not from HealthKit
- BMI — computed inline by `ClockEngine` from height + body mass; not read from `.bodyMassIndex`
- heart rate (`.heartRate`)
- VO2 max (`.vo2Max`)

These are candidates for Phase 2 advanced-HealthKit work (`ROADMAP_METRICS.md` Phase 2). Doc claims that they currently inform the engine are stale.

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

## Permission request sequence (as shipped)

The v1 implementation requests all six Tier-1 types in **a single HealthKit authorization sheet** at the `healthKitAuth` onboarding screen. The progressive multi-stage prompt described in earlier drafts is not implemented and is not on the v1 critical path. Honest disclosure pattern:

1. Explain value at the `healthKitAuth` onboarding screen.
2. Show iOS's single HealthKit sheet covering all six types.
3. Show first clock even if data is incomplete (`MockHealthKitService` is wired for simulator / `dailySnapshot` returns nil-tolerant snapshots).
4. Persist a `hasAskedHKAuth` flag in `UserDefaults` (`lc.hk.requestedCore`) so the Profile copy can honestly show "Not configured / Available / No data" — never "Denied" (`HealthKitServiceProtocol` doc comment).
5. Phase 2 may introduce a second prompt for advanced types (heart rate / VO2 max / etc.); not in v1.

## Critical UX rule

Never block the app behind full HealthKit access.
