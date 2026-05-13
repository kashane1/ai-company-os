# Confidence Model Spec — Life Clock

> **Status:** Canonical product policy. The confidence model surfaces honesty about how trustworthy a given day's signal is — a load-bearing trust decision per vision Decided constraint "Confidence is shipped, not hidden." This spec defines the thresholds, the surfaces, and the rules for never-overrating or never-underrating.
>
> Implementation: [`Sources/Engines/ConfidenceModel.swift`](../../../products/life-clock-ios/Sources/Engines/ConfidenceModel.swift) + the `sourceCompleteness` field on `DailyHealthSnapshot`.

## One-line rule

**Every per-day signal carries an explicit confidence label — High / Medium / Low — derived from `sourceCompleteness ∈ [0, 1]`. Missing data lowers confidence; it never produces a negative time delta on its own.**

## The three buckets

| Bucket | `sourceCompleteness` | UI label | Driven by |
|---|---|---|---|
| **High** | ≥ 0.7 | "Confidence: High" + "Based on Apple Health steps, exercise, sleep, body mass…" | Most/all core HK types present + recent baseline |
| **Medium** | ≥ 0.4 | "Confidence: Medium" + "Based on partial Apple Health data + your manual inputs" | Some HK + manual inputs |
| **Low** | < 0.4 | "Confidence: Low" + "Mostly manual or sparse data" | Mostly manual or empty days |

Thresholds are constants in `ConfidenceModel.swift`. Changing them is a vision-question — the bucket boundaries are a published contract.

## What confidence affects (binding)

- **Today's headline delta** — surfaced as a label below the signed-minutes readout (`ConfidenceBadge` view).
- **History weekly cards** — "Confidence: High / Medium / Low" appears in the weekly summary so users can read the trend with appropriate certainty.
- **Future tab trajectory** — Low confidence states pull back the trajectory line opacity and surface a "still learning" subhead.
- **Narrative engine** — confidence bucket feeds into the narrative state (cold-launch states 1–3 lean toward Low; full14plus + good HK auth toward High).
- **Reveal escalator** — `analyzing` → `archetypeReveal` sequence presents the user's baseline confidence honestly; a Low-confidence reveal still happens but uses softer copy.

## What confidence must NEVER do

- **Never produce a negative time delta.** Low confidence ≠ penalty. Missing data is treated as "we don't know yet," not as "you did badly."
- **Never hide entirely.** Even at very Low confidence, the user sees the label (operator memory: "Confidence is shipped, not hidden" — vision Decided). A hidden confidence indicator violates trust.
- **Never bucket as a sliding scale UI.** Three discrete buckets only. A "67% confident" progress bar reads as clinical and is wrong-shaped.
- **Never override the user's reading.** "We're confident your day was strong" is bad copy — "Confidence: High" is fine.
- **Never imply "Low confidence = unreliable data the user should fix."** Low confidence is a state of the world (not enough HK signal yet), not a user fault.

## How `sourceCompleteness` is computed

Source: `HealthKitAggregator` rolls per-type presence into a [0, 1] score. The aggregator weights:

- Steps + active energy + exercise minutes: heaviest weight (passive baseline)
- Sleep: secondary weight
- Resting HR + body mass: tertiary weight
- Manual habit log entries: tertiary weight (replace missing HK with self-report)

The exact aggregation lives in `HealthKitAggregator.swift`; this spec doesn't pin the math because the weights are tunable as more HK types ship. The bucket *thresholds* (0.4 / 0.7) are the contract; the aggregator can evolve.

## Anti-patterns (binding refusals)

- **Do not use the word "accuracy."** Confidence is about data sufficiency, not engine accuracy. "Accuracy" implies clinical claims; Life Clock does not make clinical claims.
- **Do not surface confidence numbers.** No "67%". Three-bucket only.
- **Do not penalize for choosing not to grant HK access.** A Free-state user without HK is Low-confidence — fine; they still see a meaningful Today.
- **Do not over-correct missing data.** The engine doesn't impute. Manual habit logs replace missing HK only where the signal is congruent (logged "great sleep" is not the same as a measured 7.5h).
- **Do not move thresholds without a vision-question.** Users will have built mental models around High/Medium/Low; shifting boundaries silently changes the bucket they see for the same data.

## Cross-references

- Implementation: [`Sources/Engines/ConfidenceModel.swift`](../../../products/life-clock-ios/Sources/Engines/ConfidenceModel.swift)
- Aggregator: `Sources/Engines/HealthKitAggregator.swift`
- UI surface: `Sources/Shared/ConfidenceBadge.swift` (and inline call sites in `TodayView`, `HistoryView` weekly card, `FutureView`)
- Clock model: [`CLOCK_MODEL.md`](CLOCK_MODEL.md) § Confidence calculation
- Healthspan engine (sister math): [`healthspan-coefficients.md`](healthspan-coefficients.md)
- Vision: [`vision.md`](vision.md) § Decided constraints ("Confidence is shipped, not hidden")
- Microcopy: [`microcopy-spec.md`](microcopy-spec.md) (confidence label copy follows safety registers)

## Validation

The confidence model is on-spec when ALL of the following hold:

1. Every day's signal surfaces a Confidence: High/Medium/Low label.
2. `sourceCompleteness` is the sole driver of the bucket assignment.
3. Low confidence never produces a negative time delta.
4. The label is never hidden — even on `day0` states.
5. The thresholds 0.4 / 0.7 are stable across releases.
6. No surface uses "accuracy" or a confidence percentage.
