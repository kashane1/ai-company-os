---
id: search-first
name: Search First
purpose: Before implementing a custom solution, look for existing code, solutions, or patterns that already solve the task. Produce a structured search summary with a reuse | extend | custom recommendation.
owner_agent: any
target_runtimes: [claude]
stage: active
kind: agentic
allowed_edit_boundaries:
  - state/artifacts/search-first/
forbidden_areas:
  - packages/
  - apps/
  - products/
  - docs/
---

# Skill: search-first

Kind: agentic
Owner: any
Runtimes: claude

## Purpose

Before writing a custom solution for a task, **look first.** The repo
has `docs/solutions/`, existing primitives under `packages/tools/`,
canonical skills under `skills/`, and a running history of learnings.
A ten-minute search for prior art is cheaper than a one-hour rewrite
of something that already exists.

This skill produces a **search summary** and a recommendation:
`reuse`, `extend`, or `custom`. It is the discipline that turns
"what does this codebase already have?" from an ad-hoc question into
a structured procedure.

## When to invoke

Invoke this skill at the very start of any task that would add new
code, a new primitive, a new helper, or a new workflow, when you
don't already know that the repo lacks the capability. Trigger
phrases in CLAUDE.md route here: "search first", "find existing
solution", "is there already a way to do this", "look before you
build".

Do NOT invoke this skill for:
- Debugging existing code (use the debugging / explore-agent path).
- Open-ended exploratory research (use the `Explore` agent).
- Documentation lookups for external libraries (use
  `documentation-lookup` instead).

If two trigger phrases could match, ask the operator which skill to invoke.
Do not guess — see the CLAUDE.md disambiguation rule.

## Contract

Inputs:

- `task_description`: str — what the caller is about to build.
- `scope_hint`: str — the subtree(s) or lane(s) most relevant to the
  task. Examples: `packages/tools/primitives/`, `gtm content
  pipeline`, `skills/canonical/`. MUST be specific enough to narrow
  the search. A missing or empty `scope_hint` raises
  `INSUFFICIENT_SCOPE`.

Outputs:

- `search_summary_path`: str — path under
  `state/artifacts/search-first/<task-id>/summary.md` containing the
  written summary (what was searched, where, what was found).
- `candidates`: list of `{source, relevance, excerpt}` — at most 10,
  ordered by relevance. `source` is a repo-relative path or URL.
- `recommendation`: `"reuse" | "extend" | "custom"`.
  - `reuse`: an existing artifact solves the task as-is.
  - `extend`: an existing artifact is the right base; the task is
    to add to it rather than build from scratch.
  - `custom`: no suitable prior art found after a structured sweep.

## Procedure

1. **Validate scope.** If `scope_hint` is missing or empty, raise
   `PolicyViolation(PolicyViolationCode.INSUFFICIENT_SCOPE)`. Do not
   proceed without a scope — an unbounded search is not this skill's
   job.

2. **Search the local repo in this order.** Stop as soon as a
   high-confidence match appears, but always check at least the first
   three sources before concluding `custom`:
   1. `docs/solutions/` — past solved problems, often directly
      relevant.
   2. `skills/canonical/` — existing canonical skills that might
      already implement the task.
   3. `packages/tools/primitives/` — stateless, typed helpers.
   4. `packages/tools/` — other tools.
   5. `packages/policies/` — policy wrappers that may compose the
      needed check.
   6. `packages/schemas/` — typed payloads that may already describe
      the data shape.

3. **Search existing task history.** Walk `state/checkpoints/` and
   recent commit messages for tasks that look similar. A 30-second
   `git log --grep` pass is sufficient; skip if no obvious keyword.

4. **Check the `docs/` tree.** Plans, ADRs, and gap analyses are
   strong signals that a capability was considered and either built
   or deferred. If a `deferred` decision exists, surface it — the
   caller may be about to re-open a deliberate non-goal.

5. **Fall through to web search** only when local sources return
   nothing. Use the `learnings-researcher` agent. Cap at 3 queries;
   do not loop.

6. **Write the search summary** to
   `state/artifacts/search-first/<task-id>/summary.md`. Include:
   - The `task_description` and `scope_hint`.
   - Every candidate considered, with its source, relevance, and a
     brief excerpt (≤ 80 chars).
   - The recommendation and the one-sentence reason.

7. **Return the structured output** to the caller. The caller (not
   this skill) decides whether to follow the recommendation.

## Examples

### Example — reuse

```
task_description: "Add a helper that counts tokens per skill lane"
scope_hint: "packages/tools/primitives/"
→ candidates: [
    {source: "packages/tools/primitives/context_budget.py",
     relevance: "exact match — counts tokens by lane",
     excerpt: "def count_tokens_by_lane(registry): ..."}
  ]
→ recommendation: "reuse"
```

### Example — extend

```
task_description: "Add a third redaction rule to the task-run
  redactor"
scope_hint: "packages/tools/primitives/_redact.py"
→ candidates: [
    {source: "packages/tools/primitives/_redact.py",
     relevance: "existing redactor; needs a new rule",
     excerpt: "REDACT_PATTERNS = [...]"}
  ]
→ recommendation: "extend"
```

### Example — custom

```
task_description: "Generate a social post in a new voice style"
scope_hint: "skills/canonical/content-voice-guardrail/"
→ candidates: []  # checked docs/solutions, canonical skills, primitives
→ recommendation: "custom"
```

## Boundaries and failure modes

- **Read-only outside `state/artifacts/search-first/`.** This skill
  MUST NOT edit `packages/`, `apps/`, `products/`, or `docs/`.
- **Scope is load-bearing.** A missing `scope_hint` raises
  `INSUFFICIENT_SCOPE`. An empty `candidates` list when
  `recommendation == "reuse"` is a contract violation; the test
  catches it.
- **Recommendation is advice, not a command.** The caller decides
  whether to follow it. The skill does not dispatch tasks or edit
  code.
- **No LLM round-trip for the fixture tests.** Structural tests
  freeze the procedure, not the verdict. Verdict correctness is the
  operator's judgment on each invocation.

## References

- Gap analysis: `docs/2026-04-14-everything-claude-code-gap-analysis.md` §1.
- Plan: `docs/plans/2026-04-15-feat-ecc-gap-recommendations-plan.md` Phase 1a.
- Sibling skills: `documentation-lookup`, `repo-onboarding`.
- Related: `Explore` agent (open-ended search, not structured).
