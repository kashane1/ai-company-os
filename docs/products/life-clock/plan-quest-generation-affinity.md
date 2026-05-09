# Plan: Quest Generation & Per-Genre Affinity

**Date:** 2026-05-08
**Status:** Brainstorm complete — design locked, authoring + wiring deferred to follow-up sessions
**Supersedes:** the planned V3 separate 78-string tone-keying pass (absorbed into the pool's tone-keyed copy)

## Problem

`QuestEngine.generateDailyQuests` returns ~15 hardcoded quests across three categories (`movement / sleepRecovery / nutritionHabit`), tone-monotone, not driver-keyed, not user-aware. The same title and detail render for gentle / coach / firmDirect. We want a 90-quest pre-authored pool (30 per genre × 3 genres), tone-keyed at the slug level, selected via per-genre affinity scores so today's three quests are personalized to the user's life-clock drivers, baselines, and engagement history.

No LLM at runtime. Authored copy, deterministic selection, testable.

## Decisions

### D1 — Genres rename, not redesign

The pool's three genres are **`activity / diet / sleep`**. Today's engine uses `movement / sleepRecovery / nutritionHabit` ([QuestEngine.swift:40](products/life-clock-ios/Sources/Engines/QuestEngine.swift)). The migration is a rename + a small regrouping (recovery + hydration that currently sit under `sleepRecovery` re-home to `sleep`; the existing `consistency.*` fallback remains as out-of-pool engine machinery, not part of the 30-per-genre count).

### D2 — Within-genre diversity is an intent grid

Each genre defines an explicit intent taxonomy. Slugs are kinds, not numeric variants. Variant blindness is structurally prevented: two slugs cannot share an intent unless they differ in a second authored axis (time-of-day or context).

Indicative intent grids (final intents settled at authoring time):

- **activity** (8–10 intents × ~3 slugs each = 30): cardio, strength, steps, break-up-sitting, outdoor, mobility, NEAT, recovery, balance, deload-walk
- **diet** (8–10 intents × ~3 slugs): macro-shift, portion, hydration, processed-cut, vice-cut, timing, quality-upgrade, mindful-eating, swap, pre-meal-prep
- **sleep** (8–10 intents × ~3 slugs): wind-down, consistency, environment, pre-bed-stimulant-cut, screen-cut, recovery-aid, nap-discipline, morning-light, late-meal-cut, hydration-timing

Authoring the actual 30/30/30 is out of scope this session.

### D3 — Tone parity rule

For a given slug, all three tone variants must share **the same `intent`** and **the same `target` tuple** (if `target` is present). Diet quests with no numeric target use `intent` alone as the parity anchor — no special-case branch.

#### Schema

```swift
struct PoolQuest {
    let slug: String                    // "<genre>.<intent-shortname>.v<n>", primary key
    let genre: Genre                    // .activity / .diet / .sleep
    let intent: String                  // "walk-after-dinner", "protein-with-breakfast"
    let target: QuestTarget?            // optional structured target
    let copy: [ToneMode: ToneCopy]      // .gentle / .coach / .firmDirect → {title, detail}
    let exclusionGroups: [String]       // for daily-set conflict avoidance
    let eligibility: EligibilityFilter  // contraindications, vice-flag gates, cold-start tag
    let timeOfDay: TimeOfDayWindow?     // optional, e.g. .morning / .evening / .anytime
    let coldStartReachable: Bool        // true → eligible during 7-day discovery window
}

struct QuestTarget {
    let metric: String                  // "steps", "minutes", "hours-sleep", "servings"
    let value: Double
    let unit: String
}

struct ToneCopy {
    let title: String
    let detail: String
}
```

### D4 — Slug convention (locked)

Format: `<genre>.<intent-shortname>.v<n>`, matching the existing convention ([LifeClockSchema.swift:295-334](products/life-clock-ios/Sources/Models/LifeClockSchema.swift)). Examples: `activity.walk-after-dinner.v1`, `diet.swap-soda-water.v2`, `sleep.wind-down-30min.v1`. Bump `v<n>` only for breaking copy or target changes; never re-purpose a retired slug.

### D5 — Input surface (four streams)

1. **Drivers from ClockEngine** — `TimeLedgerEntry.driverType` totals get piped into QuestEngine as the per-genre **need-weight**. (Today: sibling-consumed, not wired.)
2. **HealthKit baselines** — reuse the existing steps p50×1.10 baseline ([QuestEngine.swift:292-299](products/life-clock-ios/Sources/Engines/QuestEngine.swift)), add a sleep p50 baseline (clamped 4–10h). Diet has no metric — `dietQualityBaseline` is the proxy.
3. **Onboarding signals** — `dietQualityBaseline`, `smokingStatus`, `alcoholFrequency`, `strengthFrequencyPerWeek`, `sleepGoalHours`, `cardioMinsPerWeek` feed initial need-weight + serve as hard contraindication filters.
4. **New `QuestEvent` table** — `(date, slug, kind: .shown | .picked | .replaced | .completed)`. Designed in this work; no UI changes required (`shown` fires on engine-emit, `picked` on add-to-plan, `replaced` on plan-editor swap, `completed` on tick).

### D6 — Affinity math

Two independent variables per genre, multiplied at selection time:

- **`affinity_g ∈ [0, 1]`** — preference. Init 0.5. Updated by `QuestEvent`s via EMA: `new = (1 - α·w) * old + α·w * target`, where `α = 0.2`.
- **`needWeight_g ∈ [0, 1]`** — priority. Updated daily from drivers + HK baselines + onboarding. Higher = "the user needs this genre today."

Event signal table:

| Event | target | weight `w` |
|---|---|---|
| `completed` | 1.0 | 1.0 |
| `picked` (not completed by EOD) | 0.0 | 1.0 |
| `replaced` | 0.0 | 1.5 |
| `shown` (not picked by EOD) | 0.3 | 0.5 |

End-of-day cron resolves `picked` → completed/abandoned and `shown` → kept/replaced/passed-over.

**Hard floor (anti-trap):** every genre gets ≥ 1 slot in the slate of 3. Affinity controls *which slug within genre*; it cannot starve a genre. This is the system's escape valve given affinity is invisible and unadjustable.

### D7 — Cold-start

"Cold-start" = no quest history. NOT no HealthKit signal. Day 1 already has weeks of HK history via `HistoricalImportCoordinator`.

- **Affinity_g** = 0.5 across all three genres on day 1 (no event signal yet).
- **NeedWeight_g** is fully informed day 1: HK steps p50 < 5k → activity high; sleep p50 < 6.5h → sleep high; `dietQualityBaseline=='rough'` → diet high. **HK signal trumps onboarding self-report on disagreement** (e.g. `dietQualityBaseline=='great'` + 2,400 daily steps → activity need-weight stays high).
- **Eligibility filters** apply day 1 from onboarding (smoking-tagged slugs only if `smokingStatus != none`; alcohol-cut slugs only if `alcoholFrequency != none`).
- **Discovery window (days 1–7):** affinity weight in selection is dampened by a factor (e.g. `0.3 + 0.7 * (day/7)`) so the system rotates broadly while the EMA accumulates signal. Need-weight is undampened.

### D8 — Selection algorithm

Slate of 3, one per genre (hard floor). Greedy, deterministic given inputs + date seed.

```text
score(slug, today) =
    affinity_g(slug.genre) ^ discoveryWeight(today)
  * needWeight_g(slug.genre)
  * recencyDecay(slug)              // recently-shown slugs deprioritize
  * timeOfDayFit(slug, today)       // 1.0 by default; lower if mismatch is severe
```

Selector loop per day:

1. **Filter** the 90-slug pool by hard eligibility (vice flags, cold-start tag, contraindications).
2. **For each genre**, compute scores and select the top-scored eligible slug. Ties broken deterministically by slug.
3. **Conflict pass**: if two selected slugs share an `exclusionGroup`, replace the lower-scored one with the next-best within its genre that doesn't collide. Repeat until stable.
4. **Resolve tone** by reading `slug.copy[userProfile.toneMode]`.
5. **Emit** the slate; log a `shown` event for each.

Pairwise slug-on-slug rules are out of model — conflicts are always expressed via shared `exclusionGroups` (`evening-energy`, `pre-bed-stimulant`, `morning-cardio`, etc.). Slugs declare 0–N groups.

### D9 — Test plan (all four layers ship)

1. **Schema validity + uniqueness** — every pool entry has all required fields; slug matches format; `target` is well-formed if present; copy contains all three tone keys; no slug appears twice.
2. **Tone parity + distinctness** — for each slug: all three tone variants reference identical `intent` and identical `target` tuple (parity); tone strings differ pairwise (distinctness); vocabulary smoke-test (gentle excludes firm-direct vocabulary list, firmDirect excludes hedging vocabulary). Iterate via `for tone in ToneMode.allCases` per the existing convention ([ToneModeTests.swift:77-99](products/life-clock-ios/Tests/ToneModeTests.swift)).
3. **Coverage + reachability** — each genre has ≥ N intents (target N=8); every slug is eligible under at least one realistic user state (no never-surfaced quests); default cold-start state surfaces ≥ 1 slug per genre; no genre starves under any realistic onboarding combo.
4. **Selector property tests** — generative: feed M synthetic `(HK history + onboarding + event history)` states into the selector. Assert per run: 3 distinct slugs, 3 genres represented, no exclusion-group violation, all tone variants resolved, deterministic given same inputs and seed.

## Failure-mode mitigations

| Failure mode | Mitigation |
|---|---|
| Medically unsound for this user | Hard `eligibility` filter using `smokingStatus`, `alcoholFrequency`, future condition flags. Eliminated at filter step, never reaches scoring. |
| Unreachable target | Targets are clamped per slug to a band relative to HK baseline (e.g. step targets defined as `baseline × multiplier` rather than absolute). |
| Repeat-refused stale | `recencyDecay` lowers score after a `shown`; two consecutive `replaced` events on the same slug push affinity well below floor for the *slug*, not the genre. |
| Never-surfaced | Reachability test (D9 layer 3) catches dead slugs at lint time. |
| Cold-start blank | HK-informed need-weight + onboarding filters give a personalized day 1 (D7). |
| Affinity over-concentration | Hard genre floor (D6) — every slate has all three genres regardless of affinity. |
| Variant blindness | Intent grid (D2) — two slugs cannot share an intent without a second axis of variation. Authoring lint flags close-duplicates. |
| Multi-quest contradiction | `exclusionGroups` (D8 step 3) prevent same-day contradictions. |
| Time-of-day mismatch | Optional `timeOfDay` window per slug downweights mismatches in scoring. |
| Hidden-affinity trap | Four-event tracking (D5) + `replaced` weighted 1.5× makes active reject loud; per-genre floor + per-slug recencyDecay together guarantee a user who hates a slug stops seeing it without losing the genre. |
| Tone meaning drift | D9 layer 2 makes parity drift a build-time failure, not a polish bug. |
| Diet parity ambiguity | `intent` (string) is the parity anchor for diet, no `target` required. Same schema as activity/sleep, no branching. |
| Authoring rot | Pool stored in versioned data files (see D10); `v<n>` slug bumps surface intentional changes; the four-layer test gate runs on every PR touching the pool. |

## D10 — Phased delivery

Each phase is a separate session.

- **Phase 1 (this session, complete):** brainstorm + plan doc.
- **Phase 2:** schema + storage. Add `PoolQuest` data file format (JSON or Swift literal — decide in plan session), `QuestEvent` SwiftData entity, `Quest.tone`/copy resolution helper, `EligibilityFilter` types. No selector yet, no pool authored. Tests for D9 layers 1, 2, 4 (running against a small fixture pool of 6–9 slugs).
- **Phase 3:** selector implementation. Affinity + need-weight state. Cold-start logic. Wire `QuestEvent` emission at the four UI hook points (engine-emit, plan-add, plan-replace, complete-tick). End-of-day resolver.
- **Phase 4 (parallel-able with Phase 3 once schema lands):** author the 90 quests. Iterative — 30 at a time per genre, behind a feature flag, rotating into production as the four-layer test gate goes green per genre.
- **Phase 5:** retire the inlined quest constructors in `QuestEngine.swift`. Migrate completion records by slug (already keyed that way; `applyPersistedCompletions` already does this — it's clean).

## Out of scope for this plan

- Authoring the 90 seed quests (Phase 4).
- Selector implementation code (Phase 3).
- Migration of completion tracking (Phase 5; the slug-keyed approach already in place makes this trivial).
- A user-visible "I don't want this genre" override — explicitly rejected; the four-event refusal model is the escape valve.
- Adaptive slate size (kept at 3; revisit only if data shows warranted).

## Followups / open questions for next session

These are sub-decisions to settle when Phase 2 starts, not in this brainstorm:

- Pool storage format: JSON file vs Swift literal vs SwiftData seed. JSON gives the cleanest authoring loop and review diff; Swift literal is type-safe at compile time. Lean: **JSON in `products/life-clock-ios/Resources/QuestPool/*.json`** with a Swift codegen step.
- Final intent list per genre (≥8 intents per genre). Author + designer call.
- Final exclusion-group vocabulary (5–10 groups expected: `evening-energy`, `pre-bed-stimulant`, `morning-cardio`, `fasted-required`, `meal-adjacent`, etc.).
- `recencyDecay` curve shape (linear N-day cooldown vs exponential).
- The lint threshold for "close-duplicate" detection in D9 (cosine similarity? edit distance? human review only?).
- Vocabulary lists for the tone-distinctness smoke test (forbidden words per tone). Steal from the recent firmDirect softening commit ([8f94363](https://github.com/anthropics/apps), [13bffcc](https://github.com/anthropics/apps)) as a starting point.
- Ownership of the pool maintenance ritual — is the author the same person every quarter, or does it rotate? Cadence?
