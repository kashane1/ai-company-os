---
status: pending
priority: p2
issue_id: "031"
tags: [code-review, life-clock, ios, testability, agent-native]
dependencies: []
---

# Problem Statement

`LifeClockLaunchConfiguration` exposes only two scenarios (`onboarding`, `onboarded`) and one hardcoded fixed date. Several user-reachable UI states have no deterministic launch fixture, which means an agent (or human auditor) cannot reproduce them without manually clicking through the app first.

## Findings

In `products/life-clock-ios/Sources/App/LifeClockLaunchConfiguration.swift:7-10,26`:

- `Scenario` enum has only `.onboarding` and `.onboarded`.
- `EngineClock.fixed` uses one timestamp; no way to override via env var.

Missing seed states:
- `paywall_shown` — can't deterministically reach `PaywallSheet`.
- `health_denied` / `health_authorized_no_data` — only `LIFECLOCK_UI_TEST_AUTHORIZED=1` exists; no denied-permission path.
- `mid_onboarding_step_N` — agent can't audit a specific step in isolation.
- `streak_active` / `support_moment_visible` — these UI surfaces are conditional; no fixture forces them on.
- `quests_completed_today` / `quests_empty` — for reinforcement and empty-state audits.

## Proposed Solutions

### Option 1 (recommended): Orthogonal env vars

Add independent fixture knobs:
- `LIFECLOCK_FORCE_PAYWALL=1`
- `LIFECLOCK_HEALTH_AUTH=denied|authorized|notDetermined`
- `LIFECLOCK_SEED_STREAK=<int>`
- `LIFECLOCK_SEED_QUESTS_COMPLETED=<int>`
- `LIFECLOCK_FIXED_DATE=<ISO8601>`

Pros: composable; agent can probe any combination; doesn't grow the Scenario enum.
Cons: parsing surface widens; need a small validation pass at launch.
Effort: Small-Medium.
Risk: Low (test-only path).

### Option 2: Expand Scenario enum

Add cases per state. Simpler but combinatorial blowup.

Pros: structured.
Cons: each combination needs a new case (`onboarded_paywall_shown_streak_3`).
Effort: Medium and growing.
Risk: Medium.

## Recommended Action

(leave blank for triage)

## Technical Details

- Affected files: `LifeClockLaunchConfiguration.swift`, possibly `MockHealthKitService.swift` (denied-permission mock), tests under `UITests/`.

## Acceptance Criteria

- [ ] Paywall, health-denied, streak-N, and fixed-date scenarios all reachable via env vars.
- [ ] Adapter for `ios-simulator-ux-audit` references the env-var menu.
- [ ] At least one XCUITest exercises the paywall-dismiss flow using the new fixture.

## Work Log

(to be filled in)

## Resources

- Agent-native parity review (this audit), 2026-04-30
- `products/life-clock-ios/Sources/App/LifeClockLaunchConfiguration.swift`
