# Narrative Engine Spec — Life Clock

> **Status:** Canonical product policy. The `NarrativeEngine` composes the long-form narrative copy shown on the Future tab and the WrapUp Pro variant. Sister spec to [`future-tab-tone-pools-spec.md`](future-tab-tone-pools-spec.md), which covers the Future-tab tone-pool *content*; this doc covers the *engine that assembles it*.
>
> Implementation: [`Sources/Engines/NarrativeEngine.swift`](../../../products/life-clock-ios/Sources/Engines/NarrativeEngine.swift).

## One-line rule

**The narrative engine composes paragraphs by stitching together tone-aware fragments — never by templating raw values into a sentence.** Each paragraph (headline / dominant driver / drag / action) has a dedicated composer; each composer pulls fragments from the tone pool for the current `ToneMode` and current healthspan state.

## Composer architecture

`NarrativeEngine.compose(…)` is the entry point. It dispatches to four sub-composers in order:

1. **`headlineParagraph`** — opening line. Names the week's net direction; primary emotional read.
2. **`dominantDriverParagraph`** — what helped most. Sourced from `HealthspanEngine.Dimension`.
3. **`dragParagraph`** — what hurt most. Sourced from `HealthspanEngine.Dimension` + recent `HabitLog` signals for context.
4. **`actionParagraph`** — one concrete next-best lever. Pulled from `Sources/Engines/AffinityEngine` recommendations.

Each composer is a pure function: takes value-type inputs + the user's tone mode, returns a `String`. No side effects, no `Date()` calls. Tests pin every composer with fixture inputs.

## State-aware copy

The Future tab has four states based on data sufficiency, each with its own copy pool:

| State | Trigger | Engine behavior |
|---|---|---|
| `day0` | Onboarding done; no HealthKit days collected yet | Anticipation / preview register; engine doesn't compute drivers (no signal) — copy alludes to "your trajectory is loading." |
| `coldLaunch1to3` | 1-3 days of data | Tentative register; engine reports drivers but flags low confidence in narrative copy. |
| `warmingUp4to13` | 4-13 days of data | Forward-leaning register; engine reports drivers with medium confidence. |
| `full14plus` | 14+ days of data | Authoritative register; engine reports drivers with full confidence; narrative gains "this week" framing. |

Implementation lives in `FutureView` state branching; copy pools live in `future-tab-tone-pools-spec.md` § State pools.

## Tone composition rules

- Headline tone matches `store.toneMode` exactly (gentle / coach / firmDirect).
- Driver + drag paragraphs lean coach-register even when tone is firmDirect — they're explanatory, not dramatic.
- Action paragraph tone matches `store.toneMode` because it's a forward call-to-action and benefits from voice consistency.
- Mortality lexicon is permitted in firmDirect ONLY in the drag paragraph, and only as a metaphor (e.g., "smoking is taking the most from you") — never as a literal lifespan claim.

## Anti-patterns (binding refusals)

- **Do not template raw values into a sentence shell.** ("Your steps were \(N).") Fragments come from tone pools; values come from formatters; the composer joins them.
- **Do not let the engine know `Date()`.** Every time input is explicit. Test pinning requires it.
- **Do not generate copy in a `View`.** `View` consumes the engine's output; never the other way around.
- **Do not vary fragment count by tone.** Headline + driver + drag + action = four paragraphs in every state, every tone. Skipping creates pacing drift.
- **Do not interpolate Pro-locked content into Free narrative.** The Free narrative is shorter (headline + driver), Pro adds drag + action. Driver/drag/action are not pre-mixed.

## Cross-references

- Implementation: [`Sources/Engines/NarrativeEngine.swift`](../../../products/life-clock-ios/Sources/Engines/NarrativeEngine.swift)
- Future tab tone pools (the *content*): [`future-tab-tone-pools-spec.md`](future-tab-tone-pools-spec.md)
- Healthspan engine (the dimensions narrative pulls from): [`CLOCK_MODEL.md`](CLOCK_MODEL.md) § Two engines + `Sources/Engines/HealthspanEngine.swift`
- Affinity engine (action recommendations): `Sources/Engines/AffinityEngine.swift` + [`plan-quest-generation-affinity.md`](plan-quest-generation-affinity.md)
- Microcopy rules: [`microcopy-spec.md`](microcopy-spec.md)
- Future tab UX: [`PRD.md`](PRD.md) § Future, [`UX_GAME_LOOP.md`](UX_GAME_LOOP.md) § Future tab

## Validation

A narrative composition is on-spec when ALL of the following hold:

1. The four paragraphs are present in order: headline / dominant driver / drag / action.
2. Each composer is pure (no `Date()`, no side effects).
3. Fragments come from `future-tab-tone-pools-spec.md` pools, never inline.
4. The tone mode matches `store.toneMode` for headline + action; drivers + drag lean coach.
5. The state (`day0 / coldLaunch1to3 / warmingUp4to13 / full14plus`) drives copy register.
6. Free variant truncates to headline + driver; Pro adds drag + action.
