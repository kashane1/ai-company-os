# Polish Session - life-clock - 2026-05-08 - vision-today-completion-payoff

## Mode

vision-driven. Payload: audit the Today daily quest completion path for the 2026-04-30 finding that completed actions felt weak and disconnected. Seed: `LIFECLOCK_UI_TEST_SCENARIO=onboarded`, mock HealthKit authorized, Coach tone, fixed date `2026-05-08T12:00:00Z`. Iteration cap: 6. Final computer-use checkpoint: yes.

## Iterations

- [12:34] no commit - Observation only - Feature-tier gap - Today quest completion

## Stretch decisions (operator review)

- None. The observed gap is Feature-tier because it would add new motion/haptic behavior to the daily loop.

## Asks

### Resolved this session

- None.

### Outstanding (cycle-end batch)

- Should daily quest completion pay off as mascot motion, a temporary clock-hand advance, tone-aware micro-copy, or some combination? Appended to `vision.md` Open Question #14 with three concrete options.

## Regressions caught

- None. No product code changed.

## A11y identifiers added

- None. Existing identifiers were sufficient: `today.planAction.0`, `today.supportMoment`, `today.mascot`.

## Vision updates

- Open Questions appended: Daily quest completion payoff, with current behavior and Options A/B/C.
- Decided constraints proposed: none.

## Evidence

- Before screenshot: `products/life-clock-ios/.polish/goldens/today-completion-before.png`
- After screenshot: `products/life-clock-ios/.polish/goldens/today-completion-after.png`
- Observed current behavior: tapping the first plan action flips the row from incomplete to complete, scrolls Today to keep the completed row in view, inserts a support card (`"Nice work."` / `"Added to your progress log. Possible impact: +18 min."`), and leaves the headline/mascot at the pre-action `+28 min`.

## Next pass

- If the operator chooses an option, implement as Feature-tier with focused tests for Reduce Motion, completion undo, and tone copy.
