# Phase Status

- **Product:** Life Clock — App Store name **"Life Clock: habits earn time"**
- **Last updated:** 2026-05-01
- **Phase:** pre-TestFlight (reveal-onboarding rebuild landed)
- **Owner:** founder (Kashane)
- **Source tree:** `products/life-clock-ios/`
- **Docs root:** `docs/products/life-clock/`

## Current state

The founder pack has been translated into a working local-first iOS app. Life Clock is no longer just an MVP skeleton: it now has live Apple Health reads, SwiftData persistence, StoreKit 2 subscriptions, daily check-ins, local reminders, and a calmer post-audit UX direction.

## Implemented

- ✅ Tab bar: Onboarding (full reveal flow) → MainTabView with three tabs (Today, History, Profile). The 2026-05-01 IA refactor (PR `feat/life-clock-tab-consolidation`) collapsed the prior Progress and Plan tabs into Today — Today now hosts the headline Life Clock, "Why it changed" drivers + interpretation, "Today's Plan" actions, check-ins, and the diet streak banner. History (PR #18/#19) owns retrospective views.
- ✅ Live Apple Health reads for steps, exercise minutes, active energy, sleep, resting heart rate, and weight.
- ✅ SwiftData persistence via `LifeClockSchemaV1` (V1.1.0 after the reveal-onboarding rebuild added 12 optional fields), explicit versioning, no iCloud sync.
- ✅ Daily Check-In flow with manual diet, extras/alcohol, stress, strength, and nicotine signals.
- ✅ StoreKit 2 paywall with annual, monthly, and lifetime products plus restore flow.
- ✅ Safety Net screen with crisis resources and a hide-the-clock option.
- ✅ Daily reminder scheduling with same-day suppression when the user already checked in.
- ✅ Three tone modes: `gentle`, `coach`, and `firmDirect` (the firm/direct register reintroduced in Phase 3.B / commit 589ea81 to support the Brainrot-style onboarding voice carrying into daily use).
- ✅ Color palette personalization.
- ✅ Deterministic engine + store + HealthKit + StoreKit test coverage.
- ✅ **Reveal-onboarding rebuild** (2026-05-01): replaced 7-step onboarding
  with ~33-screen Brainrot-modeled flow. Live reactive estimate, pace-based
  archetype reveal, dot-grid escalator, one-time bounded ±5 yr healthspan
  dial folded into the reveal screen, single-tier paywall (Cal-AI-safe,
  intro pricing for new subscribers). Schema bumped to V1.1.0 with 12 new
  optional fields. `OnboardingTelemetry` protocol with `Logger` +
  `privacy: .private` on all values; sensitive PSS / UCLA / parent ages
  bucketed before logging. See
  `docs/plans/2026-05-01-feat-life-clock-reveal-onboarding-anchor-dial-plan.md`.

## Still blocking TestFlight

- ⏳ App Store Connect products still need to be created and matched to `Products.storekit`.
- ⏳ App Store Connect introductory pricing for `pro.annual` (founding-offer
  intro for new subscribers — no JWS signing required, configured per-product).
- ⏳ App Store Connect privacy questionnaire: declare new sensitive fields
  (parental mortality, PSS-10, UCLA-3) — Phase 1a follow-up. Stored on-device
  only via `cloudKitDatabase: .none`, but still must be disclosed.
- ⏳ `Info.plist` `NSHealthShareUsageDescription` audit against the new
  "let your clock learn from your body" copy on `HealthKitAuthView`.
- ⏳ `PrivacyInfo.xcprivacy` still needs the final accessed-API reason declarations.
- ⏳ App icon set is still incomplete for submission.
- ⏳ App Store listing copy, screenshots, and keywords still need founder sign-off.
- ⏳ The legal source docs still contain placeholders for publisher name, support email, and governing-law jurisdiction.
- ⏳ Founder mascot art (`ClockMascotPositive` / `ClockMascotNegative` in
  `Assets.xcassets`) — currently fallback SF Symbols.
- ⏳ Founder onboarding-preview art (`OnboardingPreview1`/`2`/`3`).
- ⏳ Remove the legacy `OnboardingView` after the new flow soaks 48h on
  TestFlight (currently still present in source but no longer reachable —
  `LifeClockApp.RootView` routes to `OnboardingCoordinator`).
- ⏳ Extract `PaywallProductsView` shared core so onboarding's
  `PaywallPrimaryView` and re-engagement's `PaywallSheet` stop drifting.

## Open product gaps

- Trend vs prior week is still missing in Weekly.
- The app has no animation layer yet for the clock, wrap-ups, or quest-completion delight.
- Export data remains a placeholder.
- Analytics and crash-reporting are still intentionally absent pre-TestFlight.
- HealthKit background delivery, widgets, Apple Watch, and deeper coaching are still deferred.

## Resolved decisions

- ✅ Brand direction: ship under **"Life Clock: habits earn time"** for now.
- ✅ Safety posture: the app ships with a calmer tone direction plus a Safety Net path.
- ✅ Local-first stance: no backend, no account, no HealthKit-derived sync.
- ✅ Tone modes: the original `mementoMori` was removed in the 2026-04-30 UX pass. A firm/direct register was reintroduced as `firmDirect` in Phase 3.B (2026-05-01) to carry the Brainrot-style onboarding voice into daily use. Three tones now ship: `gentle`, `coach`, `firmDirect`.
- ✅ Age gate: under-18 users do not see smoking or alcohol prompts.

## Recommended next steps

1. Finish the App Store and legal submission blockers.
2. Add a Yesterday / Weekly Wrap-Up concept before TestFlight if it becomes the next retention-facing feature.
3. Decide whether the first animation investment should go into a wrap-up clock motion, quest-completion feedback, or a lighter Today-screen transition system.
4. Add trend-vs-prior-week once there is enough persisted real usage to make it meaningful.
