# Submission Runbook — Life Clock

> **Status:** Operator runbook for the actual App Store submission flow. Sister to [`ASC_CHECKLIST.md`](ASC_CHECKLIST.md) (setup) and [`PHASE_STATUS.md`](PHASE_STATUS.md) (current sequencing). The checklist gets you to a configured App Store Connect record; this runbook walks you through the actual build → archive → review → ship cycle.

## Pre-flight (do these before opening Xcode for the submission build)

| Item | Where | Status check |
|---|---|---|
| All submission-blockers resolved | `founder-pack-audit-2026-05-12.md` § Submission blockers + later audits | All P1/P2 closed; legal/* 13+ landed |
| Legal placeholders filled | `legal/privacy-policy.md`, `legal/terms-of-use.md` | Replace `[LEGAL ENTITY]`, `[SUPPORT EMAIL]`, `[JURISDICTION]` |
| ASC questionnaire re-run on 4+/9+/13+/16+/18+ tiers | App Store Connect → App Information → Age Rating | Result: **13+** per `AGE_COMPLIANCE.md` § Item 1 |
| ASC IAP products match `Products.storekit` IDs | `com.lifeclock.pro.{monthly, annual, lifetime}` | Verify via `grep productID products/life-clock-ios/Sources/Services/Products.storekit` |
| Privacy policy URL is live | GitHub Pages or other static host | Apple's nutrition label points here |
| Sandbox tester credentials prepared | ASC → Users and Access → Sandbox | At least one Apple ID + 2FA disabled |
| All 5 submission-blocker remediations verified | (manage-subs row, paywall header, legal 12+→13+ ×3) | Visual + UITest |
| 6 sandbox-required Q1-Q5 lifecycle validations | `subscription-lifecycle-spec.md` § Outstanding | Each verified or logged |
| Latest audit pass = green | Run premium-feel-audit + pro-value-audit; submission-readiness green | Re-run if anything material changed |
| Build version + marketing version bumped | `project.yml` `MARKETING_VERSION` + `CURRENT_PROJECT_VERSION` | Both incremented since last submission |

## Build → archive

1. **Regenerate Xcode project**: `cd products/life-clock-ios && xcodegen generate`.
2. **Switch StoreKit config to Synced**: Xcode → Edit Scheme → Run → Options → StoreKit Configuration → **None** (uses real ASC products) for archive builds. Local `Products.storekit` is for dev only.
3. **Verify deployment target**: iOS 17. Reject if it drifted.
4. **Run the test suite**: `xcodebuild test -project LifeClock.xcodeproj -scheme LifeClock -destination 'platform=iOS Simulator,name=iPhone 17'`. Expect green.
5. **Pin a real-device destination**: Xcode → top bar → pick a connected iPhone (not simulator). Archive target must be a real device.
6. **Product → Archive**.
7. **Wait for the Organizer to open**. Verify the new archive is at the top.

## Distribute to TestFlight (first)

Always TestFlight before App Store.

1. Organizer → select archive → **Distribute App** → **App Store Connect** → **Upload**.
2. Choose default symbol upload, automatic signing.
3. **Compliance question**: "Does your app use encryption that goes beyond what's exempt under U.S. export rules?" → **No** (HTTPS-only, no custom crypto).
4. Upload. Wait for ASC to process (~10-30 min).
5. ASC → TestFlight → Builds → wait for the new build to leave "Processing."
6. Add Beta App Description, internal testers (no review required), or external testers (Apple beta review, 1-2 day turnaround).
7. **Test on real devices**:
   - Walk the 29-screen onboarding fresh-install
   - Verify under-13 hard block (use a sandbox account with DOB < 13)
   - Make a sandbox purchase on monthly + annual + lifetime
   - Run the 5 outstanding subscription-lifecycle validations (Q1-Q5 from `subscription-lifecycle-spec.md`)
   - Tap every Pro touchpoint as Free; verify paywall lands
   - Tap Manage subscription as Pro; verify iOS-native sheet opens
   - Trigger SafetyNet; verify all 3 affordances work
   - Turn on Reduce Motion + accessibility XXXL text; verify no surface breaks
8. **Iterate** if anything's off. Each TestFlight upload bumps build number.

## Distribute to App Store

When TestFlight is clean:

1. ASC → App Store → iOS App → version page.
2. Fill **What's New** copy (or leave blank for first release).
3. Verify all metadata:
   - App name: **"Life Clock: habits earn time"** (`APP_STORE_ASO.md` § Current implementation note)
   - Subtitle: **"See how habits move your life"** (`LifeClockConfiguration.appStoreSubtitle`)
   - Category: **Health & Fitness** (primary), **Lifestyle** (secondary)
   - Privacy Policy URL: live GitHub Pages URL
   - Age Rating: **13+** (from Phase 4 questionnaire)
   - Pricing: Free with IAPs
   - Screenshots: 6 minimum (verify the 6 per `APP_STORE_ASO.md` § First screenshots)
4. **Build**: pick the TestFlight build that just shipped.
5. **App Review Information**:
   - Sandbox tester credentials
   - Demo notes per `ASC_CHECKLIST.md` Phase 7 (the tone-mode hint, the under-13 block context, the medical-disclaimer policy)
   - Cite `AGE_COMPLIANCE.md` § 1 for the 12+ → 13+ rationale (proactively addresses Apple's likely question)
6. **Version Release**: "Manually release this version" (recommended for first release; flip to automatic after a stable cadence).
7. **Submit for Review**.

## Common rejection patterns (and our defenses)

| Pattern | Apple guideline | Defense |
|---|---|---|
| "Medical/Treatment claims" | § 1.4.1 | `LifeClockConfiguration.medicalDisclaimer` + `DisclaimerBanner` global + non-clinical copy throughout. Cite `PRIVACY_COMPLIANCE.md` § Medical disclaimer. |
| "HealthKit data sale / ads / data mining" | § 1.4.5, § 5.1.3 | `cloudKitDatabase: .none`, no analytics SDK, no backend, no `NSHealthUpdateUsageDescription` writes. Cite `ASC_CHECKLIST.md` row. |
| "Manipulative-fear paywall" | § 5.6.3 | Tone modes (Gentle hides clock); SafetyNet; opt-in firmDirect; paywall pitches value not fear. Cite `safetynet-spec.md` § App Review posture. |
| "Subscription disclosure missing" | § 3.1.2 | Auto-renew fineprint on every PaywallSheet render + `legal/terms-of-use.md` § Auto-Renewal Disclosure. |
| "Age-rating mismatch" | Standard guidelines | 13+ explicit; under-13 hard block; under-18 alcohol/tobacco suppression in onboarding + QuickLog. Cite `AGE_COMPLIANCE.md`. |
| "Value-claim mismatch" | Standard | Paywall bullets verbatim from `MONETIZATION.md` § Pro Annual; planned features stay out of header. See `paywall-spec.md`. |
| "Dark pattern: buried cancel" | § 3.1.2 + § 5.6 | Profile Subscription → Manage subscription row opens iOS-native sheet. Cite `pro-value-backlog-2026-05-12-standard.md` Prompt 1 (resolved). |
| "Crashes / common bugs" | § 2.1 | Test suite green; manual TestFlight walk; UITest coverage on cold-start + lifecycle. |

## If rejected

1. Read the full rejection email — Apple usually cites a specific guideline.
2. Match the guideline against the table above. If covered, the defense is already in code/docs; reply with citations.
3. If not covered, the rejection identifies a new gap — file a vision-question, address it, re-submit.
4. **Reply within 24h.** Apple's reviewer queue advances quickly; long delays compound.
5. Use the Resolution Center, not email — keeps the thread on-record.

## Post-ship

1. Monitor ASC reviews. Respond to substantive feedback within 48h.
2. Run premium-feel-audit + pro-value-audit weekly during the first month.
3. Track Q1-Q5 subscription-lifecycle outcomes in real-user data (post-instrumentation).
4. Update `PHASE_STATUS.md` to "shipped"; archive `GTM_LAUNCH_PLAN.md`'s 90-day plan as truly superseded.
5. Plan the v1.1 candidate list (advanced HealthKit / introductory trial / widgets) per `MONETIZATION.md`.

## Cross-references

- ASC setup: [`ASC_CHECKLIST.md`](ASC_CHECKLIST.md)
- Current blockers: [`PHASE_STATUS.md`](PHASE_STATUS.md)
- Age compliance: [`AGE_COMPLIANCE.md`](AGE_COMPLIANCE.md)
- Subscription lifecycle: [`subscription-lifecycle-spec.md`](subscription-lifecycle-spec.md)
- Paywall + value-claim: [`paywall-spec.md`](paywall-spec.md), [`MONETIZATION.md`](MONETIZATION.md)
- Privacy posture: [`PRIVACY_COMPLIANCE.md`](PRIVACY_COMPLIANCE.md), [`legal/privacy-policy.md`](legal/privacy-policy.md)
- SafetyNet + App Review § 5.6.3: [`safetynet-spec.md`](safetynet-spec.md)
- Audit reports: `founder-pack-audit-2026-05-12.md`, `premium-feel-backlog-2026-05-12-standard.md`, `pro-value-backlog-2026-05-12-standard.md`
