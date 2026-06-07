---
status: pending
priority: p2
issue_id: "034"
tags: [code-review, life-clock, ios, naming, wrap-up-coordinator]
dependencies: []
---

# Rename `ProfileSnapshot.onboardedAt` → `onboardingCompletedAt`

## Problem Statement

`WrapUpCoordinator.ProfileSnapshot.onboardedAt` does not match the source-of-truth field on the `UserProfile` `@Model`, which is named `onboardingCompletedAt: Date?` ([Sources/Models/LifeClockSchema.swift:54](products/life-clock-ios/Sources/Models/LifeClockSchema.swift)). When Phase 1b wires the coordinator into `LifeClockStore`, an engineer grepping for `onboardedAt` will find nothing in the schema and lose time mapping the names.

## Findings

- Architecture review (PR #18): "DTO field naming mismatch — `ProfileSnapshot.onboardedAt` vs model's `onboardingCompletedAt: Date?`. The mapping is non-obvious and silent."
- Confirmed in code: [Sources/Engines/WrapUpCoordinator.swift:19](products/life-clock-ios/Sources/Engines/WrapUpCoordinator.swift) declares `onboardedAt`; the model declares `onboardingCompletedAt`.

## Proposed Solutions

1. **Rename DTO field to `onboardingCompletedAt`** (recommended). Match the model name 1:1. Single rename in WrapUpCoordinator.swift + ProfileSnapshot init sites in tests. Effort: Small. Risk: None — pure-engine change, no callers in production yet.
2. **Add a doc comment on `onboardedAt` explaining the mapping.** Cheaper but kicks the can; future engineer still pays the grep tax.

## Recommended Action

(Triage)

## Technical Details

- File: `products/life-clock-ios/Sources/Engines/WrapUpCoordinator.swift` (line 19)
- Test file: `products/life-clock-ios/Tests/WrapUpCoordinatorTests.swift` (~10 call sites)

## Acceptance Criteria

- [ ] DTO field renamed.
- [ ] Tests updated and passing.
- [ ] grep for `onboardedAt` returns zero hits in `Sources/`/`Tests/`.

## Work Log

(empty)

## Resources

- PR: https://github.com/kashane1/ai-company-os/pull/18
- Plan: docs/plans/2026-04-30-feat-history-wrapups-and-overrides-plan.md
