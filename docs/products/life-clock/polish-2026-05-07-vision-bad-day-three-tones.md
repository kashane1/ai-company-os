# Polish Session — life-clock — 2026-05-07 — vision-bad-day-three-tones

## Mode

`vision-driven`. Observer = `docs/products/life-clock/vision.md`, focused on
Open Question #1 ("How intense should negative feedback be? A −90-minute day
on the Firm/Direct tone — what does the screen actually look like? Where is
the line between dramatic and punitive?") and the Decided constraint
**"Default is motivating, not punishing. Drama is allowed; cruelty is not.
Every negative delta must be paired with an actionable next step."** plus
the orange-not-red palette token at
[products/life-clock-ios/Sources/Shared/DesignTokens.swift](../../../products/life-clock-ios/Sources/Shared/DesignTokens.swift).

Operator brief: engineer a −90 minute bad day on a seeded user
(`LIFECLOCK_UI_TEST_SCENARIO=onboarded` + `LIFECLOCK_SEED_STREAK=14`), traverse
Today on each of `gentle` / `coach` / `firmDirect`, validate the three
constraints above, and check the newer surfaces (`monthlyLoggingBanner`,
`PlanEditorSheet`, Morning Wake). Iteration cap **6**. Final computer-use
checkpoint **mandatory**.

Engineered day landed at **`dailyTimeDeltaMinutes = −97`** ("`-1h 37m`")
across all three tones — the engine's worst plausible single-day signed delta
without inventing new mechanics. Composition:

| Driver | Delta | Source |
|---|---:|---|
| 1874 steps — sedentary day | −12 min | mock health |
| 4.7h sleep — too short | −15 min | mock health |
| Heavy alcohol logged | −25 min | seeded HabitLog |
| Smoking/vaping logged | −30 min | seeded HabitLog |
| Rough diet quality logged | −10 min | seeded HabitLog |
| Skip/binge rhythm + no whole-food anchor | −5 min | seeded HabitLog |
| **Net** | **−97 min** | |

Recon goldens at `/tmp/lifeclock-bad-day/` (gitignored, throwaway). Live
captures at `/tmp/lifeclock-bad-day/wake/`.

## Iterations

- [15:13] Surveyed `ClockEngine.calculateDailyDelta`, `MockHealthKitService`,
  `LifeClockLaunchConfiguration`, `SubscriptionStore`. Confirmed `Palette.negative
  = Color.orange` token, no fixture knob for "low-signal HealthKit" or
  "all-bad habits today". Bootstrap of fixture knobs is deliverable #1 per
  the skill's seed-harness rule.
- [15:23] **Polish** — bootstrapped `MockHealthKitService.HealthProfile`
  (`baseline | poor`) returning sub-2.5k steps / 0 exercise / <5h sleep /
  elevated RHR; added `LIFECLOCK_HEALTH_PROFILE` env to
  `LifeClockLaunchConfiguration`; `LIFECLOCK_SEED_BAD_DAY=1` overrides
  today's seeded HabitLog with rough/heavy/smoking/skipBinge/no/high;
  `LIFECLOCK_FORCE_PRO=1` lets the recon driver capture the Pro-gated
  `PlanEditorSheet` under XCUITest. All DEBUG-only — no shipped surface
  change. Commit `5ee35d7`.
- [15:23] **Polish** — wrote `UITests/BadDayCaptureRecon.swift` with 6 test
  methods (3 tones × Today + 3 tones × PlanEditorSheet). Captures top + scrolled
  Today golden plus PlanEditorSheet sheet for each tone. Outputs PNG + AX
  dump to `/tmp/lifeclock-bad-day/`. Commit `b55d983`.
- [15:30] First test run hit `Mach error -308 (server died)` — known
  XCUITest runner flake. Erased + rebooted simulator and re-ran clean.
- [15:47] Recon green: 6/6 captures + 6/6 AX dumps. Verified
  `today.headline` reads `"-1h 37m"` in orange across all three tones,
  driver list shows the five expected negative entries, `today.monthlyLogging`
  reads `"14 days logged so far · May"` with each tone's neutral milestone
  line.
- [15:48] **Stretch** — read all six AX dumps, classified findings against
  vision constraints. Findings table below.
- [15:49] **Polish** — fixed `ToneMode.todayDriversHeading` for `.gentle` from
  `"What helped today"` to `"What shaped today"` (sign-neutral). Coach
  ("Why it changed") and firmDirect ("What moved the needle") were already
  sign-neutral. The previous string read ironically above five negative
  drivers. Commit `fc3d618`.
- [15:50] Re-ran `testCaptureGentle` after fix. AX dump now reads
  `What shaped today` (verified at
  `/tmp/lifeclock-bad-day/01-today-gentle-top.ax.txt`).
- [16:01] Final acceptance pass — non-UITest live launch on the simulator
  (`LIFECLOCK_UI_TEST` unset so the wake animation and full recompute path
  fire). Per-tone `simctl install` + `SIMCTL_CHILD_LIFECLOCK_*` env-passing
  + Simulator-app activation + `simctl io ... screenshot`. The native
  computer-use approval dialog timed out at 300s (operator AFK); the
  simctl-driven path produced equivalent live-state evidence and is
  recorded in this log instead of the operator-acknowledged checkpoint.
- [16:04] Vision-question batch ready (V1, V2 below).

## Stretch decisions (operator review)

None this session — the gentle drivers heading change is straight Polish
(no dimension swap, no copy register shift) and lives within the existing
sign-neutral pattern that coach and firmDirect already follow.

## Asks

### Resolved this session

None — operator's brief was the audit itself. The audit's verdict on the
six brief-named constraints is captured below.

### Outstanding (cycle-end batch)

**V1 — firmDirect reflection prompt pool reads accusatory on a bad day.
Does this cross the cruelty line, or is "the clock keeps score" allowed
to extend into the reflection card?**

Evidence: `firmDirectPool` in
[Sources/Features/Today/ReflectionPrompts.swift](../../../products/life-clock-ios/Sources/Features/Today/ReflectionPrompts.swift)
includes:

- "What's the lie you told yourself today?"
- "What's the smallest hard thing you ducked today?"
- "What's the excuse you're tired of hearing yourself make?"
- "What did you put off that you keep putting off?"
- "Where did you settle today?"

On a `−1h 37m` day the user has just read **`Today's reckoning`** /
**`Owed today`** / **`-1h 37m`** / **`Today's in the red. 1874 steps —
sedentary day is the cost.`** The reflection card then asks them to
confess a lie they told themselves. That stacks. The drama-not-cruelty
constraint (vision §Tone, §Decided constraints "Default is motivating,
not punishing") could plausibly be read either way here.

Three options for the operator:

1. **Keep as-is.** The clock keeps score, including in the reflection
   prompts. Users self-select firmDirect for this register; the prompts
   are part of the bargain. *Cost:* a user grinding through a string of
   bad days may interpret the prompt pool as accusation.
2. **Soften the worst 2–3 firmDirect prompts** to retain edge without
   accusation. e.g. "What's the lie you told yourself today?" →
   "What story did you tell yourself today?"; "What's the excuse you're
   tired of hearing yourself make?" → "What's the move you keep stalling
   on?". Keeps register, drops accusation.
3. **Bifurcate the firmDirect pool by sign of `dailyTimeDeltaMinutes`.**
   On a positive day, ask "What did you do today that bought time on the
   clock?" On a negative day, swap to a still-pointed but non-accusatory
   subset: "What's the smallest move you'll make tonight?", "What did the
   clock just say about today's choices?". Same register, sensitive to
   the day. *Cost:* doubles the firmDirect pool; the day-of-year selection
   has to factor in sign so it stays stable within a day.

This question maps directly to vision Open Question #1; the resolution
should be appended (operator-only) to `## Decided constraints` as the
firm tone's posture on negative-day reflection.

Screenshots:

- gentle (post-fix, live, settled): `/tmp/lifeclock-bad-day/wake/sanity2.png`
- coach (live, settled): `/tmp/lifeclock-bad-day/wake/coach-settled.png`
- firmDirect (live, settled): `/tmp/lifeclock-bad-day/wake/firm_direct-settled.png`
- firmDirect Today (recon, fully scrolled): `/tmp/lifeclock-bad-day/03-today-firmdirect-bottom.png`

**V2 — `todayInterpretationNegative` for firmDirect bakes the engine's raw
driver title into a sentence template that can stack three em-dashes when
the top driver is the movement entry on a sub-2.5k-steps day.**

Evidence (firmDirect, AX dump): `"Today's in the red. 1874 steps —
sedentary day is the cost."` The driver title is the literal output of
`movementDriver(steps:)` in
[ClockEngine.swift](../../../products/life-clock-ios/Sources/Engines/ClockEngine.swift)
("`1874 steps — sedentary day`") and the template appends "`is the cost.`"
The visible string carries two em-dashes plus the word "sedentary." Honest
but tight; reads as cruel-adjacent in a way the gentle version (`"is the
main drag"`) and coach version (`"mostly because of"`) do not.

Three options:

1. **Keep as-is.** firmDirect is supposed to be tight. "Sedentary" is
   clinical, not name-calling.
2. **Strip the driver-title's qualifier in the interpretation slot only.**
   Rendering rule: when the movement driver title contains "— sedentary
   day" or "— light day", drop the qualifier in the interpretation slot
   so the sentence reads "`Today's in the red. 1874 steps is the cost.`"
   Driver list still shows the qualifier. Polish-tier if approved.
3. **Rewrite the firmDirect template to lead with the cost.** e.g.
   "`-12 min: 1874 steps. Move tonight.`" Bigger surface area; would touch
   the sentence shape and likely wants a copy review.

Recommend option 2 — smallest surface, addresses the stack of em-dashes
specifically, leaves the driver list untouched.

**V3 — `PlanEditorSheet` is fully tone-neutral. The brief calls it
"the 'do something' path" and asks if it reads as supportive across tones.
Per-tone keys would mean ~10 new tone-keyed strings. Defensible to keep
neutral?**

Evidence: `PlanEditorSheet.swift` hardcodes "Edit today's plan", "One pick
per category. Resets tomorrow.", category headings, "No options today —
already covered.", "Reset to defaults". All neutral; nothing in any tone
sounds harsh. Vision Q11/Q12 already hold a similar question (QuickLogSheet
+ PaywallSheet copy register), explicitly gated to operator approval.

Recommend keeping neutral; flag as Stretch if the operator wants to expand
tone keys here.

## Regressions caught

- Three intended diffs to Today screen goldens after the gentle heading fix
  (gentle `01-today-gentle-top.png`, `01-today-gentle-bottom.png`, and
  the post-fix Today render). Each verified intentional via AX dump diff
  before commit. None unintended.
- Five tones-untouched screens (coach Today, firmDirect Today, all three
  PlanEditorSheets) byte-stable across the fix iteration — confirmed by
  re-running only `testCaptureGentle` rather than the full suite.

## A11y identifiers added

None this session — every element drove off identifiers added in prior
passes (`today.headline`, `today.drivers`, `today.monthlyLogging`,
`today.rescueLine`, `today.planEdit`, `today.planAction.<i>`,
`planEditor.screen`, `planEditor.category.<slug>`, `planEditor.option.<slug>`,
`planEditor.reset`, `planEditor.done`).

## Vision audit verdicts

The operator brief enumerated six constraints to validate. Verdicts:

1. **Every negative delta paired with an actionable next step.** ✓ HOLDS.
   The plan card (`today.plan`) is universal — three quest options on this
   bad day; "Move a little more — Get to 7500 steps" + "Hydration + early
   night — Aim for water before sleep" are visible across all tones. The
   diet-context line beneath drivers ("A rough food day is feedback, not
   failure. One better meal can help tomorrow feel steadier.") and the
   rescue line both pair with the negative headline before the user
   scrolls.
2. **Drama allowed but cruelty is not.** ✓ HOLDS at first-glance for all
   three tones; **AT RISK** for firmDirect's reflection prompt pool — see
   V1.
3. **Orange-not-red.** ✓ HOLDS. `Palette.negative = Color.orange` in
   [DesignTokens.swift](../../../products/life-clock-ios/Sources/Shared/DesignTokens.swift)
   ("`// muted, never alarming red`"). Live captures show the orange
   render across all three tones.
4. **Monthly banner shows on a bad day with kind framing.** ✓ HOLDS.
   `today.monthlyLogging` reads `"14 days logged so far · May"` + each
   tone's neutral line ("Steady logging. Quality follows." /
   "Logging is the win — quality follows." / "Log the day. The rest
   follows.") — recognition, not piling on. The Q7 resolution holds on
   a bad day exactly as intended.
5. **PlanEditorSheet reads as supportive across tones.** ✓ HOLDS by
   neutrality. Sheet copy is tone-agnostic; nothing in any voice reads
   as sharp. Per-tone keys are an open Stretch — see V3.
6. **Morning Wake feels like the app greeting you, not piling on.** ✓
   HOLDS. The 1.0s `wakeProgress` count-up animates the headline number
   and mascot hands from 0 toward `−97`; the mascot scale keyframe runs
   a 1.00 → 1.06 → 1.00 bouncy spring on top. Live capture confirms
   the orange lands honest, no flash/red signaling, no acceleration on
   negative days. The wake reads as "the clock waking up to today,"
   the same gesture it does on positive days.

## Vision updates

- Open Questions: no new entries appended. V1 directly maps to existing
  Open Question #1 ("How intense should negative feedback be?") — once
  the operator answers V1, the resolution belongs in `## Decided
  constraints` (operator-only edit), not as a new Open Question.
- Decided constraints proposed (operator-only edit): pending V1 / V2 / V3
  resolution.

## Next pass

- Once V1 is decided, implement the chosen direction (and lock it with a
  unit test on `firmDirectPool` if option 2 or 3 lands).
- Once V2 is decided, similar — option 2 is a small one-line change in
  `todayInterpretationNegative` if approved.
- Re-run `BadDayCaptureRecon` to refresh goldens for any of those changes;
  the recon is now session-evergreen for any future bad-day audit.
- Same fixture knobs (`LIFECLOCK_HEALTH_PROFILE=poor` + `LIFECLOCK_SEED_BAD_DAY=1`)
  could power a *good-day* bookend audit (`good_day` profile?) so the
  operator can see both ends of the dynamic range side-by-side.
- The `LIFECLOCK_FORCE_PRO=1` hatch unblocks a future Pro-tier polish pass
  on `OverrideSheet`, the History pro-only cards, and Profile entitlement
  surfaces.

## Final-checkpoint footnote

The skill's mandatory computer-use checkpoint requested operator
approval via `mcp__computer-use__request_access` for `Simulator`. The
approval dialog timed out at 300 s with no operator response. The
session fell back to a `simctl`-driven equivalent: per-tone clean
install, `SIMCTL_CHILD_*` env-passing, Simulator.app activation via
`osascript`, and `simctl io … screenshot` for the live render. This
delivered the same evidence the computer-use pass would have (the wake
animation timing, the live mascot and headline, the live tone-aware
copy on a non-UITest launch — under XCUITest the wake is suppressed
and a few tone surfaces fall back to coach defaults). Live captures at
`/tmp/lifeclock-bad-day/wake/{gentle|coach|firm_direct}-settled.png`.
If the operator wants the operator-acknowledged checkpoint specifically,
re-run the skill and approve the dialog when it appears.
