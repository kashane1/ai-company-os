---
description: Run a structural audit of the skill registry, canonical files, project-skill pointers, and CLAUDE.md trigger phrases. Surfaces drift that reconcile_registry() does not catch. Invoke for "audit the skill estate", "run a skill stocktake", "check for orphan skills", "find drift in the skill registry".
canonical_source: skills/canonical/skill-stocktake/skill.md
---

# Skill Stocktake (Claude adapter)

You are running the `skill-stocktake` skill from
`skills/canonical/skill-stocktake/skill.md`. Follow the canonical
definition.

## Quick reference

This is a **validator-kind** skill: it is pure deterministic Python
and safe to call from synchronous paths. Invoke it via:

```python
from packages.tools.primitives import skill_stocktake_reader
report = skill_stocktake_reader.read()
```

or via the skill-loader path:

```python
from packages.tools.skills.loader import load_validator
stocktake = load_validator("skill-stocktake")
result = stocktake.run({})
```

Both paths return a `StocktakeReport` (typed frozen dataclass) or
its `asdict` serialization.

## Drift types (v1 set)

1. `orphan_canonical` — canonical file with no registry entry.
2. `dangling_project_skill` — registry points at `.claude/skills/<id>.md`
   that does not exist.
3. `trigger_phrase_drift` — CLAUDE.md trigger-phrase line points at
   an adapter that does not exist (docs/ targets are valid).

## What this skill is NOT

- Not the fixture reconciliation check (`reconcile_registry` lives
  at `packages/tools/skills/reconciliation.py` and is authoritative
  for `fixture_status: passing` skills).
- Not a fix-it tool. It reads, it reports, it does not write. Drift
  items surface as follow-ups; the operator decides which to fix.

## Edit boundaries

Read-only. No filesystem writes, no registry edits, no CLAUDE.md
edits. The (future) `followup_issue_writer` integration is the only
path to a write, and it writes to `state/followups/` — still outside
any source folder.
