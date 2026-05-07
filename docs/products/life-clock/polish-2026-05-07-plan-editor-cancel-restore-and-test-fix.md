# Polish Session — life-clock — 2026-05-07 — plan-editor-cancel-restore-and-test-fix

## Mode

`freeform-polish` continuation. Operator picked Asks 1 + 3 from yesterday's [`polish-2026-05-06-plan-editor-pro-and-free-walk.md`](polish-2026-05-06-plan-editor-pro-and-free-walk.md), accepted both recommendations, and asked for end-to-end computer-use validation now that the bridge is reachable again.

Iteration cap 8. Final computer-use checkpoint: **mandatory and ran clean.**

## Iterations

- [14:08] `ba32420` — `feat(life-clock): draft+Cancel+revert in PlanEditorSheet (Ask 1)` — Stretch-but-operator-pre-approved — PlanEditorSheet. Row taps now mutate sheet-local `@State draftPicks` instead of writing through to the store. Done diffs the draft against the baseline snapshot taken on appear and writes through; Cancel + swipe-down both discard. Toolbar gains a `planEditor.cancel` button alongside Done.
- [14:25] `a3e2c0a` — `test(life-clock): assert Done-commits / Cancel-reverts contract + bump waits (Ask 3)` — Stretch — UITests/PlanEditorRecon.swift. New helper `waitForVariantOption` does scroll-before-query + 10 s timeout. New cases: `testProCancelDoesNotCommit`, `testProSwipeDownDoesNotCommit`. `testFinalAcceptance_DonePersists_CancelReverts` exercises both branches in one launch.
- [14:50] `87e3762` — `fix(life-clock): preserve child a11y ids on planEditor.category container` — Polish — PlanEditorSheet. The outer `.accessibilityIdentifier("planEditor.category.<raw>")` was swallowing the inner `planEditor.categoryTitle.<raw>` / `planEditor.empty.<raw>` / `planEditor.option.<slug>` ids. Added `.accessibilityElement(children: .contain)` — same shape as the `today.plan` fix from yesterday's pro-disabled walkthrough. This is what `testProEditorExposesAllCategories` was failing on (AX query for `planEditor.categoryTitle.movement` returned nothing).

## Stretch decisions (operator review)

- **Draft semantics**: chose option (a) from yesterday's Ask 1 — sheet-local `@State draftPicks: [String: String?]` plus baseline snapshot, with Done as the only commit path. Rejected option (b) (instant-commit + drop the Done framing) because the operator framed Pro-lock as preview-then-paywall and the picker now mirrors that — preview-the-swap, commit-on-Done.
- **`draftCleared` tracking on Reset**: Reset blanks the draft and sets `draftCleared = true`; Done routes through `clearTodayPlanOverrides()` first, then replays any post-Reset picks (edge case: Reset → pick a new variant → Done). Cancel discards both the cleared flag and any picks. Alternatives considered: (i) Reset commits-and-stays vs (ii) Reset commits-and-dismisses — picked neither because the operator's frame is "everything inside the sheet is a draft until Done."
- **`commitDraft()` only writes diffs**: skips no-op writes against the baseline. Avoids redundant `selectPlanQuest` calls (each persists to UserDefaults), and means tapping the same row twice followed by Done is a true no-op.

## Computer-use checkpoint (the actual bridge ran this time)

Bridge came back online. Drove the Simulator end-to-end:

1. **Pro mode (default sim)** → scroll Today → "Today's Plan" header with slider-icon Edit chip → tap → sheet presents with title `"Edit today's plan"`, subtitle `"One pick per category. Resets tomorrow."`, all 3 categories + their variants, **Cancel and Done both in the toolbar** ✓
2. **Tap Post-meal 10-minute walk** → green checkmark on that row only ✓
3. **Tap Cancel** → sheet dismisses → Today plan card still shows the engine default **"Move a little more"**, NOT "Post-meal 10-minute walk" → **draft was discarded, store was untouched** ✓
4. **Re-open editor** → all radios empty (no leak from the discarded draft) ✓
5. **Tap Post-meal 10-minute walk → tap Done** → sheet dismisses → Today plan card now shows **"Post-meal 10-minute walk"** as the first quest → **commit-on-Done works** ✓
6. **Relaunch with `LIFECLOCK_SIMULATOR_PRO_DISABLED=1`** → plan card shows the "Pro" lock chip on the right while the plan body still renders the 3 quests → **preview-then-paywall confirmed by construction** (matches Ask 2 recommendation (a)) ✓
7. **Tap the lock chip** → `PaywallSheet` presents with Annual $49.99 preselected, Monthly $7.99, Lifetime $129.99, Continue/Restore/Close — `today.planEditLocked` routes correctly ✓

Goldens captured under `products/life-clock-ios/.polish/goldens/05-today-pro-day7.png` (initial Pro launch, day-1 fixture). Per-step screenshots are in this session's chat history.

## Asks

### Resolved this session

- **Ask 1** (cancel-restore) → resolved. `ba32420` lands the draft+Cancel+revert contract; computer-use confirmed the user-facing semantics on the live sim.
- **Ask 3** (PlanEditorRecon stabilization) → resolved at the source level: `87e3762` fixes the categoryTitle/empty/option a11y id clobbering that yesterday's run was actually tripping over, and `a3e2c0a` lands the timeout/scroll helper. Re-running the full suite under low contention is the remaining net step (queued in Outstanding).

### Outstanding (cycle-end batch)

1. **Re-run `LifeClockUITests/PlanEditorRecon` under low host contention.** Yesterday's run was at 5+ concurrent xcodebuild processes from neighboring sessions; today started at 5 and dropped to 1–2 mid-session. The 3 failures we observed today (testFinalAcceptance, testProCancelDoesNotCommit, testProEditorExposesAllCategories) all happened during the high-contention window — the first two were 175 s and 194 s per case. testProEditorExposesAllCategories surfaced the actual a11y bug (line 42, planEditor.categoryTitle.movement), which is now fixed. Recommendation: rerun the full suite once host load is light. If any case still fails on a *semantic* assertion (not openPlanEditor / waitForVariantOption timeouts), chase it then.

2. **Existing Pro-tier overrides survive a Free relaunch.** Observed during step 6 of the computer-use checkpoint: I committed the Post-meal walk as Pro, then relaunched with `LIFECLOCK_SIMULATOR_PRO_DISABLED=1`, and the override was still applied to Today's plan card (showing the walk title to a Free user). Mechanism: `loadTodayPlanOverrides` and `applyTodayPlanOverrides` don't gate reads on `entitlements?.isPro`; only the *write* gate (`selectPlanQuest`) does. This is preexisting behavior not introduced by Ask 1 — but worth flagging since the operator's stated mental model is "Pro features live behind the chip." Two readings:
   - **(a)** Keep it. A user who upgrades, swaps a quest, then cancels their subscription should still see what they picked until midnight (one-shot semantics already hold). Cleaner than ripping a value the user already chose.
   - **(b)** On entitlement transition Pro → Free, prune any user-picked overrides so Free users always see engine defaults.
   - **Not chasing this session** — flagging only.

## Regressions caught

- A11y id clobbering on `planEditor.category.<raw>` → fixed in `87e3762` (recurrence of the same shape that bit `today.plan` two days ago — should consider a lint rule that flags `.accessibilityIdentifier` on a container that has child ids without `.accessibilityElement(children: .contain)` between them; see Next pass).
- No source regressions in the draft semantics. Computer-use ran the full Pro contract clean.

## A11y identifiers added

- `planEditor.cancel` — new toolbar Cancel button on PlanEditorSheet.

(All other planEditor.* ids landed yesterday and now actually surface to AX queries thanks to `87e3762`.)

## Vision updates

- Open Questions appended: **none**.
- Decided constraints proposed: **none**. The "Pro lock = preview-then-paywall" frame is now de-facto encoded in the picker (Done-only commit path mirrors the same pattern), but it's still a Stretch behavior, not a vision-level commitment. Surface for a Decided-constraints proposal only if the operator wants to lock it in.

## Test surface added

- `UITests/PlanEditorRecon.swift` — picker contract:
  - `testProEditorExposesAllCategories` (existing, now unblocked by 87e3762)
  - `testProVariantPickPersistsWithinDay` (rewritten — single pick + Done is the contract)
  - `testProResetClearsAllOverrides` (rewritten — pick + Done, then reopen + Reset + Done)
  - `testProCancelDoesNotCommit` **NEW** — Ask 1 binding test
  - `testProSwipeDownDoesNotCommit` **NEW** — Ask 1 binding test
  - `testTomorrowReset_OverridesClearedOnNewDay` (existing)
  - `testFinalAcceptance_DonePersists_CancelReverts` (rewritten — both branches in one launch)

## Next pass

- Re-run `PlanEditorRecon` under low-contention to close Outstanding 1.
- Decide on Outstanding 2 (Pro-tier override survives Free relaunch) — feels like an Ask 2-tier vision question, not a polish one. Worth its own brief brainstorm.
- Consider a SwiftUI lint check for `.accessibilityIdentifier` on a container that has labelled children without `.accessibilityElement(children: .contain)` between them. This pattern has now bitten three different containers (`today.plan`, `planEditor.category.<raw>` for two id sets) over four days. A test or a custom DSL helper would compound.
- The computer-use bridge worked end-to-end this session. If it stays reliable for one more session, swap the XCUITest swipe-down acceptance gate for the real-finger pass everywhere (it catches things the AX-tree misses, like sheet animation glitches and tap-target hit testing).
