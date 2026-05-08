# Quest pool vocabulary

Reference for authors of `Resources/QuestPool/{activity,diet,sleep}.json`.
Three vocabularies need to stay stable across genres and authoring
phases:

1. **Slug naming** — pinned by the master plan D4.
2. **Exclusion-group names** — used by the selector's conflict pass.
3. **Eligibility filter fields** — used by the pre-scoring hard filter.

Drift between authoring phases (4a → 4b → 4c) destroys the selector's
behavior, so the canonical list lives here.

## Slug convention

Format: `<genre>.<intent-shortname>.v<n>`.

- `<genre>` is one of `activity`, `diet`, `sleep`.
- `<intent-shortname>` is lowercase letters, digits, hyphens. No dots.
- `<n>` is the version. Bump when changing the parity anchor (intent
  or target) of an existing slug; otherwise treat as immutable.

Examples:
- `activity.brisk-walk-20.v1`
- `diet.water-with-meal.v1`
- `sleep.wind-down-30min.v1`

Production slugs MUST NOT use the `fixture-` prefix. The fixture pool
(`fixture.json`, test-only) namespaces with `fixture-` and lives in a
separate basename.

## Exclusion groups

Two slugs that share an exclusion group never appear together in the
same daily slate. The selector drops the lower-scored one and replaces
it with the next-best non-conflicting slug in its genre.

Locked vocabulary (Phase 4a). Add new groups only with explicit
reasoning during a future authoring phase:

| Group | What it tags | Conflicts with |
|---|---|---|
| `meal-adjacent` | Quests bound to a specific meal slot | Other meal-adjacent quests on the same day |
| `evening-energy` | Quests that add physical energy late | Sleep wind-down quests |
| `pre-bed-stimulant` | Caffeine-cut quests | Morning-coffee quests, late-caffeine quests |
| `morning-cardio` | Cardio quests anchored to morning | Morning mobility / stretch quests |
| `intense-exertion` | Vigorous workouts | Recovery / deload-walk quests, recovery aids |
| `screen-time` | Quests that require screen-on activity | Screen-cut quests |
| `meal-timing` | Eating-window quests | Mid-day-snack quests, late-meal cuts |

### When to apply

Phase 4a (activity-only) sets exclusion groups conservatively because
the selector picks one slug per genre — intra-activity conflicts are
moot. Tags exist mostly to anticipate cross-genre conflicts that will
emerge once 4b (diet) and 4c (sleep) land.

Worked example: `activity.bodyweight-circuit.v1` is tagged
`intense-exertion`. When Phase 4c authors a `sleep.recovery-aid-stretch.v1`
also tagged `intense-exertion` — the day a user picks both, the
selector demotes the lower-scored one and replaces it.

## Eligibility filter fields

The hard filter runs BEFORE scoring in `QuestSelector.select(...)`.
A slug with no `eligibility` field is unrestricted.

| Field | Type | Semantics |
|---|---|---|
| `requiresSmoker` | `Bool?` | `nil` = any. `true` requires `smokingStatus != "none"`. `false` requires `smokingStatus == "none"`. |
| `requiresDrinker` | `Bool?` | `nil` = any. `true` requires `alcoholFrequency` ∉ `{"none","rare"}`. `false` requires `alcoholFrequency` ∈ `{"none","rare"}`. |
| `requiresStrengthRoutine` | `Bool?` | `nil` = any. `true` requires `strengthFrequencyPerWeek > 0`. `false` requires `strengthFrequencyPerWeek == 0`. |
| `coldStartReachable` | `Bool` | When `false`, slug is excluded for users with `distinctOpenDays < 7`. Use for slugs that need familiarity to make sense (e.g. zone-2 cardio framing). |
| `timeOfDay` | `TimeOfDayWindow?` | `morning`, `midday`, `evening`, `anytime`, or `nil`. Recorded as authoring intent. Non-load-bearing in Phase 4a (no time-of-day refresh hook). |

### When to use what

- **Don't use eligibility unless there's a real contraindication.** A
  walk is appropriate for everyone; tagging it with eligibility filters
  shrinks the candidate pool for no benefit.
- **`requiresSmoker: true`** — for "smoke-cut" diet quests. Don't author
  these in Phase 4a (activity).
- **`requiresStrengthRoutine: true`** — for slugs that assume good form
  or familiar load. Phase 4a uses this on `bodyweight-circuit`,
  `pushups-set`, `strength-session-30`. The intent is "don't drop a
  cold-quad through-rep prescription on a beginner."
- **`coldStartReachable: false`** — for slugs whose framing assumes the
  user has engaged with the genre already. Phase 4a uses this on
  `cardio-zone2-15` (zone-2 needs HRM familiarity).

### Cold-start window

The 7-day threshold matches `QuestSelector.discoveryDamp`'s saturation
point. A user clears discovery damp and unlocks cold-start-only slugs
at the same moment. Bookkeeping is single-source (the
`distinctOpenDays` counter on UserProfile).

## Tone voice (cross-reference)

Every authored slug carries copy for `gentle`, `coach`, and `firmDirect`.
The voice guide for each register lives in
[docs/plans/2026-05-08-feat-quest-pool-phase-4-and-5-plan.md §4.4](../../plans/2026-05-08-feat-quest-pool-phase-4-and-5-plan.md).
The vocab smoke-test in `QuestPoolToneParityTests.swift` enforces it at
build time.

## Authoring checklist

For every new slug:

1. Slug matches `^[a-z]+\.[a-z0-9-]+\.v\d+$`. ✓
2. Genre matches the intent's home genre (no `activity.foo` slugs
   under intent `wind-down`). ✓
3. `intent` is non-empty and matches the §4.1 grid for its genre. ✓
4. `target` present for numeric goals; absent for qualitative ones. ✓
5. Three tones, all distinct. No copy-paste. ✓
6. `gentle` doesn't use firm-direct vocab; `firm_direct` doesn't use
   gentle vocab. (Smoke test enforces.) ✓
7. `exclusionGroups` chosen from the locked vocabulary above; new
   groups need a doc update. ✓
8. `eligibility` only set when a real contraindication exists. ✓
