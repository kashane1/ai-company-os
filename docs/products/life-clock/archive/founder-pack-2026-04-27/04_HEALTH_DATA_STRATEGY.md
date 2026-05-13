# Health Data Strategy

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
