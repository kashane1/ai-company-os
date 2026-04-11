# App Store Connect Setup Guide: Catchbook v1.0

Step-by-step instructions for completing all remaining items in App Store Connect and Xcode. Follow these in order.

Last updated: 2026-04-09

---

## Step 1: Xcode Code Signing (HARD BLOCKER)

1. Open Xcode → Catchbook.xcodeproj
2. Select the Catchbook target → Signing & Capabilities tab
3. Check "Automatically manage signing"
4. Select your Apple Developer team
5. Verify Bundle Identifier: `io.aicompanyos.products.fishinglogbook`
6. Xcode should auto-create the App ID and provisioning profile
7. **Important:** Go to Signing & Capabilities → tap "+ Capability" → add "WeatherKit"
   - This ensures the provisioning profile includes WeatherKit
8. If Xcode shows a signing error, go to https://developer.apple.com → Certificates, Identifiers & Profiles → verify the App ID has WeatherKit enabled (you already did this)

## Step 2: Add WeatherKit Attribution (Required by Apple)

Before building, add WeatherKit attribution to the app. In `ConditionPreviewRow` or wherever weather data displays, add a small text line:

```swift
Text(" Weather")
    .font(.caption2)
    .foregroundStyle(.tertiary)
```

Apple's WeatherKit license requires visible attribution near weather data.

## Step 3: Regenerate Xcode Project

In Terminal, from `products/catchbook-ios/`:
```bash
xcodegen generate
```
This syncs the .xcodeproj with project.yml changes (WeatherKit entitlements, new test files, etc.)

## Step 4: Age Rating Questionnaire (in ASC)

1. Go to App Store Connect → My Apps → Catchbook → App Information
2. Scroll to "Age Rating"
3. Answer all questions:
   - Cartoon or Fantasy Violence: None
   - Realistic Violence: None
   - Sexual Content or Nudity: None
   - Profanity or Crude Humor: None
   - Alcohol, Tobacco, or Drug Use: None
   - Simulated Gambling: None
   - Horror/Fear Themes: None
   - Mature/Suggestive Themes: None
   - Medical/Treatment Information: None
   - Unrestricted Web Access: **No** (WeatherKit is not "web access")
4. Result should be: **4+**

## Step 5: Content Rights Declaration (in ASC)

1. In App Store Connect → Catchbook → App Information
2. Under "Content Rights": select **"This app does not contain, show, or access third-party content"**
3. Save

## Step 6: App Privacy Details / Nutrition Labels (in ASC)

1. Go to App Store Connect → Catchbook → App Privacy
2. Click "Get Started" or "Edit"
3. **Data Types:**

   **Location:**
   - Do you collect location data? **Yes**
   - Data type: **Precise Location**
   - Is this data linked to the user's identity? **No**
   - Is this data used for tracking? **No**
   - Purpose: **App Functionality**

   **Photos:**
   - Do you collect photos or videos? **Yes**
   - Data type: **Photos**
   - Is this data linked to the user's identity? **No**
   - Is this data used for tracking? **No**
   - Purpose: **App Functionality**

   **All other categories:** Select **"No, we do not collect data from this category"**
   - Health & Fitness: No
   - Financial Info: No
   - Contact Info: No
   - Contacts: No
   - User Content: No
   - Browsing History: No
   - Search History: No
   - Identifiers: No
   - Purchases: No
   - Usage Data: No
   - Diagnostics: No
   - Sensitive Info: No
   - Other Data: No

4. Save and submit

## Step 7: Pricing (in ASC)

1. Go to App Store Connect → Catchbook → Pricing and Availability
2. Set Price: **Free**
3. Availability: All territories (or select specific ones)
4. Save

## Step 8: Upload Screenshots (in ASC)

1. Go to App Store Connect → Catchbook → Version Information
2. Upload screenshots for:
   - **iPhone 6.7" Display** (1290 × 2796) — upload all 6 screenshots in order
   - **iPhone 6.5" Display** (1242 × 2688) — upload all 6 screenshots in order
3. Screenshots are in `docs/products/catchbook/screenshots/`

## Step 9: Fill In Version Metadata (in ASC)

Copy from `appstore-metadata-draft.md`:

- **Promotional Text:** "Your private fishing journal, offline and on-device. No accounts. No cloud. No tracking. Just honest catch data and weather conditions — all yours."
- **Description:** Copy the full description from the metadata draft
- **Keywords:** `fishing logbook,catch log,fishing journal,bass fishing,trout fishing,saltwater,offline,fish tracker`
- **Support URL:** https://kashane1.github.io/catchbook-legal/support.html
- **Privacy Policy URL:** https://kashane1.github.io/catchbook-legal/privacy-policy.html
- **What's New:** Copy from metadata draft
- **Review Notes:** Copy from `app-review-demo-instructions.md`

## Step 10: TestFlight Setup

1. In App Store Connect → Catchbook → TestFlight
2. Create an internal testing group (e.g., "Catchbook Team")
3. Add yourself as a tester
4. In Xcode: Product → Archive → Distribute App → App Store Connect
5. Wait for TestFlight processing (~15-30 minutes)
6. Install on your iPhone from the TestFlight app
7. Run through the QA scenarios in `manual-qa-pass.md`
8. Fix any issues found, re-archive, re-test

## Step 11: Release Type

1. In App Store Connect → Catchbook → Version Information
2. Under "Version Release": select **"Manually release this version"**
3. This lets you review everything after Apple approves before going live

## Step 12: Submit for Review

1. Verify all fields are filled (ASC shows a green checkmark for each section)
2. Click "Add for Review"
3. Click "Submit to App Review"
4. Expected review time: 24-48 hours for new apps

---

## Post-Submission Checklist

- [ ] Monitor App Store Connect for review status
- [ ] If rejected: read the rejection feedback, fix the specific issue, resubmit (turnaround: 24-48 hours)
- [ ] If approved: manually release when ready
- [ ] After release: verify the listing looks correct on the App Store
- [ ] Start v1.1 planning (RevenueCat, onboarding, review prompt)
