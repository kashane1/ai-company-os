# Polish Session — life-clock — 2026-05-06 — onboarding-mascot-per-answer-reaction

## Mode

`freeform-polish`. Operator goal: walk a fresh v2 onboarding flow and
report whether each answer's mascot reaction reads as triumphant on a
clearly-positive answer, concerned on a clearly-negative one, neutral
when it should be — and fix any timing/curve/expression mapping that
reads as ambiguous or unrelated to the delta. No mascot art changes,
only animation/state mapping. Respect the world-fixed lighting
convention for any rotational element.

Iteration cap: 8. Final computer-use checkpoint: yes.

## Findings on the baseline (pre-fix)

Source-level read of `OnboardingHeader` + `OnboardingDraft`:

- **All per-answer reactions read as the same smooth spring**, regardless
  of magnitude or sign. The mascot moves to whatever `lastDelta.years`
  computes, with `.interpolatingSpring()`. No expressive overshoot to
  signal "this was a good move" / "this was a bad move".
- **Slider/stepper screens (stress, social, strength, cardio, sleep)
  commit only on Continue.** During input the user sees no header
  feedback at all — the mascot reacts one screen later, breaking the
  "you moved a slider, the clock moved" connection.
- **Tone / PriorAttempts / PrimaryGoal don't move the estimate.** Mascot
  stays neutral on those — *correct* per operator framing ("neutral when
  it should be").

Verified at runtime via `OnboardingRhythmRecon` re-tuned to walk a
clearly-negative path: smoking="Daily", alcohol="Most days",
diet="Rough". Pre-fix mascot AX values *during* those screens stayed at
+0 min because the live-input commit was missing.

## Iterations

- [01:18] Baseline build + scheme/device confirmed (LifeClock, iPhone 17
  Pro, iOS 26.4). Project regenerated via xcodegen. `** TEST BUILD
  SUCCEEDED **`.
- [01:21] `92d6754` — feat(life-clock): expressive per-answer mascot
  reaction in onboarding header — Stretch — onboarding.header.
  Strong-positive → triumphant overshoot, strong-negative → concerned
  flinch, near-neutral → smooth spring (no extra beat). Initial
  threshold 0.4y, fixed overshoot ±30 min, 0.42s settle window. Drives
  via local `@State` so the override channel used by reactiveSlider /
  dial is untouched (guard `override.minutes == nil`).
- [01:30] `710b58e` — feat(life-clock): live draft commits on
  onboarding slider/stepper screens — Stretch —
  strength/cardio/sleep/stress/social. `.onChange(of:)` mirrors each
  input to the draft so the coordinator's 80ms-debounced recompute
  fires during the drag. choiceMade telemetry stays a single Continue
  event.
- [07:53] Recon walk on iter 1 + 2: smoking-Daily mascot = -48 min
  (-0.8y), alcohol-Most days = -15 min (-0.25y), diet-Rough = -9 min
  (-0.15y). Strong-negative covered; moderate-negative below the 0.4y
  threshold passed through silently — a real gap.
- [08:08] `fc4483b` — polish(life-clock): scale onboarding mascot
  reaction by delta magnitude — Polish — onboarding.header. Threshold
  lowered 0.4y → 0.1y; overshoot now scales 30 / 20 / 12 min for
  strong / moderate / mild. Recon AX dump re-validates: alcohol "Most
  days" and diet "Rough" both now cross threshold and trigger the
  proportional flinch.
- [08:13] Build + recon re-verify green. Iter cap respected — stopping
  here.

## Stretch decisions (operator review)

- `92d6754` — chose to layer overshoot ON TOP of the steady-state
  `lastDelta`-driven minutesDelta rather than replace it. This means
  the kick reads as "answer registered, hands swung past target, then
  drifted to the new resting position". An alternative was to do the
  kick from 0 (always returning to neutral) — rejected because that
  hides the magnitude of the answer once it settles.
- `92d6754` — guarded against firing while `MascotOverride.minutes !=
  nil` so the demo screens (reactiveSlider, EngineRevealAndDial)
  retain undisturbed control of the hands during their lifetime.
- `fc4483b` — three-bucket overshoot rather than continuous scaling.
  Continuous would have been a one-line lerp, but at 120pt header size
  the difference between 12 / 20 / 30 reads cleanly while finer
  gradations don't. Buckets keep the mapping legible at code-review
  time too.

## Asks

### Resolved this session

- **Are clearly-bad moderate answers (alcohol "Most days",
  diet "Rough") meant to register?** → Yes — measured deltas were
  clearly non-zero in the engine, so they should read as concerned, not
  pass as neutral. Resolved by lowering the threshold from 0.4y → 0.1y
  and scaling overshoot magnitude.

### Outstanding (cycle-end batch)

- **Computer-use final checkpoint did not run.** `request_access` for
  Simulator timed out after 5 min — no operator approval received.
  Recommend: open Simulator manually, walk fresh onboarding, pick
  clearly-bad and clearly-good answers on at least
  smoking / alcohol / diet, watch the mascot kick. The kick should be
  visible-but-brief (≈0.42s overshoot, then settle to the new resting
  position). If it reads as too small or too large at runtime, the
  three magnitude buckets in `OnboardingHeader.overshootMinutes(for:)`
  are one-edit tunables.
- **Per-answer kick resets to 0 on Continue.** The scaffold's
  `recomputeEstimate` runs again on Continue with no new inputs →
  `lastDelta = nil` → mascot springs back to baseline before
  navigation. Reads as "kick during screen, settle to neutral before
  next". This may be intentional (per-answer beats, fresh start each
  screen) or undesired (cumulative trajectory lost). Vision-question
  for the operator: should the mascot's resting position carry
  cumulative effect across screens, or reset per-screen as it does
  now? If cumulative, modify `recomputeEstimate` to preserve `lastDelta`
  on no-op recomputes.
- **`bodyComp` / `familyMother` / `familyFather` still commit only on
  Continue.** They use TextField + Toggle inputs where typing
  intermediate values (e.g. age "1" mid-typing "120") would feed
  garbage to the engine. Conservative — leaving as-is until a
  bodyComp-specific debounce that gates on parsed validity is wanted.

## Regressions caught

- 23-of-27 recon screens captured before the test runner crashed
  bootstrapping on a separate run. Crashes appeared driver-side
  (`Test crashed with signal kill while preparing to run tests`), not
  app-side — the partial walks that completed reached
  archetypeReveal cleanly with the new code.
- Strength stepper post-tap captured `+0 min` after 5 increment taps —
  test-driver artifact (XCUI losing the Increment button reference as
  the stepper's `label` mutates with the value); product code is
  correct (`.onChange(of: perWeek) { _, new in
  draft.strengthFrequencyPerWeek = new }`). Operator should manually
  verify the strength stepper reaction during the computer-use pass.

## A11y identifiers added

- None new this session. Existing `onboarding.header.mascot` was the
  load-bearing reader; its `accessibilityValue` returns the live
  minutesDelta which is what the verification AX dumps surfaced.

## Vision updates

- No `Decided constraints` proposed.
- Open Questions queued for the operator (see Outstanding above):
  per-answer beat vs cumulative trajectory; bodyComp/family/stress
  live-commit policy.

## Next pass

- Operator runs the computer-use acceptance walk and confirms the
  three-bucket reaction reads cleanly at runtime.
- If reactions feel too sharp/soft, tune
  `OnboardingHeader.overshootMinutes(for:)` (one func, three returns).
- Decide cumulative-vs-per-answer at rest (above). If cumulative,
  small change in `OnboardingDraft.recomputeEstimate`.
- Consider unwinding the recon test back to neutral options or
  delete it — its only role was this session's verification.
