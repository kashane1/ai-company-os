# UX Audit Playbook

Use this playbook when auditing a product in Simulator or a local runtime.

## Goal

Produce a repeatable, evidence-based UX audit that connects product behavior,
copy, feedback loops, and accessibility to concrete code and test changes.

## Setup

1. Build the app with a deterministic simulator target.
2. Prefer seeded or fixture-backed launch states when possible.
3. Turn on any launch arguments or mock services needed to reach major states.
4. Record the exact device, OS version, scheme, and launch configuration used.

## Traversal

1. Start from first launch and finish onboarding.
2. Visit each top-level section in order.
3. Trigger at least one core action per section.
4. Revisit the home screen after each action to inspect feedback loops.
5. Relaunch once to verify persistence and recovery.

## What To Inspect

### Information architecture

- Can a new user explain the major sections after one pass?
- Do labels match the mental model the product wants to teach?
- Are there dead ends, duplicate destinations, or hidden controls?

### Motivation loop

- Is the user told what to do next?
- Does a positive action cause visible, believable feedback?
- Are rewards immediate when they should be, and cumulative when they should be?
- Does the product reinforce healthy behavior without feeling manipulative?

### Copy and tone

- Remove misleading metaphors, novelty framing, or jargon.
- Check whether naming is consistent across onboarding, home, settings, and paywalls.
- Flag any copy that teaches the wrong product category.

### Onboarding

- Is trust built before sensitive asks?
- Does each step earn its place?
- Are permissions explained honestly?
- Can the user tell what happens after onboarding finishes?

### Edge states

- Empty states
- Permission-denied states
- No-data states
- Undo and recovery paths
- Relaunch persistence

### Accessibility and discoverability

- Are primary controls exposed through accessibility reliably?
- Can important actions be found without guessing?
- Are automation hooks stable enough for XCUITest?

## Evidence Template

For each finding, capture:

- screen or flow
- exact observed behavior
- why it creates friction or weakens motivation
- evidence source: simulator, accessibility tree, code path, or test
- recommended change now
- recommended change later if the full fix is larger

## Output Artifacts

- current flow map
- prioritized findings list
- implementation plan
- updated launch/test harness
- updated UI or interaction copy
- new or updated UI tests

## Next-Iteration Rubric

Score each category `1-5` after changes:

- clarity of mental model
- onboarding trust and comprehension
- ease of primary daily action
- quality of reinforcement after a positive action
- visibility of cumulative progress
- accessibility and automation readiness
- consistency of product language
