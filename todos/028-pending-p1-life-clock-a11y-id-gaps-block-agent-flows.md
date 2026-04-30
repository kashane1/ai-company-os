---
status: pending
priority: p1
issue_id: "028"
tags: [code-review, life-clock, ios, accessibility, agent-native]
dependencies: []
---

# Problem Statement

The diff added many accessibility identifiers (good — `today.checkInCard`, `today.planAction.N`, `onboarding.continue`, etc.), but missed several controls that block agent-native parity. An agent driving the simulator cannot complete onboarding or QuickLog because the form inputs have no identifiers; an agent that hits the paywall cannot dismiss it because Close/Restore are unidentified.

This violates the platform principle "any action a user can take, an agent can also take" (CLAUDE.md).

## Findings

**Onboarding baseline screen** (`OnboardingView.swift:98-133`):
- `birthDate` has an id ✅
- `biologicalSex`, `smokingStatus`, `alcoholFrequency`, `dietQualityBaseline` Pickers — no ids ❌
- `sleepGoalHours` Slider — no id ❌

**QuickLog sheet** (`QuickLogSheet.swift:23,35,48,~60`):
- save/cancel — tagged ✅
- `alcoholLevel`, `dietQuality`, `stressLevel` Pickers — no ids ❌
- strength Stepper — no id ❌

**PaywallSheet** (`PaywallSheet.swift:33,36,80,116`):
- Close, Restore, plan-option, Subscribe — no ids ❌
- Subscribe must remain agent-blocked per prohibited-actions, but Close + Restore must be agent-driveable so a paywall presentation isn't an agent dead-end.

**Today secondary surfaces** (P3):
- Per-driver row identifiers — none (`TodayView.swift:~150`)
- Diet streak chip — none (`TodayView.swift:177`)

## Proposed Solutions

### Option 1 (recommended): Add identifiers in one focused commit

Tag every interactive control with a stable identifier following the existing scheme (`<screen>.<control>` or `<screen>.<control>.<index>`). Update `LifeClockUITests` to assert form-fill works through the new ids.

Pros: tightly scoped, low-risk; closes parity gap; XCUITest gets actual coverage of onboarding form.
Cons: ~10 small changes across 3 files.
Effort: Small.
Risk: Low.

### Option 2: Auto-derive identifiers from control labels

SwiftUI defaults work in many cases — verify which controls expose default identifiers via the accessibility tree before adding manual ids.

Pros: less manual code.
Cons: brittle (label changes break tests); not all SwiftUI controls expose stable defaults.
Effort: Small (probe + decide).
Risk: Medium.

## Recommended Action

(leave blank for triage)

## Technical Details

Affected files:
- `products/life-clock-ios/Sources/Features/Onboarding/OnboardingView.swift`
- `products/life-clock-ios/Sources/Features/QuickLog/QuickLogSheet.swift`
- `products/life-clock-ios/Sources/Features/Paywall/PaywallSheet.swift`
- `products/life-clock-ios/Sources/Features/Today/TodayView.swift` (P3 follow-up)
- `products/life-clock-ios/UITests/LifeClockUITests.swift` (extend coverage)

## Acceptance Criteria

- [ ] All onboarding form controls have stable identifiers.
- [ ] All QuickLog form controls have stable identifiers.
- [ ] PaywallSheet Close + Restore have identifiers (Subscribe intentionally not driven by tests).
- [ ] A new XCUITest fills onboarding end-to-end and verifies Today reflects the choices.

## Work Log

(to be filled in)

## Resources

- Agent-native parity review (this audit), 2026-04-30
- CLAUDE.md — agent-native principle
