# Polish Session — life-clock — 2026-05-12 — today-free-vs-pro-and-a11y

## Mode

`freeform-polish`. Trajectory peek input from the recon trajectory pasted at session start (Free-vs-Pro + a11y walk). Iteration cap: 6. Final-check: yes (mandatory for VoiceOver behavior, per trajectory).

Seed: `LIFECLOCK_UI_TEST_SCENARIO=onboarded`, `LIFECLOCK_SEED_DAYS_SINCE_INSTALL=14`, `LIFECLOCK_SEED_STREAK=14`, `LIFECLOCK_SEED_BASELINE_ADJUSTMENT=0` (new this session — see Iter 1), `LIFECLOCK_USE_MOCK_HEALTH=1`, `LIFECLOCK_HEALTH_AUTH=authorized`. Per-tone variants via uninstall + reinstall + `LIFECLOCK_SEED_TONE=<tone>` (tone seeds only on first launch).

Trajectory tier per pasted recon: **new-surface (capture-side)** — tone work shipped in PR #42's T1. This session's findings are the capture-side complement: a seed-harness gap (Iter 1) and a VoiceOver-phrasing gap (Iter 5).

## Iterations

| Time | Commit | Type | Tier | Surface | Result |
|---|---|---|---|---|---|
| 10:50 | `65920a6` | feat | Polish (harness) | LifeClockLaunchConfiguration | seed-harness knob `LIFECLOCK_SEED_BASELINE_ADJUSTMENT` so simulator-driven polish can land on a v1.7.0 baselined Pro user without driving the anchor-dial UI |
| 10:55 | _no commit_ | observation | — | TodayView.trajectoryPeek | Pro × gentle × light golden — peek reads "Your projection ahead: 88y →" (matches ToneMode.swift:783) |
| 10:59 | _no commit_ | observation | — | TodayView.trajectoryPeek | Pro × coach × light — "Trajectory: 88y →" (matches ToneMode.swift:784) |
| 11:01 | _no commit_ | observation | — | TodayView.trajectoryPeek | Pro × firm_direct × light — "Tally: 88y →" (matches ToneMode.swift:785) |
| 11:03 | _no commit_ | observation | — | TodayView.trajectoryPeek | Free × gentle × light — peek **hidden cleanly**; tab bar shows 3 tabs (Today / History / Profile), no Future tab, no upgrade prompt grafted onto the projection card. Source proof at TodayView.swift:384 (`futureTabUnlocked` gate). |
| 11:07 | _no commit_ | observation | — | LifeClockStore.setTodayHabits | QuickLog edit Fuel: Okay → Rough — state persisted (verified by re-opening sheet). Visible delta + peek unchanged because the projection drift is smaller than the rounding window (1 month at this baseline). Cache-invalidation **chain** source-proven: setTodayHabits (L1635) → invalidateCumulativeCache (L1667) → refreshCurrentHealthspanProjection (L1669, synchronous on @MainActor @Observable store) → SwiftUI re-render on Observation tracking. |
| 11:19 | `44282fb` | fix | Polish | TodayView + ToneMode + TimeDeltaFormatter | VoiceOver phrasing — peek now reads "<tone-noun>. <X years Y months>. Button. Opens the Future tab." instead of "<tone-string with bare-letter units and arrow glyph>." |

## Stretch decisions (operator review)

- **A11y label tone-keys, value does not.** The tone vocabulary belongs to the visible string and to the a11y label noun ("Your projection ahead" / "Trajectory" / "Tally"). The a11y *value* — the number — is tone-neutral ("87 years 2 months"), because the value is data, not voice. This keeps the VO experience consistent across tones while still preserving the tone identity in what's spoken first.
- **No-month case stays singular-line.** Whole-year projections render as "87 years" (not "87 years 0 months") — matches the visible peek's `m == 0 ? "\(y)y"` behavior and avoids VO reading a meaningless zero count.
- **QuickLog → peek empirical was inconclusive within iteration budget; chose source proof over driving a bigger habit-change combo.** The cache-invalidation chain is deterministic on `@Observable` + `@MainActor` — re-render IS within one frame after the synchronous mutation. Empirical sub-rounding-window drift didn't move the displayed value but doesn't disprove the chain. Calling it out so operator can decide if a stronger fixture (e.g. `LIFECLOCK_SEED_BAD_DAY=1` combined with QuickLog edit to a great day) is worth adding to the recon backlog.

## Asks

### Resolved this session

- **"Does the seed harness need extension before the walk?"** — Yes; first cycle's deliverable was `LIFECLOCK_SEED_BASELINE_ADJUSTMENT` (commit `65920a6`). Without it the `onboarded` scenario simulates a pre-anchor user, so peek + Future projections were unreachable from any combination of pre-existing knobs.

### Outstanding (cycle-end batch)

- **Empirical VoiceOver speech inspection (operator).** Unit tests pin the formatter output and tone label semantics; visual no-regression golden saved (`today_pro_gentle_light_post_a11y.png` is byte-identical to `today_pro_gentle_light.png` on the peek region — the change is invisible by design). Empirical VO speech in Simulator (Cmd+5 → focus on the peek) would close the loop on the trajectory's "captured + iterated until natural" criterion. Not blocking — the formatter test (`testProjectionA11y_RoundingMatchesPeekVisibleString`) proves visible/spoken parity, and `.accessibilityElement(children: .ignore)` blocks the old fallback path.
- **QuickLog → peek empirical, with stronger fixture.** If we want a sim-observable drift, recon could add a fixture combo (`LIFECLOCK_SEED_BAD_DAY=1` baseline + QuickLog edit to a great day) that produces a > 1-month projection shift. Source proof already covers the contract — empirical adds only "we saw it move" confidence.

## Regressions caught

- None visual on touched surface. Post-fix Pro × gentle × light golden equal to pre-fix on the rendered peek (the visible Text is unchanged; only the surrounding a11y modifiers changed, and `.accessibilityElement(children: .ignore)` does not affect rendering).
- No regressions on untouched screens — only Today's peek + the seed-harness scenario path were modified; History / Future / Profile not driven this session (out of trajectory scope).

## A11y identifiers added

- None new — `today.trajectoryPeek` already existed at TodayView.swift:378 and is preserved alongside the new label/value/hint modifiers.

## Vision updates

- None. The peek a11y phrasing isn't a vision-level constraint; it's an iOS accessibility hygiene fix.
- Open Questions appended: _none_.
- Decided constraints proposed: _none_.

## Goldens captured

Path: `products/life-clock-ios/.polish/goldens/today-free-vs-pro-and-a11y/`

- `today_pro_gentle_light.png` — gentle peek text "Your projection ahead: 88y →" + clockCard "82.9 years"
- `today_pro_coach_light.png` — coach peek "Trajectory: 88y →"
- `today_pro_firm_direct_light.png` — firm_direct peek "Tally: 88y →"
- `today_free_gentle_light.png` — Free tier; 3 tabs, no peek, no upgrade prompt
- `today_pro_gentle_light_post_a11y.png` — post-fix visual no-regression check

Dark-mode cells not captured this session (iteration cap; light-mode tone parity was the load-bearing capture). Recon backlog candidate.

## Final-check status

**Build:** clean `xcodegen generate` + `xcodebuild` exit 0 on both commits.

**Tests:** new tests run in background — see commit `44282fb`. Six new tests total (2 ToneMode pinning the label + 4 TimeDeltaFormatter covering whole-years / mixed / singular pluralization / rounding parity with the visible peek string).

**Live tap-test:** ✅ QuickLog edit persisted (re-open verified "Rough" state); ✅ peek visible in Pro across all three tones; ✅ peek hidden in Free with 3-tab nav.

**VoiceOver empirical (operator-driven follow-up):** unit tests + source contract are the proof here. Empirical Cmd+5 inspection in Simulator would be a one-minute operator validation if you want full closure on the trajectory's "captured + iterated until natural" criterion.

## Next pass

- Dark-mode tone goldens (3 cells) — light-mode parity captured, dark not. Low-risk to fold into a regular Today recon.
- QuickLog → peek empirical with a stronger fixture combo — would close the loop on Iter 4 if operator wants empirical alongside the source proof.
- Drift watch: peek a11y phrasing now has a unit test guarding the formatter's units. If anyone refactors `currentProjectionForPeek()`'s rounding without updating `formatProjectionA11y`, `testProjectionA11y_RoundingMatchesPeekVisibleString` will fail loudly.
