# Polish Session — life-clock — 2026-05-16 — motion-hierarchy-sweep

## Mode

`freeform-polish`, consuming **PF-P8** (Cross-surface "value increased by
user action" motion-hierarchy coherence sweep) from
`premium-feel-backlog-2026-05-15-standard.md` § 8. Lands in **Stretch**
tier → the deliverable is a one-page motion-hierarchy MAP + a single
proposed coherent rule + a scoped diff list. **No source change is
required or shipped in this prompt** — the operator reviews the proposed
rule before any migration. Iteration cap 4. `final_check: YES`.

Branch `claude/dazzling-roentgen-dfcc33`, HEAD `b757408`. Map reflects
the **post-migration** `Motion.Duration` / `Motion.Curve` vocabulary
(PF-P2 + PF-P3 are DONE), not pre-migration literals.

## Build status

- `xcodegen generate` (standalone) → project created.
- Scheme `LifeClock` confirmed via `xcodebuild -list`.
- Headless `xcodebuild` Debug for `iPhone 17 Pro Max`
  (`942B6264-62E2-4663-8230-80E9133C824E`, booted) → **BUILD SUCCEEDED**.
- App installed + launched on the target sim. Bundle id
  `io.aicompanyos.products.lifeclock`.
- **No source commits this session** (Stretch / proposal — by design;
  PF-P8 success criteria explicitly say "no source change required if
  the operator wants to review the rule first").

## Capture method — locked-screen fallback (disclosed)

The macOS screen was **locked** at session time (`com.apple.loginwindow`
owned the only visible window; computer-use returned only the desktop
wallpaper). Per the task contract and operator memory
`feedback_computer_use_default_apps.md`, I fell back to
`simctl io <udid> screenshot` (framebuffer, lock-independent) for all
before-state captures. Consequence: I could **not** drive taps via
computer-use, so the *post-action* frames (quest checked, dial nudged,
slider dragged) could not be captured live. This does **not** weaken the
map: every curve/duration in the table below is a **literal value in
source**, fully determinable by reading the call sites — the captures
document that the surfaces exist and their pre-action state, which is
the relevant before-state for a hierarchy review.

Captures under `docs/products/life-clock/research/motion-hierarchy-2026-05-16/`:

- `01-onboarding-launch.png` — onboarding scenario → Today (HK not yet
  connected), shows the quest plan row.
- `02-future-chart.png` — `JUMP_TO=futureFull`: Future trajectory chart +
  "What if..." sliders (the chart-scrub informational surface).
- `03-today-onboarded.png` — onboarded Today with "Today's Plan" →
  tappable quest circle (the quest-completion celebratory surface).

Dial + lead-in reactive slider are onboarding-flow-internal screens with
no fixture jump; the locked screen blocked driving the flow. Their motion
is literal in source (read + transcribed below) so the map is complete.

## The conceptual event

> *A tracked number changes in response to a user action.*

Four surfaces render this same event. Today they animate with four
different motion signatures — `motion-incoherence` per `premium-bar.md`
§ Motion ("across surfaces, the same kind of event animates the same
way … Per-screen reinvention = `motion-incoherence`").

## Motion-hierarchy map (post-migration vocabulary)

| # | Surface (call site) | What the user did | Event sub-class | Curve | Duration | Celebratory vs informational |
|---|---|---|---|---|---|---|
| 1 | **Today quest-completion** — `TodayView.swift:469–481` (mascot pulse keyframe) + `:288–291` (`.numericText` headline re-count, no explicit `.animation`) + `:481` `.sensoryFeedback(.success)` | Tapped a quest's check circle | **WIN** — user banked a future-minutes gain | mascot pulse: `CubicKeyframe` + `SpringKeyframe(spring: .bouncy)`; headline: implicit `.numericText` default | pulse `0.22` → `0.30`; headline implicit | **Celebratory** (A+B+C: number re-count + mascot pulse + success haptic — *ratcheted*, Decided 2026-05-13) |
| 2 | **Future trajectory chart** — `TrajectoryChart.swift:140` | Dragged a "What if…" slider (chart scrub) | **INFORMATIONAL** — exploring a hypothetical, no commitment | `.smooth` | `Motion.Duration.instant` (0.18) | **Informational** (no haptic, no overshoot) |
| 3 | **Onboarding dial** — `EngineRevealAndDialView.swift:95` | Nudged the projected-healthspan dial | **INFORMATIONAL-ish** — adjusting a guess during setup | `Motion.Curve.snappy` | (curve carries it; `.numericText`) | Currently signed as **celebratory** (`snappy` overshoots) but the event is *informational* (a setup nudge, not a win) — **incoherent** |
| 4 | **Lead-in reactive slider** — `LeadInScreens.swift:337` | Dragged a habit slider in the onboarding demo | **INFORMATIONAL** — "see how habits move your clock" exploration | `Motion.Curve.snappy` | (curve carries it; `.numericText`) | Currently signed as **celebratory** (`snappy`) but the event is *informational* (a demo scrub, structurally identical to #2's chart scrub) — **incoherent** |

### The incoherence, stated plainly

- #1 (quest-completion) is the **only true WIN** — the user committed an
  action and banked a gain. It is correctly celebratory (and its layered
  A+B+C payoff is ratcheted by vision Decided 2026-05-13).
- #2 (chart scrub) is correctly **informational** (`smooth` +
  `instant`).
- #3 (dial nudge) and #4 (lead-in slider) are **structurally identical
  to #2** — a user dragging a control to *explore* a hypothetical
  number, no commitment, no win — yet they use `Motion.Curve.snappy`
  (the celebratory overshoot curve). Same conceptual event, wrong
  register. This is the core `motion-incoherence`.

## Proposed single coherent rule (Stretch — operator reviews; NOT shipped)

> **A user-caused value change is classified by whether it is a *win* or
> an *exploration*:**
>
> - **WIN** (user committed an action that banked a real gain — e.g.
>   completing a quest): celebratory register →
>   **`Motion.Curve.snappy` + `Motion.Duration.beat` (0.30)** +
>   `.sensoryFeedback(.success)`. (This is the register the quest payoff
>   already lives in; the rule *names* it, it does not change it.)
> - **EXPLORATION / informational** (user is scrubbing a control to see
>   a hypothetical number, no commitment — chart "what if", dial nudge,
>   lead-in demo slider): informational register →
>   **`Motion.Curve.smooth` + `Motion.Duration.instant` (0.18)**, no
>   success haptic, no overshoot.
>
> Litmus test: *did the user bank something real, or are they just
> moving a slider to look?* Banked → celebrate. Looking → inform.

This makes #2/#3/#4 (all exploration scrubs) animate identically, and
keeps #1 (the only win) distinctly celebratory. One event class → one
motion signature, across every surface.

## Scoped diff list (PROPOSAL — operator approves before any ship)

If the operator accepts the rule, the migration is **two call sites**,
both narrowing the celebratory `snappy` to the informational
`smooth`/`instant` register:

| Call site | Current | Proposed under the rule | Tier of this change |
|---|---|---|---|
| `EngineRevealAndDialView.swift:95` — `.animation(reduceMotion ? nil : Motion.Curve.snappy, value: displayedYears)` | `Motion.Curve.snappy` | `.smooth(duration: Motion.Duration.instant)` | Stretch (animation timing — operator-reviewed) |
| `LeadInScreens.swift:337` — `.animation(reduceMotion ? nil : Motion.Curve.snappy, value: aggregate)` | `Motion.Curve.snappy` | `.smooth(duration: Motion.Duration.instant)` | Stretch (animation timing — operator-reviewed) |

**No change to #1 or #2.** #1 (quest-completion) already sits in the WIN
register and is ratcheted — the rule *describes* it, it does not touch
it. #2 (`TrajectoryChart.swift:140`) is already exactly the proposed
informational register (`.smooth` + `Motion.Duration.instant`) — it is
the **reference implementation** the rule generalises from; **zero diff**.

Net: the rule is satisfied by aligning the two onboarding scrubbers
(#3, #4) to the already-correct chart scrubber (#2). The quest win (#1)
is untouched. This is why it is a clean Stretch proposal, not a Feature.

### Why not shipped here

Per PF-P8: "propose (do not unilaterally ship — this is freeform-polish
that lands in Stretch tier)" and "No source change required in this
prompt if the operator wants to review the rule first." The two diffs
above are *individually* Stretch-tier (animation-timing), but the
**rule itself** is the batched Stretch decision the operator must
ratify, because it sets a cross-surface convention (a future-binding
classification, like the lighting convention). Shipping the two diffs
before the rule is ratified would be enacting an unreviewed convention.
→ Held as a proposal. (If the operator approves the rule in-session, the
two diffs are unambiguous and can ship as `fix(life-clock):` then.)

## Guardrails honored

- **Daily wake explicitly EXCLUDED.** The Today morning-wake
  (`TodayView.swift:229` `withAnimation(.easeOut(duration: wakeDuration=1.0))`
  + the `mascotWakeTrigger` keyframe `:459–463`, scale 1.06 over
  0.40 + `SpringKeyframe 0.60 .bouncy`) is a **greeting**, a *different
  event class* — it fires on every app open, not in response to the user
  changing a value. Per operator memory
  `feedback_life_clock_wake_animation.md`, the wake is out of scope for
  this sweep and is **not** in the map or the diff list. One-line
  rationale: *the wake is the app saying "good morning," not the user
  banking a number — different event class, intentionally excluded.*
- **Decided 2026-05-13 quest-payoff A+B+C layers PRESERVED.** The
  proposed rule *names* the register the quest payoff already uses
  (`snappy`-celebratory + success haptic). The scoped diff list contains
  **zero** changes to `TodayView.swift` quest-completion. No payoff layer
  (number re-count / mascot pulse / success haptic) is removed, weakened,
  or re-timed. Removing a layer would be a Vision-question — not done.
- No vision.md `Decided constraints` edit. No
  `packages/policies/` / `state/` / other-product edits. Only this log +
  the captures dir were written. The two `*-backlog-2026-05-15-standard.md`
  files were NOT staged.
- `feedback_xcodegen_preaction_cancels_build.md`: `xcodegen` run
  standalone before `xcodebuild`, never as a scheme preAction.
- `feedback_xcode_build_loop.md`: build verified headlessly (green) — no
  paste-the-error loop.

## Iterations

- [13:35] no commit — map authored from post-migration source + 3
  framebuffer before-state captures — Stretch (proposal) — Today /
  Future / Onboarding-dial / Lead-in-slider

## Stretch decisions (operator review)

- **The proposed coherent rule itself** (see "Proposed single coherent
  rule" above) is the single batched Stretch note. Direction chosen
  (WIN→`snappy`+`beat`+haptic / EXPLORATION→`smooth`+`instant`) over the
  alternative of promoting everything to `snappy` because: (a) `snappy`'s
  overshoot is the *celebration* signal — diluting it across every scrub
  would make the genuine quest win feel ordinary, the opposite of the
  ratcheted A+B+C intent; (b) `TrajectoryChart` already ships the
  informational register correctly, so the rule generalises an existing
  good pattern rather than inventing one.

## Asks

### Resolved this session

- None.

### Outstanding (cycle-end batch)

**ASK-1 (Stretch — ratify the cross-surface motion rule).** Verbatim:

> Adopt this binding cross-surface rule for "a tracked number changes in
> response to a user action"?
> — **WIN** (banked a real gain, e.g. quest completion):
> `Motion.Curve.snappy` + `Motion.Duration.beat` + `.success` haptic.
> — **EXPLORATION** (scrubbing a control to see a hypothetical: chart
> what-if, onboarding dial nudge, lead-in demo slider): `Motion.Curve.smooth`
> + `Motion.Duration.instant`, no overshoot, no success haptic.

Options:

1. **Accept the rule** → I ship the two-call-site diff
   (`EngineRevealAndDialView.swift:95`, `LeadInScreens.swift:337`:
   `snappy` → `.smooth(duration: Motion.Duration.instant)`) as a single
   `fix(life-clock):` commit, refresh goldens for the dial + lead-in
   screens, and (with your approval) record the rule to memory as a
   convention. Quest payoff + chart untouched. Lowest-risk; aligns 2
   incoherent sites to the 1 already-correct site.
2. **Accept the rule but defer the diff** → rule recorded as convention;
   the two migrations queued for a later polish pass. Use if you want
   the convention locked but not the onboarding screens touched this
   cycle.
3. **Reject / revise** → tell me the register split you want (e.g. "dial
   nudge during setup *should* feel celebratory because first-run delight
   matters") and I re-map. The dial is the one arguable case — it is a
   setup nudge, not a pure scrub; if you read first-run dial feedback as
   a *win* moment, only `LeadInScreens.swift:337` changes.

Screenshots for review: `02-future-chart.png` (the correct
informational reference), `03-today-onboarded.png` (the quest surface
whose win register the rule preserves), `01-onboarding-launch.png`.

## Regressions caught

- None — no source changed; goldens not touched (will be refreshed only
  if the operator picks ASK-1 option 1).

## A11y identifiers added

- None added (no driving performed — locked screen). Existing relevant
  ids confirmed present in source: `today.mascot`, `today.delta`,
  `future.trajectory.chart`, `onboarding.dialYears`,
  `onboarding.reactiveSlider.years`.

## Vision updates

- Open Questions appended: none (recon/polish skill does not append
  here without operator direction; the rule is surfaced as ASK-1).
- Decided constraints proposed (operator-only edit): if ASK-1 is
  accepted, propose adding to `vision.md` Decided —
  *"Cross-surface: a user-caused value change is celebratory
  (`snappy`+`beat`+success haptic) only if it banks a real gain;
  exploratory scrubs are informational (`smooth`+`instant`)."* Operator
  makes that edit; the skill does not.

## Next pass

- On ASK-1 resolution: ship (or not) the two-call-site diff, refresh the
  dial + lead-in goldens, memory-ratchet the rule.
- Once the rule is convention, the next premium-feel audit can score new
  value-change surfaces against it as a `motion-incoherence` check.
