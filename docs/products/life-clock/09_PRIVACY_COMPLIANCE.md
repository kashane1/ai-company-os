# Privacy, Compliance, and Trust Guardrails

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
