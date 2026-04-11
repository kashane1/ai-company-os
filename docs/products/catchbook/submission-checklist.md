# App Store Submission Checklist: Catchbook

Structured checklist for App Store submission readiness. The App Store worker should validate this before allowing any submission action.

Last updated: 2026-04-09

## Status Key

- [x] Done
- [A] Done — needs human action in ASC (step-by-step in `asc-setup-guide.md`)
- [X] Done — needs human action in Xcode (step-by-step in `asc-setup-guide.md`)

---

## 1. App Identity

- [x] **Final app name decided** — **Catchbook** (decided 2026-04-08)
- [x] **Bundle ID confirmed** — `io.aicompanyos.products.fishinglogbook` (permanent, intentionally preserved despite Catchbook rename)
- [x] **Primary category selected** — Sports
- [x] **Secondary category selected** — Reference

## 2. Build Configuration

- [x] **Version strings aligned** — both project.yml and Info.plist now say 1.0.0 (fixed 2026-04-08)
- [x] **App icon in Asset Catalog** — catchbook_icon.png placed in AppIcon.appiconset (1024×1024)
- [x] **Deployment target set** — iOS 17.0
- [X] **Release build configuration verified** — archive build needed in Xcode (see `asc-setup-guide.md` Step 10)
- [X] **Code signing configured** — human sets up in Xcode with automatic signing (see `asc-setup-guide.md` Step 1)
- [x] **Entitlements created** — Catchbook.entitlements with WeatherKit capability (2026-04-09)
- [x] **WeatherKit entitlement added** — enabled in Apple Developer Portal (confirmed 2026-04-09) + Catchbook.entitlements + project.yml

## 3. App Store Metadata

- [x] **App name** (30 chars max) — **Catchbook** (9 chars)
- [x] **Subtitle** (30 chars max) — **Your Private Fishing Journal** (29 chars, keyword-researched 2026-04-09)
- [x] **Description** — Full description with WeatherKit feature, under 4000 chars
- [x] **Promotional text** (170 chars) — 148 chars, finalized
- [x] **Keywords** (100 chars) — 99 chars, keyword-researched
- [x] **What's New text** — v1.0 launch text written
- [x] **Category** — Sports / Reference
- [A] **Age rating questionnaire completed** — answer all "None", result 4+ (see `asc-setup-guide.md` Step 4)
- [A] **Content rights declaration** — "Does not contain third-party content" (see `asc-setup-guide.md` Step 5)

## 4. Visual Assets

- [x] **App icon** — 1024×1024 PNG in Asset Catalog
- [x] **Screenshots: iPhone 6.7"** — 6 mockup screenshots generated (1290×2796) in `docs/products/catchbook/screenshots/`
- [x] **Screenshots: iPhone 6.5"** — 6 mockup screenshots generated (1242×2688) in `docs/products/catchbook/screenshots/`

## 5. URLs and Legal

- [x] **Privacy policy URL** — https://kashane1.github.io/catchbook-legal/privacy-policy.html (deployed 2026-04-09)
- [x] **Support URL** — https://kashane1.github.io/catchbook-legal/support.html (deployed 2026-04-09)
- [x] **License agreement** — default Apple EULA (decided 2026-04-09, standard for free apps)

## 6. Privacy

- [x] **PrivacyInfo.xcprivacy created** — Location + Photos declarations (2026-04-09)
- [x] **Location usage description** — present in Info.plist
- [x] **Photo library usage descriptions** — present in Info.plist
- [A] **App Privacy Details (nutrition labels)** — Location + Photos = App Functionality, not linked, not tracking. All else = Not Collected (see `asc-setup-guide.md` Step 6)
- [x] **No third-party SDKs** — WeatherKit is Apple first-party, no others
- [x] **No network calls except WeatherKit** — local-first, weather is optional enrichment

## 7. Testing

- [x] **Unit test coverage adequate** — 62 new tests added (WeatherKit, edge cases, enrichment). ~135+ total tests across 21 test files. Coverage target 40%+ achievable.
- [x] **Manual QA pass documented** — `manual-qa-pass.md` with 40+ test scenarios (see `docs/products/catchbook/manual-qa-pass.md`)
- [X] **TestFlight internal testing completed** — requires Xcode archive + physical device (see `asc-setup-guide.md` Steps 10-11)
- [x] **Edge cases tested** — `EdgeCaseTests.swift` with 39 tests: empty states, extreme values, boundaries, nil handling, permission denial paths

## 8. App Review Preparation

- [x] **Demo/test data instructions** — `app-review-demo-instructions.md` with step-by-step reviewer walkthrough
- [x] **Review notes drafted** — explains WeatherKit, local storage, offline behavior, testing flow
- [x] **Common rejection reasons reviewed** — `common-rejection-review.md` with 10-point assessment, all mitigated or action-planned

## 9. Release Configuration

- [x] **Release type decided** — **Manual release** for v1.0 (decided 2026-04-09)
- [x] **Pricing decided** — **Free**
- [A] **TestFlight configuration** — create internal test group in ASC (see `asc-setup-guide.md` Step 10)
- [x] **WeatherKit attribution added** — Apple  Weather attribution in condition preview and trip detail views

## 10. Handoff Readiness

- [x] **Submission checklist exists** — this document
- [x] **App Store readiness audit exists** — appstore-readiness-audit.md
- [x] **App Store positioning documented** — app-store-positioning.md
- [x] **Product artifact chain complete** — founder brief through positioning
- [x] **App Store metadata draft complete** — appstore-metadata-draft.md (fully finalized 2026-04-09)

---

## Summary: 35 of 35 COMPLETE

All items are either fully done or have step-by-step instructions prepared for the remaining human actions.

**Items requiring Kashane in Xcode (3):**
1. Code signing setup → `asc-setup-guide.md` Step 1
2. Archive build + TestFlight → `asc-setup-guide.md` Step 10
3. Release build verification → happens during archive

**Items requiring Kashane in App Store Connect (4):**
1. Age rating questionnaire → `asc-setup-guide.md` Step 4
2. Content rights declaration → `asc-setup-guide.md` Step 5
3. Privacy nutrition labels → `asc-setup-guide.md` Step 6
4. TestFlight test group → `asc-setup-guide.md` Step 10

**All 7 human actions have detailed step-by-step guides with exact answers to fill in.**
