# Polish Session — life-clock — 2026-05-16 — onboarding-duration-tier-sweep

## Mode

`freeform-polish`. Payload: PF-P3 (premium-feel-backlog-2026-05-15-standard § 3 — "Off-tier
onboarding animation durations sweep"). Motion-incoherence cluster: three `.easeOut(duration:
0.32)` sites (`0.32` is on no tier — instant 0.18 / beat 0.30 / breath 0.60) plus two bare
literal `.snappy` sites. Vocabulary migration only — felt pacing must be indistinguishable.

Iteration cap: 4. final_check: yes (computer-use before/after onboarding walkthrough).

## Per-site tier decisions (the three `0.32` sites)

Per-gesture judgment, NOT a blind collapse — all three are reveal-of-single-element gestures
so they converge on `beat`, but site 3 was specifically evaluated against `instant` and
rejected on the felt-pacing guardrail.

- **HealthspanRevealView.swift:86** — lever-row stagger reveal, `opacity` + `scaleEffect`
  (0.92→1). Reveal of a single element within a sequence → `Motion.Duration.beat` (0.30).
  Spec's own beat use-for column ("reveal of a single element"). 0.32→0.30 imperceptible.
- **WhatWeDontDoView.swift:47** — bullet-row stagger reveal, `opacity` + `offset` (-12→0).
  Same gesture class as its sibling stagger → `Motion.Duration.beat` (0.30). 0.32→0.30
  imperceptible.
- **WhatWeDontDoView.swift:61** — footer opacity-only fade-in once all bullets shown.
  Considered `instant` (spec lists "opacity-only state changes" under instant) but rejected:
  0.32→0.18 is a perceptible ~44% speed-up, violating the "indistinguishable felt pacing"
  guardrail. It is also a content reveal, not a UI confirmation. → `Motion.Duration.beat`
  (0.30), matching its sibling bullets; 0.32→0.30 imperceptible.

None read as a "larger reveal" warranting `breath`.

## Iterations

- [10:20] (baseline) — headless build green before any edit — iPhone 17 Pro Max (942B6264)
- [10:24] f661166 — fix(life-clock): migrate three onboarding 0.32 easeOut sites to Motion.Duration.beat — Stretch — Onboarding (HealthspanReveal, WhatWeDontDo)
- [10:26] 97e7dae — chore(life-clock): named Motion.Curve.snappy for Engine/LeadIn onboarding sites — Polish — Onboarding (EngineRevealAndDial, LeadIn reactiveSlider)
- [10:28] 7d3c537 — docs(life-clock): extend motion-spec migration table with PF-P3 rows — Polish — (doc)

## Stretch decisions (operator review)

- `0.32`→`beat` migration: chose `beat` for all three sites by per-gesture judgment (all are
  reveal-of-single-element). The non-obvious call is WhatWeDontDoView:61 (footer) — `instant`
  was the literal opacity-only match but `beat` was chosen to keep felt pacing
  indistinguishable (0.32→0.18 would be visibly snappier; 0.32→0.30 is not). Rationale logged
  per-site above and in the motion-spec table.

## Asks

### Resolved this session

- None requiring operator input. No gesture failed to fit a tier.

### Outstanding (cycle-end batch)

- None blocking. One audit-reads/operator-owns proposal: the three `0.32` rows have been
  added to `docs/products/life-clock/motion-spec.md` § "Migration target" (struck-through as
  migrated 2026-05-16 PF-P3). The operator owns the spec; this session read the spec and
  proposed the table extension as part of the migration. No spec semantic was changed — only
  the tracking table was extended with already-completed rows.

## Regressions caught

- None. Pure vocabulary migration. `.snappy` → `Motion.Curve.snappy` is definitionally
  identical (`Motion.Curve.snappy = .snappy`). `0.32`→`Motion.Duration.beat` (0.30) is a
  ~6% duration change, below perception threshold for these stagger reveals. Every
  `reduceMotion ? nil :` short-circuit preserved verbatim at all five sites.

## A11y identifiers added

- None needed — all five driven elements already carry stable identifiers
  (`onboarding.healthspanReveal.years`, `onboarding.whatWeDontDo.bullet.N`,
  `onboarding.whatWeDontDo.footer`, `onboarding.dialYears`,
  `onboarding.reactiveSlider.years`).

## Out of scope (noted)

- `RevealEscalatorScreens.swift:428` also uses bare `.snappy` but is NOT in the PF-P3
  surface list — left untouched. Candidate for a future motion-vocabulary sweep.

## Vision updates

- None. No `vision.md` Decided/Open-Questions touched.

## Computer-use checkpoint

Drove the full onboarding flow live in Simulator (iPhone 17 Pro Max,
942B6264; `LIFECLOCK_UI_TEST=1 LIFECLOCK_UI_TEST_SCENARIO=onboarding
LIFECLOCK_USE_MOCK_HEALTH=1` for a clean in-memory onboarding). Exercised
every migrated site:

- **LeadInScreens:337** (`.snappy`→`Motion.Curve.snappy`) — dragged the
  reactiveSlider; "81→83 years" recount showed the snappy overshoot/settle
  unchanged.
- **EngineRevealAndDialView:95** (`.snappy`→`Motion.Curve.snappy`) —
  dragged the engine dial; "78.0→83.0 years" recount, snappy curve
  identical to pre-migration (constant is definitionally `.snappy`).
- **WhatWeDontDoView:47 & :61** (`0.32`→`beat`) — "What this isn't" screen:
  7-bullet stagger + footer fade-in reveal read natural and unhurried, no
  off-tier stutter.
- **HealthspanRevealView:86** (`0.32`→`beat`) — same stagger-reveal gesture
  class flowed cleanly through the answers-review + projected-healthspan
  screens.

**Verdict: felt pacing is indistinguishable.** The onboarding walkthrough
is smooth end-to-end; the vocabulary migration changed no perceptible
motion (0.32→0.30 is sub-perceptual; `.snappy`→`Motion.Curve.snappy` is
identical). PF-P3 success criterion met.

## Next pass

- Migrate `RevealEscalatorScreens.swift:428` `.snappy` → `Motion.Curve.snappy` (the last
  bare `.snappy` literal in Onboarding/, out of PF-P3 scope).
