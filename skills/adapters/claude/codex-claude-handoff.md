---
description: Transfer work between Codex and Claude with explicit context, boundaries, and next actions. Use when picking up work that Codex started, or when preparing work for Codex to implement.
canonical_source: skills/canonical/handoffs/codex-claude-handoff.md
---

# Codex-Claude Handoff

You are running the codex-claude-handoff skill from `skills/canonical/handoffs/codex-claude-handoff.md`. Follow the canonical definition.

## When receiving work FROM Codex

1. Read the handoff document at `state/artifacts/handoffs/<task-id>-codex-to-claude.md`
2. Verify all referenced artifact paths exist (diff, logs, task run)
3. Understand what Codex completed and what remains
4. Proceed with the remaining work specified in the handoff

## When handing work TO Codex

1. Prepare explicit scope: target repo, files, constraints, acceptance criteria
2. Create or update the task record in platform state
3. Use the `bounded-codex-implementation` skill pattern to render the task packet
4. The task packet IS the handoff — do not create a separate document

## Handoff validation rules

Before completing any handoff:

- Every referenced file path must exist
- Every next action must reference a concrete skill, file, or command
- "Finish the feature" is not an acceptable instruction
- If remaining work cannot be fully specified, create explicit open questions

## Boundaries

- **May edit**: `state/artifacts/`, `state/checkpoints/platform/tasks/`
- **Must not touch**: `packages/policies/`, `infra/`
