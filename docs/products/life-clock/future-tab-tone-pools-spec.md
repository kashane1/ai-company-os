# Future tab + History summary — tone pools spec

**Status:** v0 — authoring for implementation
**Authored:** 2026-05-11
**Plan reference:** [docs/plans/2026-05-11-feat-future-tab-history-summary-plan.md](../../plans/2026-05-11-feat-future-tab-history-summary-plan.md) §Phase 0
**Implementation home:** `products/life-clock-ios/Sources/App/ToneMode.swift` (surface-prefixed computed properties) + `Sources/Shared/ReflectionPrompts.swift` (where pool selection logic lives)

## Conventions

- **Three tones.** `gentle` / `coach` / `firmDirect`. Same enum used everywhere else; same voice characteristics.
- **Drama allowed; cruelty not.** Carried over from `polish-2026-05-10-vision-bad-day-gentle-coach-pools.md`. No mortality lexicon in any tone. Negative-direction copy holds the user accountable without shaming.
- **Surface-prefixed property names.** Match existing convention (`historyLongAbsenceHeading`, `todayHeadline`). New properties named like `futureHeadlineSubtext`, `historySummaryHero`, `futureCapReached`.
- **Pool vs template split.**
  - **Pool** = pre-authored complete string; picked by deterministic index (e.g. day-of-year mod count). Used for *short* slots. Lives in `ReflectionPrompts.pool(for:)`.
  - **Template** = format string with named slots; filled with concrete data via `String(format:)` or interpolation. Used for *Pro long-form* and the *Day 4–13 transparency line* (which is a hybrid: pre-authored per N, but selected by N).
- **Slot tokens.** When a template references data, slots use `{N}` / `{startDate}` / `{dim}` / `{dimValue}` / `{count}` / `{delta}` / `{year}`. Implementer renders via `DateComponentsFormatter` / `NumberFormatter` for i18n safety.
- **Same neutral foreground for ±.** Tone copy carries valence, not color. Same as `HistoryView` netCard convention.

## Future tab surfaces

### `futureHeadlineSubtext` (single string per tone)

Always rendered under the projection number on `dayState ∈ {warmingUp4to13, full14plus}`.

| Tone | Copy |
|---|---|
| gentle | `Updated daily from your last 14 days.` |
| coach | `Updated daily. Last 14 days of signal.` |
| firmDirect | `14-day rolling. Updated daily.` |

### `futureDay0Line` (single string per tone)

Rendered when `dayState == day0` (install day). No chart, no slider, baseline-only render.

| Tone | Copy |
|---|---|
| gentle | `Your projection arrives tomorrow. For today, your starting baseline is enough.` |
| coach | `Projection starts tomorrow. Today: log your first day.` |
| firmDirect | `Day zero. Projection turns on tomorrow.` |

### `futureColdLaunchLine` (single string per tone)

Rendered when `dayState == coldLaunch1to3` (days 1–3). Baseline + this line; no chart, no slider.

| Tone | Copy |
|---|---|
| gentle | `Your projection will sharpen as you log days. We're listening.` |
| coach | `Projection sharpens with each day. Three days in, the chart turns on.` |
| firmDirect | `Sharpens with each day. Chart unlocks at day 4.` |

### `futureWarmingUpTransparency(daysOfData:)` — pool with discrete N

Rendered when `dayState == warmingUp4to13`. The slot is N = days of data so far (4..13). Pre-authored per N per tone. **30 strings total** (10 N values × 3 tones). Pool-style selection, not templated `String(format:)`.

#### Gentle (N=4..13)

| N | Copy |
|---|---|
| 4 | `4 days in. Your projection is taking shape — the picture sharpens through day 14.` |
| 5 | `5 days of signal. Still warming up; full confidence at day 14.` |
| 6 | `6 days logged. The trajectory is forming.` |
| 7 | `One week in. Your projection still has room to settle.` |
| 8 | `8 days of data. The chart is finding its footing.` |
| 9 | `9 days in. Five more days reach full confidence.` |
| 10 | `10 days. Almost the full window.` |
| 11 | `11 days. Confidence is climbing.` |
| 12 | `12 days. Two days from full read.` |
| 13 | `13 days. Tomorrow your full 14-day window kicks in.` |

#### Coach (N=4..13)

| N | Copy |
|---|---|
| 4 | `4 of 14 days logged. Projection sharpens through day 14.` |
| 5 | `5 of 14. Building toward full confidence.` |
| 6 | `6 of 14. Trajectory taking shape.` |
| 7 | `Week one done. Halfway to full read.` |
| 8 | `8 of 14. Signal is clarifying.` |
| 9 | `9 of 14. Five days to full window.` |
| 10 | `10 of 14. Closing in.` |
| 11 | `11 of 14. Three more days.` |
| 12 | `12 of 14. Two more days.` |
| 13 | `13 of 14. Full window opens tomorrow.` |

#### FirmDirect (N=4..13)

| N | Copy |
|---|---|
| 4 | `4/14 days. Full read at 14.` |
| 5 | `5/14. Building.` |
| 6 | `6/14.` |
| 7 | `7/14. Halfway.` |
| 8 | `8/14.` |
| 9 | `9/14. Five days out.` |
| 10 | `10/14.` |
| 11 | `11/14. Three days.` |
| 12 | `12/14. Two days.` |
| 13 | `13/14. Tomorrow.` |

### `futureCapReached` (single neutral string, no per-tone variants)

Inline next to the projection number when projection is clamped to cap.

```
Projection capped at 105 years.
```

### `futureFloorReached` (single neutral string)

```
Projection at minimum.
```

### `futureNearCapCompression` (single neutral string)

Rendered as a chart annotation when projection is within 2y of cap.

```
Near projection ceiling — chart compressed.
```

### `futureFreeNarrativeLine(strongestLever:direction:)` — template per dimension × tone × direction

The line below the chart. Always rendered. Rules-based composition: identify strongest absolute-delta lever from 14-day data; pick the matching template by `(dim, direction, tone)`. Slots: `{count}` (top-N day count, integer), `{threshold}` (anchor text like `7+ hours` or `8k+ steps`).

12 templates per tone (6 dims × 2 directions) = 36 strings.

#### Gentle

| Dim | + direction | − direction |
|---|---|---|
| sleep | `Sleep has been carrying you — {count} of your top +Δ days came from {threshold}.` | `Sleep has been a quiet drag — {count} of your bottom days were short nights.` |
| dietQuality | `Whole-food days have been doing the work — {count} of your best days had {threshold}.` | `Whole food has been thin — {count} of your bottom days skipped it.` |
| steps | `Steps have been your strongest lever — {count} of your top days reached {threshold}.` | `Steps have been the drag — {count} of your bottom days fell under {threshold}.` |
| exerciseMinutes | `Movement has been earning ground — {count} top days had {threshold} of exercise.` | `Movement has been light — {count} of your bottom days had under {threshold}.` |
| extras | `Easing up on extras has been helping — {count} of your top days stayed under {threshold}.` | `Extras have been pulling — {count} of your bottom days had {threshold}+.` |
| nicotine | (n/a — gentle does not narrate nicotine on the upside; if zero, free line uses next dim) | `Nicotine has been the heaviest weight — {count} days this fortnight.` |

#### Coach

| Dim | + direction | − direction |
|---|---|---|
| sleep | `Sleep is your strongest lever — {count} of your top +Δ days came from {threshold}.` | `Sleep is dragging — {count} of your bottom days were under {threshold}.` |
| dietQuality | `Whole food is doing the work — {count} of your top days hit {threshold}.` | `Whole food is thin — {count} bottom days skipped it.` |
| steps | `Steps are leading — {count} top days reached {threshold}.` | `Steps are the drag — {count} bottom days under {threshold}.` |
| exerciseMinutes | `Movement is earning ground — {count} top days at {threshold}.` | `Movement is light — {count} bottom days under {threshold}.` |
| extras | `Extras restraint is helping — {count} top days under {threshold}.` | `Extras are pulling — {count} bottom days at {threshold}+.` |
| nicotine | (n/a) | `Nicotine is the heaviest weight — {count} days this fortnight.` |

#### FirmDirect

| Dim | + direction | − direction |
|---|---|---|
| sleep | `Sleep: top lever. {count} +Δ days from {threshold}.` | `Sleep: drag. {count} bottom days under {threshold}.` |
| dietQuality | `Whole food: doing work. {count} top days hit {threshold}.` | `Whole food: thin. {count} bottom days skipped.` |
| steps | `Steps: leading. {count} top days at {threshold}.` | `Steps: drag. {count} bottom days under {threshold}.` |
| exerciseMinutes | `Movement: earning. {count} top days at {threshold}.` | `Movement: light. {count} bottom days under {threshold}.` |
| extras | `Extras restraint: helping. {count} top days under {threshold}.` | `Extras: pulling. {count} bottom days at {threshold}+.` |
| nicotine | (n/a) | `Nicotine: heaviest weight. {count} days.` |

### `futureProLongFormParagraph(_:)` — 4 templates × 3 tones × slot variants

Pro-only. 3–4 paragraphs total. Each paragraph is a `Template` struct with named slots, filled from the week's actual data via `DateComponentsFormatter` / `NumberFormatter`.

Slot tokens used in Pro long-form:

| Token | Source | Format |
|---|---|---|
| `{delta}` | this week's projection delta vs last | `+0.4 years` |
| `{deltaSign}` | sign word | `gained` / `slipped` |
| `{dim}` | dominant driver dimension display name | `Sleep` |
| `{dimValue}` | this-week avg for that dim | `7.6h` |
| `{dimValuePrior}` | last-week avg for comparison | `6.8h` |
| `{dragDim}` | dominant drag dimension | `Extras` |
| `{dragValue}` | this-week drag value | `9 per week` |
| `{dragDetail}` | concrete factoid about the drag | `three high-extras nights Wed–Fri` |
| `{action}` | tone-conditional next-week ask | (see below) |

#### Para 1 — This week's headline movement

| Tone | Template |
|---|---|
| gentle | `{delta} {deltaSign} this week — a quiet ledger move in the right direction.` (positive) / `{delta} {deltaSign} this week. Worth a look at what shifted.` (negative) |
| coach | `{delta} {deltaSign} this week.` (both signs) |
| firmDirect | `Week's tally: {delta} {deltaSign}.` |

#### Para 2 — Dominant driver (always concrete numbers)

| Tone | Template |
|---|---|
| gentle | `{dim} carried this week — averaging {dimValue}, up from {dimValuePrior} the week before.` |
| coach | `{dim} was the lever — {dimValue} this week vs {dimValuePrior} last.` |
| firmDirect | `Top lever: {dim}. {dimValue} vs {dimValuePrior}.` |

#### Para 3 — The drag (concrete numbers)

| Tone | Template |
|---|---|
| gentle | `On the other side, {dragDim} crept up to {dragValue}. The biggest pull was {dragDetail}.` |
| coach | `Drag: {dragDim} reached {dragValue}. Largest contributor — {dragDetail}.` |
| firmDirect | `Drag: {dragDim} at {dragValue}. Source: {dragDetail}.` |

#### Para 4 — Action for next week

This paragraph is tone-divergent by structure — gentle invites, coach directs, firmDirect imperatives. The `{action}` slot is generated by the narrative engine from the same data that produced Para 3.

| Tone | Template |
|---|---|
| gentle | `For next week, you might try {action}. No pressure — small shifts compound.` |
| coach | `For next week: {action}.` |
| firmDirect | `Next week. {action}.` |

Action generation rules (in `NarrativeEngine`):
- If `dragDim` is `extras`: action = `dropping one of the {dragDetail-days} from the rotation`
- If `dragDim` is `sleep`: action = `holding 7+ hours on the bottom-three nights`
- If `dragDim` is `steps`: action = `adding 1,500 steps on rest days`
- If `dragDim` is `exerciseMinutes`: action = `one extra 30-min session`
- If `dragDim` is `dietQuality`: action = `one more whole-food day`
- If `dragDim` is `nicotine`: action = `zero-day streak target` (universal across tones — no euphemism)

### `futureWeeklyNarrativeSubhead(forWeekEnding:)` — single template per tone

Derived from `clock.now().snappedToLastSunday`. Not persisted; recomputed every tab open.

| Tone | Template |
|---|---|
| gentle | `Reflection from Sunday, {date}` |
| coach | `Reflection — week ending {date}` |
| firmDirect | `Week ending {date}` |

Slot `{date}` formatted as `MMM d` (e.g. `May 10`) via `DateFormatter.localizedString`.

## History summary surfaces

### `historySummaryHero(forState:)` — 5 states × 3 tones

States: `day0` / `day1to6` / `day7plusPositive` / `day7plusNegative` / `noSignal` (Day 7+ but <3 snapshots with data).

Slots used: `{net}` (e.g. `14d 6h`), `{startDate}` (e.g. `Mar 2`), `{year}` (e.g. `2023` — for 3-year truncation affordance).

#### Day 0 (`historySummaryDay0Hero`)

| Tone | Copy |
|---|---|
| gentle | `Your ledger starts today. Check back tomorrow.` |
| coach | `Ledger begins today. First entry tomorrow.` |
| firmDirect | `Ledger opens today.` |

#### Day 1–6 (`historySummaryDay1to6Hero`)

| Tone | Template |
|---|---|
| gentle | `+{net} since you started.` (positive) / `−{net} since you started.` (negative) |
| coach | `+{net} since {startDate}.` (positive) / `−{net} since {startDate}.` (negative) |
| firmDirect | `+{net} since {startDate}.` (both) |

#### Day 7+ positive (`historySummaryDay7PlusPositive`)

| Tone | Template |
|---|---|
| gentle | `+{net} banked since {startDate}. Your lived ledger.` |
| coach | `+{net} banked since {startDate}.` |
| firmDirect | `+{net} banked. Since {startDate}.` |

When the 3-year window truncation applies, swap `{startDate}` for `{year}` (e.g. `since 2023`).

#### Day 7+ negative (`historySummaryDay7PlusNegative`)

| Tone | Template |
|---|---|
| gentle | `−{net} since {startDate}. The lever's there when you're ready.` |
| coach | `−{net} since {startDate}.` |
| firmDirect | `−{net} since {startDate}.` |

#### No signal (`historySummaryNoSignal`)

Day 7+ but <3 days of HK/QuickLog data (typically HK denied entire week).

| Tone | Copy |
|---|---|
| gentle | `No signal yet. Once Apple Health or your check-ins start filling in, your ledger will too.` |
| coach | `No signal yet. Connect Apple Health or use QuickLog to start the ledger.` |
| firmDirect | `No signal. Connect HK or use QuickLog.` |

### `historyTopContributorsHeading` — 3 tones

Heading for the top-3 contributors panel, revealed at Day 7+.

| Tone | Copy |
|---|---|
| gentle | `What's been moving your ledger` |
| coach | `Top contributors` |
| firmDirect | `Top 3` |

### `historyTopContributorsItem(dim:direction:)` — pool per dim per direction × tone

Pool of pre-authored labels for each row. Slots: `{dimValue}` (e.g. `7.4h avg`).

#### Gentle (selected examples — full grid in code)

| Dim | + label | − label |
|---|---|---|
| sleep | `Sleep — averaging {dimValue}` | `Sleep — short at {dimValue}` |
| steps | `Steps — averaging {dimValue}` | `Steps — light at {dimValue}` |
| exerciseMinutes | `Exercise — {dimValue}/wk` | `Exercise — {dimValue}/wk` |
| dietQuality | `Whole food — {dimValue}/wk` | `Whole food — {dimValue}/wk` |
| extras | `Extras — light at {dimValue}/wk` | `Extras — at {dimValue}/wk` |
| nicotine | (skip if 0) | `Nicotine — {dimValue} days/wk` |

(Coach and firmDirect follow the same shape with terser phrasing — implementer fills using the established `gentle/coach/firmDirect` mapping pattern from existing pools.)

## Paywall

### `paywallWhatIfSimulatorScrollHeader` — single string

Rendered as the scroll-target section header in `PaywallSheet` when `scrollTo == .whatIfSimulator`.

```
The what-if simulator
```

(Title-case neutral — paywall copy is not tone-conditional in v1.)

## Telemetry

No copy. Telemetry events are emitted by the engine layer; no user-facing strings.

## Authoring notes for implementers

1. **Add ToneMode properties surface-first, not state-first.** Group new properties by feature (`futureHeadlineSubtext`, `futureColdLaunchLine`, `futureCapReached`) — do not sprinkle them between unrelated existing properties.

2. **Pool selection follows day-of-year mod count.** Existing `ReflectionPrompts.pool(for: tone, dayOfYear:)` is the precedent. Do not roll a new deterministic-selection helper.

3. **Templates use Swift `String` interpolation, not `String(format:)`.** Existing pattern in `ToneMode.swift` — slot-fill via `"\(value)"` not printf-style. Reads better and gets compile-time slot checks.

4. **Numeric slots format via `DateComponentsFormatter` / `NumberFormatter` at the call site, not inside the template.** Templates take pre-formatted strings. This keeps the template source readable and i18n-clean.

5. **Tone-distinctness test (`NarrativeEngineTests`):** paragraph-level diff between gentle/coach/firmDirect ≥ 30% by token diff. If two tones converge under any slot fill, re-author the template that converged. Carry-forward of existing tone-distinctness invariant.

6. **No mortality lexicon test:** existing invariant — none of these strings may include `die`, `death`, `dying`, `mortal`, etc. Carry forward.

7. **Negative-direction copy holds accountability without shaming.** "the lever's there when you're ready" / "is the drag" / "is the heaviest weight" — all acknowledge the drag without language like "failure" or "you let yourself down." Same standard as the 2026-05-10 bad-day pools.

## What this doc deliberately does not author

- **Re-baseline ritual copy.** Ritual deferred to v1.1; copy authored when the feature returns.
- **Reinstall-recovery sheet copy.** Sheet deferred.
- **HealthKit revoked-mid-flight banner copy.** Banner deferred.
- **Today trajectory peek copy.** Peek deferred to v1.1.
- **Onboarding-incomplete CTA copy.** Tab simply not rendered when onboarding incomplete; no CTA needed.
