# Plan — Life Clock quest completion payoff (Q14, A + B + C unified reward)

> **Status:** Draft for operator review. Surfaced 2026-05-09 after operator chose A + B + C in the simulator-driven-polish vision-notifications-audit follow-up. **Does not ship yet.** This plan is the artifact to align on before the implementation session begins.
>
> **Sources:** vision Open Question #14 (origin: Codex polish session 2026-05-08), [polish-2026-05-08-vision-today-completion-payoff.md](../products/life-clock/polish-2026-05-08-vision-today-completion-payoff.md), code investigation 2026-05-09.
>
> **Revision 2 (2026-05-09):** Operator chose persist-banked over settle-back. The clock state should reflect the user's completed quests for the rest of the day; uncheck visibly retracts. State machine simplified accordingly; Q-plan-1 closed. See "Behavior model — persist-banked" below.

---

## Goal

Close the "feels like a checkbox, not felt time" gap on daily quest completion. When the user taps a quest action complete, the reward should be felt (mascot + clock motion), seen (clock-hand advance + headline number), and read (tone-keyed micro-copy) — without corrupting the model truth that the canonical headline delta is health-and-habit-only.

## Critical model-truth finding (load-bearing for B)

`ClockEngine.calculateDailyDelta` ([ClockEngine.swift:348](../../products/life-clock-ios/Sources/Engines/ClockEngine.swift)) reads only `DailyHealthSnapshot` + `HabitLog`. It builds fresh `TimeLedgerEntry` rows at compute time but **never reads** existing rows from SwiftData.

Therefore:

- The **canonical headline delta** today is a **health + habit** delta (e.g. +28). This is the model truth and never changes due to user actions on the Today screen.
- A completed quest's `rewardEstimateMinutes` (e.g. +18) is a **projection** of what the action might contribute *to tomorrow's* delta via downstream HK signal (steps, sleep, etc.).
- The **visible headline number** (what the user sees) = canonical + sum of completed-quest rewards for today. This is "trajectory if you follow through," not prophecy. The model truth is recoverable by inspection (the canonical is computed from snapshots; the overlay is computed from `Quest.completedAt`).
- The day boundary resets the overlay — tomorrow's quests are fresh `Quest` instances with `completedAt == nil`. Yesterday's gaming doesn't poison today.
- This is honest because the user can see what they've committed to (clock high) and tomorrow's clock will reflect what their body actually delivered (HK signal validates or doesn't).

## Behavior model — persist-banked

**The visible headline delta + mascot hand position track this formula at all times:**

```
visibleDelta = canonicalDelta + completionOverlay
completionOverlay = Σ rewardEstimateMinutes for today's quests where completedAt != nil
```

| Event | What happens to the visible clock |
|---|---|
| App opens (cold launch or foreground) | Wake animation: count up from 0 → `visibleDelta` over 1.0s. Includes any already-completed quests from earlier in the day. |
| User checks a quest | Mascot hand animates from current `visibleDelta` to new `visibleDelta` (existing `.interpolatingSpring()`). Mascot pulse fires (A). Tone copy fades in (C). Success haptic on settle. |
| User unchecks a quest | Mascot hand animates from current `visibleDelta` to new (lower) `visibleDelta`. **No pulse, no tone copy, no success haptic** — uncheck is undoing, not winning. Light "selection" haptic only. |
| App backgrounded mid-day, re-foregrounded | Wake fires again, count-up to (canonical + currently-completed-overlay). Reflects in-day persistence correctly. |
| Day rolls over while app is open (rare) | New canonical recomputes (might be 0 at midnight + a few minutes). Today's quests refresh — the now-fresh quests have `completedAt == nil` → overlay = 0. Mascot animates from yesterday-end-state to today-fresh-state via the existing spring. No special-case code; the state derivation handles it. |
| Day rolls over while app is closed | App relaunch goes through cold-launch → wake fires against today's canonical + today's completed quests (none yet) → overlay = 0. Yesterday's banked is gone, as expected. |

## Scope

In-scope:

- **A — Mascot pulse** on completion (520ms scale + warm highlight respecting lighting convention).
- **B — Clock hand advance** by `quest.rewardEstimateMinutes`, then settle back to canonical with a clear ease.
- **C — Tone-aware support-card payoff line** for Gentle / Coach / Firm-Direct, replacing the hardcoded `"Possible impact: +18 min."`.
- Three-way unified timeline + state machine handling tap, undo, multi-completion, Reduce Motion, wake-animation-in-flight.
- ToneMode key: `questCompletionPayoff(minutes: Int) -> String`.
- Tests: ToneMode strings, snapshot of mascot state (Reduce Motion on/off), undo path, multi-completion path.

Out of scope:

- Persistent "banked for tomorrow" indicator (file as separate Stretch finding).
- Re-engagement notifications (Decided: not in v1).
- F9 (Profile reminder toggle no-op on `.notDetermined`) — separate Polish ship.
- Engine-level changes that would let the headline delta include completed-quest rewards (would require a new model concept "earned-today vs. forecasted-tomorrow"; too large to bundle).

## Non-negotiable constraints (from Decided)

- **Lighting convention** — opacity 0.22, offset ratio (0.35, 0.85), radius ratio 0.55× of reference size. World-fixed via inverse-rotation math for rotating elements. Source: vision Decided constraints + operator memory `feedback_life_clock_lighting_convention.md`.
- **Trajectory, not prophecy** — the canonical headline delta must not silently include forecasted quest rewards.
- **Default is motivating, not punishing** — the payoff sequence must not feel celebratory in a way that mocks a still-negative day. On a −90 day, completing a quest should feel like recovery, not victory.
- **Three tone modes; Coach default** — three copy variants required for C; no fourth.
- **Persistent mascot header / wake animation cadence** — `feedback_life_clock_wake_animation.md` says wake plays on EVERY app open (cold + foreground). The completion sequence must compose with this, not stack ugly.

## Architecture

### Single source of truth for the displayed delta (extend, don't replace)

Today's ([TodayView.swift:37](../../products/life-clock-ios/Sources/Features/Today/TodayView.swift)):

```swift
private var displayedDelta: Int {
    let real = store.todayEstimate?.dailyTimeDeltaMinutes ?? 0
    return Int((Double(real) * wakeProgress).rounded())
}
```

Becomes:

```swift
private var completionOverlay: Int {
    // Sum of rewardEstimateMinutes for today's quests where completedAt is set.
    // Derived; not @State. Recomputes when store.quests or store.toneMode changes.
    let dayStart = store.clock.calendar.startOfDay(for: store.clock.now())
    return store.todayQuests
        .filter { quest in
            guard let completedAt = quest.completedAt else { return false }
            return store.clock.calendar.isDate(completedAt, inSameDayAs: dayStart)
        }
        .map(\.rewardEstimateMinutes)
        .reduce(0, +)
}

private var displayedDelta: Int {
    let real = store.todayEstimate?.dailyTimeDeltaMinutes ?? 0
    return Int(((Double(real) + Double(completionOverlay)) * wakeProgress).rounded())
}
```

`completionOverlay` is **derived state, not stored state.** No `@State`, no manual ramp-up/ramp-down logic, no day-boundary clearing code. The store's existing observable mechanism (Quest changes via `toggleQuestCompletion`) re-fires `displayedDelta` recompute, and `LifeClockMascotView`'s existing `.animation(.interpolatingSpring(), value: minutesDelta)` handles the visual transition.

This is dramatically simpler than the settle-back state machine. Mascot animation is "free" via the existing spring; we only add the pulse + tone copy on TOP for the check path.

### Animation timeline (simplified by persist-banked)

The persist-banked model collapses the state machine. There's no "settle back" phase, because the overlay doesn't go back. The mascot's existing `.interpolatingSpring(value: minutesDelta)` does most of the work for free.

**Check path** (user ticks a quest):

| Phase | Duration | What happens |
|---|---|---|
| t = 0 | — | Light haptic on tap. `quest.completedAt = now` writes to SwiftData. Derived `completionOverlay` recomputes; `displayedDelta` increases. |
| t = 0–520ms | 520ms | Mascot hand springs from old `displayedDelta` to new (the existing `.interpolatingSpring()` handles this). Concurrently, the mascot pulse fires (scale 1.00→1.045→1.00 over 520ms) and the lighting-convention warm highlight ramps in to opacity 0.22 over the first 200ms, holds, fades over the last 200ms. |
| t = 520ms | — | Pulse settles, highlight gone. Hand at new resting position. Success haptic. Tone-keyed copy fades in on the support card (200ms cross-fade). |
| t = 720–3120ms | 2.4s | Tone copy visible. Static support-card text held. |
| t = 3120ms | 200ms | Tone copy fades out, support card returns to its default `"Added to your progress log."` line. |

Total perceived motion: ~520ms. Total reward window (motion + copy): ~3.1s.

**Uncheck path** (user un-ticks a quest):

| Phase | Duration | What happens |
|---|---|---|
| t = 0 | — | Light selection haptic on tap (default toggle haptic). `quest.completedAt = nil` writes to SwiftData. Derived `completionOverlay` recomputes; `displayedDelta` decreases. |
| t = 0–520ms | 520ms | Mascot hand springs from old `displayedDelta` down to new (existing `.interpolatingSpring()`). **No pulse, no warm highlight, no tone copy, no success haptic.** Uncheck is undoing, not winning. The clock visibly retracts. |

Total perceived motion: ~520ms. No copy window. The visible retraction IS the message.

### Edge cases

| Case | Behavior |
|---|---|
| **Undo mid-pulse** (user un-ticks during the 520ms pulse) | `quest.completedAt = nil`, derived overlay recomputes, mascot springs to new lower value. The in-flight pulse keyframe finishes its scale return-to-1.0 (don't cancel mid-keyframe; looks janky). The warm highlight fades on its existing schedule. Tone copy is dismissed if it had started fading in. No success haptic if not yet fired. |
| **Second completion during pulse** | Skip the second pulse (no double-pulse, looks chaotic). Hand spring already handles the second advance via the new `displayedDelta`. Tone copy: replace the staged copy with the second quest's payoff (single line, latest wins). |
| **Reduce Motion ON** | A: no pulse keyframe. Mascot scale stays 1.0. B: the mascot's `.interpolatingSpring(value: minutesDelta)` becomes `nil` already via the existing `reduceMotion ? nil : .interpolatingSpring()` line — hand snaps to new position with no animation. C: copy fades in/out unchanged (cross-fades aren't affected by Reduce Motion per Apple's guidance). Haptics unchanged. The visible retraction on uncheck is still snap-to-new-position. |
| **Wake animation in flight** | The completion's mascot pulse defers until `wakeProgress == 1`. The `displayedDelta` recompute is fine (the formula composes), so the underlying value is correct mid-wake; only the pulse + tone copy fire after wake settles. This means a user who taps mid-wake sees the count-up land at the new (with-overlay) value, then the pulse fires on top. |
| **Quest with rewardEstimateMinutes = 0** | Mascot doesn't move (overlay didn't change). Skip the pulse, skip the tone copy (no payoff to read). Checkbox flips, support card stays at its default text. Light haptic on tap (the default toggle haptic). |
| **Mascot already off-screen** (user scrolled down to questsCard) | Pulse + spring fire regardless; user sees the support card's tone copy. When they scroll back up, the mascot is at its new resting position. No retroactive pulse. |
| **Tab-switch mid-sequence** | The pulse + tone copy are tied to TodayView's lifetime. On tab-switch back, no replay. The mascot is at its current resting position (which reflects all completions made so far today). |
| **App backgrounded mid-sequence** | Same as tab-switch. Mascot is correct via the `displayedDelta` formula on re-foreground; wake animation re-fires the count-up to the (canonical + overlay) state. No retroactive pulse. |

### Lighting-convention adherence (A)

The warm highlight is a `Color.orange.opacity(0.22)` (or palette-specific warm tint, gated by `palette.accent` for `auroraCool`/`sunsetWarm`) rendered as a radial gradient:

- Center offset from mascot center: `(size * 0.35, size * 0.85)` — the convention's offset ratio.
- Radius: `size * 0.55`.
- World-fixed via inverse-rotation math during the mascot's rotation transform (the highlight should NOT spin with the bezel; it's a surface-light, not a body-light).
- Opacity: 0.22 throughout the pulse; do not crossfade the opacity itself, only the geometry.

This matches the operator memory spec exactly. No new constants introduced.

### Tone copy (C) — concrete strings

Add to `ToneMode.swift`:

```swift
func questCompletionPayoff(minutes: Int) -> String {
    let formatted = TimeDeltaFormatter.format(minutes: minutes)  // "+18 min", "−12 min", etc.
    switch self {
    case .gentle:
        return "You bought back \(formatted) today."
    case .coach:
        return "Banked: \(formatted)."
    case .firmDirect:
        return "\(formatted). Logged."
    }
}
```

The support card's `detail` line in `SupportMomentPresenter.swift:38` switches from:

```swift
"Added to your progress log. Possible impact: \(TimeDeltaFormatter.format(minutes: rewardMinutes))."
```

to:

```swift
toneMode.questCompletionPayoff(minutes: rewardMinutes)
```

The pre-existing static line ("Added to your progress log. Possible impact: …") fades back in after the 2.4s tone-copy window. This means the user sees the tone-keyed copy briefly, then the static factual copy. Two layers of communication.

## Test plan

| Test | What it pins |
|---|---|
| `ToneModeTests.questCompletionPayoff` | Three tone variants are distinct + non-empty; format string includes the `TimeDeltaFormatter` output verbatim. |
| `ToneModeTests.questCompletionPayoff_negativeMinutes` | Formatter handles negative reward (rare but possible — a deload-day quest with negative reward shouldn't crash). |
| `TodayViewSnapshotTests.payoff_idle` | Baseline; nothing animating. |
| `TodayViewSnapshotTests.payoff_advancing_reduceMotionOff` | Mid-pulse, mascot scaled, lighting highlight visible, hand advanced. |
| `TodayViewSnapshotTests.payoff_advancing_reduceMotionOn` | No pulse, hand at peak, lighting highlight off. |
| `TodayViewSnapshotTests.payoff_settling` | Hand returning, copy fading in. |
| `TodayViewIntegrationTests.undoMidSequence` | Tap, un-tick within 300ms, assert `completionOverlay == 0`, no success haptic, ledger entry gone. |
| `TodayViewIntegrationTests.multiCompletion` | Tap quest 1, tap quest 2 within 200ms, assert overlay = reward1 + reward2 at peak, single tone copy line (latest), single mascot pulse. |
| `TodayViewIntegrationTests.deferDuringWake` | Force wake in flight, tap, assert sequence does not start until `wakeProgress == 1`. |
| `TodayViewIntegrationTests.zeroRewardQuestSkipsSequence` | Tap a `rewardEstimateMinutes = 0` quest, assert no overlay change, no haptic, no tone copy switch. |

Test coverage for the existing wake animation is already in place; do not break it.

## Implementation order (the actual session)

The Q14 polish session should land changes in this order to keep each commit independently reviewable. **Persist-banked dramatically simplifies B** (just a derived computed property, no state machine), so the order changes vs. the original draft.

1. **Commit 1 (Polish):** add `ToneMode.questCompletionPayoff(minutes:)` + tests. No UI change yet. Three tone-keyed strings per Q-plan-4 resolution.
2. **Commit 2 (Feature):** introduce `completionOverlay` derived computed property + extend `displayedDelta` formula. **B ships here.** The mascot's existing `.interpolatingSpring()` animator picks up the input change automatically. Both check and uncheck paths now visibly move the clock. No haptics or pulses yet — just the math.
3. **Commit 3 (Stretch):** wire `SupportMomentPresenter` to use the new tone copy. Hardcoded `"Possible impact:"` line removed. Tone copy fades in/out per timeline. **C ships here**, layered on B's visible clock movement.
4. **Commit 4 (Feature):** mascot pulse keyframe + lighting-convention warm highlight. Fires only on the **check** path, not uncheck. **A ships here.**
5. **Commit 5 (Stretch):** edge cases — undo-mid-pulse, second-completion-during-pulse, wake-defer, zero-reward, scrolled-off-mascot. Each as a small named test if not already covered.
6. **Commit 6 (Polish):** any consolidation / cleanup discovered during the session. Refactor only.

C is no longer the standalone first commit because under persist-banked, the visible clock movement (B) is the load-bearing change and C's tone copy reads better with B already in place. Order optimized for "each commit ships something visibly working."

Approximate LOC: ~30 (C) + **~30 (B — much smaller now, derived not state)** + ~80 (A) + ~50 (edge cases) = **~190 LOC** across product code, plus ~120 LOC of tests. One simulator-driven-polish session, mode `freeform-polish`, iteration cap 8, mandatory final-check.

## Open questions for the operator before we ship

These are the calls I'd like you to make explicitly before the implementation session starts. None block the plan; all sharpen it.

**~~Q-plan-1 — Settle-back vs. persist-banked.~~** **RESOLVED 2026-05-09 — persist-banked.** Operator described uncheck-changes-clock behavior, which only makes sense under persist-banked. Plan revised throughout. The visible headline + mascot now track `canonical + completionOverlay` for the rest of the day; day boundary clears overlay via the per-day Quest model.

**Q-plan-2 — Hand advance peak target if `rewardEstimateMinutes` exceeds the mascot's ±120 visual cap.** Rare (no shipped quest exceeds 60), but a future quest reward of +180 would saturate the visual sweep. Under persist-banked, this also applies to the **cumulative** overlay (e.g. three +50 quests = +150). Behavior options: (a) clamp the visible hand to 120 but let the headline number show the true total, (b) extend the cap dynamically for in-session animations, (c) cap the hand at 120 and stop animating further completions past saturation. Recommendation: **(a) — clamp the hand at ±120, headline shows true total**. Matches the existing convention (the numeric readout is source of truth past the cap, per `LifeClockMascotView` comment). Document in the polish session.

**Q-plan-3 — On a deeply negative day (−90 min), should completion still advance the hand to a less-negative number?** Yes. A −90 day with a +18 quest moves to −72 and stays there until further completions or unchecks. The motion itself is the message: "you have agency even on bad days." Recommendation: **yes, identical behavior on negative days**. Aligns with "default is motivating, not punishing."

**Q-plan-4 — Should the tone copy mention "tomorrow"?** Three options for the support-card payoff line:
- **Reward-focused** (current spec): Gentle "You bought back +18 minutes today." / Coach "Banked: +18 min." / Firm-Direct "+18 min. Logged."
- **Tomorrow-focused**: Gentle "You earned +18 minutes on tomorrow's clock." / Coach "+18 min toward tomorrow." / Firm-Direct "+18 min. Tomorrow."
- **Today-focused** (matches the persist-banked visual): Gentle "Your clock just moved +18 minutes." / Coach "+18 min on the clock." / Firm-Direct "+18 min. On the clock."

Under persist-banked, the visible clock literally moves. **Today-focused** copy matches what the user just saw happen. **Reward-focused** is generic and works regardless of model. **Tomorrow-focused** is model-correct but reads as deferred-gratification when the visual is immediate. Recommendation: **today-focused**, because the copy should describe what the user is seeing on screen.

**Q-plan-5 — Should A (mascot pulse) fire even when the mascot is scrolled out of view?** The pulse keyframe fires regardless; user sees the support card payoff in scroll-down position. Recommendation: **fire regardless**. No gating logic.

**Q-plan-6 (NEW) — Should the headline number show a breakdown when there's a non-zero overlay?** Three options:
- (a) Just the visible number: "+46 min today." Caption stays on the canonical message.
- (b) Visible number + small caption: "+46 min today" with subtitle "+18 from completed actions."
- (c) Two lines: "+28 today, +18 banked" — explicit split.

(a) is the simplest, matches the operator's mental model of "the clock IS the user's day." (b) adds transparency for users who want to know why the number jumped. (c) is the most explicit but visually busiest. Recommendation: **(a) for the initial ship; (b) as a Stretch toggle in Profile if users get confused.**

**Q-plan-7 (NEW) — Day-boundary edge case while app is open past midnight.** Rare. The persist-banked model auto-clears at midnight because today's `Quest` instances become yesterday's `Quest` instances and today's fresh quests have no completion state. Behavior on the rollover transition:
- Mascot animates from yesterday-end to today-fresh via existing spring (could be a noticeable jump — e.g. yesterday's +46 to today's +0 morning).
- Acceptable? Or should we suppress the jump until next foreground (the user is unlikely to be watching the screen at midnight)?

Recommendation: **let the spring handle it.** A user who's awake watching at midnight sees their day reset; the visual matches reality. Suppressing would create a state-vs-display divergence we'd then have to reconcile.

## Risks and what could go wrong

- **Animation timing tuning is iterative.** 520ms / 350ms / 250ms are starting points; they may need to be 480 / 400 / 280 after live-feel review. Plan budget for two iterations of operator-feel review during the session.
- **Multi-completion semantics could surprise.** The "skip the second pulse, sum the overlays" behavior is a judgement call. If you'd rather have the mascot pulse on every completion (more reward), the implementation flips one boolean. Easier to start strict and loosen later.
- **Lighting-convention highlight on the mascot bezel.** The static bezel asset (`ClockMascotBezel`) is what's normally rendered. The warm highlight needs to render *over* the bezel, masked to the bezel's circular area. SwiftUI's `.mask(Circle())` should handle this; if not, the SwiftUI fallback face path is the alternative.
- **Reduce Motion fallback for B is non-obvious.** Showing the felt potential as a "jump → hold → jump back" may itself feel jarring for a Reduce Motion user. Alternative: skip B entirely under Reduce Motion (no overlay change), let A's haptic + C's copy carry the moment. Lean toward this if the snap reads bad in testing.
- **The `.interpolatingSpring()` already on `LifeClockMascotView` may double-animate** when paired with the explicit `.animation(...)` we add for `completionOverlay`. Test for stutter; may need to use `.transaction { $0.animation = ... }` to scope explicitly.

## Definition of done

- A + B + C implemented per the timeline + state machine above.
- Five tests in the table above passing on iPhone 17 simulator.
- One golden screenshot per phase saved at `products/life-clock-ios/.polish/goldens/quest-completion-payoff/<phase>.png`.
- Final-check (mandatory in the polish session) drives a real completion in all three tones, validates haptics, validates Reduce Motion, validates undo.
- PR body derived from the polish session log; one commit per logical change per the implementation order above.
- No regressions in existing wake-animation behavior (tests still green).
- No mortality lexicon introduced in any new copy (sanity, given the notification rule).

## Carry-forward (not in this ship)

- Headline breakdown caption (Q-plan-6 option b) — Stretch, file as Profile toggle if user research surfaces confusion.
- The hand-advance behavior past the ±120 visual cap, once a quest reward forces the question (Q-plan-2).
- Day-boundary explicit reset animation if the spring-handles-it approach (Q-plan-7) reads bad in operator review.
- F9 (Profile reminder toggle no-op) — separate Polish session, unrelated to Q14.
