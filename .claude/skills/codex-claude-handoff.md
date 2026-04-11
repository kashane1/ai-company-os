---
description: Dispatch bounded code-change tasks from Claude to Codex via the ai-company-os engineering lane. Use when the user says "hand this to codex", "dispatch to codex", "delegate to codex", "queue a task for codex", "find a few tasks for codex", "have codex fix/add/implement X", or any phrasing that asks Claude to route implementation work through the Codex subprocess pipeline. Covers the full loop: select task, pre-flight checks, enqueue via control plane, monitor the run, review the diff, apply to source, update the backlog.
canonical_source: skills/canonical/handoffs/codex-claude-handoff.md
adapter_source: skills/adapters/claude/codex-claude-handoff.md
---

<!-- This is a Claude Code project skill. It routes to the canonical skill via its adapter. -->
<!-- Do not add skill logic here. Edit the adapter or canonical source instead. -->

Read and follow the skill instructions at `skills/adapters/claude/codex-claude-handoff.md`.

That adapter implements `skills/canonical/handoffs/codex-claude-handoff.md` — the canonical source of truth for this skill.
