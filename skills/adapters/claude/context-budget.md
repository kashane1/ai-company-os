---
description: Count approximate tokens across every adapter file, canonical body, and project-skill pointer and report per-lane totals. v1 reports numbers, not verdicts — no thresholds, no gating. Invoke for "check the context budget", "how bloated are the skill lanes", "which lane is trending toward prompt bloat".
canonical_source: skills/canonical/context-budget/skill.md
---

# Context Budget (Claude adapter)

You are running the `context-budget` skill from
`skills/canonical/context-budget/skill.md`. Follow the canonical
definition.

## Quick reference

Validator-kind, deterministic, safe to call from synchronous paths.
Invoke via:

```python
from packages.tools.primitives import context_budget_reader
report = context_budget_reader.read()
```

or via the skill-loader path:

```python
from packages.tools.skills.loader import load_validator
budget = load_validator("context-budget")
result = budget.run({})
```

## v1 is report-only

No thresholds. No `over_threshold_lanes`. No gating. The first
landing captures numbers; a later PR sets caps when an incident
motivates a specific threshold (OpenTelemetry GenAI "attribute
don't aggregate").

The report contains:
- `lanes`: per-lane `{total_tokens, skill_count}`, sorted descending.
- `top_largest`: the N largest skills by total tokens.
- `system_prompt`: CLAUDE.md + project-skill pointers (MCP blocks
  deferred to v2 with a TODO note).
- `tokenizer`: `"tiktoken:o200k_base"` when available, otherwise
  `"char_count_fallback"`.
- `notes`: measurement caveats.

## Edit boundaries

Read-only. No writes to source. Baseline JSON is written via the
`_state_writer` primitive to `state/health/skill-estate/` — still
outside any source folder.
