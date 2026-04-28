---
title: "Skill-estate adapter/canonical mirroring and batch TODO resolution"
category: architecture
tags: [skills, skill-estate, adapters, canonical, todos, lfg, workflow, compounding]
module: skills
symptom: "Adapter file ends up duplicating ~50% of the canonical skill body; or, /resolve_todo_parallel spawns N agents that fight over the same files."
root_cause: "Two distinct workflow patterns surfaced during the same LFG run on PR #15 (app-name-discovery skill). Both have the same shape: ceremony / mechanical parallelism applied where consolidation would be simpler and safer."
discovered: 2026-04-28
discovered_in: "PR #15 — feat(skills): app-name-discovery"
related_skills: [app-name-discovery, gtm-artifact-refresh, niche-research-brief, app-store-positioning-pack]
---

# Skill-estate adapter/canonical mirroring and batch TODO resolution

Two patterns worth compounding, both surfaced during the LFG run on PR #15
(`app-name-discovery` skill estate addition). Different problems, same shape:
mechanical / parallel approach applied where consolidation is simpler.

## Pattern 1 — Adapter/canonical 50/50 mirror

### Symptom

A new Claude adapter at `skills/adapters/claude/<skill>.md` ends up
restating the canonical body's rubric tables, gate definitions, scoring
formulas, and validation checklists. The adapter even opens with a line like
"This adapter mirrors that body" and then mirrors it. Two surfaces to keep
in sync; bug-fixes become two-PR jobs by accident.

### Root cause

When authoring a new skill it is tempting to copy the canonical content into
the adapter "for completeness." The WIRING.md contract says the canonical is
the source of truth and the adapter translates for Claude, but "translates"
gets misread as "restates." The result is duplication that drifts.

### Working solution

The adapter should be a quick-reference + step-pointer that defers to
canonical phase numbers. Target shape:

```markdown
---
description: <one-paragraph; same as project-skill description>
canonical_source: skills/canonical/<skill>/skill.md
---

# <Skill Name>

Run the canonical skill at `skills/canonical/<skill>/skill.md`. The canonical
body owns the rubric, weights, gates, and validation list. Read it first.

## Quick reference
- Prerequisite: <input contract>
- Output: <output path>
- Boundaries: <may edit / read-only / forbidden>

## Steps (defer to canonical for details)
1. <step name> — canonical Phase 0.
2. <step name> — canonical Phase 1.
...

## Boundaries
- May edit: ...
- Must not touch: ...
- Read-only: ...
```

`skills/adapters/claude/gtm-artifact-refresh.md` is the reference
implementation. After the fix on PR #15, the `app-name-discovery` adapter
shrank from ~140 body lines to ~50.

### Prevention

- When reviewing a new skill PR, check the adapter line count. If it has its
  own copy of the rubric/gates/scoring formulas, that is a smell.
- The contract-freeze fixture asserts on the canonical body, not the adapter
  — so duplication is invisible to CI. Manual review is the only signal.
- Quick check: `wc -l skills/adapters/claude/<new-skill>.md` should typically
  be < 80 lines unless there's a Claude-specific reason otherwise.

## Pattern 2 — Batch TODO resolution beats parallel agents on shared files

### Symptom

`/resolve_todo_parallel` (or any "spawn N agents in parallel" workflow) is
invoked on a list of todos that all touch the same 3–5 files. The agents
race, produce conflicting edits, and either clobber each other or stall
waiting on file-locks.

### Root cause

The skill description ("spawn one agent per todo, all in parallel") is
optimized for the case where todos touch independent surfaces. When todos
all touch the same files (typical of a single-skill review pass: trim
validation, drop a field, simplify adapter), parallelism is theatre — there
is no concurrency to exploit, just merge conflicts to manage.

### Working solution

When all todos cluster on the same file set, resolve them inline in one
consolidated edit pass. Cluster signal:

- Same module / package / skill in every todo.
- Same handful of file paths in `Affected files` across todos.
- Todos describe related simplifications / refactors of one component.

Inline resolution is faster (no agent overhead, no merge step), safer (no
race conditions), and the commit stays semantically coherent
(one "resolve review findings" commit instead of N).

### When parallelism still helps

- Todos touch **different** modules / unrelated files (security finding in
  one service, perf finding in another).
- Each todo is self-contained and large (a 200-line refactor per agent is
  worth the orchestration cost).
- Heuristic: if you can't write one commit message that covers all of them,
  parallelism is fine. If you can ("refactor: resolve review findings on X"),
  inline.

### Prevention

- Before invoking `/resolve_todo_parallel`, scan the todos' `Affected files`
  sections. If they overlap on >50% of files, do it inline instead.
- Document the inline-resolve pattern in the workflow's own README so the
  next operator doesn't default to parallel-on-shared-files.

## Related

- WIRING contract: `skills/WIRING.md`.
- Reference adapter: `skills/adapters/claude/gtm-artifact-refresh.md`.
- PR where both patterns surfaced: https://github.com/kashane1/ai-company-os/pull/15.
- Past adjacent learning: `docs/solutions/architecture/multi-phase-plan-shipping-primitives-skills.md` (atomic-commit hygiene for shared-file PRs).
