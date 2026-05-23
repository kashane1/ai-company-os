# Submission Prep Report — Life Clock v1.0

> **Generated:** 2026-05-19 by Claude (autonomous prep session)
> **Branch:** `submission-prep-life-clock`
> **Status:** 99% ready. Remaining work is administrative (ASC paste-in + Archive + Submit).

---

## What this report is

The user asked: *"How close is Life Clock to App Store submission? Get it as close as you can autonomously, and tell me what I have to do myself."*

This report is the answer. Section 1 says exactly where the app stands. Section 2 lists every artifact this session produced and where to find it. Section 3 is the **founder-only-can-do** list — every step that requires you (not me) at a real keyboard, signed in to Apple's web tools.

---

## 1. Current state

### What's done (no further action needed by you)
- ✅ App is feature-complete: 33-screen onboarding, Today/History/Future/Profile tabs, paywall, Safety Net, WrapUp coordinator, 4 distinct tone modes implemented
- ✅ 46 unit-test files exist covering engines, store, HealthKit, StoreKit
- ✅ Three IAP product IDs live in `Products.storekit`, matching what we'll create in ASC
- ✅ Legal site live at `https://kashane1.github.io/life-clock-legal/` with publisher name, support email, governing-law jurisdiction filled in
- ✅ Privacy policy + terms of use have no remaining placeholders
- ✅ `PrivacyInfo.xcprivacy` declares UserDefaults + FileTimestamp reasons correctly
- ✅ HealthKit entitlement on; usage descriptions in `Info.plist`
- ✅ Bundle ID `io.aicompanyos.products.lifeclock` configured
- ✅ App icon Icon-1024.png present (1024×1024 RGB, no alpha — App Store compliant)
- ✅ xcodegen 2.45.4 installed via Homebrew
- ✅ `LifeClock.xcodeproj` regenerated from `project.yml`
- ✅ Project builds clean against iOS 26.5 simulator (no errors, 2 pre-existing warnings)
- ✅ iOS 26.5 simulator runtime installed (was missing — Xcode 26.5 needs it)
- ✅ Submission metadata bundle prepared (paste-ready ASC copy)
- ✅ Linear ship-day checklist prepared
- ✅ Screenshot UI test target added (`AppStoreScreenshotsRecon.swift`)

### What's pending (requires you)
- ⏳ Paste your 10-char Apple Developer **Team ID** into `LifeClock.local.xcconfig`
- ⏳ Create the 3 IAPs in ASC (~10 min, all fields and copy ready in `SUBMISSION_METADATA.md`)
- ⏳ Run ASC age-rating questionnaire (~3 min, answers in `SUBMISSION_METADATA.md` § Age Rating)
- ⏳ Paste App Information + version-page metadata into ASC (~10 min)
- ⏳ Upload screenshots to ASC version page (~10 min — files in `docs/products/life-clock/screenshots/submission-v1/`)
- ⏳ Create a sandbox tester in ASC (~3 min)
- ⏳ Archive in Xcode → TestFlight (~15 min)
- ⏳ TestFlight smoke test on a real device (~20 min — non-negotiable)
- ⏳ Submit for Review (~3 min)

**Total founder time-to-submit:** 60–90 minutes assuming the smoke test passes first try.

---

## 2. Artifacts produced this session

All on branch `submission-prep-life-clock`:

| File | Purpose |
|---|---|
| `docs/products/life-clock/SUBMISSION_METADATA.md` | The paste bundle for every ASC field. Each section heading matches the corresponding ASC page. |
| `docs/products/life-clock/SUBMIT_DAY_CHECKLIST.md` | Linear, no-thinking-required checklist for shipping day. |
| `docs/products/life-clock/SUBMISSION_PREP_REPORT.md` | This file — the summary. |
| `docs/products/life-clock/screenshots/submission-v1/iphone-69/` | 6 captures from iPhone 17 Pro Max simulator (6.9", 1320×2868). |
| `docs/products/life-clock/screenshots/submission-v1/ipad-13/` | 6 captures from iPad Pro 13" simulator (2064×2752). |
| `products/life-clock-ios/LifeClock.local.xcconfig` | Per-machine config (gitignored). I created it with placeholder `DEVELOPMENT_TEAM = `. You paste your Team ID. |
| `products/life-clock-ios/LifeClock.local.xcconfig.example` | Committed template for future devs / other Macs. |
| `products/life-clock-ios/UITests/AppStoreScreenshotsRecon.swift` | The test that produces the screenshots above — re-runnable any time. |

---

## 3. What I cannot do — the founder-only list

I cannot touch App Store Connect, the Apple Developer portal, your keychain, or your physical iPhone. Every step below requires you at a keyboard signed into Apple's web tools.

### 3.1 Paste your Team ID into the xcconfig (1 minute)

1. Open https://developer.apple.com/account → Membership Details.
2. Copy the 10-character **Team ID** (looks like `ABCD123456`).
3. Open `products/life-clock-ios/LifeClock.local.xcconfig` and paste it after `DEVELOPMENT_TEAM = `. Save.

Xcode picks this up automatically. No regen needed.

### 3.2 Create the IAPs in App Store Connect (10 minutes)

ASC → My Apps → Life Clock → Monetization → In-App Purchases.

Use the verbatim copy in `SUBMISSION_METADATA.md` § ASC → In-App Purchases. Create in this order:
1. Subscription Group "Life Clock Pro"
2. `com.lifeclock.pro.monthly` ($7.99/mo) inside the group
3. `com.lifeclock.pro.annual`  ($49.99/yr) inside the group
4. `com.lifeclock.pro.lifetime` ($129.99 one-time, **non-consumable**, outside the group)

After creating, verify IDs match what's in code:
```bash
grep '"productID"' products/life-clock-ios/Sources/Services/Products.storekit
```

### 3.3 Run the age-rating questionnaire (3 minutes)

ASC → App Information → Age Rating. Answers in `SUBMISSION_METADATA.md` § Age Rating. Expected result: **13+**.

### 3.4 Fill App Information + Privacy + Pricing (10 minutes)

Open `SUBMISSION_METADATA.md` and paste each labeled field into the corresponding ASC field. The headings in the doc match the ASC page names exactly.

### 3.5 Fill version page (10 minutes)

ASC → App Store → iOS App → 1.0. Paste the description, promo text, keywords, copyright from `SUBMISSION_METADATA.md`. Leave "What's New" blank for first release (or use "First release. Habits earn time.").

### 3.6 Upload the screenshots (10 minutes)

From `docs/products/life-clock/screenshots/submission-v1/iphone-69/`: upload 01-06 to **6.9" iPhone**.
From `docs/products/life-clock/screenshots/submission-v1/ipad-13/`: upload 01-06 to **13" iPad Pro**.

If captures are blurry or the screen isn't framed right, you can re-run the test:
```bash
cd products/life-clock-ios
xcodebuild test -project LifeClock.xcodeproj -scheme LifeClock \
  -destination 'platform=iOS Simulator,name=iPhone 17 Pro Max,OS=26.5' \
  -only-testing:LifeClockUITests/AppStoreScreenshotsRecon
```
Then copy from `/tmp/lifeclock-appstore-screenshots/` to the screenshots dir.

### 3.7 Create a sandbox tester (3 minutes)

ASC → Users and Access → Sandbox → **+**. Use any `you+sandbox@gmail.com`-style address. Sign in via iOS Settings → App Store → Sandbox Account on your real iPhone before testing the paywall.

### 3.8 Archive + Upload (15 minutes)

```bash
cd products/life-clock-ios
open LifeClock.xcodeproj
```

In Xcode:
1. Edit Scheme → Run → Options → **StoreKit Configuration → None** (TestFlight uses real ASC products, not the local file).
2. Top bar → destination → **Any iOS Device (arm64)**.
3. Product → **Archive**.
4. Organizer → Distribute App → App Store Connect → Upload.
5. Encryption question → **No**.
6. Wait 10-30 min for ASC processing.

### 3.9 TestFlight smoke test (20 minutes — non-negotiable)

Install on a real iPhone via TestFlight.app. Walk:
- Fresh onboarding (33 screens)
- Under-13 hard block (with sandbox DOB < 13)
- Sandbox purchase on all 3 SKUs
- Every Pro touchpoint as Free → paywall
- Manage Subscription as Pro → iOS sheet opens
- Safety Net → all 3 affordances
- XXXL text + Reduce Motion

If anything fails, bump `CURRENT_PROJECT_VERSION` in `project.yml`, regen, re-archive. Loop until clean.

### 3.10 Submit for Review (3 minutes)

ASC → 1.0 → pick the TestFlight build → Submit. Reviewer turnaround in 2026 averages ~24h, expect 1-3 days.

---

## 4. Known risks the user should track

### High-confidence safe areas
The app's biggest rejection vectors are pre-mitigated. The full defense table is in `SUBMISSION_METADATA.md` § Common rejection patterns. Highlights:
- **Medical claims (§ 1.4.1):** `DisclaimerBanner` on every primary surface + "educational estimate, not a lifespan prediction" copy in `LifeClockConfiguration.medicalDisclaimer`
- **HealthKit misuse (§ 1.4.5 / 5.1.3):** `cloudKitDatabase: .none`, no analytics, no backend, no write callsites
- **Cal AI deceptive billing (§ 3.1.1 / 3.1.2):** PaywallPrimaryView docstring explicitly cites the Cal AI precedent — no strikethrough, no countdown, no second-chance modal

### Things to keep an eye on
- **Sandbox payments under "Processing" >30 min** → not a real failure; Apple's sandbox is slow
- **Reviewer might re-question 13+** → cite `AGE_COMPLIANCE.md` § 1 in your reply (under-13 hard block, under-18 alcohol/tobacco/reveal suppression, mortality reveal is once-per-onboarding = "infrequent")
- **Reviewer might re-question medical framing** → point them at the firmDirect tone being **opt-in**, not default; default tone is Coach with no mortality language

---

## 5. If you want to re-verify before submitting

```bash
# 1. Run full test suite
cd products/life-clock-ios
xcodebuild test -project LifeClock.xcodeproj -scheme LifeClock \
  -destination 'platform=iOS Simulator,name=iPhone 17 Pro,OS=26.5' \
  -only-testing:LifeClockTests

# 2. Re-capture screenshots
xcodebuild test -project LifeClock.xcodeproj -scheme LifeClock \
  -destination 'platform=iOS Simulator,name=iPhone 17 Pro Max,OS=26.5' \
  -only-testing:LifeClockUITests/AppStoreScreenshotsRecon
ls /tmp/lifeclock-appstore-screenshots/

# 3. Verify IAP IDs match
grep '"productID"' products/life-clock-ios/Sources/Services/Products.storekit

# 4. Verify Info.plist version
plutil -p products/life-clock-ios/Info.plist | grep -E "BundleShortVersion|BundleVersion"
```

---

## 6. Cross-references

Existing project docs that remain authoritative:
- `submission-runbook.md` — full operational detail for the build → archive → review cycle
- `ASC_CHECKLIST.md` — original ASC setup walkthrough (one-time)
- `AGE_COMPLIANCE.md` — 13+ rationale for App Review
- `PHASE_STATUS.md` — bump from "pre-TestFlight" to "shipped" after approval

---

**Net:** You're a paste-and-click session away from submitting. All copy is final, all builds compile, the only unautomatable steps are Apple's web tools and the physical-device TestFlight walk.
