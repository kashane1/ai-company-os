---
title: Reveal-Onboarding Funnel — Telemetry Reference
status: active
date: 2026-05-01
---

# Reveal-Onboarding Funnel — Telemetry Reference

This doc is the analytics-consumer contract for the reveal-onboarding
flow shipped under `docs/plans/2026-05-01-feat-life-clock-reveal-onboarding-anchor-dial-plan.md`.
Every event listed here fires from the `OnboardingTelemetry` protocol
default impl (`OSLogTelemetry`) using `Logger` with `privacy: .private`
on every value parameter.

## Privacy contract

**Keys public, values private.** Sensitive scores (PSS-10, UCLA-3,
parental ages-at-death, dial adjustment years) are bucketed at the
call site BEFORE they hit `valueBucket`. Raw integer scores never enter
the public log channel. See `OnboardingTelemetryTests.testNoBucketLabelContainsRawDigits`
for the guard.

Bucketing helpers:

| Helper | Input range | Output buckets |
|---|---|---|
| `PerceivedStressBucket` | 0–40 (PSS-10) | `low`, `medium`, `high` |
| `LonelinessBucket` | 3–9 (UCLA-3) | `connected`, `lonely` |
| `ParentLongevityBucket` | age-at-death | `very_long`, `long`, `average`, `short`, `very_short` |
| `DialAdjustmentBucket` | -5.0 to +5.0 yrs | `neg5_neg3`, `neg3_neg1`, `neg1_zero`, `zero`, `zero_pos1`, `pos1_pos3`, `pos3_pos5` |

## Event reference

| Event | Args | Fires when |
|---|---|---|
| `screenAppeared(screen:)` | `screen: String` (public) | Each screen's `.onAppear` |
| `screenAdvanced(screen:durationMs:)` | `screen: String`, `durationMs: Int` (both public) | User taps the Continue CTA |
| `choiceMade(screen:key:valueBucket:)` | `screen`, `key` (public), `valueBucket` (**private** — bucketed) | User makes a selection on a question screen |
| `dialAdjusted(yearsBucket:)` | `yearsBucket` (**private** — bucketed) | User taps Confirm on `engineRevealAndDial` |
| `paywallShown(stage:)` | `stage: PaywallStage` (public) | Paywall surface appears |
| `paywallDismissed(stage:reason:)` | `stage`, `reason: PaywallDismissReason` (public) | Paywall dismissed (close / purchase / ineligible) |
| `purchased(productID:)` | `productID: String` (public — Apple identifier, not PII) | StoreKit entitlement flips to Pro |

## Funnel sequence

The canonical order screens appear (per `OnboardingScreen` enum). Skipped
screens fire NO `screenAppeared` for that screen. Drop-off rates are
computed as 1 − (next-screen-appears / this-screen-advances).

```
coldOpen
  → appPreviews
  → welcome
  → meetYourClock
  → reactiveSlider
  → visibilityFraming
  → personalizeIntro
  → goalPick                    [choiceMade: goal=<rawValue>]
  → baselineDOB
  → baselineSex                 [choiceMade: sex=<rawValue>]
  → bodyComp                    [optional toggle path]
  → smoking                     [choiceMade: status=<rawValue>]
  → alcohol                     [choiceMade: frequency=<rawValue>]
  → strength
  → cardio
  → sleep
  → diet                        [choiceMade: quality=<rawValue>]
  → sensitiveConsent            [choiceMade: consent=yes|skip]
    ├── consent=yes:
    │   → familyMother          [choiceMade: ageBucket=<bucket> if deceased]
    │   → familyFather          [choiceMade: ageBucket=<bucket> if deceased]
    │   → stress                [choiceMade: pss=<bucket>]
    │   → social                [choiceMade: ucla=<bucket>]
    └── consent=skip:
        → tone                  (skips family/stress/social block)
  → tone
  → priorAttempts
  → analyzing                   (auto-advances after ~4.5s)
  → archetypeReveal
  → concreteThisYear
  → lifeGridFull
  → lifeGridRemaining
    ├── adult AND goal != .justCurious:
    │   → bigNumberPenalty
    │   → engineRevealAndDial
    └── under-18 OR goal == .justCurious:
        → engineRevealAndDial   (skips bigNumberPenalty)
  → engineRevealAndDial         [dialAdjusted: <yearsBucket>]
  → recoveryPreview
  → healthKitAuth
  → paywallPrimary              [paywallShown: primary]
    ├── purchase:
    │   → MainTabView           [paywallDismissed: purchasedSuccessfully, purchased: <productID>]
    └── close:
        → MainTabView           [paywallDismissed: closed]
```

> **2026-05-07** — the post-paywall `entryView` placeholder was dropped.
> `paywallPrimary.onClose` writes the profile and `RootView`'s @Query
> on `UserProfile` swaps to `MainTabView` directly. Historical
> `entryView.appeared` events roll into `paywallPrimary` via
> `OnboardingScreen.deprecatedScreens`.

## Drop-off thresholds (gating)

For the TestFlight 100-user cohort:

- **Overall completion** (`coldOpen` → `paywallPrimary`): target ≥40%, **action threshold <30%** triggers a compression branch.
- **Per-screen drop-off**: any single screen >25% drop-off is a compression candidate.
- **Dial-confirm rate** (`engineRevealAndDial.appeared` → `dialAdjusted`): target ≥80%.
- **Paywall conversion** (`paywallShown` → `purchased`): target ≥3%.
- **Sensitive-skip rate** (`consent=skip` / `sensitiveConsent.appeared`): purely informational; informs whether the consent UX or the questions themselves are the friction.

## Reduce-Motion path

When `accessibilityReduceMotion` is on:
- `analyzing` collapses from three sequential progress bars (4.5s) to a single 1.5s gate.
- `engineRevealAndDial` snaps the dial to nearest 0.5 yr instead of continuous interpolation (when the slider is dragged).
- `recoveryPreview` cycling pauses.

These are NOT signaled via separate telemetry events; they're implementation details of the screens.

## Future events (not yet emitted)

- Per-screen `time_on_screen` distribution — useful for finding "stuck" moments where users hesitate; would replace the current single `durationMs` arg on `screenAdvanced`.
- A11y mode events (Reduce Motion, VoiceOver, Dynamic Type) — would let us segment funnel by accessibility setting.
- Cohort tag (founder offer eligibility) — when intro pricing lands, tag the user's eligibility cohort so paywall conversion is cleanly comparable.

Tracked as Phase 7 follow-ups; see the plan for prioritization.
