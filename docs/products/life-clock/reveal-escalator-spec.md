# Reveal Escalator Spec — Life Clock

> **Status:** Canonical product policy. The reveal escalator is the single most distinctive piece of the Life Clock app — a multi-screen narrative onboarding that builds emotional commitment to the clock before the user sees their first time delta. This spec governs *what* the escalator does, *why* it's structured this way, and the non-negotiable safety rails (Q9 inferred-softer rule, under-13 hard block, mortality-lexicon guards).
>
> Originating plan: [`docs/plans/2026-05-01-feat-life-clock-reveal-onboarding-anchor-dial-plan.md`](../plans/2026-05-01-feat-life-clock-reveal-onboarding-anchor-dial-plan.md). Implementation: [`Sources/Features/Onboarding/OnboardingScreen.swift`](../../../products/life-clock-ios/Sources/Features/Onboarding/OnboardingScreen.swift) + `OnboardingCoordinator.swift` + `Sources/Features/Onboarding/Screens/`. This spec is the rule layer; that code is the implementation.

## One-line rule

**The user must commit emotionally to the clock before the clock commits numerically to the user.** The escalator builds context (lead-in) → collects calibration (baseline) → optionally gathers sensitive signal (consent block) → projects a personalized identity (archetype reveal) → previews the projection (life grid + penalty) → invites a one-time anchor (engine reveal + dial) → previews recovery → grants HK access → primes paywall. Skipping or reordering breaks the escalator.

## The 29 screens (canonical order — `OnboardingScreen` enum is the source of truth)

| Phase | Screen cases | Purpose |
|---|---|---|
| **Lead-in** (3.5) | `welcome`, `meetYourClock`, `reactiveSlider` | Sets the tone register. The reactive slider is the first hand-on-the-product moment — a tactile preview of how habits move the clock. |
| **Personalize intro** | `goalPick` | One-tap framing of why the user is here (longevity / weight / energy / focus). Drives downstream copy + quest affinity. |
| **Baseline** | `baselineDOB`, `under13Block`, `baselineSex`, `bodyComp`, `smoking`, `alcohol`, `strength`, `cardio`, `sleep`, `diet` | Hard data the engine needs. `baselineDOB` → `under13Block` if `age < 13` (terminal — see Under-13 Hard Block below). Smoking + alcohol gated behind `AgeGate.isAdult` (under-18 users skip those screens). |
| **Sensitive consent** | `sensitiveConsent`, `familyMother`, `familyFather`, `stress`, `social` | Gated behind explicit consent priming. PSS-10 stress + UCLA-3 loneliness arrive here. Skip path is real — no penalty in the engine for opting out. |
| **Tone + meta** | `tone`, `priorAttempts` | Tone-mode picker (gentle / coach / firmDirect). PSS+UCLA scores adjust the **inferred-softer rule** here (see Q9 below). |
| **Reveal escalator** | `analyzing`, `archetypeReveal`, `lifeGridRemaining`, `bigNumberPenalty`, `engineRevealAndDial`, `recoveryPreview` | The narrative core. Six beats in a fixed order. |
| **Pre-paywall** | `healthKitAuth` | The HK auth sheet. Skip-path preserves a Free-state app; the engine downgrades confidence gracefully. |
| **Paywall** | `paywallPrimary` | Single-tier paywall priming. Skip closes the sheet and lands the user on Today. |

Total: 29 cases. Adding a screen is a vision-question — the escalator's rhythm is load-bearing.

## Telemetry contract

The `OnboardingScreen.rawValue` is consumed by the funnel-analytics layer (`OnboardingTelemetry` protocol, `privacy: .private` on stored values). **Renaming a case is a breaking change for downstream funnel analytics.** Add new screens at the end of their phase block when possible; never reorder existing cases without analytics re-mapping.

## Non-negotiable safety rails

### Under-13 hard block (binding — see [`AGE_COMPLIANCE.md`](AGE_COMPLIANCE.md))

`baselineDOB` → `under13Block` when `AgeGate.ageInYears(birthDate:asOf:calendar:) < 13`. For users we know to be under 13:

- No HealthKit consent prompt fires (`healthKitAuth` is unreachable from the block).
- No `UserProfile` is materialized (no SwiftData write).
- No telemetry value bucket captures the underlying DOB — only an `under13Block screenAppeared` event with no payload.
- No subscription paywall is reached.
- `OnboardingDraft` is transient `@State` — the blocked DOB is discarded on app exit and never persists.

The user may back out via the persistent header chevron and re-enter a different DOB; the draft clears on re-entry. This is the implementation of the COPPA actual-knowledge posture documented in `PRIVACY_COMPLIANCE.md` § Users under 13.

### Q9 — Inferred-softer rule (binding — vision Decided 2026-05-12)

When the sensitive-consent block produces a high PSS-10 (perceived stress) or UCLA-3 (loneliness) score, the tone register softens automatically — even if the user picked `firmDirect` on the `tone` screen. The escalator's later beats (especially `bigNumberPenalty`) lean toward `coach` or `gentle` copy pools instead of the dramatic register. The user retains their explicit tone selection for daily use; the inference only applies during the escalator.

This rule is a vision-Decided constraint as of 2026-05-12 (Q9 ratchet, commits `f9e8db7` + `b66cd0e`). Implementation references `feedback_life_clock_lighting_convention.md`-adjacent reveal-escalator logic — verify against `Sources/Features/Onboarding/Screens/RevealEscalatorScreens.swift` for current call sites.

### Mortality lexicon ban (binding)

Notification copy and lock-screen copy must never use the mortality lexicon. The escalator's `bigNumberPenalty` screen is *the* place dramatic framing lives; nowhere else in the app's notification or wrap-up surfaces may quote it. See vision Decided constraints + `feedback_life_clock_notifications_constraints.md`.

### Skip paths are real

- `sensitiveConsent` → skip → flow proceeds to `tone` without PSS/UCLA scores. Engine downgrades confidence; no scores are imputed.
- `healthKitAuth` → skip → flow proceeds to paywall with Free-state HK; engine uses manual baseline only; History day-detail honestly says "Not configured" (never "Denied").
- `paywallPrimary` → skip → Today loads as Free.

Skipping the escalator's *narrative* beats (`analyzing` through `recoveryPreview`) is not user-facing — those screens auto-advance via timed `.task` blocks or single-tap CTAs. They are not skippable because removing them collapses the emotional commit-then-reveal arc.

## The healthspan dial (one-time, bounded)

`engineRevealAndDial` exposes a ±5y bounded dial that anchors the user's healthspan projection. The dial:

- Writes once (`UserProfile.personalAdjustmentYears` + `anchorAdjustedAt`).
- Is atomically gated by the `(personalAdjustmentYears, anchorAdjustedAt)` pair in `ClockEngine` — partial state is not a valid configuration.
- Is **not editable** from Profile post-escalator. Re-tuning requires resetting onboarding (Profile → Delete all data → reonboard).

This is intentional: a re-tunable dial would turn the projection number into a setting, which would gut the emotional weight of the reveal. The dial is a covenant moment, not a control panel.

## Motion + tone budget

The escalator runs many animations across many screens. Each animation must:

- Honor `reduceMotion` (every site short-circuits to a non-animated equivalent).
- Stay within the [`motion-spec.md`](motion-spec.md) duration vocabulary — `instant / beat / breath` for functional motion, narrative beats (`bigNumberPenalty` flash, `engineRevealAndDial` reveal, `lifeGridRemaining` dot-fill) may exceed the `breath` ceiling because they're content, not motion.
- Use `Motion.Curve.snappy` only for the dial's "you set the anchor" moment — overshoot is celebratory and the dial is the celebration. Other escalator beats use `breathing` or `smooth`.

## Anti-patterns (binding refusals)

- **Do not add a screen.** Vision-question required; the rhythm is load-bearing.
- **Do not skip the consent block silently.** Skipping is user-driven, not engine-driven.
- **Do not reorder phases.** The Baseline → Sensitive → Tone → Reveal order is intentional: the engine needs baseline before it can reveal; the tone selection must precede the reveal because the reveal copy is tone-aware; the sensitive block precedes tone because Q9 may override tone.
- **Do not block the back-button on under-13.** Persistent header chevron stays active so a real-13+-year-old who mis-entered DOB can correct without app-uninstall.
- **Do not render the healthspan dial after `anchorAdjustedAt` is set.** Post-escalator re-entry to the dial is a regression; the atomic gate exists to prevent re-write.
- **Do not surface the escalator's dramatic copy** (`bigNumberPenalty`, archetype reveal) outside the escalator. Today, History, Future, Profile, WrapUp all use the daily-use tone pools, which are softer.

## Cross-references

- Plan (originating design doc): [`docs/plans/2026-05-01-feat-life-clock-reveal-onboarding-anchor-dial-plan.md`](../plans/2026-05-01-feat-life-clock-reveal-onboarding-anchor-dial-plan.md)
- Source: [`OnboardingScreen.swift`](../../../products/life-clock-ios/Sources/Features/Onboarding/OnboardingScreen.swift), `OnboardingCoordinator.swift`, `Sources/Features/Onboarding/Screens/*.swift`
- Q9 ratchet: [`vision.md`](vision.md) § Decided constraints (2026-05-12)
- Age gate: [`AGE_COMPLIANCE.md`](AGE_COMPLIANCE.md), `Sources/Engines/AgeGate.swift`
- Motion: [`motion-spec.md`](motion-spec.md)
- Onboarding-funnel funnel-analytics: [`onboarding-funnel.md`](onboarding-funnel.md)
- Telemetry redaction contract: `Sources/Services/OnboardingTelemetry.swift`

## Validation

The reveal escalator is on-spec when ALL of the following hold:

1. The 29-screen `OnboardingScreen` enum order matches this spec exactly (any new screen is at the end of its phase block, with a vision-question logged).
2. `baselineDOB` routes to `under13Block` on `age < 13`; the block prevents downstream screens from being reachable.
3. PSS+UCLA scores feed the inferred-softer rule (Q9) when present; copy pools in `Screens/RevealEscalatorScreens.swift` consult the rule.
4. The healthspan dial writes exactly once per user (`anchorAdjustedAt` non-nil ⇒ dial is unreachable).
5. Skip paths on `sensitiveConsent`, `healthKitAuth`, and `paywallPrimary` all land the user on Today in a coherent Free state.
6. Every animation honors `reduceMotion`.
7. Mortality lexicon never escapes the escalator into notification, wrap-up, or daily-use copy pools.

When (1)–(7) hold, the escalator is the on-spec hand-off into the daily product loop.
