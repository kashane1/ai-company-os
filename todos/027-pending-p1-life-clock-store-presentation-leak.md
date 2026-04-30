---
status: pending
priority: p1
issue_id: "027"
tags: [code-review, life-clock, ios, architecture]
dependencies: []
---

# Problem Statement

`LifeClockStore` now embeds UI presentation logic — the `supportMoment` field is constructed inline at six mutation sites with hard-coded copy ("Nice work.", "Action removed.", "Check-in saved.", etc.). The store has accreted: profile, palette, ledger, quests, health auth, persistence, AND now UX messaging copy. Every new reinforcement state will widen the store further.

## Findings

- `products/life-clock-ios/Sources/App/LifeClockStore.swift:172` (onboarding completion)
- `products/life-clock-ios/Sources/App/LifeClockStore.swift:217` (quest completion celebration)
- `products/life-clock-ios/Sources/App/LifeClockStore.swift:229` (quest undo)
- `products/life-clock-ios/Sources/App/LifeClockStore.swift:276,282,288,294` (four-branch if/else for check-in moments — also flagged as simplification)
- `products/life-clock-ios/Sources/App/LifeClockStore.swift:313` (reset)

## Proposed Solutions

### Option 1 (recommended): Extract `SupportMomentPresenter`

Pure value-typed presenter with a single entry point: `func moment(for intent: SupportIntent, delta: TimeDelta?) -> SupportMoment?`. Store mutations call the presenter; presenter owns all copy.

Pros: copy lives in one file; A/B copy testing trivial; store stops branching on UX prose; testable in isolation.
Cons: one new file.
Effort: Small.
Risk: Low.

### Option 2: Move copy strings into `ToneMode`

`ToneMode` already owns tone-aware copy. Add `supportMoment(for: SupportIntent) -> SupportMoment` keyed by tone.

Pros: tone-aware copy by default — supports future tone differentiation.
Cons: ToneMode is already overloaded; couples presenter to tone enum.
Effort: Small.
Risk: Medium.

### Option 3: Inline acceptable

Argue that 6 sites is below the threshold; document and revisit at 10.

Pros: zero work.
Cons: every reinforcement-state addition widens the leak; precedent for embedding copy in mutations.
Effort: None.
Risk: Medium (compounds).

## Recommended Action

(leave blank for triage)

## Technical Details

- Affected files: `LifeClockStore.swift`, new `SupportMomentPresenter.swift` under `Sources/Shared/` (Option 1).
- Tests: store tests should assert presenter delegation, not copy strings; copy assertions move to presenter tests.

## Acceptance Criteria

- [ ] No raw `SupportMoment(title:detail:tone:)` constructors inside `LifeClockStore` mutation methods.
- [ ] All UX copy lives in one presenter or in `ToneMode`.
- [ ] Existing store tests still pass; new presenter tests cover the copy matrix.

## Work Log

(to be filled in)

## Resources

- Architecture review (this audit), 2026-04-30
- Code-simplicity review (this audit), 2026-04-30 — flags the same four-branch if/else under "P1 — collapse"
