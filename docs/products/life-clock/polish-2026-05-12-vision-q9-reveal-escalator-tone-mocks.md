# Polish Session — life-clock — 2026-05-12 — vision-q9-reveal-escalator-tone-mocks

## Mode

Vision-driven, narrow scope: produce visual mocks for vision Open Question #9 (reveal-escalator tone-awareness) so the operator can pick (a/b/c) on evidence rather than from text alone. No production copy changes ship this session — the mock fixture is `#if DEBUG`-gated and is removed once the operator picks.

- Iteration cap: 6
- Final computer-use checkpoint: **DEFERRED** — captures produced via headless `simctl io screenshot` from the same JUMP fixture the prior terminal-screen polish sessions used. See [polish-2026-05-07-vision-terminal-screens-followup.md](polish-2026-05-07-vision-terminal-screens-followup.md) for the existing visual-acceptance precedent on this surface.
- Tone source-of-truth: [ToneMode.swift](../../../products/life-clock-ios/Sources/App/ToneMode.swift)
- Simulator target: iPhone 17 Pro (already booted; iPhone 16e from prior sessions not booted; no pre-existing goldens for the reveal escalator to match against).
- Scheme: `LifeClock` (regenerated `LifeClock.xcodeproj` via `xcodegen` at session start).

Surfaces touched:
- [RevealEscalatorScreens.swift](../../../products/life-clock-ios/Sources/Features/Onboarding/Screens/RevealEscalatorScreens.swift) — added a DEBUG-only `Q9Variant` switch and `revealEffectiveTone(draft:)` helper. Wired `LifeGridRemainingView` and `BigNumberPenaltyView` to render gentle copy when the effective tone resolves to `.gentle`. Default behavior (variant `.a`, Release builds) is identical to before this session.
- [OnboardingCoordinator.swift](../../../products/life-clock-ios/Sources/Features/Onboarding/OnboardingCoordinator.swift) — JUMP fixture now honors `LIFECLOCK_SEED_TONE` (mirrors the existing seed knob from [polish-2026-05-06-vision-tone-surface-matrix.md](polish-2026-05-06-vision-tone-surface-matrix.md) commit `215e409`) and always seeds `perceivedStressScore = 30` + `lonelinessScore = 7` so variant (c)'s inferred-softer threshold can fire under the fixture.

## The three variants

Mocks render the same dramatic-trajectory draft (heavy lifestyle + 2014 baseline) across all three, so the only diff is the reveal copy register. The visual diff lives entirely on **`lifeGridRemaining`** and **`bigNumberPenalty`** — the other three reveal screens (`analyzing`, `archetypeReveal`, `recoveryPreview`) do not carry the dramatic register at issue and are byte-identical across variants.

### Variant (a) — keep the dramatic register on principle

| Screen | Title | Body |
|---|---|---|
| `lifeGridRemaining` | "This is what's still ahead." | "Each dot is a week your habits get to shape." |
| `bigNumberPenalty` | "~19 years on the table." | "These are the years your current habits put within reach to win or lose. The clock follows what you do next." |

Goldens:
- [.polish/goldens/q9_a_lifeGridRemaining.png](../../../products/life-clock-ios/.polish/goldens/q9_a_lifeGridRemaining.png)
- [.polish/goldens/q9_a_bigNumberPenalty.png](../../../products/life-clock-ios/.polish/goldens/q9_a_bigNumberPenalty.png)

Reproduce: `SIMCTL_CHILD_LIFECLOCK_JUMP_TO=bigNumberPenalty xcrun simctl launch <UDID> io.aicompanyos.products.lifeclock`

### Variant (b) — move `ToneView` earlier so reveal can read `tone.*`

Mocked by seeding `LIFECLOCK_SEED_TONE=gentle` into the JUMP fixture, which has the same effect as if the user had picked `gentle` before the reveal escalator runs. Copy comes from `RevealEscalatorGentleCopy`:

| Screen | Title | Body |
|---|---|---|
| `lifeGridRemaining` | "These weeks are still yours." | "Each dot is a week your habits help shape." |
| `bigNumberPenalty` | "About 19 years to work with." | "These are years your everyday choices can lift. Small steps add up; today is a fine place to start." |

Goldens:
- [.polish/goldens/q9_b_lifeGridRemaining.png](../../../products/life-clock-ios/.polish/goldens/q9_b_lifeGridRemaining.png)
- [.polish/goldens/q9_b_bigNumberPenalty.png](../../../products/life-clock-ios/.polish/goldens/q9_b_bigNumberPenalty.png)

Reproduce: add `SIMCTL_CHILD_LIFECLOCK_Q9_VARIANT=b SIMCTL_CHILD_LIFECLOCK_SEED_TONE=gentle` to the launch.

For the firmDirect direction we'd also add tone-keyed copy on these two screens (and likely keep the dramatic register sharper) — out of scope for the mock; the operator-facing question is gentle-vs-dramatic, not all three tones.

### Variant (c) — infer softer from stress + connection signals on consent screens

Mocked by seeding `perceivedStressScore = 30` (Stretched bucket, ≥27) and `lonelinessScore = 7` (low-connection bucket, ≥6) in the JUMP fixture and rendering the same gentle copy as (b) regardless of whether `toneMode` has been picked. Threshold rationale: matches the existing `PerceivedStressBucket` and `LonelinessBucket` cutoffs already used by telemetry.

Identical copy to (b) — the mock uses the same `RevealEscalatorGentleCopy` strings. The visible diff vs (b) is only the trigger mechanism; in production, (c)'s wording could plausibly differ (e.g., less assertive than the operator-pick (b) since the app is guessing). That is itself a sub-decision if the operator picks (c).

Goldens:
- [.polish/goldens/q9_c_lifeGridRemaining.png](../../../products/life-clock-ios/.polish/goldens/q9_c_lifeGridRemaining.png)
- [.polish/goldens/q9_c_bigNumberPenalty.png](../../../products/life-clock-ios/.polish/goldens/q9_c_bigNumberPenalty.png)

Reproduce: `SIMCTL_CHILD_LIFECLOCK_Q9_VARIANT=c SIMCTL_CHILD_LIFECLOCK_JUMP_TO=bigNumberPenalty`.

Behavior when signals are NOT extreme (e.g. PSS=10, UCLA=3): the conditional falls through to `.coach`, so (c) renders identical to (a). The mock fixture seeds extreme signals to demonstrate the firing case; the not-firing case is by definition identical to variant (a) and was not separately captured.

## Iterations

- [18:00] pre-flight — regenerated `LifeClock.xcodeproj` via `xcodegen`; headless build green; working tree clean. iPhone 17 Pro already booted (no iPhone 16e available); no existing reveal-escalator goldens to match against.
- [18:01] variant (a) — captured 5 goldens at JUMP fixture default state.
- [18:03] variant (b/c) implementation — `Q9Variant` enum + `revealEffectiveTone(draft:)` + `RevealEscalatorGentleCopy`. Wired into `LifeGridRemainingView.copy` and `BigNumberPenaltyView.copy(yearsAtRisk:)`. `OnboardingCoordinator` JUMP fixture now honors `LIFECLOCK_SEED_TONE` and seeds stretched-stress signals.
- [18:05] variant (b) — captured 5 goldens with `LIFECLOCK_Q9_VARIANT=b LIFECLOCK_SEED_TONE=gentle`.
- [18:06] variant (c) — captured 5 goldens with `LIFECLOCK_Q9_VARIANT=c` (no tone seed; condition fires off the always-seeded stress signals).

Total: 15 goldens at `products/life-clock-ios/.polish/goldens/q9_{a,b,c}_*.png` (gitignored).

## Stretch decisions (operator review)

None this session — every change is mock-tier (DEBUG-only fixture, removed after operator pick) or test-infra (JUMP fixture honoring an existing seed-tone knob + always-seed stress signals so the (c) condition is exercisable).

## Asks

### Resolved this session

None — Q9 itself is the open Ask carried over from [polish-2026-05-06-vision-tone-surface-matrix.md](polish-2026-05-06-vision-tone-surface-matrix.md) Ask #1, and the goldens are the evidence needed to resolve it.

### Outstanding (cycle-end batch)

#### Q9 — Reveal-escalator tone-awareness (operator pick: a / b / c)

Side-by-side comparison of the two screens where the register actually differs:

**`lifeGridRemaining`:**
- (a) [q9_a_lifeGridRemaining.png](../../../products/life-clock-ios/.polish/goldens/q9_a_lifeGridRemaining.png) — *"This is what's still ahead. / Each dot is a week your habits get to shape."*
- (b) [q9_b_lifeGridRemaining.png](../../../products/life-clock-ios/.polish/goldens/q9_b_lifeGridRemaining.png) — *"These weeks are still yours. / Each dot is a week your habits help shape."*
- (c) [q9_c_lifeGridRemaining.png](../../../products/life-clock-ios/.polish/goldens/q9_c_lifeGridRemaining.png) — same copy as (b), triggered by signals not tone pick.

**`bigNumberPenalty`:**
- (a) [q9_a_bigNumberPenalty.png](../../../products/life-clock-ios/.polish/goldens/q9_a_bigNumberPenalty.png) — *"~19 years on the table. / These are the years your current habits put within reach to win or lose. The clock follows what you do next."*
- (b) [q9_b_bigNumberPenalty.png](../../../products/life-clock-ios/.polish/goldens/q9_b_bigNumberPenalty.png) — *"About 19 years to work with. / These are years your everyday choices can lift. Small steps add up; today is a fine place to start."*
- (c) [q9_c_bigNumberPenalty.png](../../../products/life-clock-ios/.polish/goldens/q9_c_bigNumberPenalty.png) — same copy as (b), triggered by signals not tone pick.

Tradeoffs:

- **(a) — keep one dramatic register**. Vision-question #9 listed "the reveal earns the drama and dropping it weakens the product" as the case for (a). The reveal-escalator's job is to make the loss concrete enough that the dial and recovery preview land emotionally. A soft register risks neutering the moment for the median user to protect a minority who self-identify as anxiety-prone. Cost: anxiety-prone users get an unsoftened experience because tone is locked to Coach pre-`ToneView`.
- **(b) — `ToneView` earlier + tone-aware reveal**. Net-new scope: re-order onboarding so `tone` precedes `analyzing`. Tone preview screen currently shows `mode.description` only — picking before the user has seen *any* of the clock's voice is a colder pick than after the lead-in. New ToneMode keys: `revealLifeGridTitle`, `revealLifeGridBody`, `revealBigNumberTitle(yearsAtRisk:)`, `revealBigNumberBody` (× 3 tones if we want firmDirect to sharpen further). Compounds with Q10/Q11 if those land tone-aware copy too.
- **(c) — infer softer when Stretched + low connection**. Smaller scope (no onboarding reorder), no new pick-step UX, soft register only fires for the users who'd benefit most (high PSS + high UCLA). Cost: implicit; user has no model for *why* the app's voice shifted. The same gentle copy from (b) is reusable, or a separate set could land for the inferred case to keep the "tone-pick" surface distinct.

**Decision authority**: operator (Vision-question, Feature-tier).

**If operator picks (a)**: this session's RevealEscalatorScreens.swift + OnboardingCoordinator.swift mock fixture is removed; Q9 lands in `## Decided constraints` in [vision.md](vision.md) as "the reveal escalator stays in a single dramatic register".

**If operator picks (b)**: a follow-up commit adds the four `ToneMode` keys (with gentle / coach / firmDirect variants), removes the `Q9Variant` switch, reorders `OnboardingPath` so `tone` precedes `analyzing`, and possibly adds a per-tone hero line to `ToneView` so the pick has visual weight pre-`analyzing` (the Q10 follow-up the prior matrix flagged). Q9 → Decided.

**If operator picks (c)**: a follow-up commit lifts `revealEffectiveTone` + `RevealEscalatorGentleCopy` out of the `Q9Variant` switch, keys the soft register off only the stress + loneliness signals, removes the variant fixture, and adds inline copy on `SafetyNetView` (or the support-moment presenter) noting the inferred-softer behavior so it's not invisible to the user. Q9 → Decided. Q10 stays open.

## Regressions caught

- None in shipped behavior. The Q9 fixture is `#if DEBUG`-gated; Release builds always resolve `Q9Variant.current == .a`, which renders the existing literal copy. Reproduced by checking `q9_a_*` goldens against unchanged copy strings in the diff.
- The `LifeGridDotView` JUMP-fixture race carried over from [polish-2026-05-07-vision-terminal-screens-followup.md](polish-2026-05-07-vision-terminal-screens-followup.md) is visible in `q9_b_lifeGridRemaining.png` (dot grid empty, just legend) — known issue, not introduced this session, does not affect the copy decision the operator is making.

## A11y identifiers added

- None this session — `LifeGridRemainingView` and `BigNumberPenaltyView` route through `OnboardingScaffold`, which already attaches `onboarding.<screenID>` containers. The Q9 copy change is text-only inside an existing identifier.

## Vision updates

- **Open Questions appended**: nothing new. Q9 itself is the open question being resolved by this session's mocks; the operator pick collapses it to `## Decided constraints`.
- **Decided constraints proposed (operator-only edit)**: none until operator picks a/b/c.

## Files touched

- `products/life-clock-ios/Sources/Features/Onboarding/Screens/RevealEscalatorScreens.swift` — `Q9Variant` enum + `revealEffectiveTone(draft:)` + `RevealEscalatorGentleCopy` + wiring in `LifeGridRemainingView.copy` and `BigNumberPenaltyView.copy(yearsAtRisk:)`. DEBUG-only switch; Release behavior unchanged.
- `products/life-clock-ios/Sources/Features/Onboarding/OnboardingCoordinator.swift` — JUMP fixture honors `LIFECLOCK_SEED_TONE` and seeds `perceivedStressScore = 30` + `lonelinessScore = 7` so variant (c) is exercisable.
- `products/life-clock-ios/.polish/goldens/q9_{a,b,c}_*.png` — 15 capture artifacts (gitignored).
- `docs/products/life-clock/polish-2026-05-12-vision-q9-reveal-escalator-tone-mocks.md` — this session log.

## Next pass

- ~~Wait for operator pick on Q9 (a / b / c above).~~ **Resolved same-day — operator picked (c). See "Q9 resolution" below.**
- Independent of Q9 resolution: pick up the carried-over `LifeGridDotView` JUMP-fixture race (still on the cycle-end list from [2026-05-07](polish-2026-05-07-vision-terminal-screens-followup.md)) and the `RecoveryPreviewCopy.headline` `yearsBack == 0` fallback.

---

## Q9 resolution — option (c), inferred-softer

Operator picked (c) after reviewing all three goldens. Reasoning (operator's, paraphrased): the dramatic register is load-bearing for the median user and the dial + recovery preview moment is calibrated against it, but the population most likely to be hit poorly by the dramatic register is precisely the population whose stress + connection signals SafetyNet was designed around — and we ask those questions one screen before the reveal escalator. Inferring soft register from those signals is consistent with the existing product posture; asking the user to pre-pick a voice (option b) is principled but doesn't actually move the needle for most users since they'll default to Coach without prior sample. Soft register stays a minority experience by design.

### Ship-version commits

- **`fix(life-clock): infer-softer reveal-escalator register from PSS + UCLA signals (Q9 option c)`**
  - Removed the DEBUG-only `Q9Variant` enum + `revealEffectiveTone(draft:)` helper. Replaced with always-on `revealUsesSofterRegister(draft:)`: returns true iff `(draft.perceivedStressScore ?? 0) ≥ 27` AND `(draft.lonelinessScore ?? 0) ≥ 6` (matches `PerceivedStressBucket.stretched` + `LonelinessBucket.lowConnection`).
  - `LifeGridRemainingView` and `BigNumberPenaltyView` swap to `RevealEscalatorGentleCopy` when the threshold fires; otherwise render the existing dramatic copy verbatim.
  - When softened, both views append an inline tertiary-tint `Text("Prefer a sharper read? Switch tone in Profile anytime.")` below their existing content (above Continue). A11y identifiers `onboarding.lifeGridRemaining.toneSwitchAffordance` and `onboarding.bigNumberPenalty.toneSwitchAffordance` on the affordance lines.
  - Tightened the gentle `bigNumberTitle` copy from `"About {N} years to work with."` → `"About {N} years to shape."` (lexical consonance with the gentle `lifeGridBody` "your habits help shape", and short enough to render on one line at iPhone 17 Pro width — the longer form truncated to `"About {N} years to work w…"` once the dot grid rendered and squeezed the title slot).
- **`chore(life-clock): JUMP fixture env-var seed for PSS + UCLA (replace always-on seeding)`**
  - JUMP fixture previously always seeded `perceivedStressScore = 30` + `lonelinessScore = 7` so the Q9 variant fixture could fire variant (c). Now reads `LIFECLOCK_SEED_PSS` + `LIFECLOCK_SEED_UCLA` env-vars; unset = nil (pre-Q9 fixture behavior — `revealUsesSofterRegister` returns false → dramatic register). Polish runs that want the softened reveal pass `SIMCTL_CHILD_LIFECLOCK_SEED_PSS=30 SIMCTL_CHILD_LIFECLOCK_SEED_UCLA=7`. `LIFECLOCK_SEED_TONE` knob retained from the prior session — orthogonal, useful across runs.

### Ship-version goldens (verification)

- **Softened (PSS=30, UCLA=7)** — softer copy + affordance:
  - [.polish/goldens/q9_ship_soft_lifeGridRemaining.png](../../../products/life-clock-ios/.polish/goldens/q9_ship_soft_lifeGridRemaining.png) — "These weeks are still yours." + affordance line
  - [.polish/goldens/q9_ship_soft_bigNumberPenalty.png](../../../products/life-clock-ios/.polish/goldens/q9_ship_soft_bigNumberPenalty.png) — "About 19 years to shape." + affordance line
- **Default (no stress seed)** — dramatic copy preserved, no affordance:
  - [.polish/goldens/q9_ship_dramatic_lifeGridRemaining.png](../../../products/life-clock-ios/.polish/goldens/q9_ship_dramatic_lifeGridRemaining.png)
  - [.polish/goldens/q9_ship_dramatic_bigNumberPenalty.png](../../../products/life-clock-ios/.polish/goldens/q9_ship_dramatic_bigNumberPenalty.png)

### Vision update

- Q9 inline resolution appended at [vision.md L71](vision.md) (preserves the original question text struck-through, with the operator's pick and reasoning beneath, per the existing Q7/Q10/Q15-19 convention).
- Decided constraint proposed (operator-only edit to `## Decided constraints`): "The reveal escalator runs in the dramatic register by default. When the user's PSS + UCLA answers on the consent screens fire both bucket thresholds (Stretched ≥27 + low-connection ≥6), `LifeGridRemainingView` and `BigNumberPenaltyView` switch to the gentle register and show an inline 'switch tone in Profile' affordance. No other reveal-escalator screen carries tone-aware copy; archetype description is already model-derived."

---

## PR body (derived from session log)

```
chore(life-clock): Q9 reveal-escalator tone-aware mock fixture + goldens

Vision-driven, scoped to producing visual mocks for vision Open Question #9
(reveal-escalator tone-awareness) so the operator can pick a/b/c on evidence.
No shipped behavior changes — the Q9 mock switch is #if DEBUG-gated and
resolves to .a (current dramatic register) in Release builds.

Commits:
- chore(life-clock): Q9 reveal-escalator tone-aware mock fixture (DEBUG)
  Adds Q9Variant enum + revealEffectiveTone(draft:) helper + gentle copy
  strings on RevealEscalatorScreens.swift; wires LifeGridRemainingView and
  BigNumberPenaltyView to render the gentle register when the effective
  tone resolves to .gentle. JUMP fixture in OnboardingCoordinator now
  honors LIFECLOCK_SEED_TONE and always seeds PSS=30 + UCLA=7 so variant
  (c)'s inferred-softer condition fires under the fixture.

- docs(life-clock): polish-2026-05-12 session log + Q9 Ask with goldens
  15 goldens at .polish/goldens/q9_{a,b,c}_*.png (gitignored). Side-by-side
  comparison + per-option tradeoffs at the bottom of the session log.

Verification:
- Headless build green for iPhone 17 Pro on each commit.
- 15 goldens captured deterministically via JUMP fixture + simctl io
  screenshot, three variants × five reveal screens.
- (a) baseline copy unchanged in the diff (literal-string check); Release
  build resolves Q9Variant.current == .a always.

Outstanding: Q9 itself — operator pick (a/b/c) needed before the
follow-up commit lands; mock fixture removed on resolution.
```
