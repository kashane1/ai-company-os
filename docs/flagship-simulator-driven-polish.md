# Case study: Life Clock simulator polish

This is a guided review of a product-development workflow: define the intended
experience, use deterministic simulator state, review screenshots, and iterate.
It combines Swift implementation, an agent skill, and recorded session notes.
Those are different kinds of evidence; this page identifies each.

## 1. Product intent

[Life Clock](../products/life-clock-ios/README.md) is a managed iOS health-app
source tree. Its [vision](products/life-clock/vision.md) records product
constraints, and its [reference-app notes](products/life-clock/reference-apps.md)
describe what to learn from other apps and which framing to avoid.

Review question: can a developer tell which decisions are settled and which
are open without inventing product requirements?

## 2. Reproducible simulator state

[LifeClockLaunchConfiguration.swift](../products/life-clock-ios/Sources/App/LifeClockLaunchConfiguration.swift)
parses debug fixture controls such as `LIFECLOCK_JUMP_TO`,
`LIFECLOCK_HEALTH_PROFILE`, and `LIFECLOCK_SEED_BAD_DAY`. The `#if DEBUG` branch
and Release defaults are visible in code. The supported presets cover specific
states; they do not guarantee access to every possible UI state.

Compare this with the
[launch-configuration tests](../products/life-clock-ios/Tests/LifeClockLaunchConfigurationTests.swift).
For Life Clock build instructions, use its README. The top-level
[`scripts/test_ios.sh`](../scripts/test_ios.sh) targets **Catchbook**, so a green
result from that command does not validate Life Clock.

## 3. Agent-guided polish

The [simulator polish skill](../skills/canonical/simulator-driven-polish/skill.md)
and [operator guide](skills/simulator-driven-polish-guide.md) specify screenshot
review, iteration limits, and decision tiers. They distinguish small polish
changes from feature or vision questions that need operator input.

These are instructions for an agent/operator workflow, not an independently
enforced image-regression service. In particular, golden-image comparison and
stop conditions in the skill should be evaluated as procedures unless a run's
evidence demonstrates that they were followed.

Two recorded sessions to inspect:

- [May 5 polish session](products/life-clock/polish-2026-05-05.md)
- [Accessibility and color-matrix pass](products/life-clock/polish-2026-05-06-accessibility-color-matrix.md)

The notes document development activity. They are not proof of a public release,
user outcomes, or comprehensive visual regression coverage. Some referenced
screenshots or local simulator artifacts may require the operator's environment.

## 4. Release handoff: current boundary

The [App Store worker](../apps/worker-appstore/main.py) prepares local release
state. It does not call App Store Connect; its result tells the operator to keep
external submission manual. The [release-readiness policy](../packages/policies/release_readiness.py)
contains checklist/approval checks, but that policy is not currently called by
this worker. The [App Store lane document](appstore-lane.md) describes the fuller
intended workflow.

This distinction matters when assessing the architecture: separate delivery
responsibilities and local approval checks exist, while an enforced, end-to-end
store submission integration remains unfinished.

## What to discuss

The useful engineering thread is the connection between product constraints,
repeatable development state, explicit agent instructions, and reviewable
session evidence. Start with one fixture and one session rather than reading
the entire product-document history.
