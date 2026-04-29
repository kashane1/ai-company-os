---
status: completed
priority: p1
issue_id: "021"
tags: [code-review, life-clock, ios, determinism, engine-clock]
dependencies: []
---

# Problem Statement

The deterministic-engine boundary is the load-bearing architectural claim of the Life Clock skeleton — `EngineClock` exists so engines never call `Date()`, `Calendar.current`, or `TimeZone.current`. Engines comply. **The store does not.** `LifeClockStore` calls `Date()` directly in `bootstrap()`, `completeOnboarding`, and `toggleQuestCompletion`, and reads `Calendar.lifeClockUTC` instead of routing through the injected `engineClock.calendar`.

Result: tests that pin time via `EngineClock.fixed(...)` still see real-wall-clock writes from the store layer. The boundary leaks at exactly the seam it was designed to protect, and every future engine added to the store will inherit the assumption that "tests pin time" while the store keeps writing real `Date()`.

## Findings

- `products/life-clock-ios/Sources/App/LifeClockStore.swift:57` — `let now = Date()` inside `bootstrap()`.
- `products/life-clock-ios/Sources/App/LifeClockStore.swift:81-82` — `profile.disclaimerAcceptedAt = Date()`, `profile.onboardingCompletedAt = Date()`.
- `products/life-clock-ios/Sources/App/LifeClockStore.swift:93,96` — `quest.completedAt = Date()` and `TimeLedgerEntry(date: Date(), ...)`.
- `products/life-clock-ios/Sources/App/LifeClockStore.swift:43` — `Calendar.lifeClockUTC.date(...)` reads a static UTC calendar instead of `engineClock.calendar`.
- `products/life-clock-ios/Sources/Engines/EngineClock.swift:5` — docstring states the contract: "Engines never call `Date()`, `Date.now`, `Calendar.current`, or `TimeZone.current` directly."
- Architecture review: "the boundary is leaking on day one."

## Proposed Solutions

### Option 1: Extend `EngineClock` ownership to the store

Pass an `EngineClock` (or a thin "wall clock" facade derived from it) into `LifeClockStore` and use it for every `Date()` and calendar lookup the store currently does inline. Tests inject `.fixed(...)` and the store layer becomes time-pinned alongside the engines.

Pros:
- Closes the boundary leak completely.
- Tests can pin "today" deterministically through the entire pipeline.
- Matches what the deepened plan implied ("engines and the store consume the same clock").

Cons:
- Slightly more plumbing — the store now has a `clock: EngineClock` field used for all timestamping.
- `LifeClockStore` already holds a `clockEngine`/`questEngine`; a third clock-shaped field could be confusing. Mitigate by exposing `clock` on the engines or sharing one `EngineClock` across both engines and the store.

Effort: small
Risk: low

### Option 2: Document a narrower contract — engines only, store free

Update `EngineClock`'s docstring to say "engines never call `Date()`; the store may, since it is the boundary between deterministic engines and real-time UI events." Keep the store's `Date()` calls.

Pros:
- Zero code change.

Cons:
- Tests cannot pin "today" for store mutations (quest completion timestamps, ledger entries).
- Sets a narrower invariant than the plan promised — risk of drift.
- The CI grep gate in the plan needs to grow an exclusion for `Sources/App/`.

Effort: trivial
Risk: medium (drift risk)

## Recommended Action

(Filled during triage.)

## Technical Details

- Add `let clock: EngineClock` to `LifeClockStore` (or expose `clockEngine.clock` publicly).
- Replace `Date()` with `clock.now()` and `Calendar.lifeClockUTC` with `clock.calendar` everywhere in `LifeClockStore.swift`.
- Remove the static `Calendar.lifeClockUTC` extension (now unreferenced) — or move it to test fixtures only.

## Acceptance Criteria

- [ ] `git grep -n 'Date()\|Date\.now\|Calendar\.current\|TimeZone\.current\|Calendar\.lifeClockUTC' products/life-clock-ios/Sources/` returns zero hits outside `EngineClock.swift`.
- [ ] `LifeClockStoreTests` constructs the store with `.fixed(...)` and asserts that quest-completion timestamps equal the pinned date.
- [ ] CI grep gate in the plan extended to cover `Sources/App/`.

## Work Log

- 2026-04-27: Created from PR #14 architecture review.

## Resources

- PR: https://github.com/kashane1/ai-company-os/pull/14
- File: `products/life-clock-ios/Sources/App/LifeClockStore.swift`
- File: `products/life-clock-ios/Sources/Engines/EngineClock.swift`
