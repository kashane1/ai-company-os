---
title: "feat: Quest Pool Phase 4a — activity authoring + EligibilityFilter"
type: feat
status: active
date: 2026-05-08
origin: docs/plans/2026-05-08-feat-quest-pool-phase-4-and-5-plan.md
---

# feat: Quest Pool Phase 4a — activity authoring + EligibilityFilter

## Scope

This is the first authoring sub-phase of Phase 4. It ships:

1. `EligibilityFilter` value type restored on `PoolQuest`.
2. Selector wiring that hard-filters ineligible slugs before scoring.
3. 30 production-pool activity quests in
   [products/life-clock-ios/Resources/QuestPool/activity.json](products/life-clock-ios/Resources/QuestPool/activity.json).
4. Exclusion-group vocab doc at
   `docs/products/life-clock/quest-pool-vocab.md`.
5. Tests: eligibility filter unit tests, production pool tone parity
   gate (already a placeholder, becomes load-bearing now), reachability
   gate for activity slugs.

**Out of scope (Phase 4b/4c):** diet (30 slugs), sleep (30 slugs).
`diet.json` + `sleep.json` stay empty in this PR. The flag stays
default `false` so production behavior is unchanged on merge.

## Origin

- Phase 4 + 5 plan: [docs/plans/2026-05-08-feat-quest-pool-phase-4-and-5-plan.md](docs/plans/2026-05-08-feat-quest-pool-phase-4-and-5-plan.md). §4.0 (EligibilityFilter), §4.1 (activity intent grid), §4.2 (exclusion-group vocab), §4.4 (tone voice guide), §4.6 (quality gates).
- Master plan: [docs/plans/2026-05-08-feat-quest-pool-affinity-engine-plan.md](docs/plans/2026-05-08-feat-quest-pool-affinity-engine-plan.md). D2/D3/D4/D9.
- Predecessor PRs: [#30](https://github.com/kashane1/ai-company-os/pull/30), [#31](https://github.com/kashane1/ai-company-os/pull/31), [#32](https://github.com/kashane1/ai-company-os/pull/32).

## Execution sequence

### 1. EligibilityFilter restoration

Add to [products/life-clock-ios/Sources/Models/QuestPoolTypes.swift](products/life-clock-ios/Sources/Models/QuestPoolTypes.swift):

```swift
struct EligibilityFilter: Codable, Equatable, Hashable, Sendable {
    let requiresSmoker: Bool?
    let requiresDrinker: Bool?
    let requiresStrengthRoutine: Bool?
    let coldStartReachable: Bool
    let timeOfDay: TimeOfDayWindow?
}

enum TimeOfDayWindow: String, Codable, Sendable {
    case morning, midday, evening, anytime
}
```

Add `eligibility: EligibilityFilter?` field to `PoolQuest` (optional —
fixture pool slugs decode unchanged because they don't carry the field;
production-pool slugs always emit one).

`coldStartReachable` defaults to `true` when `eligibility` is nil. The
filter is purely additive when omitted (back-compat with fixture).

### 2. QuestSelector wiring

Insert a hard-filter step in `QuestSelector.select(...)` BEFORE the
per-genre scoring loop:

```swift
let eligibleByGenre: [Genre: [PoolQuest]] = pool.byGenre.mapValues { genreQuests in
    genreQuests.filter { Self.isEligible($0, profile: profile) }
}
```

Add `static func isEligible(_:profile:) -> Bool` that returns false when:
- `requiresSmoker == true` and `profile.smokingStatus == "none"`.
- `requiresSmoker == false` and `profile.smokingStatus != "none"`.
- `requiresDrinker == true` and (`alcoholFrequency` ∈ `{"none","rare"}`).
- `requiresDrinker == false` and (`alcoholFrequency` ∉ `{"none","rare"}`).
- `requiresStrengthRoutine == true` and `strengthFrequencyPerWeek == 0`.
- `coldStartReachable == false` and `distinctOpenDays < 7`.

`timeOfDay` is decorative for Phase 4a (no time-of-day refresh routing
yet — record + load-bearing in Phase 4b/c). Pass-through for now.

### 3. Activity intent grid (10 × 3)

| Intent | Slug 1 | Slug 2 | Slug 3 |
|---|---|---|---|
| `cardio` | `activity.brisk-walk-20.v1` | `activity.cardio-zone2-15.v1` | `activity.bike-or-row-15.v1` |
| `strength` | `activity.bodyweight-circuit.v1` | `activity.pushups-set.v1` | `activity.strength-session-30.v1` |
| `steps` | `activity.steps-baseline-plus.v1` | `activity.lunchtime-walk.v1` | `activity.evening-stroll.v1` |
| `break-up-sitting` | `activity.standup-each-hour.v1` | `activity.pomodoro-walk.v1` | `activity.desk-stretch-3.v1` |
| `outdoor` | `activity.outside-15.v1` | `activity.park-loop.v1` | `activity.sunlit-walk.v1` |
| `mobility` | `activity.morning-stretch.v1` | `activity.hip-mobility-flow.v1` | `activity.shoulder-rolls.v1` |
| `neat` | `activity.stairs-instead.v1` | `activity.errand-on-foot.v1` | `activity.park-far.v1` |
| `recovery-walk` | `activity.easy-walk-10.v1` | `activity.cooldown-walk.v1` | `activity.gentle-stroll.v1` |
| `balance` | `activity.balance-stand-1min.v1` | `activity.heel-to-toe-walk.v1` | `activity.single-leg-balance.v1` |
| `deload-walk` | `activity.deload-walk-10.v1` | `activity.recovery-day-walk.v1` | `activity.easy-day-stroll.v1` |

Each slug carries: `intent`, `target` (when numeric), `exclusionGroups`
(optional), `eligibility` (optional — only used for slugs with real
contraindication shape), and three tone variants per §4.4 voice guide.

### 4. Exclusion-group placement

From the seven-group vocab in §4.2, the relevant ones for activity:
- `evening-energy` — slugs that cue cardio/strength late (conflicts with sleep wind-down).
- `morning-cardio` — morning-only cardio (conflicts with morning-stretch).
- `intense-exertion` — vigorous workouts (conflicts with recovery slugs).
- `meal-adjacent` — for slugs that bind to a meal slot.

Activity 4a applies these conservatively (only where genuine conflict
exists with future diet/sleep slugs in 4b/4c). Mostly empty arrays in
4a since intra-genre conflicts within activity-only slate are
irrelevant (the selector picks one quest per genre).

### 5. Eligibility usage

Activity 4a uses eligibility filters sparingly. Most slugs are
universally appropriate. Specific cases:
- `activity.strength-session-30.v1` — requiresStrengthRoutine = true (a
  user with `strengthFrequencyPerWeek == 0` shouldn't be told to do a
  30-min strength session cold).
- `activity.pushups-set.v1` — requiresStrengthRoutine = true.
- `activity.bodyweight-circuit.v1` — requiresStrengthRoutine = true.
- `activity.cardio-zone2-15.v1` — coldStartReachable = false (zone-2
  framing assumes the user has engaged with activity tracking).

All other activity slugs default to "anyone, anytime" — the simplest
shape (no `eligibility` field, decoded as nil).

### 6. Tone voice gates

Per §4.4 the three tones must:
- **gentle**: warm, encouraging, soft. Avoid imperatives. ~15-25 words detail.
- **coach**: balanced, names the why. Action-oriented. ~15-25 words detail.
- **firmDirect**: short, no hedging. Imperative. Often <20 words detail.

The vocabulary smoke-test in
[products/life-clock-ios/Tests/QuestPoolToneParityTests.swift](products/life-clock-ios/Tests/QuestPoolToneParityTests.swift)
will fail any slug where gentle copy contains firm-direct vocab
(`Banked`, `owe`, `tally`, `reckoning`) or vice versa. Author against
that gate.

### 7. Tests

Add to [products/life-clock-ios/Tests/QuestPoolTests.swift](products/life-clock-ios/Tests/QuestPoolTests.swift):
- `testEligibilityFilterFieldsRoundTripJSON` — encode/decode all five fields.
- `testProductionPoolNonEmptyForActivity` — `pool.quests(in: .activity).count == 30`.

Add new `QuestSelectorEligibilityTests.swift`:
- `testFilterRequiresSmokerExcludesNonSmokers`
- `testFilterRequiresStrengthExcludesNoRoutine`
- `testColdStartReachableFalseExcludesEarlyDays`
- `testNilEligibilityIsAlwaysReachable`

The existing
`QuestPoolToneParityTests.testProductionPoolToneInvariants` becomes
load-bearing automatically — pool now has 30 entries to cover.

Reachability test (new):
- `QuestPoolToneParityTests.testEveryActivitySlugIsReachable` — for
  each activity slug, find one synthetic profile + event-history combo
  that surfaces it as the activity pick. Caps at 50 days of synthetic
  refreshes per slug; failures name the unreachable slug.

### 8. Vocab doc

Write `docs/products/life-clock/quest-pool-vocab.md` documenting:
- The seven exclusion-group names and what each conflicts with.
- The five EligibilityFilter fields and their semantics.
- The slug-naming convention.

Future authors (4b, 4c, future versions) reference this so vocab
doesn't drift.

## Quality gates (must pass before merge)

1. Schema validity + slug uniqueness — `QuestPoolTests` green.
2. Tone parity + distinctness + vocab smoke — `QuestPoolToneParityTests` green
   on all 30 activity slugs.
3. Reachability — every activity slug surfaces for at least one synthetic profile.
4. Selector + flag + integration tests still green.
5. Eligibility filter coverage tests green.

If any gate fails, the PR doesn't merge — stop, fix, retest.

## Honesty constraint

If by quest 20 the tone-distinction starts feeling formulaic (gentle =
"a short walk", coach = "10-minute walk", firmDirect = "10 min. Walk."
— same shape repeated), STOP authoring. Ship the 20 quests that pass
quality, capture the remaining 10 in a P3 todo, and move on. Quality
> count.

## Branch + PR

- Branch: `claude/eloquent-heyrovsky-c27bc0-phase-4a` (off PR #32 head).
- PR title: `feat(life-clock): activity quest pool + EligibilityFilter (Phase 4a of 5)`.
- Stacked on PR #32. Phase 4b branches off this on next cycle.

## Acceptance

- [ ] EligibilityFilter restored, decode round-trips, selector filters correctly.
- [ ] 30 activity slugs authored, all tone-parity green, all distinctness green, all vocab smoke green.
- [ ] Activity reachability test green.
- [ ] Existing tests still green.
- [ ] Vocab doc committed.
- [ ] Flag still default `false`.
- [ ] No legacy constructor deletions in this PR.
