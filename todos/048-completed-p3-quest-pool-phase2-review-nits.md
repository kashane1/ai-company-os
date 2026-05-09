---
status: completed
priority: p3
issue_id: 048
tags: [code-review, life-clock, ios, cleanup, quest-pool]
dependencies: []
pr: https://github.com/kashane1/ai-company-os/pull/30
---

# Quest Pool Phase 2 — review nits

## Problem Statement

The multi-agent review of PR #30 (Quest pool + tone-keyed schema, Phase 2 of 5) found **no P1 issues and no merge-blocking P2 issues**. The two IMPORTANT items from `data-integrity-guardian` (`bootstrapQuestGenres` not implemented, `LifeClockStore.upsertQuest` drops `genre`) are forward-looking — they describe work Phase 3 must complete and have no current breakage because `Quest.genre` is intentionally inert in this PR. Those are tracked as Phase 3 prep in todo 049.

This todo bundles the small actionable cleanups that can land alongside Phase 2 if a follow-up commit goes out, or be folded into Phase 3.

## Findings

### Finding 1 — Dead initializer (definitely cut)

**Source:** `code-simplicity-reviewer`
**Location:** [QuestPool.swift:24-26](products/life-clock-ios/Sources/Engines/QuestPool.swift)

```swift
init(quests: [String: PoolQuest]) {
    self.quests = quests
}
```

Has zero callers in `Sources/` or `Tests/`. The array overload at line 28 is the only init the loader calls. Three lines, one cognitive decision ("which init do I call") removed for Phase 3.

**Action:** delete it.

### Finding 2 — Subdirectory fallback hides bundle-layout regression

**Source:** `architecture-strategist`
**Location:** [QuestPool.swift:102-103](products/life-clock-ios/Sources/Engines/QuestPool.swift)

```swift
guard let url = bundle.url(forResource: name, withExtension: "json", subdirectory: "QuestPool")
    ?? bundle.url(forResource: name, withExtension: "json")
else { ... }
```

The fallback (no-subdirectory lookup) was added defensively to tolerate flattened test bundles, but in production it never triggers — `project.yml` folder-references `Resources/QuestPool/`, so the subdirectory path always resolves first. If that folder reference ever regresses to a flat add, the fallback hides the bug instead of failing the build.

**Action:** either drop the fallback, or add a test asserting the subdirectory path resolves first. Lean: drop the fallback; it's dead in practice.

### Finding 3 — Quest round-trip test sibling-coverage gap

**Source:** `data-integrity-guardian` (#5e)
**Location:** [LifeClockSchemaMigrationTests.swift:392-414](products/life-clock-ios/Tests/LifeClockSchemaMigrationTests.swift) — `testQuestGenreRoundTripsThroughFileBackedStore`

Currently asserts `category` and `title` round-trip alongside `genre`, but doesn't check `slug`, `detail`, `target`, `rewardEstimateMinutes`, `completedAt`, or `progress`. The HabitLog sibling-fields test ([LifeClockSchemaMigrationTests.swift:197-216](products/life-clock-ios/Tests/LifeClockSchemaMigrationTests.swift)) sets a higher bar and catches a class of regression where someone refactors the Quest schema and silently drops a column default.

**Action:** mirror the HabitLog pattern — assert every Quest field round-trips, not just genre/category/title.

### Finding 4 — `intent` decoded as free String with no validation

**Source:** `architecture-strategist`
**Location:** [QuestPoolTypes.swift:93](products/life-clock-ios/Sources/Models/QuestPoolTypes.swift) — `let intent = try c.decode(String.self, forKey: .intent)`

`intent` is the parity anchor (D3 in the plan). If a Phase 3 affinity engine groups slugs by `intent`, a typo in one of three tone-keyed authoring entries silently collapses two slugs onto the same intent, skewing affinity. The custom Codable already validates slug format and tone presence — adding a non-empty + slug-suffix-matches-intent check fits the existing decode-time-validation pattern.

```swift
guard !intent.isEmpty else { throw ... }
// Optional stronger check: slug ends with "<intent>.v<n>"
guard slug.contains(".\(intent).") else { throw ... }
```

**Action:** add non-empty validation; consider slug-suffix-matches-intent if authoring-time tooling won't catch it.

## Proposed Solutions

**Option A: One follow-up PR doing all four (Small, Low risk)**
- Delete dead init (Finding 1), drop subdirectory fallback (Finding 2), expand sibling-field coverage (Finding 3), add intent validation (Finding 4).
- ~30 LOC of changes plus one new test assertion block.
- Lands on top of PR #30 before Phase 3 starts.

**Option B: Fold into Phase 3's first PR (Small, Lower risk)**
- All four are inert wins; folding into Phase 3's schema-touching PR groups related work.
- Risk: forgotten if Phase 3 plan doesn't reference this todo.

**Option C: Skip 2 + 4, do 1 + 3 (Tiny, Lowest risk)**
- Findings 1 and 3 are definitely-cut and definitely-tighten; 2 and 4 are arguably-defensible.
- Smallest delta, lowest review burden.

## Recommended Action

(Filled during triage)

## Technical Details

**Affected files:**
- [products/life-clock-ios/Sources/Engines/QuestPool.swift](products/life-clock-ios/Sources/Engines/QuestPool.swift)
- [products/life-clock-ios/Sources/Models/QuestPoolTypes.swift](products/life-clock-ios/Sources/Models/QuestPoolTypes.swift)
- [products/life-clock-ios/Tests/LifeClockSchemaMigrationTests.swift](products/life-clock-ios/Tests/LifeClockSchemaMigrationTests.swift)

**Tests touched:** `testQuestGenreRoundTripsThroughFileBackedStore`. Custom-Codable decode tests in `QuestPoolTests` may need an "empty intent" failure-case test if Finding 4 lands.

## Acceptance Criteria

- [x] `QuestPool.init(quests: [String: PoolQuest])` removed; build green.
- [x] Subdirectory fallback removed (or test added to lock the production path).
- [x] `testQuestGenreRoundTripsThroughFileBackedStore` asserts every Quest field round-trips.
- [x] Custom Codable rejects empty `intent`; new test in `QuestPoolTests` covers the failure.
- [x] All existing tests still pass.

## Work Log

- **2026-05-08** — Created from PR #30 review synthesis.
- **2026-05-08** — All four findings landed in a single follow-up commit on the PR #30 branch:
  - Finding 1: deleted `QuestPool.init(quests: [String: PoolQuest])`. Confirmed zero callers.
  - Finding 2: removed the no-subdirectory bundle-lookup fallback; `QuestPool.loadFromBundle` now fails loud if the `QuestPool/` folder reference regresses to flat.
  - Finding 3: expanded `testQuestGenreRoundTripsThroughFileBackedStore` to assert all Quest fields round-trip (slug, detail, target, progress, rewardEstimateMinutes, completedAt) — mirrors the HabitLog sibling-coverage pattern.
  - Finding 4: added a non-empty `intent` guard to PoolQuest's custom Codable + a matching `testDecodeFailsOnEmptyIntent`. The optional slug-embeds-intent check was dropped after the fixture's `fixture-` prefix made it inconsistent with the chosen namespacing scheme. Rationale documented inline.
- Build green; pool/parity/migration suites: 27 tests pass (was 26 + 1 new).

## Resources

- PR: https://github.com/kashane1/ai-company-os/pull/30
- Plan: [docs/plans/2026-05-08-feat-quest-pool-affinity-engine-plan.md](docs/plans/2026-05-08-feat-quest-pool-affinity-engine-plan.md)
- Brainstorm: [docs/products/life-clock/plan-quest-generation-affinity.md](docs/products/life-clock/plan-quest-generation-affinity.md)
- HabitLog sibling-test pattern (template for Finding 3): [LifeClockSchemaMigrationTests.swift:197](products/life-clock-ios/Tests/LifeClockSchemaMigrationTests.swift)
