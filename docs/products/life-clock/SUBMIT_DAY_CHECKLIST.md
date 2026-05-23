# Submit Day Checklist — Life Clock v1.0

> **Purpose:** the linear, no-thinking-required list to ship Life Clock from "everything prepped" to "Submitted for Review."
>
> **Inputs already prepared by automation:**
> - `LifeClock.xcodeproj` regenerated via `xcodegen`
> - `LifeClock.local.xcconfig` created with a `DEVELOPMENT_TEAM = ` placeholder (paste your Team ID before archive)
> - `SUBMISSION_METADATA.md` — paste-ready copy for every ASC field
> - `screenshots/submission-v1/` — captured 6×iPhone-6.9" + 6×iPad-13" set (assuming the sim-runtime download succeeded; see fallback below)
> - Branch: `submission-prep-life-clock` (rebase to main before opening Xcode if main moved)
>
> **Time estimate:** 60–90 minutes if Apple Developer Program is enrolled, bank/tax filled, and ASC app record exists. Add ~30 min if any of those are still pending.

---

## 0 — Pre-flight (1 minute)

- [ ] `git -C /Users/kashane/dev/ai-company-os status` — make sure you're on `submission-prep-life-clock` (or merged into your trunk).
- [ ] Confirm legal site loads: open https://kashane1.github.io/life-clock-legal/privacy-policy.html in Chrome. Should render real privacy text, not 404.
- [ ] Confirm support email inbox exists: log into lifeclock.support@gmail.com. Apple reviewers will email this if they reject.

## 1 — Paste your Team ID (1 minute)

1. In your browser, sign in to https://developer.apple.com/account.
2. Click "Membership Details." Copy the 10-character **Team ID**.
3. Open `products/life-clock-ios/LifeClock.local.xcconfig`. Paste the Team ID after `DEVELOPMENT_TEAM = `. Save.
4. Xcode picks this up at build time; no `xcodegen generate` re-run is needed.

## 2 — Confirm ASC IAPs match `Products.storekit` (5 minutes)

In ASC → My Apps → Life Clock → Monetization → In-App Purchases, you should have:

- [ ] Subscription Group "Life Clock Pro" with two subscriptions:
  - `com.lifeclock.pro.monthly` @ $7.99 / 1 month
  - `com.lifeclock.pro.annual`  @ $49.99 / 1 year
- [ ] One non-consumable: `com.lifeclock.pro.lifetime` @ $129.99

Display names + descriptions + Review Notes verbatim from `SUBMISSION_METADATA.md` § ASC → In-App Purchases.

Verify IDs match the code:
```bash
grep '"productID"' products/life-clock-ios/Sources/Services/Products.storekit
```

All three should appear. If any is missing, paywall in TestFlight will show "no products available" — single most common pre-submission bug.

## 3 — Run Apple's Age Rating questionnaire (3 minutes)

ASC → App Information → Age Rating → walk it. Answers in `SUBMISSION_METADATA.md` § ASC → Age Rating. Result: **13+**. Save.

## 4 — Fill in App Information + Pricing + App Privacy (5 minutes)

Each field in `SUBMISSION_METADATA.md` corresponds to an ASC field with the same heading. Paste verbatim.

- [ ] App Information → Name, Subtitle, Categories, Privacy Policy URL, Terms URL, Support URL.
- [ ] Pricing → Free, all territories.
- [ ] App Privacy → Run Apple's questionnaire. Every data-category answer is "No, we do not collect." Final disclosure: Data Linked = None, Data Not Linked = None, Tracking = None.

## 5 — Fill in the version page (5 minutes)

ASC → App Store → iOS App → 1.0.

- [ ] Promotional Text (170 chars; from metadata bundle)
- [ ] Description (4000 chars; from metadata bundle)
- [ ] Keywords (100 chars; from metadata bundle)
- [ ] Copyright (from metadata bundle)
- [ ] Support URL, Marketing URL (leave Marketing blank)
- [ ] What's New (skip for first release, or use "First release. Habits earn time.")

## 6 — Upload screenshots (10 minutes)

ASC version page → Media → Screenshots.

- [ ] **6.9" iPhone:** upload 6 PNGs from `docs/products/life-clock/screenshots/submission-v1/iphone-69/` in numeric order (01–06).
- [ ] **13" iPad Pro:** upload 6 PNGs from `docs/products/life-clock/screenshots/submission-v1/ipad-13/`.

Apple no longer requires 6.5" iPhone or 12.9" iPad screenshots if you provide 6.9" iPhone + 13" iPad. The set we captured is sufficient.

If captures didn't happen because of the sim-runtime mismatch, fallback path:
1. Open Xcode → Window → Devices and Simulators → Simulators tab → boot iPhone 17 Pro Max + iPad Pro 13" (M5) on iOS 26.3.
2. In Xcode → Product → Run on each simulator with the `LIFECLOCK_UI_TEST_SCENARIO=onboarded LIFECLOCK_HEALTH_AUTH=authorized LIFECLOCK_SEED_STREAK=7 LIFECLOCK_HEALTH_PROFILE=baseline` env vars set.
3. Navigate to each screen in `APP_STORE_ASO.md` § First screenshots.
4. ⌘S in the simulator menu → File → Save Screen → save each.

## 7 — Archive + Upload (15 minutes)

In a terminal:
```bash
cd /Users/kashane/dev/ai-company-os/products/life-clock-ios
# bump build number if you're re-uploading after a previous attempt
# (open project.yml, increment CURRENT_PROJECT_VERSION, then `xcodegen generate`)
open LifeClock.xcodeproj
```

In Xcode:
1. Top bar → destination → pick **"Any iOS Device (arm64)"**. Real device or generic — NOT simulator.
2. Edit Scheme → Run → Options → **StoreKit Configuration** → set to **None** (so TestFlight builds hit the real ASC products, not the local `Products.storekit`).
3. **Product → Archive**.
4. When Organizer opens → select the new archive → **Distribute App** → **App Store Connect** → **Upload**.
5. Compliance question — encryption beyond what's exempt? → **No** (HTTPS-only, no custom crypto).
6. Symbols → automatic. Signing → automatic.
7. Upload. Wait ~10-30 min for ASC processing.

## 8 — TestFlight smoke test (20 minutes — non-negotiable)

ASC → TestFlight → wait for build to leave "Processing."
- [ ] Add yourself as Internal Tester (no Apple review needed for internal).
- [ ] Install on a real iPhone via TestFlight.app.
- [ ] Walk the 33-screen onboarding fresh.
- [ ] Try a sandbox purchase on **all three** SKUs (monthly + annual + lifetime). Confirm each unlocks Pro touchpoints. Confirm Restore Purchases works.
- [ ] Tap a Pro-gated touchpoint as Free → confirm PaywallSheet renders.
- [ ] Tap Manage Subscription as Pro → confirm iOS-native sheet opens.
- [ ] Tap Profile → Safety Net → confirm gentle-tone switch, hide-clock toggle, and crisis-resource links all work.
- [ ] Set iOS Settings → Accessibility → Larger Text → XXXL. Re-launch app. Confirm no surface breaks.
- [ ] Settings → Accessibility → Motion → Reduce Motion on. Confirm clock + onboarding still animate gracefully.

If anything fails: fix in code, bump `CURRENT_PROJECT_VERSION` in `project.yml`, regenerate, re-archive. Loop until TestFlight is clean.

## 9 — Submit for Review (3 minutes)

ASC → App Store → iOS App → 1.0.
- [ ] Build → pick the TestFlight build that just passed the smoke test.
- [ ] App Review Information → fill from `SUBMISSION_METADATA.md` § App Review Information. **Critically include the sandbox tester credentials.**
- [ ] Version Release → "Manually release this version."
- [ ] Click **Submit for Review** at the top right.

Median Apple review time in 2026 is ~24 hours; expect 1–3 days.

## 10 — While you wait

- [ ] Set a reminder for 48 hours from submission to check Resolution Center.
- [ ] If rejected → read the specific guideline cited → match against the "Common rejection patterns" table in `SUBMISSION_METADATA.md` → reply via Resolution Center within 24h with citations.
- [ ] Once approved → manually release in ASC.

---

## What can go wrong (in order of probability)

### "No products available" on paywall in TestFlight
- Cause: IAP product IDs in ASC don't exactly match `Products.storekit`. Check capitalization and dots.
- Fix: edit ASC IAP → save → re-test (no rebuild needed).

### "Missing Compliance" warning after upload
- Cause: Forgot to answer the export-compliance question.
- Fix: ASC → TestFlight → Builds → click the build → answer "No" to the encryption question.

### Apple rejects on § 1.4.1 (medical claims)
- Defense: cite the DisclaimerBanner + "educational estimate, not a lifespan prediction" copy in the response. Reference paths from `SUBMISSION_METADATA.md` § Common rejection patterns.

### Apple rejects on § 5.6.3 (manipulative paywall)
- Defense: cite the Safety Net affordances + the firmDirect tone being opt-in (Coach default). Tell them to switch to Gentle in Profile to see the calm rendering.

### Build won't archive due to signing
- Cause: `DEVELOPMENT_TEAM` empty in `LifeClock.local.xcconfig`, or Xcode is not signed in to your Apple ID.
- Fix: paste Team ID; Xcode → Settings → Accounts → Add Apple ID → log in.

### TestFlight upload stuck at "Processing" > 1 hour
- Usually transient. If > 6 hours, contact Apple Developer Relations via developer.apple.com → Contact Us.

---

## After-ship (post-approval)

1. Manually release via ASC → App Store → iOS App → 1.0 → "Release This Version."
2. Confirm the app is live at https://apps.apple.com/us/app/life-clock-habits-earn-time/idXXXXXXXX (the ID appears in ASC after approval).
3. Monitor reviews + crashes. The app has no crash-reporting SDK in v1; you'll need to read Xcode Organizer → Crashes for any TestFlight + production crashes Apple shares.
4. Update `PHASE_STATUS.md` from "pre-TestFlight" to "shipped."
5. Plan v1.1 candidate list — advanced HealthKit metrics, introductory pricing for `pro.annual`, widgets.

---

## Sources of truth

- Submission metadata: `docs/products/life-clock/SUBMISSION_METADATA.md`
- Operational runbook (full detail): `docs/products/life-clock/submission-runbook.md`
- ASC walkthrough (one-time setup): `docs/products/life-clock/ASC_CHECKLIST.md`
- Age compliance: `docs/products/life-clock/AGE_COMPLIANCE.md`
- Auto-renewal disclosure: `docs/products/life-clock/legal/terms-of-use.md`
- Privacy posture: `docs/products/life-clock/PRIVACY_COMPLIANCE.md`, `legal/privacy-policy.md`
