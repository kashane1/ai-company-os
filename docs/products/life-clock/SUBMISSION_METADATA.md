# App Store Connect Submission Metadata — Life Clock

> **Status:** Paste-ready. Every field below is final copy at the character limits Apple enforces. Open ASC → My Apps → Life Clock → the section named in each heading, and paste verbatim.
>
> **Last updated:** 2026-05-19
> **Build target:** v1.0 (1)
> **Bundle ID:** `io.aicompanyos.products.lifeclock`

---

## ASC → App Information

### Name (30 chars max, used 28)
```
Life Clock: habits earn time
```

### Subtitle (30 chars max, used 29)
```
See how habits move your life
```

### Primary Category
**Health & Fitness**

### Secondary Category
**Lifestyle**

### Bundle ID
`io.aicompanyos.products.lifeclock`

### SKU
`LIFECLOCK-IOS-001`

### Privacy Policy URL
```
https://kashane1.github.io/life-clock-legal/privacy-policy.html
```

### Subscription EULA / Terms URL (optional but recommended)
```
https://kashane1.github.io/life-clock-legal/terms-of-use.html
```

### Support URL
```
https://kashane1.github.io/life-clock-legal/support.html
```

### Marketing URL (optional)
Leave blank for v1.

---

## ASC → Pricing and Availability

- **Price tier:** Free
- **Availability:** All territories
- **Pre-order:** No

---

## ASC → App Privacy

Per `legal/privacy-policy.md` § App Privacy Details:

- **Data Linked to You:** None
- **Data Not Linked to You:** None
- **Data Used to Track You:** None
- **Privacy Choices:** None required (no data collected)

Apple's questionnaire walks through every data category. For each, answer **"No, we do not collect this data."** This is verified by the codebase — there is no analytics SDK, no remote backend, no `cloudKitDatabase` enabled, no `NSHealthUpdateUsageDescription` write callsites.

---

## ASC → Age Rating Questionnaire

> Re-run on the new 4+/9+/13+/16+/18+ tiers (Apple deprecated 12+ in July 2025).
> Target: **13+**. Detailed rationale in `AGE_COMPLIANCE.md` § 1.

| Category | Answer |
|---|---|
| Cartoon or Fantasy Violence | None |
| Realistic Violence | None |
| Prolonged Graphic or Sadistic Realistic Violence | None |
| Sexual Content or Nudity | None |
| Graphic Sexual Content and Nudity | None |
| Profanity or Crude Humor | None |
| **Alcohol, Tobacco, or Drug Use or References** | **Infrequent/Mild** |
| Mature/Suggestive Themes | None |
| Horror/Fear Themes | None |
| **Medical/Treatment Information** | **Infrequent/Mild** |
| Gambling — Simulated | None |
| Gambling — Contests | None |
| Unrestricted Web Access | No |
| Made for Kids | No |

**Expected result:** 13+.

---

## ASC → App Store → iOS App version page

### Promotional Text (170 chars max, used 164)
```
A calmer way to see how today's habits move your life. Apple Health–powered, local-first, no ads — your data never leaves your iPhone. Earn time, one day at a time.
```

### Description (4000 chars max, used 2,847)
```
Life Clock turns your Apple Health data and daily habits into a simple, time-based picture of where you're headed — and what you can change today.

WHAT IT DOES
Life Clock estimates how today's habits move your healthspan trajectory. Connect Apple Health and you'll see a personal Life Clock that responds to how you actually slept, moved, ate, and lived. Build a small daily plan. See what's costing you time. Earn time back with steady, doable changes.

NOT A DEATH PREDICTION
Life Clock is not a death-date prediction. It's an educational estimate built on population research and a transparent rules engine. The clock moves with your behavior so you can see the cost of a rough day and the payoff of a good one — never as a verdict, always as feedback.

THREE TONES, YOUR CHOICE
- Coach (default): motivating, no mortality language
- Gentle: softer framing, optional hide-the-clock
- Firm/Direct: a dramatic, agency-led register if that's what moves you

CORE LOOP
- Today: Life Clock, why it changed, top drivers, your daily plan
- History: yesterday's wrap-up, weekly net delta, drill into any day
- Future: long-horizon trajectory + Pro What-If Simulator
- Profile: tone, palette, Apple Health, subscription, Safety Net

APPLE HEALTH
With your permission, Life Clock reads — never writes — steps, exercise minutes, active energy, resting heart rate, sleep, and weight. Your data stays on your iPhone. No backend. No analytics. No advertising.

LIFE CLOCK PRO
The free tier is the full daily loop. Pro unlocks depth, archive, and correction:
- Full daily history (every day, not just the last few)
- Weekly drivers + your next-best lever
- Override Apple Health imports you know are wrong
- Custom daily plan (Plan Editor)
- Future tab's What-If Simulator

PRICING
- Monthly: $7.99
- Annual: $49.99
- Lifetime: $129.99 (one-time)

Subscriptions auto-renew until cancelled in iOS Settings. The free tier never expires.

SAFETY NET
Some people find mortality framing motivating; some find it heavy. The Safety Net screen (Profile) lets you switch to a softer tone, hide the clock entirely, or jump to mental-health crisis resources at any time.

PRIVACY POSTURE
- Local-first. No account.
- No third-party analytics, no advertising IDs.
- Apple Health data never leaves your device.
- Under-13 users are hard-blocked from the app.
- Full policy: https://kashane1.github.io/life-clock-legal/

DISCLAIMER
Life-impact minutes are educational estimates from population-level research. Life Clock is not medical advice, diagnosis, or treatment, and does not predict your lifespan. Talk to a qualified clinician for medical decisions.
```

### Keywords (100 chars max, used 99, comma-separated, no spaces)
```
longevity,healthspan,habit tracker,Apple Health,life expectancy,wellness,sleep,fitness,health score
```

### What's New in This Version (leave blank for first release, or use:)
```
First release. Habits earn time.
```

### Support URL
```
https://kashane1.github.io/life-clock-legal/support.html
```

### Marketing URL (optional, leave blank)

### Copyright
```
© 2026 Kashane Justin Sakhakorn
```

### Routing App Coverage File
Not applicable.

---

## ASC → App Review Information

### Sign-in required
**No** (no account required by app).

### Contact Information
- First Name: Kashane
- Last Name: Sakhakorn
- Phone Number: [your number]
- Email: lifeclock.support@gmail.com

### Demo Account
None required — the app has no account system. If ASC insists on a value, write `n/a` in both username and password.

### Notes (App Review Notes)
```
LIFE CLOCK — APP REVIEW NOTES

Local-first wellness + habit-tracking app. No backend, no account, no analytics, no ads. Apple Health data is read-only and never leaves the device (cloudKitDatabase: .none; no NSHealthUpdateUsageDescription write callsites in Sources/).

WHAT THE APP IS — AND ISN'T
- Life Clock estimates how today's habits move a healthspan trajectory.
- It is NOT a death-date prediction. The mortality reveal is shown once during onboarding and is suppressed for under-18 users.
- It is NOT medical advice. The DisclaimerBanner is present on every primary surface (Today, QuickLog, Profile, SafetyNet, Paywall, Onboarding).

DEFAULT TONE
The app launches in "Coach" tone (motivating, no mortality language). Reviewers can switch to "Firm/Direct" in Profile → Tone to see the dramatic register (shipped enum: firmDirect; earlier docs called this "Memento Mori").

AGE-COMPLIANCE BEHAVIOR
- Under-13 users hit a hard block at the DOB picker (BaselineDOBView → Under13BlockView). No HealthKit prompt, no paywall, no profile materialization.
- Under-18 users do not see smoking, alcohol, or mortality-reveal onboarding screens.
- Re-rated 13+ on the new (post-July-2025) Apple tier system. Full rationale: see app's bundled disclaimer + privacy policy.

IN-APP PURCHASES TO TEST
- com.lifeclock.pro.monthly  ($7.99/mo)
- com.lifeclock.pro.annual   ($49.99/yr)
- com.lifeclock.pro.lifetime ($129.99 one-time)

Each is presented in PaywallSheet with the full auto-renewal disclosure, Terms of Use link, Privacy Policy link, and a Restore Purchases button.

SAFETY POSTURE
The Safety Net screen (Profile → "If this app is making you anxious") provides:
1. One-tap switch to Gentle tone
2. Hide-the-clock toggle (the Life Clock card collapses to a calm summary)
3. Links to mental-health crisis resources (988 in US, plus international equivalents)

SANDBOX TESTER (PROVIDED ABOVE)
Sign in to iOS Settings → App Store → Sandbox Account before launching the app. The paywall will read the sandbox products. Restore Purchases works against sandbox transactions.

ONE-TIME REVEAL
The "~N years on the table" healthspan reveal is shown once per onboarding and never re-shown unless the user resets their profile. We answered "Infrequent/Mild" for Medical/Treatment Information accordingly.

LEGAL
- Privacy: https://kashane1.github.io/life-clock-legal/privacy-policy.html
- Terms:   https://kashane1.github.io/life-clock-legal/terms-of-use.html
- Support: https://kashane1.github.io/life-clock-legal/support.html
```

### Attachments
Skip — no demo video required.

---

## ASC → Version Release

**Manually release this version.** (Recommended for the first release; flip to automatic after a stable cadence.)

---

## ASC → In-App Purchases (must be created before Submit for Review)

### Subscription Group
- **Reference Name:** `Life Clock Pro`
- **App Name(s):** Life Clock

### `com.lifeclock.pro.annual` (Auto-Renewable Subscription)
- **Reference Name:** Life Clock Pro Annual
- **Subscription Group:** Life Clock Pro
- **Duration:** 1 Year
- **Price:** $49.99
- **Display Name:** `Life Clock Pro · Annual`
- **Description:** `Auto-renews yearly until cancelled in iOS Settings.`
- **Review Screenshot:** any paywall screenshot (use `screenshots/2026-05-19-paywall.png` once captured)
- **Review Notes:** `Subscription unlocks full daily history, weekly drivers + next-best lever, Apple Health override correction, custom daily plan editor, and the Future tab's What-If Simulator. Tested via the in-app PaywallSheet — accessible from any Pro-gated touchpoint or Profile → Subscription.`

### `com.lifeclock.pro.monthly` (Auto-Renewable Subscription)
- Same group as Annual
- **Duration:** 1 Month
- **Price:** $7.99
- **Display Name:** `Life Clock Pro · Monthly`
- **Description:** `Auto-renews monthly until cancelled in iOS Settings.`
- **Review Notes:** same as Annual.

### `com.lifeclock.pro.lifetime` (Non-Consumable IAP, outside the subscription group)
- **Reference Name:** Life Clock Pro Lifetime
- **Price:** $129.99
- **Display Name:** `Life Clock Pro · Lifetime`
- **Description:** `One-time purchase. All Pro features forever.`
- **Review Notes:** same as Annual.

After creating these, run this in the repo to verify IDs match Products.storekit:
```bash
grep '"productID"' products/life-clock-ios/Sources/Services/Products.storekit
```
Expected output:
```
"productID" : "com.lifeclock.pro.lifetime"
"productID" : "com.lifeclock.pro.monthly"
"productID" : "com.lifeclock.pro.annual"
```

---

## ASC → Sandbox Tester

ASC → Users and Access → Sandbox → **+** create one tester:
- Email: any `you+sandbox@gmail.com`-style address
- Password: an 8+ char password you'll remember
- Country/Region: United States
- First/Last name: anything

Sign in via iOS Settings → App Store → Sandbox Account (NOT the main Apple ID sign-in). Required to test the paywall against ASC's sandbox.

---

## ASC → TestFlight (before Submit for Review)

Test these on a real device:
1. Walk the 33-screen onboarding fresh-install end-to-end.
2. Verify under-13 hard block (use a sandbox account with DOB < 13).
3. Make a sandbox purchase on monthly, annual, and lifetime.
4. Tap every Pro touchpoint as Free → paywall should land.
5. Tap Manage Subscription as Pro → iOS-native sheet should open.
6. Trigger Safety Net → all 3 affordances should work.
7. Turn on Reduce Motion + accessibility XXXL text → no surface should break.
8. Q1–Q5 subscription lifecycle validations from `subscription-lifecycle-spec.md` § Outstanding.

---

## Screenshot set

See `docs/products/life-clock/screenshots/submission-v1/` for the captured set:
- 6 screenshots × iPhone 6.9" (iPhone 17 Pro Max simulator, 1320×2868)
- 6 screenshots × iPad 13" (iPad Pro 13" simulator, 2064×2752)

Each screenshot's caption is encoded in the filename suffix:
- `01-see-your-life-clock.png`
- `02-earn-time-with-habits.png`
- `03-apple-health-updates.png`
- `04-find-whats-costing-time.png`
- `05-daily-longevity-quests.png`
- `06-track-healthspan-trend.png`

Upload all six per device size to the ASC version page.

---

## Common rejection patterns (and our defenses)

| Pattern | Apple guideline | Defense |
|---|---|---|
| "Medical/Treatment claims" | § 1.4.1 | `LifeClockConfiguration.medicalDisclaimer` + `DisclaimerBanner` global; explicit "educational estimate, not a lifespan prediction" copy |
| "HealthKit data misuse" | § 1.4.5, § 5.1.3 | `cloudKitDatabase: .none`; no analytics SDK; no backend; no write callsites |
| "Manipulative-fear paywall" | § 5.6.3 | Tone modes (Gentle hides clock); Safety Net; paywall pitches value not fear |
| "Subscription disclosure missing" | § 3.1.2 | Auto-renew fineprint on every PaywallSheet render; Terms section in Terms of Use |
| "Age-rating mismatch" | Standard | 13+ explicit; under-13 hard block; under-18 alcohol/tobacco/reveal suppression |
| "Cal AI deceptive billing" | § 3.1.1, § 3.1.2 | No strikethrough, no countdown, no second-chance modal; total billed amount shown with equal prominence |
| "Dark pattern: buried cancel" | § 3.1.2 + § 5.6 | Profile → Subscription → Manage Subscription opens iOS-native sheet |

---

## Cross-references

- Original ASC setup walkthrough: `ASC_CHECKLIST.md`
- Submission-day operational runbook: `submission-runbook.md`
- Age compliance details: `AGE_COMPLIANCE.md`
- Paywall spec: `paywall-spec.md`
- Privacy + safety: `PRIVACY_COMPLIANCE.md`, `legal/privacy-policy.md`
