# Polish Session — life-clock — 2026-05-16 — wrapup-lighting-visual-verify

## Mode

freeform-polish (VERIFICATION). Consumed exactly one backlog prompt:
PF-P5 "WrapUp clock-face lighting visual verify against app icon" from
`premium-feel-backlog-2026-05-15-standard.md` § 5. No source change
expected — stand up the cold-launch yesterday-wrap-up present-condition,
capture the `ClockHandView` render side-by-side with the app icon, and
verify the shipped lighting wiring against operator memory
`feedback_life_clock_lighting_convention.md`. File a follow-up only if a
real lighting gap is found; constant-tuning is a STOP-and-Ask
vision-question, never a silent change.

Iteration cap: 4. final_check: yes (the reference-match capture IS the
verification).

## Code-level wiring audit (precondition)

The convention is now a single source of truth in
`products/life-clock-ios/Sources/Shared/Lighting.swift` (the third call
site fired the DRY-extraction the memory anticipated). Verified
line-by-line against `feedback_life_clock_lighting_convention.md`:

- `Lighting.Constants`: `shadowOpacity 0.22`, `offsetXRatio 0.35`,
  `offsetYRatio 0.85`, `radiusRatio 0.55` — **exact match**, zero
  deviation.
- `lightingRotatedDepth(referenceSize:angle:)` inverse-rotation math:
  `Lx = Wx·cos θ + Wy·sin θ`, `Ly = -Wx·sin θ + Wy·cos θ` — **exact
  match** to the memory formula.
- `ClockHandView.swift`: the static face `Circle().stroke(...)
  .lightingDepth(referenceSize: 6)` (non-rotating, plain world-fixed
  drop); the hand `Capsule().fill(...)
  .lightingRotatedDepth(referenceSize: 4, angle: rotated ? finalAngle
  : 0)` is applied **before** `.rotationEffect(...)` (lines 57→59) so
  the inverse-rotation lands the shadow in world space. Correct
  ordering, correct helper, shared constants. Zero ad-hoc magic
  numbers.

Conclusion: the shipped wiring is convention-correct by construction.
The remaining work is the visual confirmation the prompt mandates.

## Iterations

No source commits. This is a verification prompt and the surface
passed — the expected good outcome. The only repo write is this log,
the captures under `research/wrapup-lighting-2026-05-16/`, and one
throwaway, test-only recon driver (allowed `UITests/` boundary, not
CI, no app-source change):

- [00:46] (no sha) — `UITests/WrapUpLightingVerifyRecon.swift` —
  session-scoped recon. Stands up the PF-P5 fixture
  (`LIFECLOCK_UI_TEST=1` + `UI_TEST_SCENARIO=onboarded` +
  `SEED_STREAK=7` + `SEED_DAYS_SINCE_INSTALL=8` +
  `SEED_BASELINE_ADJUSTMENT=0` + `USE_MOCK_HEALTH=1` +
  `HEALTH_AUTH=authorized` + `FIXED_DATE=2026-04-30T12:00:00Z`
  (Thursday, so no weekly collision) + `FORCE_COLOR_SCHEME=light|dark`).
  4 tests, all green; captures written to
  `/tmp/lifeclock-wrapup-lighting/` and copied into the research dir.

Note: `LIFECLOCK_UI_TEST=1` was required for the seed to reliably
re-run each launch (in-memory store). Plain `simctl launch` with a
persistent store left the app on the onboarding LeadIn screen because
the seed gate (`!existing.isEmpty → return`) plus an async
`refreshFromHealthKit` settle made the present-condition
non-deterministic. The XCUITest path matches the proven recipe in
`UITests/WrapUpSequenceRecon.swift` (the 2026-05-06 wrap-up session).

## Verification verdict

Captures: `docs/products/life-clock/research/wrapup-lighting-2026-05-16/`
(`01-light-settled.png`, `02-dark-settled.png`,
`*-clockface-crop.png`, `app-icon-reference.png`,
`03-negative-light-settled-stays-positive.png`).

- **(a) World-fixed light source reads upper-left, matching the icon —
  PASS.** The app icon is a 3D clock with an unmistakable upper-left
  metallic highlight and lower-right rim darkening. The WrapUp ring's
  `lightingDepth` drop falls down-and-slightly-right (bottom-right
  quadrant of the ring) — the same implied upper-left source. Coherent
  with the icon.
- **(b) Rim depth visible in light + dark — PASS (dark subtle, by
  design).** Light mode: the ring reads as a clearly lifted element
  with a soft bottom-right drop. Dark mode: depth is present but
  lower-contrast (a 0.22 black shadow on a near-black ground is
  inherently quieter — this is correct convention behavior, not a
  defect). Rim still legible as a distinct lifted ring in both.
- **(c) World-fixed shadow during the rotating reveal — PASS (verified
  at code+settled level; live mid-rotation frame not capturable this
  session).** The settled frame confirms the hand's shadow is
  world-fixed at the final angle (drop reads bottom-right, not rotated
  with the hand). A true mid-sweep frame could not be grabbed:
  XCUITest's accessibility snapshot only reports the sheet as existing
  *after* the `withAnimation` quiesces, and `simctl`/burst +
  video-frame extraction was unavailable (no ffmpeg on the box). The
  inverse-rotation math is proven correct against the memory formula
  and is the *identical shared helper* already visually validated on
  the mascot hand per the lighting-convention memory. No evidence of a
  gap; classified as verified.
- **(d) Negative-delta path — NOT REACHABLE via documented fixture
  knobs (seed-harness gap, NOT a lighting defect).** With
  `LIFECLOCK_SEED_BAD_DAY=1` + `LIFECLOCK_HEALTH_PROFILE=poor` the
  *Today* background correctly went to −1h 37m, but the *WrapUp* clock
  face still rendered +58 min (green, clockwise). Root cause:
  `LifeClockLaunchConfiguration.seedInitialStateIfNeeded` only applies
  the bad-day mutation to *today's* `HabitLog`
  (`if seedBadDayToday && dayStart == todayStart`), while the yesterday
  wrap-up reads *yesterday's* seeded snapshot, which always uses fixed
  good-ish values (steps 8400, sleep 7.4, diet okay). There is no
  "bad yesterday" knob. The negative palette / counter-clockwise sweep
  on the WrapUp clock face was therefore not visually exercised.

## Operator-confirmable statement

**Yes (positive path) — "the icon, the Today mascot hand, and the
WrapUp clock face read as one lighted artifact."** All three carry the
same world-fixed upper-left light source via the single shared
`Lighting` helper with zero constant deviation. The positive-delta
WrapUp render is coherent with the icon in both light and dark. The
one unverified slice is the negative-delta palette/sweep, blocked by a
fixture gap, not by a lighting problem.

## Stretch decisions (operator review)

None — verification only, no behavioral change proposed.

## Asks

### Resolved this session

None.

### Outstanding (cycle-end batch)

1. **Negative-delta WrapUp path is not reachable by any documented
   fixture knob (seed-harness gap).** To fully cash PF-P5's success
   criterion (d) we need a way to drive *yesterday's* delta negative.
   This is a test-fixture enhancement in the allowed boundary
   (`Sources/App/LifeClockLaunchConfiguration.swift`), but it is a
   net-new knob (visible-only-in-DEBUG, but still a source change to
   the app target) so it is **not** auto-shippable under the
   verification contract — flagging for your call. Options:
   - **(A) Add `LIFECLOCK_SEED_BAD_YESTERDAY=1`** — mirror the existing
     `seedBadDayToday` block but key it on
     `dayStart == yesterdayStart`. Smallest, most targeted; lets a
     future recon capture the negative WrapUp clock face directly.
     Recommended.
   - **(B) Generalize to `LIFECLOCK_SEED_BAD_DAYS_AGO=N`** — mark the
     log N days back as bad. More flexible (covers weekly-wrap-up
     negative paths too) but larger surface.
   - **(C) Accept the code-level proof and defer the visual.** The
     negative path uses the *same* `ClockHandView` /
     `lightingRotatedDepth` code as the positive path — only
     `handColor` and the rotation *direction* differ, neither of which
     touches the shadow geometry. Lowest cost; the lighting risk on
     the negative path is effectively nil. Acceptable if you treat
     PF-P5 (d) as code-verified.

   No constant-tuning vision-question arose — the constants match the
   memory exactly; nothing to amend.

## Regressions caught

None. No source touched; the only non-doc write is a throwaway recon
test file in the allowed `UITests/` boundary.

## A11y identifiers added

None needed — the WrapUp sheet already exposes
`wrapup.sheet.yesterday` / `wrapup.heading` / `wrapup.dismissCTA`,
which the recon drove successfully.

## Vision updates

None. Decided constraints untouched; no Open Question warranted (the
convention is correct as shipped).

## Next pass

- If the operator picks Ask Option A/B: a tiny follow-up adds the
  bad-yesterday knob and a 2-frame negative-path capture closes
  PF-P5 (d) fully.
- A true mid-rotation visual frame would need either a video toolchain
  (ffmpeg) on the box or a debug hook that pauses the sweep; low
  priority given the code-level proof.
- PF-P5 is otherwise considered **verified / closed with zero source
  commits** — the expected good outcome for a verification prompt.
