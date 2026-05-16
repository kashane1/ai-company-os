# Polish Session — life-clock — 2026-05-16 — motion-duration-migration

## Mode

`fix-list` — PF-P2 (Reveal-escalator + Future-chart `Motion.Duration` migration).
Payload: migrate the two clearest spec-table sites from numeric duration
literals to named `Motion.Duration` constants. Mechanical vocabulary
migration, NOT re-tuning. Iteration cap 3. No computer-use checkpoint.

## Iterations

- [12:30] `<sha-1>` — fix(life-clock): migrate RevealEscalator + Future chart durations to Motion.Duration — Polish — RevealEscalatorScreens / TrajectoryChart
- [12:30] `<sha-2>` — chore(life-clock): strike migrated rows in motion-spec table — Polish — docs

The fix is two-site and trivially atomic; combined into one source commit
per the prompt's "one combined commit per operator preference" allowance,
with the doc table update as a separate `chore` commit (different concern:
spec bookkeeping vs source).

### Sites

- `RevealEscalatorScreens.swift:449` — `.easeInOut(duration: 0.35)` →
  `.easeInOut(duration: Motion.Duration.beat)` (0.30). 50ms tightening to
  the nearest brand tier — the PF-P2-sanctioned migration. Site is a
  `.contentTransition(.opacity)` cross-fade on the cycling recovery-preview
  phrase label. `reduceMotion ? nil :` guard preserved verbatim.
- `TrajectoryChart.swift:140` — `.smooth(duration: 0.18)` →
  `.smooth(duration: Motion.Duration.instant)`. `Motion.Duration.instant`
  == 0.18 exactly → provably zero perceived-speed change to the chart
  redraw. `(isScrubbing || reduceMotion) ? nil :` guard preserved verbatim.

## Stretch decisions (operator review)

None — pure constant substitution, Polish tier only.

## Asks

### Resolved this session

None.

### Outstanding (cycle-end batch)

- **motion-spec table line-number / curve drift (FYI, not blocking).** The
  pre-existing migration table listed the chart row as
  `TrajectoryChart.swift:139 (.animation(...)) | — | Motion.Curve.smooth
  with Motion.Duration.beat`. The actual un-migrated literal is at `:140`
  (`.smooth(duration: 0.18)`), and PF-P2's binding payload maps it to
  `Motion.Duration.instant` (to preserve the existing 0.18 perceived
  redraw speed), NOT `beat`. I struck the row reflecting what was actually
  done and annotated the rationale inline. Flagging so the operator knows
  the spec table's pre-existing chart row was stale on both line number
  and target tier; no action needed unless the operator wants the chart
  redraw re-tuned to `beat` (would be a perceptible re-tune, out of PF-P2
  scope — would need a separate freeform/vision prompt).

## Regressions caught

- Today screen rendered intact post-edit (RevealEscalator edit lives in an
  onboarding screen not on the default launch path; no regression). Future
  chart change is numerically identity (0.18 → instant == 0.18) so no
  redraw delta is possible by construction.

## A11y identifiers added

None — both driven/inspected elements already had stable identifiers
(`onboarding.recoveryPreview.cyclingPhrase`, `future.trajectory.chart`).

## Vision updates

None.

## Next pass

- PF-P3 (off-tier `0.32` onboarding sweep) is the heaviest remaining
  un-migrated motion cluster — separate prompt, do NOT bundle.
- The motion-spec migration table has further un-struck rows that may or
  may not be landed in source; a future pass could reconcile the whole
  table against source ground-truth in one bookkeeping commit.
