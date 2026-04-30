---
id: ios-simulator-ux-audit
name: iOS Simulator UX Audit
purpose: Run a repeatable simulator-driven audit of an iOS app, capture UX findings with evidence, and leave behind reusable artifacts and test hooks.
owner_agent: ios
target_runtimes: [claude, codex]
stage: draft
inputs:
  - product path and Xcode scheme
  - target simulator device
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
dependencies:
  - docs/ux-audit-playbook.md
validation_steps:
  - app builds for the chosen simulator target
  - at least one first-launch and one returning-user flow is exercised
  - findings are captured in a dated product doc
  - any logic-bearing changes add or update iOS tests
handoff_contract:
  what_is_handed_off: audit findings, implemented improvements, and repeatable test/audit artifacts
  handed_to: supervisor or iOS worker for prioritization and release planning
---

# iOS Simulator UX Audit

Use this skill when a product needs a real simulator-based UX review instead of a code-only opinion.

## Procedure

1. Read the product docs and map the main screens, persistence layer, onboarding flow, and reward logic before editing.
2. Build and run the app in Simulator.
3. Traverse the app from onboarding through at least one daily-action loop.
4. Record evidence for friction, confusion, weak reinforcement, dead ends, naming issues, and accessibility gaps.
5. Prefer accessibility-driven inspection and stable launch states over brittle screenshot-only guessing.
6. Translate findings into:
   - flow improvements
   - copy changes
   - reward or reinforcement changes
   - accessibility identifiers
   - XCUITest coverage
7. Update `docs/ux-audit-playbook.md` or add a product-specific audit note if the audit uncovered a new reusable pattern.

## Minimum Checklist

- launch succeeds in Simulator
- onboarding completed
- major tabs visited
- primary action completed
- reinforcement observed
- relaunch performed
- no-data or permission edge state checked
- tests updated for the changed flow

## Evidence Standard

Every major finding should tie back to one of:

- simulator observation
- accessibility tree behavior
- source-code path
- automated test result

## Output Style

Keep findings concise, ranked by product impact, and biased toward fixes that improve clarity, motivation, and long-term maintainability.
