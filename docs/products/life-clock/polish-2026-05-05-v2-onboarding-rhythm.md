# Polish Session — life-clock — 2026-05-05 — v2-onboarding-rhythm

## Mode

`freeform-polish`. Operator goal: walk the full v2 onboarding from
cold-open through the first Life Clock reveal as a fresh user
(`LIFECLOCK_UI_TEST_SCENARIO=onboarding`). Every screen should feel
snappy, every body line should earn its place, every Continue should
land in the same spot vertically. Persistent mascot should read as
reactive, not decorative. Coach tone preserved.

Iteration cap: 8. Final computer-use checkpoint: yes.

## Iterations

- [02:00] Baseline build (`** BUILD SUCCEEDED **`).
- [02:30] Recon driver written (`UITests/OnboardingRhythmRecon.swift`)
  to walk cold-open → engine reveal capturing per-screen PNG +
  AX-tree under `/tmp/lifeclock-polish/`.
- [02:35] First runs failed: scaffold's outer
  `accessibilityIdentifier("onboarding.\(screenID)")` collapsed every
  screen into a single button, shadowing
  `onboarding.continue` / `onboarding.tone.coach` / etc. Existing
  `LifeClockUITests` was silently broken too.
- [02:40] `85a134c` — fix(life-clock): preserve scaffold child a11y
  identifiers — Polish — scaffold. Added
  `.accessibilityElement(children: .contain)` so children keep their
  ids. Recon test went green end-to-end with this fix.
- [02:43] Captures landed for all 22 screens. Goldens copied to
  `products/life-clock-ios/.polish/goldens/`.
- [02:46] `b4f6b75` — polish(life-clock): tighten coldOpen
  auto-advance to 1.2s — Polish — coldOpen. Was 2.0s, felt like a
  stall before the flow had begun.
- [02:48] `d4dc947` — polish(life-clock): tighten analyzing duration
  4.5s -> 2.4s — Polish — analyzing. Three sequential 1.5s "computing"
  gates were filler; 0.8s/stage keeps the reveal beat. Reduce-Motion
  path (single 1.5s gate) untouched.
- [02:50] `ac7467e` — polish(life-clock): drop redundant Welcome
  title, lead with value prop — Stretch — welcome. Persistent wordmark
  already shows "LIFE CLOCK"; promoted the body line ("Earn time with
  better habits.") to the title.
- [02:52] `ed1ae86` — feat(life-clock): mascot wake on MeetYourClock
  pays off the promise — Stretch — meetYourClock. The screen's body
  says "the hands move with you" past a static clock. On appear, drive
  the persistent-header mascot positive (+90 min) for 0.7s, then
  negative (-45 min) for 0.6s, then settle back to 0 — user sees
  reactivity the instant they read about it.
- [02:54] `6baf330` — polish(life-clock): cut personalizeIntro from
  onboarding flow — Stretch — coordinator. ReactiveSlider just demo'd
  the calibration metaphor literally; the next screen "Let's calibrate
  your clock. A few questions." restated it. Coordinator now goes
  reactiveSlider → goalPick directly. One fewer tap before reveal.
- [02:55] Build re-verified green. Recon re-run end-to-end green.
- [03:00] Computer-use checkpoint: tapped through cold-open → engine
  reveal. Cold-open felt fast; analyzing felt like a beat instead of a
  stall; goalPick lands directly after the slider; meetYourClock's
  mascot shows movement during the read. Reveal lands clean at "79.0
  years (June 11, 2069)".
- [03:05] Late finding from end-to-end: SensitiveConsent's primary
  Continue sat ~65pt higher than every other Continue because the
  optional "Skip these" secondary action was laid out *before* the
  primary CTA. Operator's vertical-landing concern crystalized here.
- [03:08] `1c2a85f` — polish(life-clock): pin scaffold primary CTA,
  move secondary below — Polish — scaffold. Reordered so the primary
  stays at the standard bottom-pinned y on every screen and the
  soft-skip sits below it.
- [03:10] Build green; CTA lands at consistent y across the flow.
- [03:20] `13938e6` — feat(life-clock): mascot pulse on archetype
  reveal — Stretch — archetypeReveal. Brief reactivity beat scaled by
  recovery capacity (±120 min ceiling).
- [03:23] `c0043e2` — feat(life-clock): mascot pulse on engine reveal
  first glance — Stretch — engineRevealAndDial. Pulse +110 → -55 →
  hand-off to dial-driven mascotDelta. `hasPulsed` gate keeps the
  pulse from fighting dial input once the user starts dragging.
- [03:25] `3194d51` — chore(life-clock): drop dead v1 onboarding
  screens — Polish — coordinator/screens. Deleted appPreviews /
  visibilityFraming / personalizeIntro views + enum cases + stale
  UITest waits. Telemetry roll-up via deprecatedScreens preserves
  historical funnel joinability.
- [03:30] Unit suite + recon walk green after cleanup.

## Stretch decisions (operator review)

- `ac7467e` — collapsed Welcome's two-line copy (title + body) into a
  single title. The body line carried the value prop and the title was
  a wordmark echo; folding them keeps the screen earning its place.
  Could go further (lead with verb only) — flag for later if it reads
  as too soft.
- `ed1ae86` — wake-nudge values (+90 min / -45 min, total 1.3s
  envelope) follow the existing wake-anim cadence (per memory: 1.0s
  envelope on Today). Kept the swing modest so it reads as a "breath"
  not a flinch.
- `6baf330` — cut personalizeIntro entirely rather than re-copying it.
  The enum case stays; the coordinator just doesn't route to it. If we
  decide later we want a between-demo-and-data beat, re-route a slim
  version.

## Asks

### Resolved this session

- **EngineRevealAndDial mascot static at reveal** → operator approved
  pulse → `c0043e2` (forward 0.55s, settle 0.45s, then dial-driven).
- **ArchetypeReveal mascot static** → operator approved pulse →
  `13938e6` (recovery-capacity-shaped magnitude).
- **Dead v1 screens** → operator approved cleanup → `3194d51`. Removed
  appPreviews / visibilityFraming / personalizeIntro views, enum
  cases, and coordinator branches. Telemetry roll-up via
  `deprecatedScreens` keeps historical funnel rows joinable.

### Outstanding (cycle-end batch)

- None — full operator brief executed.

## Regressions caught

- 22 screens diffed against pre-session goldens: title/copy changes
  intentional on `02-welcome` and `03-meetYourClock` (mid-animation
  capture); timestamp pixel diffs on the rest. No layout regressions
  on touched-or-untouched screens. Personalize-intro golden removed.

## A11y identifiers added

- None new. Iter 1 unblocked the existing identifiers (Continue,
  per-option buttons) that were being shadowed.

## Vision updates

- No `Decided constraints` proposed.
- Open Questions appended (above): mascot reactivity at archetype +
  engine-reveal moments; dead-code cleanup for v1 onboarding screens.

## Next pass

- Operator nod on EngineReveal + ArchetypeReveal mascot pulses; ship
  same pattern as `runWakeNudge`.
- Separate `polish-cleanup` session to delete `appPreviews` /
  `visibilityFraming` views + enum cases (touches telemetry
  deprecated-screens map and any test fixtures).
- The `OnboardingRhythmRecon.swift` driver lives in `UITests/` for
  this session — usable for future polish runs. Decide whether to keep
  as a permanent recon harness or delete with the next polish merge.
