# Life Clock Privacy Policy

**Last updated:** 2026-04-28
**App:** Life Clock: habits earn time
**Publisher:** [REPLACE WITH LEGAL ENTITY OR INDIVIDUAL NAME]
**Contact:** [REPLACE WITH SUPPORT EMAIL]

## Plain-English Summary

Life Clock is a healthspan habit-tracking app for iPhone. We are designed local-first, which means **your health data does not leave your device** unless you explicitly ask it to (e.g., a future export feature). We do not have a backend that stores your data, we do not show ads, we do not sell or share your data with third parties for marketing, and we do not use your Apple Health data for anything other than running the app for you.

**If you remember nothing else from this page, remember this:** what stays on your iPhone, stays on your iPhone.

## What Data the App Touches

### Apple Health (HealthKit)

If you grant permission, the app reads — but **never writes** — the following from Apple Health to estimate your daily Life Clock delta:

- Step count
- Apple Exercise minutes
- Active energy burned
- Resting heart rate
- Sleep analysis (asleep duration)
- Body mass (weight)

We **do not** request permission to read or write any other Apple Health data type. You can revoke any of these permissions at any time in iOS Settings → Health → Data Access & Devices → Life Clock.

Apple Health data:
- Stays on your device.
- Is **not** stored in our database (we don't have one).
- Is **not** transmitted to any server.
- Is **not** used for advertising, marketing, or data mining.
- Is **not** shared with third parties.

This is required by Apple's HealthKit policy and by our own privacy posture. If a future version ever changes this, we will update this policy and require your explicit consent before any change takes effect.

### Information You Enter Manually

When you onboard and use the app, you may enter:

- Your date of birth
- Your biological sex (optional, for population life-expectancy baseline)
- Your height and weight (optional)
- Your smoking status, alcohol frequency, baseline diet quality, baseline stress, sleep goal, weekly strength training frequency
- Per-day "Quick Log" entries: alcohol level, smoking/vaping, diet quality, stress, strength training, optional notes
- Tone-mode preference (gentle / coach / memento mori)

This information is stored **only** on your device using Apple's SwiftData framework, and is **not** synced to iCloud, our servers, or any third party. Apple's iCloud sync is explicitly disabled for our data store (`cloudKitDatabase: .none`).

If you choose **Profile → Delete all data** in the app, all of the above is permanently removed from your device. We have no copy to delete on our side, because we never had one.

### Subscription Information

If you purchase Life Clock Pro (monthly, annual, or lifetime), the transaction is handled entirely by Apple via StoreKit 2. Apple is the merchant of record. We receive an **anonymous, app-scoped transaction record** confirming whether you currently have an active subscription. We do not receive your name, email, billing address, payment method, or any other identifying information from Apple. We cannot link a subscription to a person.

## What Data the App Does NOT Touch

We want to be explicit about what the app does **not** do, because the wrong assumption here is the most common privacy concern:

- **No third-party analytics SDKs.** No Firebase, no Mixpanel, no Amplitude.
- **No third-party crash reporting in v1.** (If we add Sentry or TelemetryDeck later, we will update this policy first and never include health-derived fields in crash reports.)
- **No advertising IDs.** We do not use IDFA, IDFV-for-tracking, or any ad-tech identifier.
- **No tracking across apps or websites** as defined by Apple's App Tracking Transparency framework.
- **No location collection.** We do not request `CoreLocation` permission.
- **No microphone or camera access.**
- **No contacts, calendar, or photos access.**
- **No background data uploads.** The app cannot upload data because there is nowhere to upload it to.

## App Privacy Details (App Store "Nutrition Label")

Per Apple's privacy disclosure requirements, our App Store listing reports:

- **Data Linked to You:** None.
- **Data Not Linked to You:** None.
- **Data Used to Track You:** None.

If we ever change this — for example, by adding optional crash reporting — we will update both this page and the App Store listing before the change ships.

## Children's Privacy

Life Clock is rated **12+** in the App Store. Users who report a date of birth that makes them under 18 will not see the app's smoking or alcohol logging questions. The app is not designed for children under 12, and we do not knowingly collect data from children under 12.

## Health Disclaimer

Life Clock is a wellness and habit-tracking app. It is **not a medical device, a diagnostic tool, or a substitute for professional medical advice**. The Life Clock estimate is based on publicly available population life-expectancy data (CDC FastStats) and a transparent rules engine. It is not a personalized prediction of your lifespan. Always talk to a qualified clinician about health concerns.

If the app's mortality framing causes anxiety, the in-app **Profile → If this app is making you anxious** screen offers a softer presentation, a "hide the clock" toggle, and links to mental-health crisis resources.

## Your Choices

- **Revoke Apple Health access** at any time: iOS Settings → Health → Data Access & Devices → Life Clock.
- **Delete all data** stored by the app: in-app, Profile → Delete all data.
- **Cancel a subscription:** iOS Settings → [your name] → Subscriptions.
- **Stop using the app:** delete it from your device. Because we have no server, there is nothing for us to retain on your behalf.

## Contact

Questions about this privacy policy: **[REPLACE WITH SUPPORT EMAIL]**.

We respond within 7 business days.

## Changes to This Policy

If we materially change this policy, we will post the updated version at the same URL (this page) and bump the "Last updated" date at the top. For significant changes (e.g., adding any data collection that didn't exist before), we will surface an in-app notice and require your acknowledgement before the change applies to you.
