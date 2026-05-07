# Polish Session — life-clock — 2026-05-06 — vision-terminal-onboarding-screens

## Mode

Vision-driven (`docs/products/life-clock/vision.md`). Iteration cap 6, final computer-use checkpoint mandatory.

Focus: the four post-dial onboarding screens that hadn't yet had a focused polish pass — `recoveryPreview`, `healthKitAuth`, `paywallPrimary`, `entryView`. For each, audit (a) does it earn its place, (b) is the persistent mascot trajectory believable here, (c) does the Continue/secondary placement match the pinned-CTA rhythm 1c2a85f established. Walk both `LIFECLOCK_HEALTH_AUTH=denied` and `=authorized` so the HK branch is exercised.

## Iterations

- [11:14] `973a2bd` — chore(life-clock): debug-only LIFECLOCK_JUMP_TO fixture for terminal-screen polish — Polish — coordinator + cold-open
- [11:43] `bea2fba` — fix(life-clock): center paywall.restore to match scaffold secondary-action rhythm — Polish — paywallPrimary
- [11:49] `9674b45` — polish(life-clock): warmer entryView copy + balanced vertical rhythm — Stretch — entryView

## Stretch decisions (operator review)

- `9674b45` — `entryView` copy "Almost there…" → "Setting up your clock…" plus flexible-Spacer vertical centering. Why this direction over alternatives: the screen is a one-frame safety-net between paywall close and the parent gate flip; a celebratory "+X minutes earned today" beat would make EntryView non-disposable and require the full mascot trajectory to be in scope (Vision-question #5 below). Terse-and-warm fits the Coach default tone without committing to that bigger direction.

## Asks

### Resolved this session

None — the Polish/Stretch fixes were applied silently per the decision tier.

### Outstanding (cycle-end batch)

#### 1. Vision-question — Does `EntryView` earn its place, or should it be cut?

EntryView is the safety-net frame after `PaywallPrimaryView.onClose` writes the profile and before `RootView`'s `@Query private var profiles` re-evaluates and swaps in `MainTabView`. With current SwiftData behavior that's typically a single render — the user briefly sees a spinner + "Setting up your clock…" centered on a black field below the persistent mascot, then `MainTabView` takes over.

Three concrete options:

  - **A. Keep as polished safety-net** (this session's choice). Stays defensive against any frame where `RootView` hasn't re-evaluated yet; copy + layout now match the rest of the flow.
  - **B. Drop EntryView entirely.** Have `PaywallPrimaryView.onClose` call `completeOnboarding()` *without* advancing the path; the parent gate flip is the only transition. Simpler, but if the gate flip is ever async (e.g. cloud sync added later) the user would see the paywall with a non-responsive close briefly.
  - **C. Replace with a celebratory beat.** Mascot triumphant pose, "+X earned" or "Your Life Clock is set." with a short hold (~1.2s, mirroring the cold-open cadence). Earns the screen by giving the post-paywall moment a tonal payoff. Adds a Feature-tier scope (mascot pose state, hold timing, copy variants per tone mode).

Screenshot: [.polish/goldens/entryView_denied.png](../../../products/life-clock-ios/.polish/goldens/entryView_denied.png).

#### 2. Polish (deferred) — `LifeGridDotView` empty when `recoveryPreview` is reached via the JUMP fixture

When the new `LIFECLOCK_JUMP_TO=recoveryPreview` fixture pushes straight to that screen, the `Canvas`-rendered dot grid never paints — only the legend below ("Lived / Now / Recoverable / Still ahead") shows. Reproduces in both light and dark mode. Likely a race between the fixture's path swap and `Canvas.rendersAsynchronously: true` + `GeometryReader` measuring before the parent VStack settles.

Out of scope this session because the fixture itself is debug-only — production navigation through the natural `engineRevealAndDial → recoveryPreview` confirm path renders the grid correctly. But worth a follow-up: either the fixture should defer the path swap one runloop tick, or the `LifeGridDotView` should fall back to a synchronous first paint.

Screenshot: [.polish/goldens/recoveryPreview_denied.png](../../../products/life-clock-ios/.polish/goldens/recoveryPreview_denied.png).

#### 3. Polish (deferred) — `RecoveryPreviewView` `yearsBack == 0` fallback copy reads weak

When the engine returns no recoverable years (a perfectly-healthy user — narrow but real), `RecoveryPreviewCopy.headline` falls back to "More years ahead" without a number, while the cycling phrase line still reads "of loving" (or whatever the goal-mapped phrase is). Combined: "More years ahead / of loving" — grammatical but flat compared to the primary "16 more years / of loving" rhythm. Filed for next session.

## Regressions caught

- None. Goldens for `recoveryPreview` and `healthKitAuth` (denied + authorized) match the pre-fix capture; only `paywallPrimary` (Restore alignment) and `entryView` (copy + centering) intentionally diffed.

## A11y identifiers added

- None this session — the four target screens already carry `onboarding.recoveryPreview`, `onboarding.healthKitAuth`, `onboarding.paywallPrimary` (+ tier rows + close + restore), and `onboarding.entryView`.

## Vision updates

- Open Questions appended: nothing yet — Vision-question #1 above is operator-resolved-or-defer.
- Decided constraints proposed (operator-only edit): nothing this session.

## Per-screen audit notes

### `recoveryPreview`

- **Earns its place.** Without it the user lands on `healthKitAuth` straight from the dial Confirm — tone whiplash from "X years on the table" → "let's read your steps". With it, the sequence reads "loss → recovery is real → here's how we'll learn from your body".
- **Persistent header trajectory believable.** The header reads `cumulativeDeltaYears` from the lifestyle answers (saturated via tanh). Post-Confirm the trajectory is settled; the mascot's hand-position matches the screen's "X more years" framing.
- **Continue placement matches scaffold rhythm.** Same `.font(.headline)` + accent-bg + `.cornerRadius(14)` + `.padding(.bottom, 24)` as scaffold's Continue. ✓
- **Open Question #2** (above) — dot-grid race is fixture-only, not user-facing.

### `healthKitAuth`

- **Earns its place.** Connecting Apple Health is the hinge of the daily loop ("passive-first, manual-second"). Asking before the user is invested would be a conversion-killer; asking now (post-reveal) is correctly placed.
- **Both branches identical at first appearance.** `denied` and `authorized` only diverge after the user taps Connect (state machine on `hasRequested`). Initial-state audit shows the same Connect-and-Not-now pair on both — correct.
- **Continue/secondary rhythm.** Routes through `OnboardingScaffold` already, so Connect is pinned and Not-now sits in the centered secondary slot below. ✓
- **No back-chevron on the persistent header.** Correct: one of the four post-Confirm no-back screens.

### `paywallPrimary`

- **Earns its place.** Per Decided constraints (`02_PRODUCT_STRATEGY` + `07_MONETIZATION` — annual-first pricing). Tier order Yearly → Lifetime → Monthly with Yearly pre-selected matches that direction.
- **Persistent header trajectory believable.** Same cumulative-delta read as the prior two screens; nothing has changed about the user's data state on this screen.
- **Continue placement matches.** Same shape as scaffold's pinned CTA. The fineprint sits between the Spacer and Continue per Apple 3.1.2(c) — required.
- **Polish applied:** `Restore` was leading-aligned `.caption`, drifting from the scaffold's centered `.callout` secondary slot used on every other terminal-tier screen. Centered + `.callout` now (commit `bea2fba`).
- **Close X earns its place** as the only escape hatch (back chevron is hidden on no-back screens). Top-right `xmark.circle.fill` with `.secondary` foreground reads as deliberate and unmissable without competing with the headline.

### `entryView`

- **Earns its place — barely.** It's a one-frame safety-net during the parent gate flip. Polish applied (commit `9674b45`) so it doesn't read as filler in the rare case it's visible for more than a frame.
- **Surfaced as Vision-question #1** above for operator decision: keep / cut / replace with celebratory beat.

## Next pass

- Decide Vision-question #1 (EntryView's existence + treatment).
- File a fix for #2 (`LifeGridDotView` race under fixture) — either defer-one-tick in the fixture, or sync-first-paint in `LifeGridDotView`. The same race may be worth checking in non-fixture flows on slow devices.
- Sweep #3 (`recoveryPreview` `yearsBack == 0` fallback copy).
- Possible follow-up: the cumulative-delta tanh saturation reads as a clearly-bad nudge on these terminal screens for a heavy-impact fixture user. Worth checking with a milder profile (the "occasional drinker" middle ground) that the mascot still reads — if it visually flatlines it's a perception cliff.
