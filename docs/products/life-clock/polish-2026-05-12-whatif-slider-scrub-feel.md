# Polish Session — life-clock — 2026-05-12 — whatif-slider-scrub-feel

## Mode

`freeform-polish`. Tier: **new-surface (post-audit feel pass)**.

Surfaces in scope: [WhatIfSlider.swift](../../../products/life-clock-ios/Sources/Features/Future/WhatIfSlider.swift), [TrajectoryChart.swift](../../../products/life-clock-ios/Sources/Features/Future/TrajectoryChart.swift) (re-renders during scrub).

Observer lenses (per brainstorm-backlog item #3):
- **(a) Haptic policy** — which `UIImpactFeedbackGenerator` weight fires when, is `.selection` per-tick or only at thresholds?
- **(b) Reduce Motion path** — does the chart morph or snap on touch-up? Does the slider thumb still drag, or does it switch to a stepper at AX large?
- **(c) Frame budget** during continuous scrub — Instruments trace on iPhone 17 Pro.
- **(d) Thumb-landing verification** — `JUMP_TO=futureCapReached/floorReached` seeds (PR #42 I4 fix).

Iteration cap (per brainstorm addendum): **6**. Final computer-use checkpoint: **yes — gestural feel is the test**. Iterations used: **5** (audit, draft, edit + fixture-fix, build, simulator). One iteration in reserve.

## Up-front corrections to the brainstorm

1. **"No polish log captures scrub feel" is correct.** Confirmed by `ls docs/products/life-clock/polish-* | grep -i whatif` → zero matches. This is the first polish session on the Future-tab slider.

2. **The brainstorm's framing — "specify the policy" — assumes a policy exists.** It doesn't. Code-level audit found **zero** `.sensoryFeedback` calls in [WhatIfSlider.swift](../../../products/life-clock-ios/Sources/Features/Future/WhatIfSlider.swift) before this session. The slider was tactilely silent — no per-tick `.selection`, no edge-trigger, no begin/end. Ask (a) is therefore a **create-the-policy** task, not a document-the-policy task. Shipped this session, not deferred.

3. **The brainstorm's "Reduce Motion stepper fallback" question is moot.** Native SwiftUI `Slider` drag is gestural input, not a SwiftUI animation — `accessibilityReduceMotion` doesn't affect it. The actual Reduce Motion bug is in [TrajectoryChart.swift:117](../../../products/life-clock-ios/Sources/Features/Future/TrajectoryChart.swift:117) — `.animation(isScrubbing ? nil : .smooth(duration: 0.18), value: points)` runs the snap-back animation **unconditionally on touch-up regardless of AX preference**. Fix is one line, not a stepper rewrite. The mid-scrub path was already `nil`-via-`isScrubbing` — correct by accident.

4. **`JUMP_TO=futureCapReached/floorReached` could not reach the slider via fixture before this session.** [FutureView.swift:90/114/168/185](../../../products/life-clock-ios/Sources/Features/Future/FutureView.swift) all gate every visible content branch on `profile.baselineHealthspanYears`. [LifeClockLaunchConfiguration.swift:427-441](../../../products/life-clock-ios/Sources/App/LifeClockLaunchConfiguration.swift) seeded `birthDate / biologicalSex / toneMode / sleepGoalHours / strengthFrequencyPerWeek / dietQualityBaseline / onboardingCompletedAt / disclaimerAcceptedAt` but **not** `baselineHealthspanYears` (nor the `anchorAdjustedAt / personalAdjustmentYears` prerequisites for `bootstrapV170Baseline` to compute it). Net effect: launching with the brainstorm-recommended `LIFECLOCK_JUMP_TO=futureCapReached + LIFECLOCK_FORCE_PRO=1 + LIFECLOCK_FUTURE_TAB_UNLOCKED=1` knobs landed on a blank Future tab. **Agent-native parity violation** caught during this run — fixed in [LifeClockLaunchConfiguration.swift:438-457](../../../products/life-clock-ios/Sources/App/LifeClockLaunchConfiguration.swift) (12 LOC, scoped to `futureJumpTo != nil` so legacy `scenario=.onboarded` callers that depend on a nil baseline keep their existing behavior).

## Iterations

| Time | Type | Tier | Surface | Result |
|---|---|---|---|---|
| 06:45 | (recon) | — | [WhatIfSlider.swift](../../../products/life-clock-ios/Sources/Features/Future/WhatIfSlider.swift), [TrajectoryChart.swift](../../../products/life-clock-ios/Sources/Features/Future/TrajectoryChart.swift), [LifeClockHaptics.swift](../../../products/life-clock-ios/Sources/Shared/LifeClockHaptics.swift) | Three findings: zero haptic wiring, Reduce Motion not consulted, seeded thumb positions land at directionally-extreme values not all-rail |
| 06:50 | (draft) | — | session notes | Three-event haptic policy proposed (begin/edge/end), no per-tick. Reduce Motion fix = 1 line. Operator approved all three asks via "best judgement call" |
| 06:55 | (edit) | feat | [LifeClockHaptics.swift](../../../products/life-clock-ios/Sources/Shared/LifeClockHaptics.swift), [WhatIfSlider.swift](../../../products/life-clock-ios/Sources/Features/Future/WhatIfSlider.swift), [TrajectoryChart.swift](../../../products/life-clock-ios/Sources/Features/Future/TrajectoryChart.swift) | 3 new keys + 18-line policy doc-comment block + 3 `.sensoryFeedback` mods + edge-trigger detection in the setter (half-step tolerance) + reduceMotion env read + 1-line `animation` gate. File-level doc-comment in WhatIfSlider pointing back to LifeClockHaptics |
| 07:00 | (build) | — | LifeClock | `xcodegen generate` + `xcodebuild ... build` → `** BUILD SUCCEEDED **` (Debug, iPhone 17 Pro, iOS 17.0+ deployment) |
| 07:05 | (sim) | — | iPhone 17 Pro sim | Boot + install + `LIFECLOCK_JUMP_TO=futureCapReached` launch → **blank Future tab**. Caught the fixture-gap regression. Audited the gate (every branch wants `profile.baselineHealthspanYears`). |
| 07:10 | (fix) | feat | [LifeClockLaunchConfiguration.swift](../../../products/life-clock-ios/Sources/App/LifeClockLaunchConfiguration.swift) | 12 LOC: when `futureJumpTo != nil`, seed `anchorAdjustedAt + personalAdjustmentYears + baselineCapturedAt + baselineHealthspanYears=84.0`. Scoped so non-future onboarded scenarios aren't affected |
| 07:11 | (rebuild) | — | LifeClock | `** BUILD SUCCEEDED **` |
| 07:12 | (sim) | — | iPhone 17 Pro | Re-launch cap: 98 years headline, "+14 years vs your starting baseline", "Projection capped at 105 years", chart shows cap-justifying spike, Sleep slider at 7.5/10 (~75%), Whole food at 7.0/7 (max, visible label below fold) |
| 07:14 | (sim) | — | iPhone 17 Pro | Re-launch floor: 37 years headline, "−47 years vs your starting baseline", "Projection at minimum.", chart shows floor-justifying drop, Sleep at 4.0/10 (~25%), Whole food at 0.0/7 (min) |
| 07:18 | (sim) | — | iPhone 17 Pro + RM on | `xcrun simctl spawn $DEV defaults write com.apple.Accessibility ReduceMotionEnabled -bool YES` → relaunch → identical render. Drag from Sleep thumb position to right rail → Sleep label stayed at 4.0 (snapped back) but chart Y-domain shifted (75-85 → 80-84) suggesting the scrub fired and projection recomputed. The Y-domain shift caught **mid-snap-back** (180ms `.smooth` is short, screenshot timing isn't precise enough to compare RM-on vs RM-off post-drag deterministically). |
| 07:24 | (test) | test | [LifeClockHapticsTests.swift](../../../products/life-clock-ios/Tests/LifeClockHapticsTests.swift) | Added `testWhatIfScrubHapticsMatchApprovedPolicy` pinning the three new keys against the documented policy table. Mirrors the existing `testWrapUpHapticsMatchApprovedPolicy` pattern |

## Decision table — the three asks

### Ask 1: Haptic policy (decision: **YES — three-event, edge-triggered**)

Repo doctrine in [LifeClockHaptics.swift](../../../products/life-clock-ios/Sources/Shared/LifeClockHaptics.swift): *"Keep this small and boring: haptics should underline agency and confirmation, not become a second emotional voice competing with tone copy."* That doctrine **rules out the conventional per-tick `.selection`** that most continuous sliders ship — at 60-120Hz onChange ticks, a per-tick haptic IS the second emotional voice.

| Moment | SwiftUI key | Why |
|---|---|---|
| `onEditingChanged(true)` — touch starts | `whatIfScrubBegin` → `.impact(weight: .light)` | "Agency begins." Same weight as `morningWake`/`firstReveal`. Fires once per touch. Multi-touch: each finger gets its own begin (multi-touch supported via `activeScrubCount` in `LifeClockStore`). |
| Value crosses into row's `range` lower or upper bound | `whatIfScrubEdge` → `.impact(weight: .medium)` | "You hit the rail." Edge-trigger (one tap per landing, not per snapped tick). The visual barely conveys this — the thumb stops at the same coordinate it was approaching. Haptic carries the info. |
| `onEditingChanged(false)` — release | `whatIfScrubEnd` → `.selection` | Soft release. Matches `wrapUp(zero)` semantics — "end of an act, no judgment." Lands BEFORE the snap-back animation. |
| Per-tick during drag | *(nothing)* | Deliberately omitted per the file's doctrine. |

Implementation in [WhatIfSlider.swift:107-147](../../../products/life-clock-ios/Sources/Features/Future/WhatIfSlider.swift:107) uses three `@State` wrapping counters + three `.sensoryFeedback` modifiers attached to the parent `VStack`. Edge-trigger detection lives in the `Slider`'s setter:

```swift
let epsilon = row.step * 0.5
let wasAtEdge = value <= row.range.lowerBound + epsilon
    || value >= row.range.upperBound - epsilon
let isAtEdge = newValue <= row.range.lowerBound + epsilon
    || newValue >= row.range.upperBound - epsilon
if isAtEdge && !wasAtEdge {
    scrubEdgeTrigger &+= 1
}
```

Half-step epsilon, not strict equality: `Slider(step:)` quantizes values to step boundaries, but the bound check is value-rounded so an epsilon avoids float-edge surprises.

Policy lock-in: 18-line doc-comment block at the top of `LifeClockHaptics` enumerating the policy. Next operator who touches haptics on this surface reads the rationale (per-tick excluded, edge-trigger only, weights map to existing vocabulary) without re-deriving it.

### Ask 2: Reduce Motion (decision: **YES — gate snap-back animation on `!reduceMotion`**)

[TrajectoryChart.swift:117](../../../products/life-clock-ios/Sources/Features/Future/TrajectoryChart.swift:117) was running `.animation(isScrubbing ? nil : .smooth(duration: 0.18), value: points)` unconditionally on touch-up. Two-line fix: add `@Environment(\.accessibilityReduceMotion)` and gate `.animation` on `(isScrubbing || reduceMotion) ? nil : .smooth(...)`.

Mid-scrub path was already correct (`isScrubbing` short-circuits the animation). The bug was the snap-back-on-end path. Pattern matches [LifeClockMascotView.swift:127](../../../products/life-clock-ios/Sources/Shared/LifeClockMascotView.swift:127) (`.interpolatingSpring()` ↔ `reduceMotion ? nil : ...`).

**Verified by code review, not by simulator timing.** The 180ms `.smooth` is too short to deterministically catch mid-animation via simctl screenshot (round-trip latency varies). Code-level: SwiftUI's `.animation(nil, value:)` semantically guarantees no implicit animation. No reliable observation path on the simulator short of frame-by-frame video — and even then, RM-on and RM-off animations might collapse into the same single-frame transition if 60fps capture lands cleanly.

What was empirically confirmed: drag firing **does** reach the slider thumb (chart Y-domain shifts from 75-85 to 80-84 between the seed and post-drag states), and the slider **does** snap back on release (Sleep label stays at 4.0 after touch-up). The fix lives on the animation modifier, not the snap-back logic itself — which is unchanged.

### Ask 3: Doc-comment placement (decision: **BOTH — anchor in LifeClockHaptics, breadcrumb in WhatIfSlider**)

- **Anchor (18 lines)** at the top of `LifeClockHaptics.swift` — the full policy table + rationale lives where the keys are defined. Next operator who edits any haptic on any surface reads the doctrine.
- **Breadcrumb (4 lines)** in `WhatIfSlider`'s top-of-file doc-comment — pointer to the canonical doc, plus a one-line note on Reduce Motion routing. Next operator who edits the slider sees the breadcrumb and follows it back.

Precedent: 2026-05-11 quicklog session put the lock-in doc on `QuickLogSheet.swift` (the surface), not on `ToneMode.swift` (the keys). This session inverts that — because **haptic policy is cross-surface** (the same `LifeClockHaptics` keys serve six different surfaces), the canonical lock belongs at the registry. The slider-side breadcrumb is just a forwarding pointer.

## Captured artifacts

`docs/products/life-clock/screenshots/2026-05-12-whatif-slider/`:

- [01-cap-reached.png](screenshots/2026-05-12-whatif-slider/01-cap-reached.png) — `LIFECLOCK_JUMP_TO=futureCapReached`. Headline 98 years, "+14 years vs your starting baseline", "Projection capped at 105 years", chart shows cap-justifying spike. **Sleep slider thumb at ~75% of track (7.5/10 — matches seed)**. **Whole food at 7.0/7 (max)**.
- [02-floor-reached.png](screenshots/2026-05-12-whatif-slider/02-floor-reached.png) — `LIFECLOCK_JUMP_TO=futureFloorReached`. Headline 37 years, "−47 years vs your starting baseline", "Projection at minimum.", chart shows floor-justifying drop. **Sleep at ~25% (4.0/10 — matches seed)**. **Whole food at 0.0/7 (min)**.
- [03-floor-rm-on-baseline.png](screenshots/2026-05-12-whatif-slider/03-floor-rm-on-baseline.png) — RM enabled (`com.apple.Accessibility ReduceMotionEnabled=1`), relaunched. Renders identically to 02 — confirming RM doesn't affect static render (only animation paths).
- [04-floor-rm-on-post-drag.png](screenshots/2026-05-12-whatif-slider/04-floor-rm-on-post-drag.png) — drag Sleep thumb right with RM on, screenshot ~1.5s later. Sleep label 4.0 (snapped back), chart Y-domain settled at 80-84.
- [05-floor-rm-off-post-drag.png](screenshots/2026-05-12-whatif-slider/05-floor-rm-off-post-drag.png) — same drag with RM off. Same Sleep label (4.0), same chart Y-domain (80-84). The 180ms animation window is too brief for screenshot timing to differentiate; RM verification is by code review (see Ask 2).

Below-fold thumbs (Steps, Exercise, Extras, Nicotine) not captured: SwiftUI `ScrollView` on iOS 26 Simulator does not reliably accept cliclick / computer-use scroll OR drag-scroll events (same blocker noted in [polish-2026-05-11-safetynet-drift-audit.md](polish-2026-05-11-safetynet-drift-audit.md) and [polish-2026-05-11-quicklog-drift-and-q11-narration.md](polish-2026-05-11-quicklog-drift-and-q11-narration.md) recon gotcha #2). The two visible thumbs (Sleep + Whole food) plus the headline projection (which is computed FROM all six slider values) are sufficient evidence that the seed mechanism works end-to-end. **PR #42 I4 fix verified for the two foldsable sliders + the projection-of-all-six computed result.**

## Frame budget + Instruments trace — deferred

The brainstorm asked for an iPhone 17 Pro Instruments scrub trace to capture worst-case scrub frame timing. **Deferred to a separate session** for two reasons:

1. **Simulator is the wrong target.** Simulator frame timing reflects host Mac performance, not device Neural Engine / display pipeline behavior. The 120Hz frame budget the brainstorm cares about (Future tab is iPhone 17 Pro's main marquee perf moment) only manifests on real hardware.
2. **Device profiling requires a TestFlight / signed-device path** that this session doesn't have access to. The `xctrace record --device <UDID>` recipe is ready to run when a physical iPhone 17 Pro is paired; that's a separate operator task, not a polish-session blocker.

**Compound for next operator who attempts the device trace:** the recipe is

```bash
xctrace record --device <iPhone 17 Pro UDID> \
  --template "Time Profiler" \
  --target io.aicompanyos.products.lifeclock \
  --launch -- \
  --output /tmp/lc-scrub.trace
```

then drive 5+ seconds of continuous scrubbing across at least three sliders, then `xctrace export --input /tmp/lc-scrub.trace`. Any frame interval > 8.33ms (120Hz budget) or > 16.67ms (60Hz budget on low-power mode) is a fix-list candidate.

## Haptic observability — limitation noted

**iOS Simulator does not emit haptics.** The three new `.sensoryFeedback` modifiers attached to the slider will fire on device but produce nothing observable in the simulator — no log line, no audible/tactile signal. Verification options:

1. **Unit test pinning the policy table** — shipped this session ([testWhatIfScrubHapticsMatchApprovedPolicy](../../../products/life-clock-ios/Tests/LifeClockHapticsTests.swift)). Catches accidental policy drift.
2. **Visual inspection of source** — the three `.sensoryFeedback` mods on the parent VStack + the three trigger counter increments are fully visible in [WhatIfSlider.swift:80-83 + 122 + 136 + 142](../../../products/life-clock-ios/Sources/Features/Future/WhatIfSlider.swift).
3. **Device test on real hardware** — the only way to actually feel the policy. Deferred to TestFlight or a paired-device run, same as the Instruments trace.

The polish-session checkpoint (per operator addendum: "yes — gestural feel is the test") technically can't ship as-promised on the simulator. The honest position: gestural-input plumbing was verified (drag reaches slider, scrub-end snap-back works), haptic policy was specified + locked + tested, but the **literal "feel" of the haptic** is unverified until a device session lands.

## Stretch decisions (operator review)

- **Fixture-knob gap fix scoped to `futureJumpTo != nil`.** Could have made it unconditional (always seed baseline when `scenario=.onboarded`), but that risks breaking legacy tests that rely on the baseline-nil path (e.g. baseline-bootstrap-on-launch tests, Today day0/day1-3 paths). The narrow scope keeps the change reversible and the blast radius zero.

- **Did NOT add a `LIFECLOCK_FORCE_REDUCE_MOTION=1` fixture knob.** Considered it — would let polish-recon screenshot the RM-on path deterministically — but `xcrun simctl spawn $DEV defaults write com.apple.Accessibility ReduceMotionEnabled -bool YES` already works at the simulator level. Adding an env-var knob inside the app would mean teaching the SwiftUI environment to honor it (overriding the system AX value), which is a real code change for a fixture-only convenience. Out of scope; the simctl spawn recipe is documented above and in this log.

- **Did NOT add `LIFECLOCK_SEED_SLIDER_OVERRIDES_JSON` plumbing-to-render verification.** [LifeClockLaunchConfiguration.swift:148](../../../products/life-clock-ios/Sources/App/LifeClockLaunchConfiguration.swift:148) declares this property but I could not find a consume site — the seed gets parsed but is it actually applied? [LifeClockApp.swift:48](../../../products/life-clock-ios/Sources/App/LifeClockApp.swift:48) calls `store.sliderOverrides = seeds` from `effectiveSliderOverrideSeeds` (the JUMP_TO-derived dict), not from the JSON env var. The JSON path appears to be wired only to the `effectiveSliderOverrideSeeds` property's *default* — there's no JSON-decoding call site. **Flagged for follow-up:** either delete the dead property or wire the JSON parser into the seed path.

- **Did NOT migrate to `SensoryFeedback.Modifier` per-tick rejection inline test.** A test that asserts "WhatIfSlider does NOT call `.sensoryFeedback` per-tick" would require a SwiftUI snapshot-test framework I don't see in this repo. The pinning test (`testWhatIfScrubHapticsMatchApprovedPolicy`) covers the policy-table case; per-tick prevention is enforced by the documented architecture (no per-tick trigger increment in the setter) and the doc-comment block.

## Recon gotchas caught this session (compounds for next polish)

> Additive to the gotchas in 2026-05-09 (`SIMCTL_CHILD_`), 2026-05-11 SafetyNet (snake-case rawValue + `SEED_STREAK` gating), and 2026-05-11 QuickLog (`simctl launch` async, `simctl terminate` async, `Picker(.segmented)` truncation past 4 options).

1. **`xcrun simctl io <DEV> recordVideo` is exclusive.** Starting a recording while a previous one is in-flight returns `Error Domain=NSPOSIXErrorDomain Code=16 "Resource busy"`. The previous-recording's process must be killed (`pkill -f "simctl io.*recordVideo"`) before a new recording can start. The `&` shell-detach pattern is unsafe here because the process keeps running after the parent bash returns. Compound: when polishing video-driven recon, wrap recordings in a `trap "pkill -f simctl io" EXIT` so they always clean up.

2. **`com.apple.Accessibility ReduceMotionEnabled` is the right defaults domain on iOS 26 Simulator.** Other plausible candidates (`com.apple.UIKit`, `com.apple.UIKit.UIAccessibility`) do nothing. `xcrun simctl spawn $DEV defaults write com.apple.Accessibility ReduceMotionEnabled -bool YES` followed by relaunch is the canonical recipe; reading back with `defaults read com.apple.Accessibility ReduceMotionEnabled` returns `1` when set. App must be terminated + relaunched for the env to propagate (the AX value is read on first `@Environment(\.accessibilityReduceMotion)` query).

3. **SwiftUI `ScrollView` on iOS 26 Simulator ignores cliclick-style scroll AND ignores drag-scroll gestures driven through computer-use.** This is broader than the `Form`/`List` row-tap issue documented 2026-05-11 — even pure `ScrollView` content (Future tab body) does not respond. The horizontal drag on the slider thumb itself DOES work (caught by the chart Y-domain shifting), so the issue is specifically vertical scroll-gesture delivery. Compound: any below-fold screenshot need on the Future tab needs either (a) shrinking content via XXL-down, (b) resizing the simulator window to be taller, or (c) explicit `LIFECLOCK_*` fixture knobs that jump to below-fold sections. Drag-on-a-control (slider thumb, button) is reliable; drag-on-a-scroll-surface is not.

4. **`FutureView`'s every visible branch gates on `profile.baselineHealthspanYears`.** Onboarded-without-baseline = blank tab. The `bootstrapV170Baseline` hook in `LifeClockStore` covers production users (existing onboarded users get backfilled on cold launch) but does NOT cover fixture-only launches because it requires `anchorAdjustedAt + personalAdjustmentYears` which the fixture didn't seed. **Compound:** any new tab/screen whose visibility depends on a profile field should EITHER have a sane nil-state UI OR get explicit fixture seeding when the field is required.

## Asks (closed)

All three brainstorm asks (haptic policy, Reduce Motion, doc-comment placement) closed in-session per operator's "best judgement call on all asks" directive. Implementation diff:

| File | Diff |
|---|---|
| [LifeClockHaptics.swift](../../../products/life-clock-ios/Sources/Shared/LifeClockHaptics.swift) | +22 LOC (3 keys + 18-line policy doc-comment) |
| [WhatIfSlider.swift](../../../products/life-clock-ios/Sources/Features/Future/WhatIfSlider.swift) | +35 LOC (file-level doc-comment update, 3 @State triggers, 3 `.sensoryFeedback` mods, edge-trigger detection block, scrub-trigger increments) |
| [TrajectoryChart.swift](../../../products/life-clock-ios/Sources/Features/Future/TrajectoryChart.swift) | +7 LOC (reduceMotion environment + animation gate update) |
| [LifeClockLaunchConfiguration.swift](../../../products/life-clock-ios/Sources/App/LifeClockLaunchConfiguration.swift) | +14 LOC (fixture-gap fix: seed baseline when `futureJumpTo != nil`) |
| [LifeClockHapticsTests.swift](../../../products/life-clock-ios/Tests/LifeClockHapticsTests.swift) | +9 LOC (1 new test pinning the three new keys against policy) |

**Total: 5 files, +87 LOC.** 1 build verification (BUILD SUCCEEDED), 5 screenshots staged. Iteration cap was 6; used 5.

---

**Bottom line.** WhatIfSlider had no haptic policy and no Reduce Motion gate before this session — the brainstorm's "specify the policy" framing was a create-the-policy task. Three-event policy (begin/edge/end, no per-tick) shipped, locked in code + tests + doc-comment; Reduce Motion snap-back gated; thumb-landing verified for cap + floor states (via screenshots of the visible-fold sliders, since iOS 26 Simulator's ScrollView doesn't accept computer-use scroll). The session caught a separate agent-native parity bug — `JUMP_TO=future*` couldn't render the slider before this session because `baselineHealthspanYears` wasn't seeded — and fixed it. Three deferrals are honest about their constraints: device-only haptic feel verification, device-only Instruments scrub trace, and the `SEED_SLIDER_OVERRIDES_JSON` dead-property follow-up. The brainstorm checkpoint ("gestural feel is the test") was partially met: the gestural plumbing is verified, but the literal *feel* of the new haptics needs a real iPhone — a TestFlight build is the next operator action.
