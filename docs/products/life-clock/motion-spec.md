# Motion Spec — Life Clock

> **Status:** Canonical product policy. Defines the elevation vocabulary for animation curves, durations, and motion hierarchy. Sibling to [`haptics-spec.md`](haptics-spec.md). The shipped implementation lives in `Sources/Shared/Motion.swift` (planned — premium-feel-backlog Prompt 3 lands the enum and migrates 8 sites against this spec).
>
> The 2026-05-12 premium-feel audit found **9 distinct hand-rolled durations across 9 surfaces** with no shared vocabulary. None of those durations hit the 100ms / 250ms / 500ms tiers the rubric demands, so motion reads as ad-hoc and inconsistent — animations land at different speeds even for the same conceptual gesture (e.g., a confirm vs a confirm). This spec defines the binding vocabulary so future surfaces inherit a coherent motion grammar.

## One-line rule

**Motion has a vocabulary of three durations and one set of named curves.** Pick the duration that matches the conceptual weight of the gesture; pick the curve that matches the gesture's physical metaphor. No surface invents its own duration.

## The three duration tiers (binding)

| Tier | Value | Use for |
|---|---|---|
| `instant` | **0.18s** (~180 ms) | UI confirmation; sheet scroll-to; opacity-only state changes; selection ring lift; menu open/close. The user perceives this as "the app responded." |
| `beat` | **0.30s** (~300 ms) | Short transitions; card expansion; tab cross-fade; a value re-counting; reveal of a single element. The user perceives this as "one beat — something changed." |
| `breath` | **0.60s** (~600 ms) | Large reveals; first-impression moments; the reveal escalator's per-card sweep; wake animation on app foreground; trajectory chart redraw. The user perceives this as "the app took a breath, then showed me the new thing." |

These tiers were chosen to land on the premium-bar.md "Motion" rubric thresholds (100ms perception floor, 250ms beat, 500ms breath) while matching distinct points already in the shipped code (0.18 already used in PaywallSheet, 0.25 already in ClockHandView, 0.6 already in LifeGridDotView). The migration is small-diff, not a wholesale animation re-tune.

### Anti-tier: `glacial` (>0.8s) — escalate to vision-question

A duration over **0.8s** is not a motion choice, it's a narrative beat. Surface that wants one — the engine reveal, the healthspan dial, the life-grid penalty animation — must go through `vision-driven` review because the duration is a content decision, not a motion decision.

## Named curves

| Curve | When |
|---|---|
| `Motion.Curve.smooth` (= SwiftUI `.smooth`) | Default for opacity, fades, color. |
| `Motion.Curve.spring` (= `.interpolatingSpring()`) | Spatial motion — anything that has a position, scale, or rotation. Springs *feel* like physical objects; ease curves *feel* like timelines. Springs are default for the mascot hand, the healthspan dial, the trajectory line drawing in. |
| `Motion.Curve.snappy` (= `.snappy`) | A spring that overshoots slightly — use for celebratory affordances (purchase success, completion checkmarks, badge unlocks). Sparing. |
| `Motion.Curve.breathing` | Custom `.timingCurve(0.2, 0.8, 0.2, 1.0, duration:)` — slow-out / hold / slow-in. The wake animation uses this. Use for once-per-session reveals only. |

## What the enum looks like

```swift
enum Motion {
    enum Duration {
        static let instant: TimeInterval = 0.18
        static let beat: TimeInterval = 0.30
        static let breath: TimeInterval = 0.60
    }

    enum Curve {
        static let smooth: Animation = .smooth
        static let spring: Animation = .interpolatingSpring()
        static let snappy: Animation = .snappy
        static func breathing(duration: TimeInterval) -> Animation {
            .timingCurve(0.2, 0.8, 0.2, 1.0, duration: duration)
        }
    }
}
```

Convenience callsites:

```swift
withAnimation(.smooth(duration: Motion.Duration.instant)) { ... }
.animation(.easeInOut(duration: Motion.Duration.beat), value: foo)
```

## Migration target (premium-feel-backlog Prompt 3)

Current ad-hoc durations and their migration targets:

| Site | Current | Migrate to |
|---|---|---|
| `PaywallSheet.swift:61` (scrollTo smooth) | 0.18 | `Motion.Duration.instant` |
| `ClockHandView.swift:78` (`easeInOut`) | 0.25 | `Motion.Duration.beat` |
| `ClockHandView.swift:86` (custom `timingCurve`) | param | `Motion.Curve.breathing(duration:)` |
| `LifeGridDotView.swift:65, 71` (`easeInOut`) | 0.6 | `Motion.Duration.breath` |
| `RevealEscalatorScreens.swift:435` (`easeInOut`) | 0.25 | `Motion.Duration.beat` |
| ~~`RevealEscalatorScreens.swift:449` (`easeInOut`)~~ | ~~0.35~~ | ~~`Motion.Duration.beat`~~ — migrated 2026-05-16 (PF-P2) |
| `TodayView.swift:231` (wake animation `easeOut`) | `Self.wakeDuration` | `Motion.Curve.breathing(duration: Motion.Duration.breath)` |
| `LifeClockMascotView.swift:127` (`interpolatingSpring`) | — | `Motion.Curve.spring` |
| ~~`EngineRevealAndDialView.swift:95` (`.snappy`)~~ | ~~—~~ | ~~`Motion.Curve.snappy`~~ — migrated 2026-05-16 (PF-P3); literal→named constant, zero behavior change |
| ~~`LeadInScreens.swift:337` (`.snappy`)~~ | ~~—~~ | ~~`Motion.Curve.snappy`~~ — migrated 2026-05-16 (PF-P3); literal→named constant, zero behavior change |
| ~~`TrajectoryChart.swift:140` (`.smooth(duration:)`)~~ | ~~0.18~~ | ~~`Motion.Duration.instant`~~ — migrated 2026-05-16 (PF-P2); kept at `instant` to preserve the existing 0.18 perceived redraw speed (PF-P2 binding payload) |
| ~~`HealthspanRevealView.swift:86` (`.easeOut`, lever-row stagger reveal)~~ | ~~0.32~~ | ~~`Motion.Duration.beat`~~ — migrated 2026-05-16 (PF-P3); reveal-of-single-element gesture (opacity+scale), spec beat use-for; 0.32→0.30 imperceptible |
| ~~`WhatWeDontDoView.swift:47` (`.easeOut`, bullet stagger reveal)~~ | ~~0.32~~ | ~~`Motion.Duration.beat`~~ — migrated 2026-05-16 (PF-P3); reveal-of-single-element gesture (opacity+offset), matches sibling stagger; 0.32→0.30 imperceptible |
| ~~`WhatWeDontDoView.swift:61` (`.easeOut`, footer fade-in)~~ | ~~0.32~~ | ~~`Motion.Duration.beat`~~ — migrated 2026-05-16 (PF-P3); evaluated against `instant` (opacity-only) but rejected: 0.32→0.18 perceptibly snappier, violates felt-pacing guardrail; reveal-of-single-element → `beat`, 0.32→0.30 imperceptible |

Migration order:

1. Land `Motion.Duration` + `Motion.Curve` in `Sources/Shared/Motion.swift`.
2. Replace each ad-hoc duration in the table above with the named constant. One commit per call site (or one commit total — depends on operator review preference).
3. Re-record the premium-feel-backlog → motion-incoherence prompts as resolved.

## Anti-patterns (binding refusals)

- **Do not invent a new duration.** If your use case doesn't fit `instant / beat / breath`, the use case is wrong, not the spec. Either escalate to vision-question (if the duration is narrative) or pick the closest tier (if the duration is functional).
- **Do not pile multiple animations at different durations on the same gesture.** A purchase confirm should not have a 0.2s checkmark + 0.25s color flash + 0.6s sheet dismiss. Pick one duration; let the rest follow.
- **Do not animate motion for users with `reduceMotion`.** Every modifier must short-circuit when `@Environment(\.accessibilityReduceMotion) var reduceMotion` is true. The `LifeClockMascotView` already follows this pattern (`reduceMotion ? nil : ...`) — keep that pattern across all motion sites.
- **Do not bind motion to user data values that change fast.** Spring animations on a per-frame computed value (e.g., HK aggregate during scroll) cause stutter. The `LifeClockStore.swift:96` `.animation(nil, value:)` gate on the chart exists for this reason.

## Anti-patterns specific to springs

- **Do not use `.spring` for opacity** — springs are spatial. Opacity uses `smooth` or `easeInOut`.
- **Do not use `.snappy` for non-celebratory motion.** Snappy overshoots; it reads as "ta-da!" Reserve it for genuine moments of accomplishment.

## How this spec interacts with the lighting spec

Motion and lighting share one rule: **the gesture should read as part of the same lighted, lit-from-above scene.** If a card adopts `lightingDepth(referenceSize:)` and then animates into view, it should use `Motion.Curve.spring` so its arrival has physical weight — not `easeIn`, which reads as a 2D card slide without depth.

## Cross-references

- Premium-bar: `premium-bar.md` § "Motion" (the rubric).
- Premium-feel audit: `premium-feel-backlog-2026-05-12-standard.md` Prompts 3, 6, 7, 14 (motion-incoherence category).
- Lighting spec: [`lighting-spec.md`](lighting-spec.md) (sibling — the visual-coherence rule).
- Haptics spec: [`haptics-spec.md`](haptics-spec.md) (sibling — the tactile-coherence rule).

## Validation

A motion choice is on-spec when ALL of the following hold:

1. The duration is `Motion.Duration.instant | .beat | .breath`, not a literal.
2. The curve is one of the four named curves (`smooth / spring / snappy / breathing`), not a one-off.
3. The animation respects `reduceMotion` (short-circuits to `nil`).
4. The animation does not stack with another animation on the same gesture at a different duration.

The premium-readiness flag in `premium-bar.md` requires zero unresolved `motion-incoherence` prompts in the active backlog — i.e., every shipped animation site passes the four checks above.
