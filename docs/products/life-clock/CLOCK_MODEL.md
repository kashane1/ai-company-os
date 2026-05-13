> Source: Life Clock Founder Pack (2026-04-27). Normalized for platform use.

# Clock Model

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

## Two engines (both ship)

The shipped app uses two parallel projection layers. **The doc must distinguish them.**

- **`ClockEngine`** (`Sources/Engines/ClockEngine.swift`) — emits the **additive daily minutes ledger**. Calculates `baseline`, `dailyDelta`, and `weeklyTrend`. This is what powers Today's signed delta + History per-day decomposition.
- **`HealthspanEngine`** (`Sources/Engines/HealthspanEngine.swift`) — emits the **years-based healthspan projection** shown on the Future tab and as the headline projection number. Coefficient table lives in `docs/products/life-clock/healthspan-coefficients.md` and is verbatim-matched to the engine's published constants (14 coefficients, +14y cap above baseline, smoking-dominance 0.3× scale, floor at `currentAge + 1`).

When a section below talks about "the clock," interpret it as `ClockEngine` unless explicitly otherwise.

## Score components

### Baseline profile score (engine inputs as shipped)

The shipped baseline engine reads **all** of these from `UserProfile`:

- age (from `birthDate`)
- biological sex
- height + weight → BMI (computed inline)
- smoking status
- alcohol frequency
- **cardio minutes per week** (`cardioMinsPerWeek`)
- **strength frequency per week**
- sleep goal hours
- diet quality baseline (`dietQualityBaseline`)
- **parental longevity** (mother + father age-at-death / alive)
- **PSS-10 perceived stress score** (`perceivedStressScore` — vision Q9 Decided constraint 2026-05-12)
- **UCLA-3 loneliness score** (`lonelinessScore` — vision Q9 Decided constraint 2026-05-12)

### Daily behavior score

Inputs:

- steps
- exercise minutes
- workouts
- sleep duration and consistency
- strength training
- diet quality
- diet amount rhythm (V1.2.0)
- whole-food anchor (V1.2.0)
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

### Diet composite (V1.2.0)

The daily diet driver composes three self-reported signals into one
ledger entry. Conservative additive coefficients keep the composite
range bounded; quality sets the dominant sign.

- Quality (`great` / `okay` / `rough`): +12 / 0 / -10
- Amount rhythm (`right` / `overate` / `undereate` / `skipBinge` / `irregular`): 0 / -3 / -3 / -5 / -2
- Whole-food anchor (`yes` / `almost` / `no` / `unknown`): +3 / +1 / 0 / 0

Composition: pure additive. No clamps. Range bounded at -15..+15. Defaults
(`okay` / `right` / `unknown`) all contribute zero, so a row that exists
without explicit user input produces no ledger noise.

Confidence: when only rhythm or anchor contribute (no quality answer
beyond the default), the entry is emitted at `low` confidence rather than
`medium` — preserves the confidence-by-evidence invariant.

Schema versioning: V1.0 → V1.1 → V1.2 are all in-place `versionIdentifier`
bumps on a single `LifeClockSchemaV1` enum with `MigrationStage.stages =
[]`. Pragmatic for purely-additive lightweight migrations; the next
non-additive change (rename / custom transform) will force a real
`SchemaV2` split per WWDC25 Session 291 guidance.
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

## Smoothing (as shipped — honest)

The clock should not swing wildly day by day. **v1 ships an additive rolling sum, not an EMA.** Specifically:

- Daily time delta for immediate feedback — accurate.
- Weekly trend = additive sum of daily deltas across the seven-day window (`ClockEngine.calculateWeeklyTrend`). No exponential smoothing or anti-jitter logic.
- "Significant warning before big negative changes" — not implemented in v1; the rescue line (`rescueLine` on Today) is the only soft-interpretation layer for negative deltas. Trajectory math (`HealthspanEngine.weeklyTrajectory`) uses linear interpolation from `baseline at -weeksBack` to `baseline-current at -1`, not a sliding window of historical aggregates — see engine comment for the v1 simplification rationale.

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
