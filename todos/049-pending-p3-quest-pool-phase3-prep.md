---
status: pending
priority: p3
issue_id: 049
tags: [code-review, life-clock, ios, phase-3-prep, quest-pool, do-not-resolve-this-session]
dependencies: [048]
pr: https://github.com/kashane1/ai-company-os/pull/30
---

# Quest Pool Phase 3 — prep reminders

## Problem Statement

Multi-agent review of PR #30 surfaced seven items that are **forward-looking concerns for Phase 3**, not bugs in Phase 2. They have no current breakage because Phase 2 ships schema + storage that's intentionally inert (no selector, no event emission, no UI changes). Capturing them here so the Phase 3 work plan can reference them.

**Do not auto-resolve this todo in the current session.** It exists to be pulled into Phase 3 planning.

## Findings

### Finding 1 — `LifeClockStore.upsertQuest` drops `genre` (data-integrity-guardian #5b)

**Severity:** IMPORTANT for Phase 3.
**Location:** [LifeClockStore.swift:1122 + :1136-1140](products/life-clock-ios/Sources/App/LifeClockStore.swift)

Upsert constructs `Quest(...)` with 7 named args but does not pass `genre:`, defaulting it to `""`. The update branch copies `title/detail/target/progress/rewardEstimateMinutes` but not `genre`. Currently safe because `Quest.genre` is inert in Phase 2.

When Phase 3 wires the engine to emit Quests with `genre`, persisted rows will silently strip the value. **Action for Phase 3:** add `genre: quest.genre` to the constructor call AND `stored.genre = quest.genre` to the update block. One-line fix in two places, but it must land in the same PR that starts emitting `genre`.

### Finding 2 — `bootstrapQuestGenres` referenced in comment, not implemented (data-integrity-guardian #5a)

**Severity:** IMPORTANT for Phase 3.
**Location:** [LifeClockSchema.swift:323-334](products/life-clock-ios/Sources/Models/LifeClockSchema.swift)

The `Quest.genre` field comment says "populated at bootstrap from a slug→genre map (LifeClockStore.bootstrapQuestGenres)." That symbol does not exist yet. Existing rows from prior versions will sit at `genre = ""` indefinitely until Phase 3 ships the backfill.

**Action for Phase 3:** implement `LifeClockStore.bootstrapQuestGenres()` that walks all persisted Quests and populates `genre` from a slug-prefix lookup using the same migration map in [docs/plans/2026-05-08-feat-quest-pool-affinity-engine-plan.md](docs/plans/2026-05-08-feat-quest-pool-affinity-engine-plan.md). Idempotent: safe to re-run.

### Finding 3 — `QuestEvent.kind` and `resolvedKind` should have an enum companion (architecture-strategist #7, security-sentinel #3)

**Severity:** IMPORTANT for Phase 3 (latent).
**Location:** [LifeClockSchema.swift:434-436](products/life-clock-ios/Sources/Models/LifeClockSchema.swift)

Stringly-typed `kind` and `resolvedKind` invite copy-paste errors across emit sites. The enum companion would be:

```swift
enum QuestEventKind: String { case shown, picked, replaced, completed }
enum QuestResolvedKind: String { case passedOver = "passed_over", abandoned }
```

`@Model` can't store enums directly without conversion overhead, so the persisted column stays `String` — but emit sites should funnel through `QuestEventKind.rawValue` so a typo becomes a compile-time error. Pairs with security-sentinel's "model-layer validation gap" — once an emit path exists, gate writes through the enum.

**Action for Phase 3:** add the enums alongside the emit hooks; route every write site through them.

### Finding 4 — Composite uniqueness on QuestEvent (data-integrity-guardian #5c)

**Severity:** NICE-TO-HAVE for Phase 3.
**Location:** [LifeClockSchema.swift:402](products/life-clock-ios/Sources/Models/LifeClockSchema.swift) (doc claim) vs schema enforcement.

Comment says "One row per (date, slug, kind)" but only `id` is `.unique`. SwiftData doesn't support composite uniqueness via `@Attribute`, so dedup must be application-level on emit. If two foreground transitions race, duplicate `shown` events would over-count exposure and skew the EMA in Phase 3's affinity computation.

**Action for Phase 3:** in the emit hook, query for existing `(date == today, slug == slug, kind == "shown")` before inserting; skip if present. Idempotent emit.

### Finding 5 — Precompute `byGenre` in QuestPool init (performance-oracle #4)

**Severity:** NICE-TO-HAVE for Phase 3.
**Location:** [QuestPool.swift:42-46](products/life-clock-ios/Sources/Engines/QuestPool.swift) — `func quests(in genre: Genre) -> [PoolQuest]`

Currently O(n) filter + O(k log k) sort per call. At n=90 the cost is ~50µs — irrelevant unless a SwiftUI body calls it inside a `ForEach` re-evaluation, which is plausible.

**Action for Phase 3:** in `QuestPool.init(quests:)`, precompute `byGenre: [Genre: [PoolQuest]]` (sorted once). `quests(in:)` becomes a dict lookup. Trivial cost insurance.

### Finding 6 — `Quest.genre` denormalization (architecture-strategist #6)

**Severity:** NICE-TO-HAVE for Phase 3.
**Location:** [LifeClockSchema.swift:323-334](products/life-clock-ios/Sources/Models/LifeClockSchema.swift)

`Quest.genre: String = ""` denormalizes the field that `PoolQuest.genre: Genre` types strongly. The SwiftData side has to stay stringly-typed because of the migration default, but the bootstrap path should funnel through `Genre(rawValue:)` so the `""`-sentinel is never observable outside that one function.

**Action for Phase 3:** when implementing `bootstrapQuestGenres` (Finding 2), wrap reads in a single helper that returns `Genre?` and treats `""` as nil. Document at the call site that consumers should never observe the empty string.

### Finding 7 — Emit events from method, not view body (agent-native-reviewer)

**Severity:** NICE-TO-HAVE for Phase 3.
**Location:** Plan's Phase 3 task 10.

If `QuestEvent` writes happen inside SwiftUI view `.onAppear` / button closures only, an agent-driven path that bypasses the view (a future MCP tool) won't produce events and affinity will skew.

**Action for Phase 3:** put event emission on a method on the engine or store (`QuestSelector.recordShown(slug:)`, etc.) that views call AND a future agent tool can call. Avoid coupling emit to view lifecycle.

## Proposed Solutions

This is a tracking todo — solutions are scoped per finding above and are owned by the Phase 3 implementation plan, not this todo.

## Recommended Action

Pull Findings 1 + 2 + 3 into Phase 3's first PR as hard requirements. Findings 4–7 can land alongside but are nice-to-haves. Reference this todo from the Phase 3 plan doc.

## Technical Details

**Affected files (forward-looking, modified by Phase 3):**
- [products/life-clock-ios/Sources/App/LifeClockStore.swift](products/life-clock-ios/Sources/App/LifeClockStore.swift) — Findings 1, 2, 7
- [products/life-clock-ios/Sources/Models/LifeClockSchema.swift](products/life-clock-ios/Sources/Models/LifeClockSchema.swift) — Findings 3, 4, 6
- [products/life-clock-ios/Sources/Engines/QuestPool.swift](products/life-clock-ios/Sources/Engines/QuestPool.swift) — Finding 5

## Acceptance Criteria

This todo is **complete** when Phase 3's plan document explicitly references each of the seven findings above and either:
- (a) closes the gap in Phase 3 PR(s), or
- (b) explicitly defers the gap with a written rationale.

## Work Log

- 2026-05-08 — Created from PR #30 review synthesis. Status `pending`, tag `do-not-resolve-this-session` to keep `/resolve_todo_parallel` from auto-acting on Phase 3 work.

## Resources

- PR: https://github.com/kashane1/ai-company-os/pull/30
- Plan: [docs/plans/2026-05-08-feat-quest-pool-affinity-engine-plan.md](docs/plans/2026-05-08-feat-quest-pool-affinity-engine-plan.md)
- Brainstorm: [docs/products/life-clock/plan-quest-generation-affinity.md](docs/products/life-clock/plan-quest-generation-affinity.md)
- Sibling Phase 2 nits todo: [todos/048-pending-p3-quest-pool-phase2-review-nits.md](todos/048-pending-p3-quest-pool-phase2-review-nits.md)
