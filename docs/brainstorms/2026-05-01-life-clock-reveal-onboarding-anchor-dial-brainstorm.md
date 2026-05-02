---
date: 2026-05-01
topic: life-clock-reveal-onboarding-anchor-dial
---

# Life Clock: Reveal-Driven Onboarding + Healthspan Anchor Dial

## What We're Building

A complete rebuild of the Life Clock onboarding flow modeled on Brainrot's
proven $200K/mo onboarding pattern, ending in a personalized healthspan reveal
that the user can fine-tune with a one-time **anchor dial** before the paywall
fires.

Today's onboarding collects DOB and lifestyle inputs but the final "Reveal"
step is static copy — the personalized estimate that `ClockEngine.swift:19-33`
already computes is never surfaced. The paywall sits in Profile and History and
never fires at the moment of peak emotional buy-in. We're moving the paywall
to the end of an expanded, value-building onboarding that delivers a live,
reactive Life Clock estimate, lets the user calibrate it once via a bounded
dial, and only then converts.

## Why This Approach

We considered three onboarding tactic levels (full Brainrot, Brainrot-lite,
elegant reveal). We're going **full Brainrot** because Life Clock is uniquely
positioned to use Brainrot's pattern: the mortality dot-grid metaphor that
powers Brainrot's most emotional screens ("This is your life", "This is what
you have left", "X years rotting") is *already* Life Clock's core brand
metaphor. We're not borrowing — we're using our own product as a first-class
onboarding element.

For the one-time anchor adjustment, we considered: persistent banner on Home,
modal on first day-of-use, settings-only time-boxed editor, and inline at end
of onboarding. We chose **inline at end of onboarding, folded into the reveal
screen** — it forces a confident decision at the emotional peak and keeps the
paywall selling a number the user has personally calibrated.

For dial semantics, we considered DOB editor vs healthspan dial. We chose
**bounded ±5-year healthspan dial** — the user nudges the engine's projected
healthy-time output (e.g., 53.2 yrs) up or down within a tight, scientifically
defensible range. Birth date stays fixed; the dial expresses gut-feel
calibration the engine can't capture (genetic outliers, recent diagnoses,
"I exercise more than I checked").

## Key Decisions

- **Onboarding becomes ~25 screens** (today: 7), structured as nine phases:
  cold open → app previews → welcome + reactive slider → threat reframe →
  personalize intro → expanded data collection → 3-bar fake-progress
  "analyzing" → 5-step emotional escalator → engine reveal **with dial** →
  recovery preview → research credibility → rating ask → permission →
  commitment ritual → two-stage paywall → free fallback.

- **Reveal style is live and reactive.** Once the user finishes baseline
  questions (DOB, sex), a running number appears (e.g. "Currently: 53.2 yrs
  left") and animates with each subsequent answer, accompanied by a one-line
  "why" ("+1.4 yrs from regular strength training"). Engagement pattern, not
  a back-loaded drumroll.

- **Five new lifestyle factors collected**, on top of existing
  smoking/alcohol/strength/sleep/diet:
  - **Body composition** (height/weight → BMI, one screen)
  - **Cardio activity** (mins/week, one screen, separate from existing strength)
  - **Family longevity** (parents alive / age at death, two short screens —
    sensitive copy required)
  - **Stress + social connection** (perceived stress + loneliness scale, two
    short screens)
  - All five extend `ClockEngine.lifestyleAdjustmentYears` at
    [ClockEngine.swift:44-74](products/life-clock-ios/Sources/Engines/ClockEngine.swift)
    with bounded, sourced coefficients.

- **The anchor dial sits on the engine reveal screen.** Engine output is
  visible. User drags ±5 years. Confirmation locks the value. **One time
  only** — this screen never reappears post-onboarding. Persistence: a
  `personalAdjustmentYears: Double?` field on `UserProfile` plus a
  `anchorAdjustedAt: Date?` timestamp; once set, the dial UI is gone forever.
  Reinstall behavior matches the rest of `UserProfile` (i.e., not preserved
  across full reinstall + delete-all-data).

- **Sequence at end-of-onboarding:** Engine reveal + dial → user confirms →
  recovery preview ("Adjust your habits and gain N more years of …") →
  research credibility → rating ask → permission → commitment ritual ("wind
  your clock 5x") → "loading premium options…" → paywall. The dial fires
  before the paywall so the paywall sells the user's locked-in number.

- **Tactics dial: full Brainrot.** Adopt all of:
  - Threat-state reframe ("It's not about willpower. It's about visibility.")
  - 3-bar fake-progress analyzing screen
  - Persona/archetype reveal with sub-meters ("Your longevity profile is:
    The Marathoner")
  - Five-step emotional escalator (concrete-this-year → full life grid →
    remaining grid → big number → recovery animation)
  - Commitment ritual (tap-N-times physical action)
  - In-flow 5-star rating ask + testimonials
  - Two-stage paywall: yearly anchor / weekly tier first, then **80%-off
    one-time-offer overlay** with strikethrough pricing
  - Inverted dismissal: "I'd rather pay full price" instead of "No thanks"
  - "Cancel anytime · Money back guarantee" badges

- **Free vs Pro split: unchanged from current `MONETIZATION.md`.**
  Free = today/yesterday wrap-up + today's clock + 7 days history. Pro = full
  history, weekly drivers, all wrap-ups. The locked-in personalized clock +
  dial value are *visible to free users* — they're earned during onboarding
  and would feel like a bait-and-switch if locked.

- **App preview screens at the start.** Before any onboarding question, show
  2–3 phone-in-phone previews of the actual Life Clock dashboard, history-grid,
  and a representative wrap-up. Builds confidence that the product is real.
  Lifts the get-started CTA past skepticism.

## Resolved Questions

- **Visual metaphor: BOTH dot grid + new mascot.** The Life Clock face/grid
  reacts (dots fade/brighten) AND a new mascot is introduced — the **clock
  from the iOS app icon**, with two states: a positive/happy clock and a
  negative/sad clock. Two static art assets only; the mascot swaps between
  them as the user's running estimate moves up or down during onboarding.
  Reinforces the existing brand identity rather than introducing a foreign
  character.

- **HealthKit timing: after reveal+dial, before paywall.** Frame as "let
  your clock learn from your body" — moves grant request to a moment of high
  commitment, lifting permission grant rate. Replaces the existing
  mid-onboarding position at
  [OnboardingView.swift:184-211](products/life-clock-ios/Sources/Features/Onboarding/OnboardingView.swift).

- **Family-longevity sensitivity: 'Prefer not to say' as a first-class
  choice.** Each parent screen offers it as one of the primary options.
  Engine treats missing data as zero adjustment (population baseline only).
  No penalty, no shame.

- **Goal selection: 4–5 focused goals.** Surface set: Live longer / Have
  more energy / Be there for family / Beat family history / Just curious.
  The selected goal personalizes downstream copy (most importantly the
  recovery animation; see below).

- **Archetype taxonomy: pace-based.** Four archetypes on the persona-reveal
  screen: **The Marathoner** (steady, well-paced), **The Sprinter** (high
  acute risk, recoverable), **The Sleeper** (huge upside if engaged), **The
  Outlier** (genetics carrying weight). Sub-meter axes to refine in plan
  phase but likely behavioral risk × recovery capacity.

- **Commitment ritual: "Wind your clock 5x."** User performs a winding
  swipe gesture 5 times around the clock-mascot. Reinforces the clock
  metaphor and ownership-of-time framing. Replaces Brainrot's
  handcuffed-phone tap-5x.

- **Recovery animation: goal-driven cycling.** Words match the goal the
  user picked. Goal=family → cycles "with your kids / showing up / at the
  dinner table." Goal=energy → cycles "feeling alive / on the trail / awake
  at dawn." Goal=beat family history → cycles "outliving the odds /
  rewriting your story / proving them wrong." Word lists per goal to be
  finalized in plan phase.

## Related Side-Notes (out of scope — tracked separately)

- **Tone-mode rename + reintroduction of "Firm / Direct".** The onboarding
  voice in this brainstorm is firm and direct (Brainrot-style). The user
  wants the in-app tone-mode selector to mirror that flavor so users can
  carry the onboarding voice into daily use. Concretely:
  - Reintroduce a third tone case ("Firm / Direct") that was removed in
    Phase 3.A on 2026-04-30 (see
    [ToneMode.swift:5-13](products/life-clock-ios/Sources/App/ToneMode.swift)
    for the historical note). All keyed copy properties need to be re-defined
    for this case (todayHeadline, deltaPositivePrefix, wrapUpPositiveBody,
    etc. — full set in `ToneMode.swift`).
  - Rename `.gentle` displayName "Gentle" → "Calm / Gentle".
  - Rename `.coach` displayName "Coach" → "Default / Average".
  - Storage migration: `UserProfile.toneMode` is a String. New value
    "firm_direct" (or similar) needs to be a valid raw value; existing
    "memento_mori" fallback in `fromStored(_:)` should remain (legacy data)
    but new storage paths use the new key.
  - Tracked as a separate task; not blocking this brainstorm.

## Watch-List (for after launch, not blocking)

- **Onboarding length tolerance.** ~25 screens is heavy. Full Brainrot is
  confirmed as the goal, but we should instrument per-screen completion
  from day one and validate via TestFlight before App Store launch. Have
  a contingency plan to compress if drop-off is severe.

## Next Steps

→ Run `/workflows:plan` to convert these decisions into an implementation
plan (file changes, engine extensions, new SwiftUI screens, persistence
schema migration for `personalAdjustmentYears` and `anchorAdjustedAt`,
analytics events, paywall product-ID changes if any).
