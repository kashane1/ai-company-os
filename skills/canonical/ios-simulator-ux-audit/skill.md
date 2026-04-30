---
id: ios-simulator-ux-audit
name: iOS Simulator UX Audit
purpose: Run a repeatable simulator-driven audit of an iOS app, capture UX findings with evidence, and leave behind reusable artifacts and test hooks.
owner_agent: ios
target_runtimes: [claude]
stage: active
inputs:
  - product path under products/<product-id>-ios/
  - Xcode scheme name
  - target simulator device + iOS version
  - audit mode (first-launch | returning-user | both)
  - launch arguments or fixture scenarios if available
outputs:
  - simulator audit summary
  - prioritized UX findings
  - recommended flow and reward improvements
  - reusable audit docs and testability hooks
allowed_edit_boundaries:
  - docs/
  - products/
  - skills/
forbidden_areas:
  - packages/policies/
  - state/
preconditions:
  - the chosen Xcode scheme exists in the project (verify with xcodebuild -list)
  - the target Simulator runtime is installed (verify with xcrun simctl list devices available)
  - code-sign config is valid for the simulator destination
  - Xcode CLI tools are selected (xcode-select -p)
  - the app builds for the chosen simulator destination before the audit starts
dependencies:
  - docs/ux-audit-playbook.md
validation_steps:
  - app builds for the chosen simulator target
  - at least one first-launch and one returning-user flow is exercised (unless audit mode pins to one)
  - findings are captured in a dated product doc
  - any logic-bearing changes add or update iOS tests
handoff_contract:
  what_is_handed_off: the dated audit doc itself; recommendations for prioritization are inline
  handed_to: supervisor or iOS worker for prioritization and release planning
  channel: docs/products/<product-id>/ux-audit-<YYYY-MM-DD>.md (the audit doc IS the handoff; no queue/state mechanism)
---

# iOS Simulator UX Audit

Use this skill when a product needs a real simulator-based UX review instead of a code-only opinion.

## Procedure

1. Read the product docs and map the main screens, persistence layer, onboarding flow, and reward logic before editing.
2. Build and run the app in Simulator. Verify the build succeeds before traversing.
3. Traverse the app according to the chosen audit mode:
   - `first-launch`: fresh install → onboarding (if any) → at least one daily-action loop.
   - `returning-user`: seeded launch state → revisit primary flows → relaunch persistence check.
   - `both`: run first-launch then returning-user in sequence.
4. Record evidence for friction, confusion, weak reinforcement, dead ends, naming issues, and accessibility gaps.
5. Prefer accessibility-driven inspection and stable launch states over brittle screenshot-only guessing.
6. Translate findings into:
   - flow improvements
   - copy changes
   - reward or reinforcement changes
   - accessibility identifiers
   - XCUITest coverage
7. Update `docs/ux-audit-playbook.md` if the audit uncovered a new reusable pattern. Otherwise add a dated note under `docs/products/<product-id>/ux-audit-<YYYY-MM-DD>.md`.

## Minimum Checklist

The checklist adapts to the chosen audit mode and product state:

- [ ] launch succeeds in Simulator
- [ ] onboarding completed (N/A if the product has no onboarding — document why)
- [ ] every top-level tab visited
- [ ] at least one primary action completed
- [ ] reinforcement / feedback observed
- [ ] relaunch performed (persistence verified)
- [ ] one no-data or permission edge state checked
- [ ] tests updated for the changed flow (if a UITest target exists; if not, bootstrapping the target is the audit's first deliverable and must be flagged)

## Evidence Standard

Every major finding should tie back to one of:

- simulator observation
- accessibility tree behavior
- source-code path
- automated test result

Findings without evidence are out of scope.

## Output Style

Keep findings concise, ranked by product impact, and biased toward fixes that improve clarity, motivation, and long-term maintainability.

The audit doc must include four sections:

```
## Current Flow Map
## Biggest Friction Points
## Recommended Flow
## Audit Notes For Next Pass
```

## Output Collisions and Resume

If `docs/products/<product-id>/ux-audit-<YYYY-MM-DD>.md` already exists, append a timestamped H2 section to it (e.g. `## Audit run 14:32`) rather than creating a sibling file. Same-day re-audits accumulate, not branch.

If the audit is interrupted mid-flow (Simulator crash, operator handoff), restart from step 1 of the Procedure on the next attempt. Partial state is not persisted; treat each run as a single transaction so audit notes stay coherent.

## Failure modes

- Simulator won't boot → stop, report device/scheme/iOS version, ask the operator before retrying.
- Scheme not present in project → stop, list `xcodebuild -list` output, ask which scheme to use.
- First launch crashes before reaching the audit start state → fix the crash first; audit cannot continue.
- Onboarding blocked by permission state (Apple ID, iCloud, push) → use a launch fixture (mock Health, seeded profile) before continuing; if no fixture is available, stop and ask.
- Product has no XCUITest target → bootstrapping it is in scope; flag the cost in the audit doc before starting test work.
- Findings without evidence → drop them. Code-only opinions are out of scope.
