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

## Users under 13 (COPPA posture)

Life Clock is a general-availability app, not a Kids Category app. We do not target or knowingly collect personal information from users under the age of 13.

The onboarding flow asks for date of birth at the `BaselineDOBView` step. If the reported DOB resolves to age below 13, the user is routed to a terminal block screen (`Under13BlockView`) and the flow stops there. Specifically, for a user we know to be under 13:

- No HealthKit consent prompt is shown.
- No `UserProfile` is materialized; no SwiftData write occurs.
- No telemetry value bucket records the underlying DOB — only an `under13Block` `screenAppeared` event with no payload.
- No subscription paywall is reached.
- The `OnboardingDraft` holding the reported DOB is transient `@State`; it is discarded on app exit and is never persisted to disk, Keychain, or iCloud.

This posture relies on the FTC's [February 2026 policy statement on age verification](https://www.ftc.gov/news-events/news/press-releases/2026/02/ftc-issues-coppa-policy-statement-incentivize-use-age-verification-technologies-protect-children), which explicitly permits operators to ask date of birth solely to determine age and to act on that result, without itself triggering verifiable-parental-consent obligations. Implementation reference: [09b_AGE_COMPLIANCE.md](09b_AGE_COMPLIANCE.md) §2.

**Public-facing privacy policy (the URL Apple's nutrition label points to) must include equivalent language.** Suggested paragraph:

> Life Clock does not knowingly collect personal information from users under the age of 13. As part of onboarding we ask for date of birth solely to determine age. If the date entered resolves to an age below 13, the app stops the onboarding flow at a block screen — no HealthKit data is requested, no profile is created, no subscription is offered, and the date of birth itself is not retained. If you believe a user under 13 has somehow provided us with information, contact us at [contact email] and we will delete it.

## Users in the EU (GDPR-K posture)

GDPR Article 8 sets the threshold for valid consent for information-society services at 16, with member-state discretion to lower to 13. Effective thresholds vary by country.

V1 ships a uniform 13+ floor across all storefronts. The defense relies on the local-first architecture: no personal data is transmitted off-device, so the bite of GDPR-K's verifiable-parental-consent requirement on data *processing* arguably does not attach. **This defense collapses the moment any off-device data flow is added** (analytics, backup, sync, server-side endpoints). Adding such a flow without first implementing per-jurisdiction age floors is a regression on this posture. See [09b_AGE_COMPLIANCE.md](09b_AGE_COMPLIANCE.md) §3 for the operator's accepted residual-risk decision and the country-by-country threshold table.
