---
status: pending
priority: p3
issue_id: 050
tags: [code-review, life-clock, ios, cleanup, quest-pool, phase-3-polish]
dependencies: []
pr: https://github.com/kashane1/ai-company-os/pull/31
---

# Quest Pool Phase 3 — polish + deferrals from PR #31 review

## Problem Statement

Multi-agent review of PR #31 (Phase 3a + 3b: engines + schema V1.5.0) surfaced 3 P1 must-fix items (resolved inline on the PR — see commit history) and ~10 P3 items split between simplicity nits and deferred-by-design items. This todo bundles the P3 work as one followup so the next session can pick from it.

## Findings

### P3 simplicity nits (definitely-cut category, not yet applied)

1. **`ExclusionConflict` struct has a single `Genre` field** — could be a plain `Genre?` return value. Saves 3 LOC + 1 type. ([QuestSelector.swift:283-285](products/life-clock-ios/Sources/Engines/QuestSelector.swift)).
2. **`NeedWeightEngine` static threshold constants** — `stepsLowThreshold`, `stepsHighThreshold`, `sleepLowThreshold`, `sleepHighThreshold`, `minHKDaysForBaseline`, `hkWindowDays` are declared as `static let` but never overridden externally. Inline as literals at use sites with brief comments. Keep `high/medium/low` band constants (those ARE reused). Saves ~15 LOC of declarations. ([NeedWeightEngine.swift:29-43](products/life-clock-ios/Sources/Engines/NeedWeightEngine.swift)).
3. **`AffinityEngine.signal` unresolved cases** — `(.picked, _) → nil` and `(.shown, _) → nil` can collapse into a single `default: nil` since all resolved variants are matched above. Saves 4 LOC. ([AffinityEngine.swift:46-58](products/life-clock-ios/Sources/Engines/AffinityEngine.swift)).
4. **`AffinityEngine.computeAffinities` pre-init loop** — `var ema: [Genre: Double] = [:]; for genre in Genre.allCases { ema[genre] = 0.5 }` could be a dict literal `[Genre: Double] = [.activity: 0.5, .diet: 0.5, .sleep: 0.5]`. Saves 3 LOC. ([AffinityEngine.swift:67-70](products/life-clock-ios/Sources/Engines/AffinityEngine.swift)).
5. **`testDiscoveryDamp` redundant test cases** — day 0, 3, 7, 100 over a linear formula. Keep day-0 and day-7 (boundary); cut day-3 (interpolation implied) and day-100 (clamp tested by day-7). ([QuestSelectorTests.swift:42-56](products/life-clock-ios/Tests/QuestSelectorTests.swift)).
6. **`firstExclusionConflict` Set construction in inner loop** — builds `Set(quest.exclusionGroups)` per pair-check. With 3 pairs total this is irrelevant, but if exclusionGroups grow, hoist Set conversion. ([QuestSelector.swift:295-306](products/life-clock-ios/Sources/Engines/QuestSelector.swift)).

### P3 design deferrals (intentional)

7. **Pure/impure split at function vs file level** (pattern-recognition reviewer) — `QuestSelector.swift` mixes pure `select(...)` with impure `resolveEndOfDay(...)`. Existing convention keeps pure engines in `Sources/Engines/` and SwiftData mutation in `LifeClockStore` (`Sources/App/`). Plan deepening pass explicitly chose the function-level split for Phase 3; revisit if a future engine wants to mutate state too. **Action for now:** add a doc comment on `QuestSelector` acknowledging the cross-engine convention tension and link to this todo.

8. **`bootstrapQuestGenres` `try? save()` swallows errors** (data-integrity reviewer) — silent save failure on disk-full or store corruption. The pattern is endemic in `LifeClockStore.swift` (12+ instances) — not unique to Phase 3. **Action for now:** track in the existing pattern; not a Phase 3-specific fix. A separate sweep replacing every `try?` with `do/catch` + log + telemetry would be a coordinated change across the file.

9. **`#Index<QuestEvent>([\.date, \.slug, \.kind])`** — iOS 18+ macro; project deploys to iOS 17.0 minimum. Add when the deployment target bumps to 18 OR when event volume warrants the cost. Tracked in master plan Out-of-Scope.

10. **True cross-version migration test (V1.3.0 → V1.5.0)** (data-integrity CRITICAL on test-coverage gap) — current "round-trip with legacy-shaped writes" tests don't exercise SwiftData's cross-version migration code path. To genuinely test, need either (a) a frozen `LifeClockSchemaV1_3` enum kept in test sources, or (b) a hand-rolled SQLite store with V1.3.0 columns. Both are non-trivial. **Action for now:** the V1.5.0 round-trip tests catch property-level-default regressions at the same-version layer; cross-version coverage requires real-device build verification. Test was renamed to be honest about its scope (`testV150FieldsDefaultCorrectlyOnFileBackedRoundTripWithLegacyShapedWrites`).

11. **`slugGenreMap` drift risk vs JSON pool** (data-integrity reviewer) — the static map on `LifeClockStore` will diverge from the master plan migration table and the eventual Phase 4 production JSON. Adding a test that walks `Resources/QuestPool/*.json` and asserts every slug is mapped is meaningful only after Phase 4 lands content. Defer to Phase 4 PR.

12. **`bootstrapQuestGenres` short-circuit flag** (performance reviewer) — `bootstrapQuestGenresCompleted: Bool` on UserProfile would avoid the no-op predicate fetch on every cold launch after the first backfill. Cost is sub-millisecond at current row counts; add only if launch profiling shows it.

## Proposed Solutions

**Option A: Apply simplicity nits 1-6 in one small PR.**
~30 LOC delta, all in engines + tests. Low risk; lands as a polish commit on top of #31.

**Option B: Bundle into Phase 3c PR (emission hooks + flag wiring).**
Keeps the polish near the same context. Risk: Phase 3c's surface is larger; nits compete for review attention.

**Option C: Skip; come back if a real maintenance burden surfaces.**
Each individual nit is small. The aggregate is ~30 LOC. None are correctness-affecting.

## Recommended Action

(Filled during triage)

## Technical Details

**Affected files:**
- [products/life-clock-ios/Sources/Engines/AffinityEngine.swift](products/life-clock-ios/Sources/Engines/AffinityEngine.swift)
- [products/life-clock-ios/Sources/Engines/NeedWeightEngine.swift](products/life-clock-ios/Sources/Engines/NeedWeightEngine.swift)
- [products/life-clock-ios/Sources/Engines/QuestSelector.swift](products/life-clock-ios/Sources/Engines/QuestSelector.swift)
- [products/life-clock-ios/Tests/QuestSelectorTests.swift](products/life-clock-ios/Tests/QuestSelectorTests.swift)
- [products/life-clock-ios/Sources/App/LifeClockStore.swift](products/life-clock-ios/Sources/App/LifeClockStore.swift) (deferral #11 + #12 + #8)
- [products/life-clock-ios/Sources/Models/LifeClockSchema.swift](products/life-clock-ios/Sources/Models/LifeClockSchema.swift) (deferral #9 — `#Index` when iOS 18 minimum)
- [products/life-clock-ios/Tests/LifeClockSchemaMigrationTests.swift](products/life-clock-ios/Tests/LifeClockSchemaMigrationTests.swift) (deferral #10 — true cross-version test)

## Acceptance Criteria

When this todo is "complete":
- Items 1–6 either applied or explicitly skipped.
- Items 7–12 either applied (when their preconditions are met) or explicitly cited from the future PR that addresses them.

## Work Log

- 2026-05-08 — Created from PR #31 review synthesis. Three P1 items resolved inline on PR; this todo captures P3 nits + design deferrals.

## Resources

- PR: https://github.com/kashane1/ai-company-os/pull/31
- Phase 3 plan: [docs/plans/2026-05-08-feat-quest-pool-phase-3-engines-plan.md](docs/plans/2026-05-08-feat-quest-pool-phase-3-engines-plan.md)
- Master plan: [docs/plans/2026-05-08-feat-quest-pool-affinity-engine-plan.md](docs/plans/2026-05-08-feat-quest-pool-affinity-engine-plan.md)
- Phase 3 prep todo: [todos/049-pending-p3-quest-pool-phase3-prep.md](todos/049-pending-p3-quest-pool-phase3-prep.md)
- Phase 2 review nits (precedent for this kind of bundle): [todos/048-completed-p3-quest-pool-phase2-review-nits.md](todos/048-completed-p3-quest-pool-phase2-review-nits.md)
