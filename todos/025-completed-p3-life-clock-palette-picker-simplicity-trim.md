---
status: completed
priority: p3
issue_id: 025
tags: [code-review, quality, simplicity, life-clock]
dependencies: []
---

# Trim over-commenting and tautological tests in palette picker

## Problem statement

The palette-picker feature shipped in commits `2d26f90` and `8c5cf8d`
on `feat/life-clock-mvp-skeleton` carries ~29 LOC of doc-comments
that explain WHAT the code does (which the well-named identifiers
already convey) and two tests that exercise framework behavior
(Swift's `RawRepresentable` synthesis, `CaseIterable.allCases.count`)
rather than our logic.

CLAUDE.md is explicit: *"Default to writing no comments. Only add one
when the WHY is non-obvious."* and *"Don't add tests that assert
framework behavior rather than our logic."*

Code is correct and ships safely as-is — this is a quality polish, not
a bug. P3, not blocking.

## Findings

From the simplicity-reviewer pass on the actual diff:

1. **LifeClockPalette.swift:3-11** — 9-line doc comment is mostly
   restating the toneMode-mirror pattern. Collapse to ~3 lines: keep
   only the structural-enforcement note about the absence of a
   `negative` field.
2. **LifeClockPalette.swift:27-29** — Doc on `accent` explains
   standard SwiftUI `.tint(_:)` behavior. Delete (3 LOC).
3. **LifeClockPalette.swift:33** — `// Matches AccentColor.colorset
   (R 0.137, G 0.282, B 0.612 → #23489C)` is WHAT the numbers are.
   Delete (1 LOC); the RGB literals carry the values.
4. **LifeClockPalette.swift:35-36, 39-40** — comments on aurora and
   sunset *do* name an intent ("picks up icon's chrome side", "track
   contrast in follow-up") — keep these.
5. **LifeClockPaletteTests.swift `testInitFromKnownRawValue`** —
   exercises `RawRepresentable` synthesis. Framework behavior, not
   our logic. Delete (4 LOC); the unknown-rawValue test implicitly
   confirms the wiring.
6. **LifeClockPaletteTests.swift `testAllCasesHasThreePresets`** —
   tautological. Fails only when someone deliberately adds/removes a
   case (the change they meant to make). Delete (3 LOC).
7. **LifeClockStoreTests.swift `testSetPaletteWithNoProfileUpdatesInMemoryOnly`**
   — marginal value; the no-profile in-memory path is exercised
   implicitly by other tests. Delete (7 LOC).
8. **LifeClockStore.swift:170-175** — 6-line doc on `setPalette` re-explains
   what the unannotated `setToneMode` (identical shape, two methods up)
   already establishes as project pattern. Trim to one line or delete (5 LOC).

## Proposed solutions

### Option 1: Apply all 7 trims as a single follow-up commit (recommended)

- Pros: Aligned with CLAUDE.md, ~29 LOC removed, no behavior change,
  trivially safe to revert if anything goes sideways.
- Cons: One more commit on the branch.
- Effort: Small (~10 minutes).
- Risk: Negligible — pure deletions of comments + 2 tautological tests.

### Option 2: Defer indefinitely

- Pros: Branch is already shipped; no more churn.
- Cons: Code style drift; the next palette feature will copy the
  verbose pattern and amplify it.
- Effort: None.
- Risk: Style debt accrues.

### Option 3: Trim source comments only, keep all tests

- Pros: Compromise; conservative on test surface.
- Cons: The two tautological tests *are* tautological — they don't
  catch any bug they wouldn't catch via the unknown-rawValue test.
  Keeping them out of caution rewards busy-work.
- Effort: Small.
- Risk: Negligible.

## Recommended action

(Filled during triage.)

## Technical details

**Affected files:**
- `products/life-clock-ios/Sources/Shared/LifeClockPalette.swift`
- `products/life-clock-ios/Sources/App/LifeClockStore.swift`
- `products/life-clock-ios/Tests/LifeClockPaletteTests.swift`
- `products/life-clock-ios/Tests/LifeClockStoreTests.swift`

**No changes to:** `LifeClockApp.swift`, `LifeClockSchema.swift`,
`ProfileView.swift` — those edits in the original commit were
single-line and already minimal.

## Acceptance criteria

- [x] `LifeClockPalette.swift` doc-comment header reduced to ≤3 lines.
- [x] `accent` doc-comment removed.
- [x] `// Matches AccentColor.colorset` line removed.
- [x] `testInitFromKnownRawValue` deleted.
- [x] `testAllCasesHasThreePresets` deleted.
- [x] `testSetPaletteWithNoProfileUpdatesInMemoryOnly` deleted.
- [x] `setPalette` doc reduced to ≤1 line or removed.
- [x] CI grep gates still pass.
- [x] Remaining palette tests still pass conceptually
      (testInitFromUnknownRawValueReturnsNil + the 3 lifecycle tests
      in LifeClockStoreTests).

## Work log

- 2026-04-29 — Created during `/workflows:review` pass on commits
  `2d26f90`/`8c5cf8d`. Source: simplicity-reviewer agent on the
  actual diff (not the deepened plan).
- 2026-04-29 — Resolved via `/resolve_todo_parallel`. Applied 7
  trims inline; net -35 LOC across 4 files. Behavior unchanged.
  All 8 acceptance-criteria boxes satisfied.

## Resources

- Plan: [`docs/plans/2026-04-29-001-feat-life-clock-palette-picker-plan.md`](../docs/plans/2026-04-29-001-feat-life-clock-palette-picker-plan.md)
- Commits: `2d26f90` (icon swap), `8c5cf8d` (palette feature)
- CLAUDE.md (project root) — comment + test discipline rules
