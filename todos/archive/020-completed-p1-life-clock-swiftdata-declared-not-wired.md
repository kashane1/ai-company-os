---
status: completed
priority: p1
issue_id: "020"
tags: [code-review, life-clock, ios, swiftdata, architecture, yagni]
dependencies: []
---

# Problem Statement

`LifeClockSchemaV1: VersionedSchema` declares 8 `@Model` classes with `@Attribute(.unique)` constraints, plus an empty `LifeClockMigrationPlan: SchemaMigrationPlan`. None of it is wired: `LifeClockApp` never calls `.modelContainer(...)`, `LifeClockStore` never holds a `ModelContext`, and the README explicitly states the store re-seeds from `MockHealthKitService` on every cold start. The `@Model` reference types are mutated outside any `ModelContext`, which is undefined behavior the moment a container *is* attached.

This is a half-built abstraction: the v1 skeleton has the cost of SwiftData (typealiases, versioned schema scaffolding, attribute defaults to satisfy migration rules, ~218 LOC in `LifeClockSchema.swift`) without the value (no persistence). It also sets a load-bearing precedent for v2: when persistence lands, the next contributor will discover that `@Model` objects have been mutated outside any context for months.

## Findings

- `products/life-clock-ios/Sources/Models/LifeClockSchema.swift` — defines 8 `@Model` classes wrapped in `LifeClockSchemaV1: VersionedSchema` plus `LifeClockMigrationPlan` with empty stages.
- `products/life-clock-ios/Sources/App/LifeClockApp.swift:5-13` — no `.modelContainer(for:)`; the `WindowGroup` only injects the store via `.environment(store)`.
- `products/life-clock-ios/Sources/App/LifeClockStore.swift` — store mutates `@Model` properties (`profile?.toneMode = ...`, `quest.completedAt = Date()`) without a context.
- Architecture review (architect agent): "compiles fine, ships fine, then corrupts on the first migration when someone adds a container in v2."
- Simplicity review: "saves ~200 LOC and removes the migration-landmine surface area the comment warns about."

## Proposed Solutions

### Option 1: Strip SwiftData from v1 — use plain reference types

Convert the eight `@Model final class` types into plain `final class` (or `struct` where mutation is local). Remove `LifeClockSchemaV1`, `LifeClockMigrationPlan`, the typealiases, and `import SwiftData`. Keep the property-level defaults (still good practice). When persistence lands, re-introduce `@Model` and `VersionedSchema` in the same PR that constructs the `ModelContainer` and routes mutations through `ModelContext`.

Pros:
- Removes ~150-200 LOC of unused scaffolding and the foot-gun of mutating `@Model` outside contexts.
- Aligns with the v1 "no persistence" mandate stated in the README and the founder pack's `12_TECHNICAL_ARCHITECTURE.md` § "V1 engineering rule".
- Matches the After Plans pattern (plain Swift models in `AfterPlansModels.swift`).

Cons:
- A future PR will re-add `@Model` annotations across the same files. Costs ~30 min of re-annotation.
- Loses the "VersionedSchema from day one" insight from the deepened plan.

Effort: medium
Risk: low

### Option 2: Wire a real `ModelContainer` and route mutations through `ModelContext`

Add `.modelContainer(for: LifeClockSchemaV1.models, migrationPlan: LifeClockMigrationPlan.self) { result in ... }` on the `WindowGroup`. Inject `ModelContext` into the store. Refactor `LifeClockStore` mutations to insert/update via `context.insert(...)` and `try? context.save()`. Disable CloudKit on the container.

Pros:
- Honors the deepened plan's stance ("v1 ships SwiftData persistence with VersionedSchema from day one").
- Cold-start re-seed becomes an `if context.fetch(UserProfile).isEmpty { seed() }` instead of unconditional re-seed.
- The v2 follow-up plan inherits a working persistence layer.

Cons:
- Bigger diff in this PR.
- Persistence wasn't in this PR's stated scope; arguably belongs to a focused follow-up.

Effort: medium
Risk: medium

### Option 3: Wire a minimal in-memory `ModelContainer` only

Same as Option 2 but with `ModelConfiguration(isStoredInMemoryOnly: true)`. Persistence stays out of scope; the boundary is correct; mutations route through a context.

Pros:
- Smallest fix that honors `@Model` semantics.
- Tests can construct an in-memory container per case.

Cons:
- Cold-start re-seed still happens — exactly the "feels persistent but isn't" trap.
- Not a meaningful step toward v2.

Effort: small
Risk: low

## Recommended Action

(Filled during triage.)

## Technical Details

- Files to change in Option 1: `Sources/Models/LifeClockSchema.swift`, `Sources/App/LifeClockApp.swift`, `Sources/App/LifeClockStore.swift`, all `Sources/Features/**/*.swift` that import the model types (typealiases keep the surface stable if preserved as plain class names).
- Files to change in Option 2: `Sources/App/LifeClockApp.swift`, `Sources/App/LifeClockStore.swift`, plus a new `LifeClockContainer.swift` that owns container construction.

## Acceptance Criteria

- [ ] No `@Model` reference types are mutated outside a `ModelContext` in the production code path. (Greppable: any `@Model` mutation must be within a closure that receives a context.)
- [ ] OR: `@Model`, `VersionedSchema`, and `SchemaMigrationPlan` are removed from `Sources/Models/`.
- [ ] App still launches into Onboarding on first run and Today on subsequent runs.
- [ ] All unit tests still pass.
- [ ] CI grep gate added: if `@Model` is reintroduced without `ModelContainer`, the gate fails.

## Work Log

- 2026-04-27: Created from PR #14 review (architecture + simplicity reviewers).

## Resources

- PR: https://github.com/kashane1/ai-company-os/pull/14
- Plan: `docs/plans/2026-04-27-002-feat-life-clock-ios-mvp-skeleton-plan.md`
- Past learning: `docs/solutions/integration-issues/swiftdata-mandatory-attribute-migration-landmine.md`
- Past learning: `docs/solutions/integration-issues/swiftdata-deleting-model-from-child-sheet.md`
- Reference (canonical analog): `products/after-plans-ios/Sources/Models/AfterPlansModels.swift`
