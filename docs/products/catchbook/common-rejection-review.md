# Common Rejection Reasons Review: Catchbook v1.0

Reviewed against Apple's most common rejection reasons for new apps (2025-2026 data). Each item below is assessed for Catchbook's specific stack and marked as mitigated or requiring action.

Last updated: 2026-04-09

---

## 1. Privacy Manifest (PrivacyInfo.xcprivacy) — 12% of Q1 2025 rejections

**Status: MITIGATED**

- PrivacyInfo.xcprivacy created with Location + Photos declarations
- NSPrivacyTracking set to false
- No tracking domains declared (correct — we don't track)
- No third-party SDKs requiring separate manifests
- WeatherKit is first-party Apple — no separate declaration needed

**Action needed:** Verify PrivacyInfo.xcprivacy is in Build Phases → Copy Bundle Resources after `xcodegen generate`. XcodeGen should handle this via the `buildPhase: resources` entry in project.yml, but verify.

## 2. Performance / Crashes (10% of rejections)

**Status: MITIGATED**

- App is local-first, no network dependency for core flow
- WeatherKit failure returns nil gracefully — never crashes
- SwiftData persistence uses PersistenceWriteCoordinator with rollback
- 60+ unit tests covering edge cases and error paths

**Action needed:** Test on physical device via TestFlight. Simulator doesn't catch signing, memory, or permission issues that real devices surface.

## 3. Incomplete Information (14% of rejections)

**Status: MITIGATED**

- All metadata fields finalized (name, subtitle, description, keywords, promotional text, What's New)
- Privacy policy URL live and accessible
- Support URL live and accessible
- Review notes written with clear testing instructions
- No accounts = no test account needed

**Action needed:** None.

## 4. Metadata Accuracy (Guideline 2.3)

**Status: MITIGATED**

- Description accurately reflects v1.0 feature set
- WeatherKit mentioned — feature exists in code
- No claims about features that don't ship in v1.0
- Screenshots are mockups — **replace with real simulator captures before submission if possible**
- No competitor names in description or keywords

**Action needed:** Consider replacing mockup screenshots with real Xcode simulator captures for submission. Apple may reject screenshots that show non-existent UI.

## 5. Privacy Policy URL (Guideline 5.1.1)

**Status: MITIGATED**

- Privacy policy at https://kashane1.github.io/catchbook-legal/privacy-policy.html
- Addresses GDPR and CCPA: "All data stored locally on your device"
- URL returns 200 (verified deployment)

**Action needed:** Consider adding an in-app link to the privacy policy (Settings or About screen). Not strictly required for v1.0 but strengthens the submission.

## 6. WeatherKit Attribution (Guideline 5.2.5)

**Status: NEEDS ATTENTION**

- Apple requires visible attribution for WeatherKit data
- The official requirement: display "Weather" Apple logo or text attribution near weather data
- Missing attribution can trigger rejection

**Action needed:** Add WeatherKit attribution text near weather display in the app. Apple provides specific attribution requirements in their WeatherKit documentation. A simple " Weather" line in the condition display is sufficient.

## 7. App Privacy Details (Nutrition Labels)

**Status: NEEDS HUMAN ACTION**

- Must be filled out in App Store Connect before submission
- Location: "Used for App Functionality", not linked to identity, not for tracking
- Photos: "Used for App Functionality", not linked to identity, not for tracking
- All other categories: "Not Collected"

**Action needed:** Fill in ASC (see asc-setup-guide.md for step-by-step).

## 8. WeatherKit Entitlement Configuration

**Status: PARTIALLY MITIGATED**

- Catchbook.entitlements file created with `com.apple.developer.weatherkit`
- project.yml references entitlements file
- WeatherKit enabled in Apple Developer Portal (confirmed by Kashane 2026-04-09)

**Action needed:** After code signing setup, verify the provisioning profile includes WeatherKit entitlement. Re-download provisioning profile if it was created before WeatherKit was enabled.

## 9. Screenshots Device Sizes

**Status: MITIGATED**

- 6.7" screenshots generated (1290 × 2796)
- 6.5" screenshots generated (1242 × 2688)

**Action needed:** Upload both sets to App Store Connect.

## 10. Age Rating

**Status: NEEDS HUMAN ACTION**

- No objectionable content, no user-generated content, no web access (except WeatherKit)
- Should qualify for 4+ rating

**Action needed:** Complete age rating questionnaire in ASC (see asc-setup-guide.md).

---

## Summary

| Category | Status |
|----------|--------|
| Privacy manifest | Mitigated (verify build phase) |
| Performance | Mitigated (needs TestFlight device test) |
| Incomplete info | Mitigated |
| Metadata accuracy | Mitigated (screenshot caveat) |
| Privacy policy | Mitigated |
| WeatherKit attribution | **Needs code change** |
| Privacy nutrition labels | **Needs ASC action** |
| Entitlement config | Partially mitigated |
| Screenshot sizes | Mitigated |
| Age rating | **Needs ASC action** |

**Highest risk:** WeatherKit attribution missing from UI. Add before submission.
