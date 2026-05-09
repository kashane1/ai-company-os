# Plan — Life Clock quest completion payoff (Q14, A + B + C unified reward)

> **Status:** Draft for operator review. Surfaced 2026-05-09 after operator chose A + B + C in the simulator-driven-polish vision-notifications-audit follow-up. **Does not ship yet.** This plan is the artifact to align on before the implementation session begins.
>
> **Sources:** vision Open Question #14 (origin: Codex polish session 2026-05-08), [polish-2026-05-08-vision-today-completion-payoff.md](../products/life-clock/polish-2026-05-08-vision-today-completion-payoff.md), code investigation 2026-05-09.

---

## Goal

Close the "feels like a checkbox, not felt time" gap on daily quest completion. When the user taps a quest action complete, the reward should be felt (mascot + clock motion), seen (clock-hand advance + headline number), and read (tone-keyed micro-copy) — without corrupting the model truth that the canonical headline delta is health-and-habit-only.

## Critical model-truth finding (load-bearing for B)

`ClockEngine.calculateDailyDelta` ([ClockEngine.swift:348](../../products/life-clock-ios/Sources/Engines/ClockEngine.swift)) reads only `DailyHealthSnapshot` + `HabitLog`. It builds fresh `TimeLedgerEntry` rows at compute time but **never reads** existing rows from SwiftData.

Therefore:

- The +28 headline today is a **health + habit** delta.
- A completed quest's `rewardEstimateMinutes` (e.g. +18) is a **projection** of what the action might contribute *to tomorrow's* delta via downstream HK signal (steps, sleep, etc.).
- Animating the clock to +46 and STAYING there overstates today's settled state — that drifts toward "prophecy, not trajectory" (a Decided constraint).
- Animating to +46 and SETTLING BACK to +28 is honest if the visual makes "felt potential vs. settled today" legible.

The plan below lands on settle-back. A persistent "Banked: +18 min for tomorrow" indicator could optionally live elsewhere (queued, not in scope for this ship).

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
@State private var completionOverlay: Int = 0  // ramps 0 → reward → 0 during the payoff sequence

private var displayedDelta: Int {
    let real = store.todayEstimate?.dailyTimeDeltaMinutes ?? 0
    return Int(((Double(real) + Double(completionOverlay)) * wakeProgress).rounded())
}
```

`completionOverlay` is the in-session "felt time" surcharge. It composes correctly with `wakeProgress` so a completion that fires during a wake animation still scales with the count-up. Settled state has `completionOverlay = 0`; the headline always reflects model truth.

### State machine

`@State private var payoff: PayoffState = .idle` on TodayView:

```
enum PayoffState {
    case idle
    case advancing(quest: Quest, startedAt: Date)
    case holding(quest: Quest)
    case settling(quest: Quest)
    case copyVisible(quest: Quest, until: Date)
}
```

Transitions (durations chosen for legibility on a 60Hz device):

| Phase | Duration | What happens |
|---|---|---|
| `.idle → .advancing` | t = 0 | Light haptic. `completionOverlay` springs to `quest.rewardEstimateMinutes` over 520ms. Mascot pulse keyframe fires (scale 1.00→1.045→1.00, lighting-convention warm highlight ramps in). Tone-keyed copy is staged but not yet shown. |
| `.advancing → .holding` | t = 520ms | Hand and overlay rest at peak. Heartbeat continues at 30Hz. Tone copy still hidden. |
| `.holding → .settling` | t = 870ms (350ms hold) | `completionOverlay` springs back to 0 over 250ms. Tone copy fades in at the start of this phase, anchored to the support card. Success haptic on settle. |
| `.settling → .copyVisible` | t = 1170ms | Hand at canonical. Tone copy fully visible. Hold for 2.4s. |
| `.copyVisible → .idle` | t = 3570ms | Tone copy fades to the existing static `"Added to your progress log."` line. Sequence ends. |

Total perceived motion: ~1.2s. Total reward window (motion + copy): ~3.6s.

### Edge cases

| Case | Behavior |
|---|---|
| **Undo mid-sequence** (user un-ticks before sequence ends) | `payoff → .idle`. `completionOverlay` snaps to 0 (no animation). Tone copy dismissed. Suppress success haptic if not yet fired. The toggle's `removeAll` of the TimeLedgerEntry is unchanged. |
| **Second completion during sequence** | Skip the mascot pulse (no double-pulse, looks chaotic). Update `completionOverlay` target by adding the second quest's reward (so hand advances from current peak to a new higher peak). Reset hold timer. Replace the staged tone copy with the second quest's copy. |
| **Reduce Motion ON** | A: no pulse. Mascot scale stays 1.0. B: no animation; `completionOverlay` jumps 0 → reward, holds 350ms, jumps back to 0. (Better UX than nothing — the user still sees the felt potential briefly.) C: copy fades in/out unchanged (cross-fades are not affected by Reduce Motion). Haptics unchanged. |
| **Wake animation in flight** | If `wakeProgress < 1`, defer the entire payoff sequence. The `displayedDelta` formula composes correctly so a deferred sequence layered on top of an in-flight wake still reads right, but the visual conflict (two count-ups simultaneously) is too noisy. Wait until `wakeProgress == 1` then start. |
| **Quest with rewardEstimateMinutes = 0** | Skip the sequence entirely. Tap → checkbox flips → support card unchanged. There's no felt potential to show. |
| **Mascot already off-screen** (user scrolled down to questsCard) | Sequence still fires; the user sees the support card payoff line. The visual completion + scroll-to-keep-row-visible behavior already centers the completed row, so the mascot pulse may be partially or fully off-screen. Acceptable — the payoff is the copy and haptic in this scroll position. |
| **Tab-switch mid-sequence** | Sequence cancels. State resets to `.idle` on next entry (don't replay; the user has already taken the action). |

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

The Q14 polish session should land changes in this order to keep each commit independently reviewable:

1. **Commit 1 (Polish):** add `ToneMode.questCompletionPayoff(minutes:)` + tests. No UI change yet.
2. **Commit 2 (Stretch):** wire `SupportMomentPresenter` to use the new tone copy when the moment is `.questCompleted`. Hardcoded `"Possible impact:"` line removed. Visible tone-aware copy on completion. **C ships standalone here.**
3. **Commit 3 (Feature):** introduce `completionOverlay: Int` state + extend `displayedDelta` formula. Drive overlay 0 → reward → 0 with the timeline above. **B ships here.** The mascot's existing `.interpolatingSpring()` animator picks up the input change automatically.
4. **Commit 4 (Feature):** mascot pulse keyframe + lighting-convention warm highlight. **A ships here.**
5. **Commit 5 (Polish):** state machine consolidation if commits 3+4 ended up with redundant timing logic. Refactor only; no behavior change.
6. **Commit 6 (Stretch):** edge cases — undo, multi-completion, defer-during-wake, zero-reward skip. Each as a small named test if not already covered.

This way C ships first as the cheapest win (≈30 LOC + 2 tests, can ship even if B/A run into trouble); B ships second on top of C; A composes on B's foundation.

Approximate LOC: ~30 (C) + ~80 (B) + ~80 (A) + ~40 (edge cases) = **~230 LOC** across product code, plus ~150 LOC of tests. One simulator-driven-polish session, mode `freeform-polish`, iteration cap 8, mandatory final-check.

## Open questions for the operator before we ship

These are the calls I'd like you to make explicitly before the implementation session starts. None block the plan; all sharpen it.

**Q-plan-1 — Settle-back vs. persist-banked.** The plan settles `completionOverlay` back to 0 (the canonical health-only delta). An alternative: keep `completionOverlay` at the cumulative reward total *for the rest of the session*, with a small "Banked for tomorrow: +18 min" caption. Reading: settle-back is honest-but-fleeting (the felt moment is the moment); persist-banked is honest-but-louder (an in-session reminder of agency). My recommendation: **settle-back**, because the canonical Today screen should always tell the same model story. Persist-banked is a future Stretch surface, not part of A+B+C.

**Q-plan-2 — Hand advance peak target if `rewardEstimateMinutes` exceeds the mascot's ±120 visual cap.** Rare (no shipped quest exceeds 60), but a future quest reward of +180 would saturate the visual sweep. Behavior options: (a) clamp to 120 (matches current cap), (b) extend the cap dynamically for the in-session animation, (c) skip the hand advance and let only A+C fire. Recommendation: **(a) clamp to 120**, document, ignore until a future quest forces the question. Smallest surprise.

**Q-plan-3 — On a deeply negative day (−90 min), should completion still pop the hand to a less-negative number?** Yes — the gesture is "this action moves you up." A −90 day with a +18 quest pops to −72, holds, settles back to −90. The motion itself is the message: "you have agency even on bad days." Recommendation: **yes, identical behavior on negative days**. Aligns with "default is motivating, not punishing" and "every negative delta paired with an actionable next step."

**Q-plan-4 — Should the tone copy mention "tomorrow"?** The current spec is reward-focused ("Banked: +18 min."). A more model-honest version would say "+18 min on tomorrow's clock." More honest; longer; loses some snap. Recommendation: **stay reward-focused** for the in-the-moment payoff; let the persistent static line ("Added to your progress log.") carry the model framing. The user reads the felt copy first, then the model copy underneath.

**Q-plan-5 — Should A+B+C all fire even when the mascot is scrolled out of view?** Currently the completion path scrolls Today to keep the completed row visible — which often pushes the mascot off-screen. The pulse + hand sweep fire whether visible or not (no perf cost; no visual lie). The user mostly sees the support card payoff in this case. Recommendation: **fire regardless of visibility**. Don't add scroll-position gating logic.

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

- Persistent "banked for tomorrow" indicator (Stretch).
- The hand-advance behavior past the ±120 visual cap, once a quest reward forces the question.
- Q-plan-1 if the operator changes the answer post-ship.
- F9 (Profile reminder toggle no-op) — separate Polish session, unrelated to Q14.
