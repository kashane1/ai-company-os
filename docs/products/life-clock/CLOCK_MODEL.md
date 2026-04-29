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
