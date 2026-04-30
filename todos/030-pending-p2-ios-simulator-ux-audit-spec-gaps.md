---
status: pending
priority: p2
issue_id: "030"
tags: [code-review, skills, spec, ios-simulator-ux-audit]
dependencies: []
---

# Problem Statement

The new `ios-simulator-ux-audit` skill is `stage: draft` and has multiple flow gaps that would block another operator (or another product) from running it without asking questions. Captured here for a single graduation pass before flipping `stage: active`.

## Findings (from spec-flow-analyzer)

1. **Path implies product-coupling.** Canonical lives under `skills/canonical/products/life-clock/` but the skill is generic. A second product (catchbook, after-plans) auditor will not know whether to fork, move, or symlink. Move to `skills/canonical/ios-simulator-ux-audit/` before activation.

2. **Preconditions unstated.** "Scheme builds successfully" is implied but not declared. Add: scheme exists in project, simulator runtime installed, code-sign valid for sim, Xcode CLI tools selected. Adapter's "If any are missing, ask" only covers the 4 inputs.

3. **No-onboarding / returning-user-only audits unhandled.** Procedure step 3 hardcodes "first launch → onboarding → tabs → loop." Products without onboarding fail the Minimum Checklist. Add a `mode: first-launch | returning-user | both` input. *(Partially addressed in adapter trim — add to canonical.)*

4. **Same-day collision behavior undefined.** Output `ux-audit-<YYYY-MM-DD>.md` collides on re-run. Adapter trim now says "append timestamped H2 section" — mirror that into canonical.

5. **Minimum Checklist unrealistic for greenfield.** "Tests updated for the changed flow" is mandatory but a brand-new app has no XCUITest target. Either gate the line or make bootstrapping the test target the audit's first deliverable.

6. **Handoff is aspirational.** `handed_to: supervisor or iOS worker` has no mechanism. Either name the channel (queue payload, file under `state/checkpoints/`) or downgrade to "audit doc is the handoff."

7. **Resume contract missing.** Mid-flow interruption has no checkpoint. State the policy explicitly.

8. **Output artifact mismatch.** Playbook lists 6 output artifacts; canonical `outputs:` lists 4 generic items; adapter output template names 4 H2 sections. Reconcile or mark optional.

## Proposed Solutions

### Option 1 (recommended): One graduation PR before flipping to active

Address all 8 gaps in one focused diff: move canonical path, add preconditions, add `mode` input, define collision policy, gate test-target requirement, name handoff channel, define resume contract, reconcile outputs. Then flip `stage: active` and add a contract-freeze fixture.

Pros: skill is genuinely reusable across products afterward; fixture-freezable.
Cons: defers activation until the cleanup lands.
Effort: Medium.
Risk: Low.

### Option 2: Activate as-is, document constraints

Keep the path under `products/life-clock/`, accept it's life-clock-specific, deprioritize reuse.

Pros: zero immediate work.
Cons: future ports will copy-paste; "draft" lingers.
Effort: None.
Risk: Medium (drift compounds).

## Recommended Action

(leave blank for triage)

## Technical Details

- Affected files: `skills/canonical/products/life-clock/ios-simulator-ux-audit.md` (move + edit), `skills/adapters/claude/ios-simulator-ux-audit.md` (edit), `skills/registry.yaml` (path field), `.claude/skills/ios-simulator-ux-audit.md` (canonical_source path), `CLAUDE.md` (no change if path moves correctly).

## Acceptance Criteria

- [ ] Canonical lives at a product-agnostic path.
- [ ] Preconditions, mode input, collision policy, resume contract are explicit in canonical.
- [ ] Output artifact list reconciled across canonical / adapter / playbook.
- [ ] Handoff channel is named or downgraded honestly.
- [ ] Contract-freeze fixture in place; `fixture_status: passing`; `stage: active`.

## Work Log

(to be filled in)

## Resources

- Spec-flow-analyzer review (this audit), 2026-04-30
- `skills/WIRING.md`
- `docs/adr/2026-04-14-canonical-skill-layout.md`
