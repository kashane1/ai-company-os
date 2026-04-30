---
status: pending
priority: p3
issue_id: "032"
tags: [code-review, life-clock, ios, quality, nits]
dependencies: []
---

# Problem Statement

Low-severity polish items + prevention checks surfaced by the multi-agent review of the 2026-04-30 UX audit diff. None block merge.

## Findings

### Code nits

1. **`SupportMoment.Tone` is two-case overspecified.** `SupportMoment.swift:4-7` — the enum maps 1:1 to icon + color in `SupportMomentCard` and nowhere else. Two cases. A `Bool isCelebration` (or pass `(systemImage: String, tint: Color)` directly) would do. Premature taxonomy.
2. **`useInMemoryStore` is a one-line alias** for `isUITest` (`LifeClockLaunchConfiguration.swift`). Inline it.
3. **`momentumCard` duplicates the elevated-rounded-rect pattern** present in `clockCard`, `driversCard`, `questsCard`, and `checkInCard`. Five copies in `TodayView.swift`. Extract a single `card { ... }` helper.
4. **`dismissSupportMoment()` + raw `supportMoment` setter** — two write paths to one field. Make `supportMoment` `private(set)`; route mutations through helpers.
5. **`applyPersistedCompletions(to: inout [Quest], ...)`** — `inout` is misleading because `Quest` is a `@Model class`. The inout lies about what's being mutated. Drop `inout`; return `[Quest]`. (Also note: this whole method goes away if todo 026 lands.)
6. **Per-row driver identifiers missing** (`TodayView.swift:~150`) — agent can't assert which driver moved.
7. **Diet streak chip identifier missing** (`TodayView.swift:177`).
8. **Carry-over ledger entries from the old format** — `fetchLatestQuestLedgerEntry` only matches `"Completed action: …"`. Pre-rename `"Completed quest: …"` entries won't be removed on undo. Probably negligible (no shipped users) — confirm and discard, or grep for both formats.

### Prevention checks (from learnings-researcher)

9. **SwiftData `@Model` property-level defaults.** `docs/solutions/integration-issues/swiftdata-mandatory-attribute-migration-landmine.md` documents how non-optional `@Model` properties without defaults brick the store on lightweight migration. Audit all new/modified Quest fields in `LifeClockSchema.swift` for mandatory props without defaults. *(Tightly related to todo 026.)*
10. **`TARGETED_DEVICE_FAMILY` check.** Past learning: `docs/solutions/integration-issues/ios-ipad-compatibility-mode-cramped-layout.md` — Catchbook had iPad cramped layout from `TARGETED_DEVICE_FAMILY = 1`. Verify Life Clock's `project.yml` sets the family explicitly to match intent (iPhone-only is fine; just be explicit).

## Proposed Solutions

### Option 1 (recommended): Sweep all in a follow-up cleanup commit

After todos 026-031 land, batch all P3 nits + prevention checks into a single low-risk diff. Items 9 and 10 are checks (might be no-ops), the rest are micro-edits.

Pros: one coherent diff for review.
Cons: defers individual fixes.
Effort: Small.
Risk: Low.

### Option 2: Fix opportunistically as touched

Tag the todo as "free-roll" — fix any item when a related file is open for another reason.

Pros: zero scheduled work.
Cons: some items linger forever.
Effort: None.
Risk: Low.

## Recommended Action

(leave blank for triage)

## Technical Details

Affected files: `SupportMoment.swift`, `SupportMomentCard.swift`, `LifeClockLaunchConfiguration.swift`, `TodayView.swift`, `LifeClockStore.swift`, `LifeClockSchema.swift`, `project.yml`.

## Acceptance Criteria

- [ ] Items 1-7 either fixed or explicitly deferred with rationale.
- [ ] Item 8 grep run; result documented (delete pre-format ledger rows or confirm none exist).
- [ ] Item 9 audit run; any missing defaults added.
- [ ] Item 10 verified.

## Work Log

(to be filled in)

## Resources

- Multi-agent /workflows:review (this audit), 2026-04-30
- `docs/solutions/integration-issues/swiftdata-mandatory-attribute-migration-landmine.md`
- `docs/solutions/integration-issues/ios-ipad-compatibility-mode-cramped-layout.md`
