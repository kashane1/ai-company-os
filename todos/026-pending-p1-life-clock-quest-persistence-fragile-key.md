---
status: pending
priority: p1
issue_id: "026"
tags: [code-review, life-clock, ios, persistence, swiftdata]
dependencies: []
---

# Problem Statement

`LifeClockStore` persists Quest completion state across relaunch, but matches persisted records to engine-generated quests using the tuple `(date, title, category)`. `QuestEngine` regenerates `Quest.id` on every refresh, so the title string is the de-facto stable key. Renaming a quest title silently orphans every previously-completed quest with that title — completion state vanishes from `Today`, the ledger entry stays. The bug surfaces only on re-launch, never in tests, and never until the next copy edit.

The same diff also reimplemented this matching logic four times (`applyPersistedCompletions`, `fetchPersistedQuests`, `persistedQuestRecord`, `fetchPersistedQuest`, `persistedQuestMatches`) — a single `upsertQuest` keyed on a stable slug would replace ~70 LOC.

## Findings

- `products/life-clock-ios/Sources/App/LifeClockStore.swift:394-408` — predicate matches by `date == ... && title == ... && category == ...`.
- `products/life-clock-ios/Sources/Engines/QuestEngine.swift` — generates fresh `Quest` instances per refresh with new UUIDs; titles are the only stable identity.
- Past learning at `docs/solutions/integration-issues/swiftdata-mandatory-attribute-migration-landmine.md` warns about silent SwiftData write failures on schema drift; this is a related class of "simulator works, real users break."

## Proposed Solutions

### Option 1 (recommended): Add a stable slug to QuestEngine

Have `QuestEngine` emit `quest.key: String` (e.g. `"nutrition.water-with-meal.v1"`). Persist on slug. Title becomes free-form display copy.

Pros: persistence survives all copy edits; collapses the four overlapping methods into one upsert; explicit versioning when intent changes (`v1` → `v2`).
Cons: requires QuestEngine change; one-time migration for any existing on-device data (probably none — pre-launch).
Effort: Medium.
Risk: Low.

### Option 2: Hash the quest definition at generation time

Compute key as `sha256(category + canonical_intent_string)` inside `QuestEngine`.

Pros: no manual slug bookkeeping.
Cons: opaque key, harder to debug; intent-string drift still breaks identity.
Effort: Small.
Risk: Medium.

### Option 3: Do nothing; document the constraint

Add a comment at the top of `QuestEngine` saying "do not edit existing quest titles; create a new quest type instead."

Pros: zero code change.
Cons: hidden contract, easy to violate, not enforceable.
Effort: Minimal.
Risk: High (behavioral landmine).

## Recommended Action

(leave blank for triage)

## Technical Details

- Affected files: `LifeClockStore.swift`, `QuestEngine.swift`, possibly `LifeClockSchema.swift` (Quest model — add `key` attribute with property-level default to avoid the SwiftData migration landmine).
- Database changes: add `Quest.key: String = ""` (default required for safe lightweight migration on existing simulator data).

## Acceptance Criteria

- [ ] `QuestEngine` emits a stable `key` per quest type.
- [ ] `LifeClockStore` persistence keyed on `key`, not `(title, category)`.
- [ ] Renaming a quest title preserves completion state across relaunch (test).
- [ ] The four overlapping methods collapse to one `upsertQuest` + one `fetchQuests(on:)`.

## Work Log

(to be filled in)

## Resources

- Architecture review (this audit), 2026-04-30
- `docs/solutions/integration-issues/swiftdata-mandatory-attribute-migration-landmine.md`
