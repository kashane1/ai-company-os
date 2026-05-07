# Polish Session — life-clock — 2026-05-06 — plan-editor-pro-and-free-walk

## Mode

`freeform-polish`. Observer = vision tone matrix + memory conventions + the design system. Iteration cap 8. Final computer-use checkpoint requested; the local computer-use bridge timed out a third time (`request_access` 300 s) — substituted with `testFinalAcceptance_VariantSurvivesSwipeDown` in XCUITest, matching the substitution from `polish-2026-05-06-pro-disabled-touchpoints-walkthrough.md`.

The new `Sources/Features/Today/PlanEditorSheet.swift` was the focus. Walked Pro path (default in sim) + Free path (`LIFECLOCK_SIMULATOR_PRO_DISABLED=1`).

## Iterations

- [22:11] _build_ — `xcodegen generate && xcodebuild build` — green on `iPhone 16e (17.x)`
- [22:13] _observe_ — Today screen golden as Pro: `.polish/goldens/01-today-pro.png`. Bundle id is lowercase (`io.aicompanyos.products.lifeclock`) and `xcrun simctl launch` requires `SIMCTL_CHILD_*=` env-var prefixes; positional args are silently dropped.
- [22:18] `48fba32` — `feat(life-clock): tone-aware copy on PlanEditorSheet (gentle/coach/firmDirect)` — Stretch — PlanEditorSheet, ToneMode. Added `planEditorTitle` / `planEditorSubtitle` / `planEditorResetCTA` to ToneMode and wired them through PlanEditorSheet. Same commit added a11y ids for the subtitle, each category title (`planEditor.categoryTitle.<rawValue>`), and the empty-state line (`planEditor.empty.<rawValue>`) — those are part of the same logical "PlanEditorSheet identifier + copy hygiene" change.
- [22:21] `1bd363a` — `feat(life-clock): personalize step-target detail when ≥5 days logged` — Stretch — QuestEngine. Movement detail copy now reads "Get to N steps — tuned from your last K days" once we have ≥5 logged step-days, and "We'll tune this once we have a week of your data." otherwise. Picker no longer reads "stock 7,500 for everyone."
- [22:25] _UITest_ — added `UITests/PlanEditorRecon.swift` with five cases: `testProEditorExposesAllCategories`, `testProVariantPickPersistsWithinDay`, `testProResetClearsAllOverrides`, `testTomorrowReset_OverridesClearedOnNewDay`, `testFinalAcceptance_VariantSurvivesSwipeDown`. Drives the AX-tree path the operator asked for (`(a)–(c)`) plus the swipe-down acceptance gate.

## Stretch decisions (operator review)

- **Tone strings** — gentle reads "Today's plan" / "Swap any line for another. One pick per area, just for today." / "Use today's defaults"; coach keeps the existing "Edit today's plan" / "One pick per category. Resets tomorrow." / "Reset to defaults"; firmDirect reads "Pick today's plan" / "One pick per slot. Today only. Resets at midnight." / "Drop my picks". Picked imperative-but-not-mean for firmDirect to match `todayPlanSubline = "Pick one. Do it."` already in ToneMode.
- **Step-target copy** — chose to surface the day-count explicitly ("last K days") rather than a vague "your usual." The exact integer reads as honest about the sample, which is the calibration reading the picker actually owes the user. With <5 days the line admits the default is provisional rather than pretending it's tuned.

## Asks

### Resolved this session

_none — both planned Stretch commits landed without operator input._

### Outstanding (cycle-end batch)

1. **Mid-edit dismissal does not restore prior plan** _(Feature → always Ask)_
   The operator's checklist included _"sheet dismissal restores prior plan if user cancels mid-edit."_ Current PlanEditorSheet calls `selectPlanQuest(...)` synchronously on row tap, which calls `persistTodayPlanOverrides()` immediately. Done is the only commit affordance; swipe-down already commits. There is no Cancel.
   - **(a)** Add a draft layer + Cancel button + revert-on-dismiss. Roughly: snapshot `todayPlanOverrides` on `.onAppear`; route row taps to a local `@State draftPicks`; commit on Done; revert to snapshot on swipe-down/Cancel. Adds a per-sheet draft field; matches the operator's stated intent.
   - **(b)** Accept instant-commit, remove the "Done" framing, drop the Cancel implication entirely. Today's screen already shows the changes the moment a variant is picked, which is its own confirmation. Lower-friction; matches how iOS settings sheets often behave.
   - Recommendation: **(a)**. The operator framed the Pro-lock value as "preview-then-paywall, not 'you can't do this' wall" — cancel-restore is the equivalent affordance for committed users (preview-the-swap, commit-on-Done) and the picker becomes safer to explore. Cost is one snapshot field + one button.
   - Goldens for context: `01-today-pro.png` (Today as Pro before edit). Editor goldens to come once `PlanEditorRecon` runs green.

2. **"Preview-then-paywall" framing for the Free Pro lock** _(Vision-question)_
   The operator phrased this as preview-then-paywall rather than "you can't do this." Today's plan card _already_ shows the engine's defaults to Free users — only the chip routes to paywall (`today.planEditLocked → PaywallSheet`). Two readings:
   - **(a)** Current behavior is already preview-then-paywall by construction: Free users see today's plan content (the variants the engine picked); they only hit the paywall when they try to swap. No change needed.
   - **(b)** Operator's intent is that Free users should be allowed to _open the editor sheet_ and see all variants behind a frosted overlay with a single CTA — a richer preview before the paywall lands. This is a Pro-tier preview pattern (Apple's own paywall sheet does this for some features). Costs another sheet variant + a frosted-row decoration.
   - Recommendation: **(a) for v1**. The Today plan card body is the preview surface; a second "preview the swaps you can't do" UI doubles up on the same message. If the variant pool grows beyond 3-per-category later, revisit.
   - Append to `vision.md` Open Questions iff the operator picks (b). I have not appended; this is the proposal.

## Regressions caught

- _Pending PlanEditorRecon run + golden refresh — final state to be appended once `xcodebuild test` returns._ No source-only regressions noticed in the Polish/Stretch fixes; the only screens the loop intentionally changed are PlanEditorSheet (entirely new copy + ids) and the movement quest detail line on Today's plan card.

## A11y identifiers added

- `planEditor.subtitle` — tone-aware subtitle inside the sheet
- `planEditor.categoryTitle.movement`
- `planEditor.categoryTitle.sleepRecovery`
- `planEditor.categoryTitle.nutritionHabit`
- `planEditor.empty.movement`
- `planEditor.empty.sleepRecovery`
- `planEditor.empty.nutritionHabit`

(Existing ids on the sheet were already complete from the original implementation: `planEditor.screen`, `planEditor.done`, `planEditor.reset`, `planEditor.category.<rawValue>`, `planEditor.option.<slug>`.)

## Vision updates

- Open Questions appended: _none._ The two Asks above stay in this session log until the operator resolves them; only Vision-questions resolved as constraints flow into `vision.md`, and these are still open.
- Decided constraints proposed: _none._

## Test surface added

- `UITests/PlanEditorRecon.swift` — 5 cases. Pro variant-discoverability, within-day persistence, reset, tomorrow-reset (relaunch with advanced `LIFECLOCK_FIXED_DATE`), swipe-down acceptance gate. Free Pro-lock path stays in `ProTouchpointsRecon.testTouchpoint3_PlanEditorLockedRoutesToPaywall` (no duplication).

## Computer-use bridge status

`mcp__computer-use__request_access` timed out at 300 s for the third consecutive session. The MCP also formally disconnected mid-loop in a side-chat fork. Treating "bridge unreachable" as the working assumption and substituting XCUITest acceptance gates is now the de facto pattern. Worth a separate spike to repair the bridge before the next App Store submission, since the only thing real-finger validation reliably catches that XCUITest doesn't is rasterization regressions during multi-touch.

## Next pass

- **Resolve the two Asks above** (cancel-restore, preview-then-paywall framing) before this work goes to a PR.
- **Capture editor goldens per tone** (`02-editor-pro-coach.png`, `03-editor-pro-gentle.png`, `04-editor-pro-firm.png`) once the `LIFECLOCK_SEED_TONE` matrix is wired into PlanEditorRecon — current PlanEditorRecon launches the default coach tone only.
- **Repair the computer-use bridge** so the final acceptance pass can be a real-finger session before the next App Store push.
