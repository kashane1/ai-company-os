---
status: completed
priority: p1
issue_id: "005"
tags: [code-review, agent-native, primitives, ecc-gap-plan]
dependencies: []
---

# Problem Statement

The ECC gap plan's Phase 2a says "drift surfaced by stocktake is captured as a follow-up issue rather than blocking the skill's ship", but **captured** is undefined. Today that means a human files a GitHub issue. There is no agent-callable sink for drift items, which means drift detected by `skill-stocktake` has no way to become action without an operator in the loop. This is the one agent-native parity gap the deepening pass did not close.

## Findings

- Plan [lines 405, 435, 543](/Users/simons/ai-company-os/docs/plans/2026-04-15-feat-ecc-gap-recommendations-plan.md) reference "follow-up issue" as the drift disposition but name no writer.
- Agent-native reviewer second pass: "6 of 7 closed, 1 still open. Blocking fix before Phase 2a ships: add `followup_issue_writer.py` to Phase 2a scope so drift detection has an agent-callable sink."
- Spec-flow-analyzer flow-gap #8: operator-in-the-loop path is undefined; the plan does not say who writes the issues.
- The Hermes plan's `dispatch_health_reader.py` is the precedent for agent-callable reader primitives; this is the same pattern inverted (writer).

## Proposed Solutions

### Option 1: `packages/tools/primitives/followup_issue_writer.py` writing structured YAML to `state/followups/`

Agent-callable typed writer that emits structured YAML files under `state/followups/<yyyy-mm-dd>-<slug>.yaml`. Schema: `{id, source, severity, title, body, affected_files, captured_at}`. Operator-readable, agent-readable, and can be post-processed into GitHub issues by a separate workflow later.

Pros:
- Fully local, no GitHub API dependency
- Agent-native by construction (typed function, no CLI invocation)
- Can be composed into a future `github_issue_writer.py` that uploads YAML → gh issue
- Keeps the drift-capture surface inside `state/` per the platform invariant

Cons:
- Operators still need to turn YAML into issues manually for now
- Adds a new `state/followups/` directory that needs glossary entry

Effort: small
Risk: low

### Option 2: Leave drift capture as operator-manual and document it

Add plan text stating "follow-up issue authoring is operator-manual; agent-authored issues are out of scope". Close the gap by making it explicitly human-only.

Pros:
- Zero new code
- Matches the Hermes Phase 3 "trigger-phrase edits are human-only" precedent

Cons:
- Agent-native parity gap stays open for the Phase 2a + Phase 4 drift-capture flows
- The moment an evolution worker or verification loop wants to capture drift, we're back here

Effort: trivial
Risk: medium (defers a real gap)

## Recommended Action

Option 1. Ship as a Phase 2a deliverable alongside `registry_drift.py`. Add `state/followups/` to the Phase 0 `state/README.md` glossary.

## Acceptance Criteria

- [ ] `packages/tools/primitives/followup_issue_writer.py` exists with a typed `write(entry: FollowupEntry) -> Path` function
- [ ] `FollowupEntry` is a frozen dataclass with fields `id, source, severity, title, body, affected_files, captured_at`
- [ ] Writes to `state/followups/<yyyy-mm-dd>-<slug>.yaml` atomically via the `registry_writer` helper
- [ ] `skill-stocktake` calls it on each drift item when invoked with `capture_followups=True`
- [ ] `state/README.md` glossary lists `state/followups/` with owner = agent+operator
- [ ] Unit test: writes a synthetic drift item, asserts file exists and parses back to an equivalent dataclass

## Work Log

### 2026-04-15 - Captured during technical review
**By:** Claude (review workflow)
**Actions:** Agent-native reviewer flagged this as the single unresolved parity gap from the deepening pass.
