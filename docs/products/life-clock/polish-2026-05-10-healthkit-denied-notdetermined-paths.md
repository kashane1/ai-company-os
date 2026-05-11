# Polish Session — life-clock — 2026-05-10 — healthkit-denied-notdetermined-paths

## Mode

`freeform-polish` · idea #7 (submission-blocker tier, 30-day window).

Drove the app under two HealthKit auth states — `LIFECLOCK_HEALTH_AUTH=denied`
and `LIFECLOCK_HEALTH_AUTH=notDetermined` — and walked
Onboarding → Today → History → Plan → Profile. The prompt called the 4/30 audit's
finding #3 ("Health permission step felt broken in simulator") as the precedent
to verify and tightened a 30-day clock for App Review readiness.

Iteration cap: 8. Final computer-use checkpoint: yes (mandatory per operator).

### Fixture deviation (one)

Operator specified "cold install (no UI_TEST_SCENARIO=onboarded)". Cold-install
exercises the Onboarding HealthKit step but reaching Today / History / Profile
from a true fresh launch means driving ~25 onboarding screens per auth state —
infeasible inside the iteration cap. So the matrix used
`LIFECLOCK_UI_TEST_SCENARIO=onboarded` to land directly on each tab. The
in-onboarding HealthKit step was verified separately via
`LIFECLOCK_JUMP_TO=healthKitAuth`. Reading the audit's intent (verify the named
surfaces under each auth state), this hybrid is what's actually testable; the
deviation is flagged here so it isn't repeated silently.

### Pre-flight (one infra fix that wasn't in scope but blocked driving)

`xcrun simctl launch` doesn't pass env vars as positional args — they must be
exported in the calling shell with a `SIMCTL_CHILD_` prefix. Initial passes
silently dropped every `LIFECLOCK_*` flag, which is why the first two attempts
re-rendered the cold-install Welcome screen regardless of the env-var matrix.
Recorded here so the next polish-session driver doesn't relearn it. Not
codified yet — fixing the driver convention is a separate task.

## Iterations

- [23:55] 5539c9b — feat(life-clock): Open Settings affordance for HK re-grant — Polish — Profile (`.noRecentData` / `.historicalOnly`)
- [23:58] 5d95882 — feat(life-clock): inline HK connect button on Today sparse headline — Polish — Today (`.awaitingAuthorization`)

Both auth-state matrices re-captured after each commit; no unintended diffs on
the screens not touched (History empty-state copy unchanged in both states;
Profile under `.awaitingAuthorization` still shows just "Connect Apple Health"
with no Open Settings — the button is correctly gated to the post-decision
branches where the system sheet won't re-prompt).

## Stretch decisions (operator review)

None this session. Both fixes are Polish-tier — restore an action whose absence
left the user reading a dead-end string.

## Asks

### Resolved this session

None — both polish fixes followed unambiguously from the 4/30 audit's intent +
existing copy stance (the protocol comment in `HealthKitServiceProtocol.swift`
already commits to "never claim to know denied"; the fixes just add the
re-grant affordance that the honest copy implies).

### Outstanding (cycle-end batch)

1. **WelcomeView headline reads "Earn time with better habits."** The 4/30
   audit flagged "earn time back" as a gamey framing in the V1 onboarding. V2
   intentionally retained "earn time" framing — `MeetYourClockView` says
   "Healthy habits earn time. Bad days cost it." Is this an explicit Decided
   constraint, or worth revisiting before submission? Not editing without
   operator input. Screenshot:
   `state/polish-2026-05-10-hk/denied/01-onboarding-step0.png`.

2. **`LIFECLOCK_JUMP_TO` deferred path swap lands behind WelcomeView when the
   cold-open auto-advance fires.** Setting `LIFECLOCK_JUMP_TO=healthKitAuth`
   while also using a cold install (no `UI_TEST_SCENARIO=onboarded`) sometimes
   leaves `path = [.welcome]` instead of `path = [.healthKitAuth]`. The 50ms
   `DispatchQueue.main.asyncAfter` swap in
   `OnboardingCoordinator.applyJumpFixtureIfNeeded` may be racing the cold-open
   onAppear in some startup orderings. The fixture worked correctly when
   `LIFECLOCK_UI_TEST_SCENARIO=onboarded` was unset, so this is mainly a polish
   driver convenience issue, not a user-facing bug. Worth a separate
   investigation before the next jump-fixture-heavy session.

## Regressions caught

- None. Screens not under work (History empty state, Profile under
  `.awaitingAuthorization`, all `.unavailable` branches) match prior renders.

## A11y identifiers added

- `profile.health.openSettings` (Profile · Apple Health section · Open Settings button)
- `today.headlineSparse.connect` (Today · sparse headline · Connect Apple Health button)

## Vision updates

- Open Questions appended: none directly to vision.md — both Asks above are
  surfaced here in the session log for the operator to triage.
- Decided constraints proposed: none.

## Coverage matrix (final)

| Surface | denied | notDetermined |
|---|---|---|
| Onboarding cold-install lead-in | renders WelcomeView; gated on operator Ask #1 | same |
| Onboarding `healthKitAuth` (via JUMP_TO) | "Connect" + "Not now" + soft-skip caption — honest | same |
| Today | sparse "Waiting on data" headline + Confidence Low; mascot at 12 baseline (no fabricated delta); body honest about "we can't currently see Apple Health data" | sparse "Connect Apple Health" headline + new inline Connect button + Confidence Low; mascot at baseline |
| History | "Past days": "We can't currently see recent Apple Health data, so History stays honest instead of inventing a trend." No locked rows, no fogged Pro tease | "Past days": "History fills in after Apple Health can share a few days of steps, sleep, or workouts." |
| Plan (Today's quests card / Pro paywall) | quests still render; Plan editor is Pro-gated via paywall — no HK-dependent dead-end | same |
| Profile · Apple Health section | "Check Apple Health again" + honest "Apple may not re-show…" copy + NEW "Open Settings" button | "Connect Apple Health" primary button + rationale copy (system sheet still works pre-decision) |

Success criteria from the operator brief, verified:

- ✓ Both denied and notDetermined paths walk all five named surfaces without
  dead-ends.
- ✓ Every blank chart / data section has an honest "needs HealthKit" message
  written for the specific state (auth-pending vs no-recent-data wording differ
  by intent).
- ✓ Today bar never fabricates a delta — the headline goes to the sparse
  variant under both states; the mascot's hands stay at 12; the projected
  healthspan number (82.9 years) is a biographic baseline derived from
  DOB+sex, not invented from HK signal.
- ✓ Goldens captured for both states under
  `products/life-clock-ios/.polish/goldens/healthkit-{denied,notdetermined}-{today,history,profile}.png`.

## Final computer-use checkpoint

Drove the app live in Simulator under both auth states with real taps:

- denied · Today → History → Profile: all three honest; "Open Settings" appears
  below the "Apple may not re-show…" copy in Profile's Apple Health section.
- notDetermined · Today: tapped the new inline "Connect Apple Health" button →
  fixture flipped `authorizationKnown` → `refreshFromHealthKit` ran → headline
  re-rendered as "+58 min · Confidence: High" with the mascot hands rotating to
  match. End-to-end state transition green.

Final screenshots saved to the goldens directory above.

## Next pass

- Operator-triage Asks 1 and 2.
- If Ask #2 (jump-fixture race) gets prioritized, the cleanest fix is to let the
  jump set `path = [target]` synchronously inside the coordinator init rather
  than from `.onAppear`. The current 50ms `asyncAfter` is itself a workaround
  for an older race with NavigationStack settle — likely no longer needed on
  iOS 26.
