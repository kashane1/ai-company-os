---
status: completed
priority: p3
issue_id: "024"
tags: [code-review, life-clock, ios, quality, nits]
dependencies: []
---

# Problem Statement

Low-severity polish items surfaced by reviewers. None block merge or correctness.

## Findings

1. **`AppTab` declares unused conformances** (`Identifiable`, `CaseIterable` are never iterated). Drop or use them.
2. **`ToneMode: Codable`** — never encoded in v1. Drop the conformance or add a comment.
3. **`QuestEngine.sleepQuest` always returns non-nil** despite an `Optional` return type — misleading. Make non-optional or actually return `nil` when sleep goal is hit.
4. **`ClockEngine.nextBestLever` falls back to `positiveDrivers.first` from a `Set`** — non-deterministic order. Tests that exercise this path will flake. Use sorted iteration.
5. **`OnboardingView.permissionEducationScreen`** describes a feature not in this PR (live HealthKit). YAGNI — collapse to one line on the reveal screen and reintroduce when live HealthKit lands.
6. **Tests partially redundant:** `LifeClockStoreTests.testBootstrapPopulatesEstimateAndQuests` and `testToneModeChangePropagatesToProfile` overlap with engine tests. Keep `testQuestCompletionAddsLedgerEntry` (the only store-specific assertion); merge or trim the others.
7. **`Confidence` enum's `assign` method's `weightKgIfTracked` extension** uses `activeEnergyKcal` as a "weight tracked" proxy — confusing semantics, nonzero false-positive rate. Either rename or use the actual presence of `weightKg` if/when SwiftData persistence captures it.

## Proposed Solutions

### Option 1: Sweep all in a follow-up cleanup PR

After P1 + P2 todos land, batch all P3 items into a single low-risk cleanup commit.

Pros:
- One coherent diff for review.
- Keeps PR #14 focused on the structural P1/P2 fixes.

Cons:
- Some items (`nextBestLever` non-determinism) could matter if tests grow before the cleanup ships. Low likelihood near-term.

Effort: small
Risk: low

## Recommended Action

(Filled during triage.)

## Acceptance Criteria

- [ ] No unused protocol conformances on `AppTab` or `ToneMode`.
- [ ] `nextBestLever` iterates a sorted collection.
- [ ] `OnboardingView.permissionEducationScreen` either drops the misleading copy or links to a real HealthKit education flow.
- [ ] `LifeClockStoreTests` keeps the bootstrap smoke test and the quest-completion test; tone-mode propagation merged.

## Work Log

- 2026-04-27: Created from PR #14 simplicity review.

## Resources

- PR: https://github.com/kashane1/ai-company-os/pull/14
