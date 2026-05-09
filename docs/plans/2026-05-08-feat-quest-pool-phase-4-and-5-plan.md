---
title: "feat: Quest Pool Phase 4 (authoring) + Phase 5 (cutover)"
type: feat
status: draft
date: 2026-05-08
origin: docs/plans/2026-05-08-feat-quest-pool-affinity-engine-plan.md
---

# feat: Quest Pool Phase 4 (90-quest authoring) + Phase 5 (cutover)

## Overview

Phase 4 authors the 90-quest production pool (30 per genre × 3 genres × 3 tones = 270 strings + targets + exclusion groups + eligibility filters). Phase 5 flips the `useQuestPoolEngine` flag and retires the 15 inlined `Quest(...)` constructors.

**Phase 4 is content work with a quality gate. Realistic cycle count: 3-5 LFG cycles.** Authoring 90 tone-aware quests with proper intent assignments + per-genre exclusion-group placement does not fit in a single agent run at high quality. Recommended split: Phase 4a (foundations + activity), Phase 4b (diet), Phase 4c (sleep), Phase 5a (flag flip), Phase 5b (legacy deletion). A single LFG can attempt all of Phase 4 in one PR if context allows — quality bar is the gate, not the cycle count.

**Phase 5a flag flip is calendar-bound: ≥1-week production bake before Phase 5b lands.** The agent ships the flag-flip PR; the user merges and bakes; the agent ships the legacy-deletion PR after.

## Origin

This plan inherits design from:
- **Master plan**: [docs/plans/2026-05-08-feat-quest-pool-affinity-engine-plan.md](docs/plans/2026-05-08-feat-quest-pool-affinity-engine-plan.md). D2 (intent grid), D3 (parity tuple), D4 (slug convention), D9 (test plan), D10 (phased delivery).
- **Phase 3 plan**: [docs/plans/2026-05-08-feat-quest-pool-phase-3-engines-plan.md](docs/plans/2026-05-08-feat-quest-pool-phase-3-engines-plan.md). Tracks 3a–3d shipped in PRs #31 + #32.
- **Phase 3 prep findings**: [todos/049-pending-p3-quest-pool-phase3-prep.md](todos/049-pending-p3-quest-pool-phase3-prep.md) — closed by PRs #31 + #32.
- **Phase 3 polish + deferrals**: [todos/050](todos/050-pending-p3-quest-pool-phase3-polish-and-deferrals.md), [todos/051](todos/051-pending-p3-quest-pool-phase3cd-polish-and-deferrals.md). Phase 5a hardening pulls from these.

State as of 2026-05-08:
- PR #30 (Phase 2 — schema), PR #31 (Phase 3a+3b — engines + bootstrap), PR #32 (Phase 3c+3d — wiring) all open in stacked review.
- `useQuestPoolEngine` defaults `false` → production behavior unchanged.
- Production JSON pool (`Resources/QuestPool/{activity,diet,sleep}.json`) ships empty.
- Fixture pool (6 slugs) is the only authored content; tests use it.

## Phase 4 — Authoring

### 4.0 — Restore `EligibilityFilter` on `PoolQuest`

Phase 2 cut `EligibilityFilter` from `PoolQuest` per simplicity-reviewer (YAGNI when fixture pool had no contraindicated slugs and production pool was empty). Phase 4 brings it back because authored slugs reference contraindications.

Add to [Sources/Models/QuestPoolTypes.swift](products/life-clock-ios/Sources/Models/QuestPoolTypes.swift):

```swift
struct EligibilityFilter: Codable, Equatable, Hashable, Sendable {
    /// nil = any; true = smokingStatus != "none"; false = smokingStatus == "none"
    let requiresSmoker: Bool?
    /// nil = any; true = alcoholFrequency != "rare" && != "none"
    let requiresDrinker: Bool?
    /// nil = any; true = strengthFrequencyPerWeek > 0
    let requiresStrengthRoutine: Bool?
    /// false = excluded from selection during the 7-distinct-open-days
    /// discovery window. Use for slugs that need familiarity to be
    /// useful (e.g., "track macros for one meal" assumes the user has
    /// engaged with diet quests already).
    let coldStartReachable: Bool
    /// Optional time-of-day window. nil = anytime.
    let timeOfDay: TimeOfDayWindow?
}

enum TimeOfDayWindow: String, Codable, Sendable {
    case morning, midday, evening, anytime
}
```

Wire into `QuestSelector.select(...)` as a hard-filter step BEFORE scoring:

```swift
let eligibleByGenre: [Genre: [PoolQuest]] = pool.byGenre.mapValues { quests in
    quests.filter { quest in
        Self.isEligible(
            quest,
            profile: profile,
            distinctOpenDays: profile.distinctOpenDays
        )
    }
}
```

Add `static func isEligible(_:profile:distinctOpenDays:) -> Bool` that gates each filter field. Cold-start reachability uses 7 as the window threshold (matches discovery damp).

### 4.1 — Intent grid (settle per genre)

Each genre gets 8–10 intents × ~3 slugs = 30 slugs. The grid below is the **starting point**; revise during authoring if the slug-per-intent count doesn't divide cleanly.

**Activity (10 intents × 3 slugs):**
- `cardio` — light cardio session
- `strength` — bodyweight or weighted strength move
- `steps` — daily step target / push
- `break-up-sitting` — pomodoro-style movement break
- `outdoor` — get outside
- `mobility` — stretch / mobility flow
- `neat` — non-exercise activity (stairs, errands, walk-instead-drive)
- `recovery-walk` — easy active recovery
- `balance` — balance training (one-leg stand, etc.)
- `deload-walk` — gentle low-stress walk

**Diet (10 intents × 3 slugs):**
- `macro-shift` — protein/fiber/water emphasis at a meal
- `portion` — portion control
- `hydration` — water intake
- `processed-cut` — reduce processed foods
- `vice-cut` — alcohol / caffeine cut
- `timing` — meal timing / eating window
- `quality-upgrade` — swap to whole foods
- `mindful-eating` — eat slowly, no distractions
- `swap` — sugar swap, oil swap, soda swap
- `pre-meal-prep` — prep one ingredient ahead

**Sleep (10 intents × 3 slugs):**
- `wind-down` — pre-bed routine
- `consistency` — same bedtime within a window
- `environment` — bedroom prep (cool, dark)
- `pre-bed-stimulant-cut` — caffeine cutoff timing
- `screen-cut` — screens off N min before bed
- `recovery-aid` — stretch / breathing / journaling
- `nap-discipline` — short naps or none
- `morning-light` — sunlight on waking
- `late-meal-cut` — last meal N hours before bed
- `hydration-timing` — front-load water early

### 4.2 — Exclusion-group vocabulary

Settle 5–10 group names for the production pool. Starting set:

- `meal-adjacent` — anything tied to a specific meal slot (walk-after-dinner conflicts with add-protein-to-dinner)
- `evening-energy` — anything that adds physical energy late (evening cardio conflicts with wind-down)
- `pre-bed-stimulant` — caffeine cuts conflict with morning-coffee quests
- `morning-cardio` — morning cardio conflicts with morning-stretch
- `intense-exertion` — intense workouts conflict with recovery quests
- `screen-time` — screen-on quests conflict with screen-cut quests
- `meal-timing` — eating-window quests conflict with mid-day-snack quests

Document the vocabulary in `docs/products/life-clock/quest-pool-vocab.md` so future authors don't introduce drift.

### 4.3 — Slug convention (locked)

Format: `<genre>.<intent>.v<n>` per master plan D4. For Phase 4 production:

- `activity.walk-after-dinner.v1`
- `diet.water-with-meal.v1`
- `sleep.wind-down-30min.v1`

No `fixture-` prefix on production slugs. The fixture pool's `fixture-*` slugs stay separate (they live in `Resources/QuestPool/fixture.json`, never in production basenames).

### 4.4 — Tone voice guide

Authored tone variants must follow the project's established register patterns from [Sources/App/ToneMode.swift](products/life-clock-ios/Sources/App/ToneMode.swift) (40+ existing examples).

| Tone | Voice | Title pattern | Detail pattern |
|---|---|---|---|
| `gentle` | Warm, encouraging, soft. No urgency. | "A short walk after dinner" | "Just ten gentle minutes after your evening meal. It can feel restful." |
| `coach` | Balanced, action-oriented. Names the why. | "Walk 10 minutes after dinner" | "A short walk after your largest meal helps glucose response. Keep it easy." |
| `firmDirect` | Short, no hedging. Imperative. | "10 minutes. After dinner. Walk." | "After tonight's biggest meal, walk ten minutes. That's the rep." |

**Constraints (from existing QuestEngine.swift comments):**
- No medication, supplements, or specific clinical targets.
- Diet quests: never reference calories, macros (in numeric form), gram targets, named diets ("keto", "intermittent fasting"), or "clean food" / "bad food" framing.
- Coarse, encouraging, body-neutral.
- No reference to weight loss as a goal.

### 4.5 — Per-slug authoring template

Use [Resources/QuestPool/fixture.json](products/life-clock-ios/Resources/QuestPool/fixture.json) as the working template. Each entry:

```json
{
  "slug": "<genre>.<intent>.v1",
  "genre": "activity|diet|sleep",
  "intent": "<intent-shortname-matching-section-4.1>",
  "target": { "metric": "...", "value": ..., "unit": "..." },
  "exclusionGroups": ["<group-from-section-4.2>"],
  "eligibility": {
    "requiresSmoker": null,
    "requiresDrinker": null,
    "requiresStrengthRoutine": null,
    "coldStartReachable": true,
    "timeOfDay": "anytime"
  },
  "copy": {
    "gentle":      { "title": "...", "detail": "..." },
    "coach":       { "title": "...", "detail": "..." },
    "firm_direct": { "title": "...", "detail": "..." }
  }
}
```

`target` is optional — diet slugs without numeric targets omit it (`intent` alone is the parity anchor per master plan D3).

### 4.6 — Quality gates (D9 layers, plus tone parity smoke-tests)

Before merging Phase 4 PRs, the following test gates must be green:

1. **Schema validity + slug uniqueness** — `QuestPoolTests.testProductionPoolHasNoSlugCollisions` etc.
2. **Tone parity + distinctness** — `QuestPoolToneParityTests.testProductionPoolToneInvariants`. Every slug has all three tones; tones differ pairwise; vocabulary smoke-test passes per [Sources/App/ToneMode.swift](products/life-clock-ios/Sources/App/ToneMode.swift) register patterns.
3. **Coverage + reachability** — every authored slug must be reachable for at least one realistic synthetic user (no never-surfaced quests). Add `QuestPoolToneParityTests.testEveryProductionSlugIsReachable`.
4. **No exclusion-group deadlocks** — generative test with random affinity + need-weight: assert selector never falls back to `consistency.open-app-tomorrow.v1` for a default user.
5. **Eligibility filter coverage** — `requiresSmoker == true` slugs only emit when `smokingStatus != "none"`.

Each gate fails the build, not just the test. The Phase 4 PR is not mergeable until all five are green.

### 4.7 — Authoring increments (suggested phasing)

If the agent's context window can't sustain 90 quests at quality, split:

- **Phase 4a** — Restore `EligibilityFilter` + finalize intent grid + exclusion-group vocab + author 30 activity quests. PR ships with empty `diet.json` and `sleep.json` (production guard at PR #30 ships them empty by default; the empty-pool flag-on guard from PR #32 falls back to legacy).
- **Phase 4b** — Author 30 diet quests.
- **Phase 4c** — Author 30 sleep quests.

Each sub-phase is a separate PR. The flag stays default `false` throughout — no production impact until Phase 5a.

## Phase 5 — Cutover

### 5a — Flag flip

One-line code change: `useQuestPoolEngine: Bool = true` in [Sources/Models/LifeClockSchema.swift](products/life-clock-ios/Sources/Models/LifeClockSchema.swift).

**Preconditions:**
- All Phase 4 sub-phases merged.
- All four quality gates green on the production pool.
- Phase 3 polish + deferrals from todos 050 + 051 reviewed; any items marked "must-fix-before-flag-flip" addressed (specifically the data-integrity items 2/3 and the retention policy from todo 051).

**Acceptance:**
- [ ] Existing user upgrades flip to the new path on next launch.
- [ ] Day-1 affinity = 0.5 across all genres (no events yet) → discovery damp dampens to ~0.81×; need-weight drives initial selection per HK + onboarding.
- [ ] First-week selection feels personalized but not locked-in.
- [ ] Real-device verification: no migration crash on V1.5.0 → V1.6.0 (this is a value-only change, lightweight migration applies).

**Production bake: ≥1 week.** Watch for:
- `selector.deadlock` telemetry events (should be near-zero).
- `pool.empty.guard` telemetry (should be zero — pool is now non-empty).
- User reports of unfamiliar quest copy or tone misalignment.
- Affinity behavior: are EMA values converging where expected?

### 5b — Legacy deletion

Once 5a has baked ≥1 week with no rollback signals:

1. Delete the 15 inlined `Quest(...)` constructors in [QuestEngine.swift](products/life-clock-ios/Sources/Engines/QuestEngine.swift) — `movementVariants`, `sleepRecoveryVariants`, `nutritionHabitVariants`, plus `consistencyFallback` (kept as the deadlock fallback per master plan G16).
2. Delete the `legacyEnginePath` private method.
3. Remove the `useQuestPoolEngine` flag from `UserProfile`. Update existing tests that toggle the flag.
4. Phase out `Quest.title` / `Quest.detail` reads from views — route through `QuestPool.copy(slug:tone:)`. Delete the snapshot population in `selectorPath`.
5. Migrate any historical `Quest` rows whose `slug` is in the legacy slug→genre map (via `bootstrapQuestGenres`) — already in place; no new code.
6. Remove the `LegacyQuestCompatShim` if added by intermediate work.

Tests touched:
- `QuestEngineTests.swift` — old assertions over inlined slugs deleted; replace with selector-output assertions over the production pool (some already exist via `QuestEngineSelectorPathTests.swift`).
- `LifeClockE2ETests.swift` — verify no breakage; existing test was already pre-existing-failure on main.
- `QuestEngineSelectorPathTests.swift` — drop the `testFlagOffPreservesLegacyEnginePath` test (no flag-off path to preserve).
- All Phase 3c integration tests in `LifeClockStoreTests` that use `flagOn: false` mode — drop the parameter and run unconditionally.

LOC delta: roughly -250 LOC in `QuestEngine.swift`, -50 LOC in tests, +20 LOC in pool resolution helpers.

## PR sequencing (recommended)

| PR | Title | Dependencies | Calendar |
|---|---|---|---|
| Phase 4a | activity authoring + EligibilityFilter | PR #32 merged | Day 0 |
| Phase 4b | diet authoring | Phase 4a merged | Day 0–2 |
| Phase 4c | sleep authoring | Phase 4b merged | Day 0–4 |
| Phase 5a | flip useQuestPoolEngine default | Phase 4c merged + tests green | Day 4–7 |
| (bake) | ≥1-week production bake | Phase 5a merged | Day 7–14 |
| Phase 5b | delete legacy constructors | Phase 5a baked | Day 14+ |

A single LFG run can attempt 4a–5a in one cycle if context permits; 5b waits for the bake regardless. The user controls bake timing.

## Test plan

In addition to the four quality gates from §4.6:

- `QuestPoolToneParityTests.testEveryProductionSlugIsReachable` — for every slug in the production pool, find at least one realistic synthetic user state (HK history + onboarding combo) where the selector emits it.
- `QuestSelectorTests.testNoDeadlockOnDefaultUserAcrossDays` — generative: 30 days of synthetic refreshes; selector never falls back to consistency-fallback for a default-cold-start user.
- `LifeClockStoreTests.testFlagFlipPathProducesPoolSlugs` — set `useQuestPoolEngine = true`, refresh, assert all emitted slugs are in `Genre.activity / .diet / .sleep` namespaces (no legacy `movement.*` etc.).
- `QuestPoolTests.testEligibilityFilterFiltersCorrectly` — synthetic profiles with each filter field set; assert filtered slugs don't appear in selector output.

## Acceptance criteria

### Functional

- [ ] All 90 production-pool slugs (30 per genre) authored, tone-parity green, distinctness green, vocabulary smoke-test green.
- [ ] `EligibilityFilter` restored on `PoolQuest` and wired into selector.
- [ ] Exclusion-group vocabulary documented in `docs/products/life-clock/quest-pool-vocab.md`.
- [ ] No selector deadlock for any synthetic default-user state.
- [ ] `useQuestPoolEngine` defaults `true` after Phase 5a.
- [ ] Legacy inlined constructors deleted in Phase 5b.

### Non-functional

- [ ] Selector p99 < 5ms with 90-slug pool + 1500 events (from Phase 3 plan acceptance).
- [ ] Pool JSON files < 200KB total.
- [ ] V1.5.0 → V1.6.0 (Phase 5a flag default flip) lightweight migration runs cleanly.

### Quality gates

- [ ] All four Phase 4 quality gates green.
- [ ] All Phase 2 + 3 tests still pass.
- [ ] Real-device verification on Phase 5a flag flip.

## Out of scope

- Localization of authored quest copy. English-only for Phase 4.
- A/B testing harness on top of the deterministic selector.
- iCloud sync for `QuestEvent` (deferred per master plan).
- iOS 18 deployment-target bump + `#Index<QuestEvent>` macro.
- True cross-version migration test (V1.3.0 → V1.5.0 → V1.6.0 path) — todo 050 #10.

## Out of scope but flag if hit

- New `EligibilityFilter` field design. The five fields above are the locked set. If authoring reveals a sixth (e.g., `requiresWearsFitnessTracker`), flag for review before adding.
- New exclusion-group vocabulary. The seven groups above are the locked set. New ones surface in Phase 4 only with explicit reasoning.
- Tone vocabulary smoke-test forbidden-word lists. Reuse the lists already in `QuestPoolToneParityTests.swift` from Phase 2; expand only if a new tone-drift class surfaces.

## Sources

- Master plan: [docs/plans/2026-05-08-feat-quest-pool-affinity-engine-plan.md](docs/plans/2026-05-08-feat-quest-pool-affinity-engine-plan.md)
- Phase 3 plan: [docs/plans/2026-05-08-feat-quest-pool-phase-3-engines-plan.md](docs/plans/2026-05-08-feat-quest-pool-phase-3-engines-plan.md)
- Phase 3c+3d wiring plan: [docs/plans/2026-05-08-feat-quest-pool-phase-3cd-wiring-plan.md](docs/plans/2026-05-08-feat-quest-pool-phase-3cd-wiring-plan.md)
- Brainstorm: [docs/products/life-clock/plan-quest-generation-affinity.md](docs/products/life-clock/plan-quest-generation-affinity.md)
- Predecessor PRs: [#30](https://github.com/kashane1/ai-company-os/pull/30), [#31](https://github.com/kashane1/ai-company-os/pull/31), [#32](https://github.com/kashane1/ai-company-os/pull/32)
- Phase 3 polish + deferrals: [todos/050](todos/050-pending-p3-quest-pool-phase3-polish-and-deferrals.md), [todos/051](todos/051-pending-p3-quest-pool-phase3cd-polish-and-deferrals.md)
- Tone register precedent: [Sources/App/ToneMode.swift](products/life-clock-ios/Sources/App/ToneMode.swift)
- Tone parity test pattern: [Tests/QuestPoolToneParityTests.swift](products/life-clock-ios/Tests/QuestPoolToneParityTests.swift)
- Authoring template: [Resources/QuestPool/fixture.json](products/life-clock-ios/Resources/QuestPool/fixture.json)
