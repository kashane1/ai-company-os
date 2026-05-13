# App Store Connect Setup Checklist

> ASC = **App Store Connect**, the web console where you configure everything Apple's App Store needs to know about Life Clock: app listing, in-app purchases, sandbox testers, build uploads, review submissions.
>
> This is a **founder-only** checklist — none of these steps can be done from code. They're administrative actions on Apple's side. Plan ~3–4 hours total spread over 2–3 days (some steps gate on Apple processing time).

## Phase 0 — Prerequisites

- [ ] **Apple Developer Program membership** — $99/year. Sign up at <https://developer.apple.com/programs/enroll/>. If you're enrolling as an individual it's same-day; as a legal entity it can take ~1 week to validate D-U-N-S.
- [ ] **Bank/tax info in ASC** — required before you can sell IAPs. ASC → Agreements, Tax, and Banking. Without this, IAP products stay in "Missing Metadata" forever.
- [ ] **Two-factor auth on your Apple ID.** Required.

## Phase 1 — Create the app record

ASC → My Apps → "+" → New App.

- [ ] **Platform:** iOS.
- [ ] **Name:** `Life Clock: habits earn time` (max 30 chars — fits at 28).
- [ ] **Primary language:** English (US).
- [ ] **Bundle ID:** match your Xcode project: `io.aicompanyos.products.lifeclock`. (You'll need to register this Bundle ID first under [Identifiers](https://developer.apple.com/account/resources/identifiers/list) — check "HealthKit" capability when you do.)
- [ ] **SKU:** `LIFECLOCK-IOS-001` (internal-only; pick anything stable).
- [ ] **User Access:** Full Access (you).

## Phase 2 — App Information

ASC → My Apps → Life Clock → App Information.

- [ ] **Subtitle:** `See how habits move your life` (29 chars).
- [ ] **Category — Primary:** Health & Fitness.
- [ ] **Category — Secondary (optional):** Lifestyle.
- [ ] **Privacy Policy URL:** the GitHub Pages URL you set up per `legal/README.md`.
- [ ] **Subscription EULA URL** (optional, recommended): same site, terms-of-use page.

## Phase 3 — App Privacy

ASC → My Apps → Life Clock → App Privacy.

Per `legal/privacy-policy.md`, declare:

- [ ] **Data Types Collected:** None.
- [ ] **Tracking:** Not used.

The app does not collect any data on Apple's "linked to user / not linked / used to track" matrix. Health data is read locally and never leaves the device.

## Phase 4 — Age Rating Questionnaire

ASC → My Apps → Life Clock → App Information → Age Rating.

> **2026-05-10 update — Apple overhauled the rating system in July 2025.** The old `4+ / 9+ / 12+ / 17+` tiers were replaced with `4+ / 9+ / 13+ / 16+ / 18+`, with a Jan 31 2026 compliance deadline. Legacy `12+` was auto-mapped to **13+**. Apps that did not re-run the questionnaire by the deadline lost the ability to ship updates. Re-run before next submission. Full context in [09b_AGE_COMPLIANCE.md](09b_AGE_COMPLIANCE.md).

Walk through Apple's questionnaire on the new tiers. Answers that match the implemented behavior (target rating: **13+** with in-app under-13 hard block + under-18 alcohol/tobacco onboarding suppression + under-18 mortality-reveal suppression):

| Category | Answer | Rationale |
|---|---|---|
| Cartoon or Fantasy Violence | **None** | Mascot is non-violent. |
| Realistic Violence | **None** | — |
| Prolonged Graphic or Sadistic Realistic Violence | **None** | — |
| Sexual Content or Nudity | **None** | — |
| Graphic Sexual Content and Nudity | **None** | — |
| Profanity or Crude Humor | **None** | Tone modes don't profane. |
| Alcohol, Tobacco, or Drug Use or References | **Infrequent/Mild** | User self-reports baseline + daily check-in. Under-13 users hard-blocked from app entirely; under-18 users see neither the onboarding picker (since `35fdd54`) nor the QuickLog picker (`store.isAdultUser` gate). The 18+ users who do see these inputs choose from a small picker, not narrative content. |
| Mature/Suggestive Themes | **None** | — |
| Horror/Fear Themes | **None** | Lifespan framing is motivational, not horror. |
| Medical/Treatment Information | **Infrequent/Mild** | Healthspan habits content + explicit medical disclaimer ([09_PRIVACY_COMPLIANCE.md](09_PRIVACY_COMPLIANCE.md) §"Medical disclaimer draft"). The "~N years on the table" reveal screen is shown once per onboarding, suppressed for under-18 — that is "infrequent" by any reasonable reading. |
| Gambling — Simulated | **None** | — |
| Gambling — Contests | **None** | — |
| Unrestricted Web Access | **No** | App has no web view. |
| Made for Kids | **No** | Life Clock is general-availability, not Kids Category. See [09b_AGE_COMPLIANCE.md](09b_AGE_COMPLIANCE.md) §2 for why Kids Category isn't right for this app. |

**Expected result: 13+.** Confirm and save.

**Ambiguity flag (re-verify on submission):** the questionnaire asks about *frequency*. If a future App Review reviewer reads the once-per-onboarding mortality reveal as "frequent medical/treatment information" rather than "infrequent," the result could land at 16+. Pre-launch, walk a real reviewer's POV through onboarding once with the auditor's mindset and document the answer chosen. See `docs/products/life-clock/09b_AGE_COMPLIANCE.md` §1 for the line we landed on.

## Phase 5 — In-App Purchase Setup

This is the workflow that the engineering side of `Products.storekit` is designed to integrate with. The product IDs **must match** the ones already in code.

ASC → My Apps → Life Clock → Monetization → In-App Purchases.

### 5a — Subscription Group

- [ ] Click **"+"** next to Subscription Groups → **Create**.
- [ ] **Reference Name:** `Life Clock Pro` (internal-only).
- [ ] **App Name(s):** Life Clock.
- [ ] Save.

### 5b — Annual Subscription

Inside the Pro group, click **+ Subscription**:

- [ ] **Product ID:** `com.lifeclock.pro.annual` *(must match Products.storekit)*
- [ ] **Reference Name:** `Life Clock Pro Annual`
- [ ] **Subscription Duration:** 1 Year
- [ ] **Price:** $49.99 (or your preferred annual price)
- [ ] **Subscription Display Name:** `Life Clock Pro · Annual`
- [ ] **Description:** `Auto-renews yearly until cancelled in iOS Settings.`
- [ ] **Review Screenshot:** placeholder; can be replaced before submission.
- [ ] **Review Notes:** "Subscription unlocks the full weekly report breakdown — drivers, biggest drag, next best lever. Tested via in-app paywall on Weekly Report screen."

### 5c — Monthly Subscription

Same group, **+ Subscription**:

- [ ] **Product ID:** `com.lifeclock.pro.monthly`
- [ ] **Subscription Duration:** 1 Month
- [ ] **Price:** $7.99
- [ ] **Display Name:** `Life Clock Pro · Monthly`
- [ ] **Description:** `Auto-renews monthly until cancelled in iOS Settings.`

### 5d — Lifetime (Non-Consumable)

This is **outside** the Subscription Group. ASC → IAPs → **+** → **Non-Consumable**:

- [ ] **Product ID:** `com.lifeclock.pro.lifetime`
- [ ] **Reference Name:** `Life Clock Pro Lifetime`
- [ ] **Price:** $129.99
- [ ] **Display Name:** `Life Clock Pro · Lifetime`
- [ ] **Description:** `One-time purchase. All Pro features forever.`

### 5e — Confirm IDs match

```bash
# In the repo, verify the IDs in Products.storekit equal what you just typed in ASC:
grep productID products/life-clock-ios/Sources/Services/Products.storekit
```

Expected:

```
"productID" : "com.lifeclock.pro.lifetime"
"productID" : "com.lifeclock.pro.monthly"
"productID" : "com.lifeclock.pro.annual"
```

If any ID mismatches, the paywall in production will show "no products available". This is the most common pre-submission bug.

### 5f — Switch StoreKit config to Synced (when ready for TestFlight)

Today, `Products.storekit` is a **local** test config. Before TestFlight:

- Open Xcode → **Edit Scheme** → **Run** → **Options** → **StoreKit Configuration**
- For TestFlight builds, set this to **None** (so the app reaches the real ASC) or to **Synced** (so the local file mirrors ASC).
- For local sim development, leave it on `Products.storekit`.

## Phase 6 — Sandbox Testing

ASC → Users and Access → Sandbox.

- [ ] Create a sandbox tester account (a fake Apple ID + email — Apple provides a "+" button for this; the email is yours+`@gmail`-style, the password and name are made up).
- [ ] Sign into a real device's iOS Settings → Developer → Sandbox Apple ID with that account.
- [ ] Test all three product purchases. Test restore. Test refund (ASC → Sandbox → Manage transactions).

You will need the sandbox account's email + password to provide to App Review in submission notes.

## Phase 7 — TestFlight

After your first build is uploaded via Xcode:

- [ ] ASC → TestFlight → wait for the build to process (~10–30 min).
- [ ] **Test Information:** App Description, Feedback Email, Privacy Policy URL, License Agreement (Apple's standard EULA is fine).
- [ ] **Internal Testing** group → add yourself + early testers; no review needed.
- [ ] **External Testing** group → upload to Apple for "Beta App Review" (~24–48 hours). Once approved, invite up to 10,000 testers via email or public link.

Founder pack (`GTM_LAUNCH_PLAN.md` Days 46–65) targets 50–100 external testers.

## Phase 8 — Submission for Review

After TestFlight feedback and any necessary fixes:

- [ ] **App Preview & Screenshots:** 6.7" and 6.1" iPhone screens at minimum. Founder pack `APP_STORE_ASO.md` lists six suggested screen ideas.
- [ ] **Promotional Text** (170 chars, can be updated without resubmission).
- [ ] **Description** (4000 chars).
- [ ] **Keywords** (100 chars total, comma-separated, no spaces). Suggested set from `APP_STORE_ASO.md`: `longevity,healthspan,habit tracker,Apple Health,life expectancy,wellness,sleep,fitness,self improvement,health score`
- [ ] **Support URL:** could be the same GitHub Pages root.
- [ ] **App Review Notes:**
  - Sandbox tester credentials (Phase 6).
  - "Life Clock estimates a healthspan trajectory; it does **not** claim to predict death. The app is local-first; no health data leaves the device. Wedge is 'earn time with better habits' — agency-led, not fear-led."
  - Link to `legal/privacy-policy.md` (the live URL).
  - Tone-mode hint: "Default tone is 'Coach' (motivating, no mortality language). Tester can switch to 'Firm/Direct' in Profile to see the dramatic variant (shipped enum: `firmDirect`; earlier docs called this 'Memento Mori')."
- [ ] Submit for review. Median Apple review time in 2026 is ~24 hours; expect 1–3 days.

## Common Rejection Reasons (and how we've already addressed them)

| Guideline | Risk | Mitigation already in place |
|---|---|---|
| 1.4.1 Health/Medical | Claims of accuracy, diagnosis, treatment | `LifeClockConfiguration.medicalDisclaimer` + DisclaimerBanner on every screen + "estimate" framing throughout |
| 1.4.5 / 5.1.3 HealthKit | Data sale, ads, third-party sharing | `cloudKitDatabase: .none`, no analytics SDK, no backend. `NSHealthUpdateUsageDescription` is declared as forward-looking ("may save optional wellness entries… if you choose to enable this later"); v1 ships read-only — no write call sites exist in `Sources/`. |
| 3.1.1 In-App Purchase | External purchase flow | StoreKit 2 only; no web checkout |
| 3.1.2 Subscriptions | Missing renewal disclosure, ToS, restore | All three present in `PaywallSheet` |
| 4.0 Design / Minimum functionality | "Just a website" / dead app | Six functional screens + engines + persistence |
| 5.1.1 Data Collection | Mandatory account before value | No account in v1 — local-first |
| 5.1.2 Data Use | Health data for advertising | Forbidden by code path; no ad SDKs |

## Reference URLs (bookmark these)

- App Store Connect: <https://appstoreconnect.apple.com>
- Developer Program enrollment: <https://developer.apple.com/programs/enroll/>
- App Review Guidelines (read once, sections 1.4, 3.1, 5.1): <https://developer.apple.com/app-store/review/guidelines/>
- HealthKit privacy: <https://developer.apple.com/documentation/healthkit/protecting_user_privacy>
- Subscription policy: <https://developer.apple.com/app-store/subscriptions/>
- TestFlight overview: <https://developer.apple.com/testflight/>
