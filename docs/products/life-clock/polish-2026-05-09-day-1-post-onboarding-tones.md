# Polish Session — life-clock — 2026-05-09 — day-1-post-onboarding-tones

## Mode

`freeform-polish`. Operator framing: most polish so far has been on returning
users with `LIFECLOCK_SEED_STREAK=14`. The day-1 user — the one who installs
from the App Store — has not had a focused capture. Drive: post-onboarding,
Today on day 1 (no logged habits, fresh HK auth, mock baseline data only),
each tone. Find rough edges across Today / History / Weekly Report /
PlanEditorSheet / monthlyLoggingBanner; polish anything Polish-tier; queue
Feature-tier asks for missing null-state copy.

Iteration cap: 8. Final computer-use checkpoint: yes (degraded — see Asks).

## Recon fixture

Per-tone launch combo:

```
LIFECLOCK_UI_TEST_SCENARIO=onboarded
LIFECLOCK_USE_MOCK_HEALTH=1
LIFECLOCK_HEALTH_AUTH=authorized
LIFECLOCK_HEALTH_PROFILE=baseline
LIFECLOCK_SEED_STREAK   (unset → 0)
LIFECLOCK_SEED_QUESTS_COMPLETED   (unset → 0)
LIFECLOCK_SEED_TONE=gentle | coach | firm_direct
```

Goldens captured under `products/life-clock-ios/.polish/goldens/`.

### Recon-fixture caveats (load-bearing for the findings below)

1. **Mock baseline always returns 7 days of synthesized HK signal.** A
   true-cold-start user on real HealthKit could land on 0–7 days of usable
   data depending on their HK history; this fixture papers over that
   variance. Findings about "weekly visible on day 1" reflect the
   rich-HK-history case.
2. **The simulator is auto-Pro.** StoreKit configuration grants the Pro
   entitlement on launch, so `subscriptions.isPro == true` for the recon.
   This triggers the `historicalImporter` from `HistoryView.onAppear`,
   which back-fills 90 days of mock snapshots into SwiftData on first
   History visit. The free-user "Past days" empty state is therefore
   unreachable from this fixture without a `LIFECLOCK_FORCE_FREE` knob
   (which does not exist; flagged as Feature ask below).
3. **`LIFECLOCK_SEED_TONE` only takes effect on a fresh install.**
   `seedInitialStateIfNeeded` short-circuits when a `UserProfile` already
   exists. The first capture pass missed `sleep 1` between
   `simctl uninstall` and `simctl install`, which left a stale profile on
   disk and caused gentle-toned History to render with coach copy.
   Subsequent captures use the install-then-launch order with the
   intervening sleep. Worth standardizing in the recon harness.

## Iterations

- [09:30] `8f4d913` — fix(life-clock): tone-keyed empty placeholders for weekly drivers — Polish — `history.weekly.drivers`
- [09:31] `c77140d` — chore: ignore .claude/scheduled_tasks.lock runtime file — Chore — repo

Iter-1 post-fix verified live across all three tones:

- gentle → `postfix-gentle-history.png` reads "Top drag / Nothing held you back" in secondary color.
- coach → `postfix-coach-history.png` reads "Top drag / No drag this week" in secondary color.
- firm_direct → `postfix-firm_direct-history.png` reads "Top drag / No drag." in secondary color.

The em-dash placeholder is gone from all three; the negative-driver row no longer reads as a broken state on a clean week.

## Stretch decisions (operator review)

None this session.

## Asks

### Resolved this session

None.

### Outstanding (cycle-end batch)

Pasted in the PR body.

## Regressions caught

None — only one product surface touched (`history.weekly.drivers`). Other
goldens unchanged across the iter-1 rebuild + relaunch.

## A11y identifiers added

None this session.

## Vision updates

- Open Questions to consider: see Asks F1–F5 in PR body. None auto-appended
  to `vision.md` — operator drives the ratchet.
- Decided constraints proposed: none yet; pending operator answers on
  weekly suppression and confidence-label calibration.

## Next pass

- Add a `LIFECLOCK_FORCE_FREE=1` env knob so the free-user Day-1 surfaces
  (`paywallTeaser`, fogged history rows, free `weeklyEmptyState` paths)
  are reachable from the recon harness. Today they're hidden behind
  StoreKit's auto-Pro grant in DEBUG.
- Tone-key the QuickLog card subtitle ("Fuel, extras, recovery, strength,
  nicotine. About 30 seconds.") — currently single-tone; a Stretch-tier
  win once we also know what the gentle/firm rephrasings should sound like.
- Stabilize the simctl-driven scroll/tap helper. iOS interpreted several
  of this session's drag taps as a system swipe-up-to-home on the iPhone
  17 Pro layout; lost minutes per launch. A small Swift helper that uses
  `IOKit` HID events instead of CGEvents may behave better.
- Verify the PlanEditor Day-1 fallback copy live on a true-free user once
  `LIFECLOCK_FORCE_FREE` exists. Source-side the fallback fires when
  `loggedDays < 5` (commit `1bd363a`); the auto-Pro fixture imports
  ≥5 days of mock data immediately, so the personalized variant masks
  the fallback in the recon I ran.

## Final-check

Operator approved Simulator computer-use access on the second request.
Drove the device via `mcp__computer-use__*` tools at full tier:

1. **Iter-1 fix verified live on gentle History.** Tapped History from
   Today; "What helped, what didn't" rendered with "Top positive: Sleep"
   in green and "Top drag: Nothing held you back" in secondary color.
   No em-dash regression. Symmetrical positive-side placeholder also
   exercised across the three tones via the simctl-driven recapture
   above.
2. **PlanEditor sheet exercised.** Tapped Today's Plan → Edit; sheet
   opens cleanly. Three categories render with their variants:
   - Movement: 1-minute single-leg stand / 15-minute bike or rowing
     session / Bodyweight circuit, 3 rounds.
   - Sleep & Recovery: Run your bedtime routine tonight / 5-min bedtime
     stretch / 5-min slow breathing before bed.
   - Nutrition & Habit: Eat within an hour of waking / Caffeine cutoff
     at 2pm today / Slow chewing at one meal.
3. **Step-target quest fallback copy NOT surfaceable from this fixture.**
   The `movement.steps-target.v1` quest (the one with the "(We'll tune
   this once we have a week of your data.)" Day-1 fallback added in
   commit `1bd363a`) is absent from Movement's variant list in this
   fixture's PlanEditor. Movement instead shows the three pool
   alternatives above. Possible causes (untriaged):
   - The QuestEngine is selecting a different default Movement quest
     when the auto-Pro fixture's `historicalImporter` has back-filled
     ≥5 days of mock snapshots, so the step-target quest never enters
     the slot in the first place.
   - The plan-variants resolver may filter out the steps-target quest
     when `loggedDays` crosses the personalization threshold.
   Either way, source-side the fallback string is verified by reading
   the Phase-3 step-target diff. Live verification needs a true free /
   `loggedDays < 5` fixture — this loops back to Ask F4
   (`LIFECLOCK_FORCE_FREE=1` recon knob).
4. **Cancel button on PlanEditor works** (returned to Today; underlying
   view briefly rendered black before the next tab-switch — transient,
   not a regression).
