---
status: pending
priority: p3
issue_id: "062"
tags: [code-review, agent-native, disambiguation, skills-index]
dependencies: []
---

# Problem Statement

`docs/skills-index.md`'s binding disambiguation rule says "ASK before routing" when prompts are ambiguous. An interactive agent in a chat loop can surface the four-way menu; a **non-interactive agent** (queue worker, scheduled job, codex-claude-handoff consumer) has no asking channel and is forced to either refuse or guess — the spec doesn't define which.

Also: `skills/canonical/shared/recon-scaffolding.md` is a hard pre-flight dependency for all three recon-family skills, but it isn't in `skills/registry.yaml`. Agents can only discover it by following a canonical-skill link, not via the registry.

## Findings

- **agent-native-reviewer (MINOR — disambiguation):** "A non-interactive agent has no asking channel and is forced to either refuse or guess — the spec doesn't define which. Add a 'non-interactive default' clause (e.g. 'if no operator channel, refuse with the four-option menu in the report')."

- **agent-native-reviewer (MINOR — shared-doc discoverability):** "`recon-scaffolding.md` is referenced as a hard pre-flight but isn't in the registry as a skill — agents can't discover it via the index, only by following a canonical link. Consider listing it under `kind: shared`."

## Proposed Solutions

### Option 1: Combined fix

**Disambiguation:** Add to the top-level disambiguation section in `docs/skills-index.md`:

> **Non-interactive default:** if no operator channel exists (queue worker, scheduled job, etc.), the skill MUST refuse the bare prompt and write a "disambiguation report" containing the four-option menu, the matching trigger phrases for each option, and a one-line guide for the operator to re-invoke with a qualified prompt.

**Shared-doc discoverability:** Add a new top-level section to `skills/registry.yaml` called `shared_docs:` listing the canonical-shared docs that aren't skills themselves but are referenced as dependencies:

```yaml
shared_docs:
  - id: recon-scaffolding
    name: Recon Scaffolding
    path: canonical/shared/recon-scaffolding.md
    referenced_by: [simulator-polish-recon, premium-feel-audit, pro-value-audit]
    kind: contract-spine
```

Pros: closes both gaps; makes the spine discoverable; defines non-interactive behavior
Cons: adds a new top-level concept to the registry
Effort: Small
Risk: Low

## Recommended Action

Option 1. Both gaps are real and trivial-to-fix. The `shared_docs:` registry block makes future shared-spine documents discoverable without inventing a new skill type.

## Technical Details

- Files affected:
  - `docs/skills-index.md` (add non-interactive default clause)
  - `skills/registry.yaml` (add `shared_docs:` block)
- `packages/tools/skills/loader.py` may need updating to recognize the new top-level block — verify whether ignoring it is safe (likely yes, since it's a separate dictionary key, not inside `skills:`).

## Acceptance Criteria

- [ ] `docs/skills-index.md` defines non-interactive default behavior for the disambiguation rule
- [ ] `skills/registry.yaml` has a `shared_docs:` block listing `recon-scaffolding.md`
- [ ] Reconciliation test (`test_skill_reconciliation.py`) still passes (the new top-level block must not break the loader)

## Work Log

(empty)
