---
id: agent-preflight
name: Agent Preflight
purpose: Produce a structured preflight report for a fresh agent session — git state, edit boundaries, read-first paths, product-app scope — so the agent does not start work on a stale or out-of-scope assumption.
owner_agent: supervisor
target_runtimes: [claude]
stage: active
kind: agentic
allowed_edit_boundaries:
  - state/artifacts/agent-preflight/
forbidden_areas:
  - packages/
  - apps/
  - products/
  - docs/
  - skills/canonical/
  - skills/adapters/
  - skills/registry.yaml
  - .claude/skills/
  - .claude/settings.json
  - .claude/hooks/
  - state/
---

# Skill: agent-preflight

Kind: agentic
Owner: supervisor
Runtimes: claude

## Purpose

A fresh agent — Claude, Codex, or a future runtime — should not start
work without a 60-second snapshot of the repo's current state and the
session's edit boundaries. This skill produces that snapshot in a
fixed, structured shape so the agent's first action is informed, not
improvised.

This is explicitly **not** open-ended exploration. The brief is
bounded. If the operator needs an area-specific architecture brief
instead, route to `repo-onboarding`. If the operator wants to know
what's stale across the docs, route to `stale-doc-detector`.

## When to invoke

Trigger phrases in `CLAUDE.md` / `docs/skills-index.md`: "preflight",
"agent preflight", "what can I touch", "what's the state of this
repo", "orient me before I start", "session preflight".

Do NOT invoke this skill for:

- Open-ended exploratory search (use the `Explore` agent).
- Area-specific architecture briefs (use `repo-onboarding`).
- Doc-drift detection (use `stale-doc-detector`).
- Writing a session handoff at session end (use `handoff-write`).

If two trigger phrases could match, ask the operator which skill to
invoke. Do not guess.

## Contract

Inputs:

- `task_scope`: str | None — the operator's one-line description of
  what this session is for. Recorded verbatim in the report; the
  skill does NOT interpret or expand it.
- `include_skills_index`: bool = true — when true, the report
  enumerates the trigger phrases visible in `docs/skills-index.md` so
  the agent knows what's routable.

Outputs (a single structured report):

- `branch`: str — current git branch, from `git rev-parse --abbrev-ref HEAD`.
- `dirty`: bool — true if `git status --porcelain` is non-empty.
- `dirty_files`: list[str] — `git status --short` entries (paths only).
- `read_first_present`: object — boolean presence flags for the four
  canonical entry docs:
  - `REPO_MAP.md`
  - `docs/preflight-for-agents.md`
  - `CLAUDE.md`
  - `docs/skills-index.md`
- `default_safe_areas`: list[str] — paths the session may edit
  without per-edit approval (derived verbatim from
  `docs/preflight-for-agents.md`).
- `explicit_approval_areas`: list[str] — paths requiring founder
  approval before edit (derived verbatim from
  `docs/preflight-for-agents.md`).
- `forbidden_areas`: list[str] — paths the session may never inspect
  or edit (`products/*`, `state/`, `.claude/skills/`,
  `.claude/commands/`, `.claude/hooks/`, `.claude/settings*.json`,
  `.local`, `.codex/`).
- `product_in_scope`: bool — true only if `task_scope` clearly names
  a product implementation task; false otherwise. Default false.
- `warnings`: list[str] — anything notable: dirty tree, missing
  read-first doc, branch that is not the expected working pattern,
  superseded `HANDOFF.md` referenced by the operator, etc.

Total report size ≤ 4 KB (enforced at write time).

## Procedure

1. **Capture git state.** `git rev-parse --abbrev-ref HEAD` for
   `branch`. `git status --porcelain` (paths only) for `dirty_files`
   and the `dirty` flag.

2. **Check read-first presence.** For each of the four canonical
   entry docs, set the boolean flag based on filesystem existence.
   If any flag is false, add a warning naming the missing doc.

3. **Derive boundaries.** Read `docs/preflight-for-agents.md` and
   extract the bulleted paths from the "Default-safe areas",
   "Explicit-approval areas", and "Forbidden areas" sections.
   Preserve verbatim — do not paraphrase or expand.

4. **Classify product scope.** If `task_scope` is None or empty, set
   `product_in_scope: false`. If it explicitly references one of the
   product ids in `infra/products.json` (`catchbook`, `after-plans`,
   `life-clock`) AND uses language like "implement", "fix", "build",
   "feature", set `product_in_scope: true`. Otherwise false.
   Borderline cases default to false; the operator can override.

5. **Skills index trigger surface.** If `include_skills_index` is
   true, extract the trigger-phrase list from `docs/skills-index.md`
   and include it inline in the report so the agent knows what's
   routable without re-reading the index.

6. **Write the report** to
   `state/artifacts/agent-preflight/<session-slug>/preflight.md`.
   `<session-slug>` is the current git branch with `/` replaced by
   `-`, plus a UTC timestamp. Assert total size ≤ 4 KB at write time.

7. **Return the structured output.** The caller decides what to do
   with it.

## Examples

### Example — clean tree, no task scope

```
input: {task_scope: null}
→ branch: "claude/competent-johnson-62eccc"
→ dirty: false
→ dirty_files: []
→ read_first_present: {REPO_MAP.md: true, ...all true}
→ default_safe_areas: [...]
→ explicit_approval_areas: [...]
→ forbidden_areas: [...]
→ product_in_scope: false
→ warnings: []
```

### Example — dirty tree, scoped to a product

```
input: {task_scope: "implement life-clock daily reminder UI"}
→ dirty: true
→ dirty_files: ["M apps/worker-ios/main.py", ...]
→ product_in_scope: true
→ warnings: ["Working tree is dirty — review uncommitted changes before starting"]
```

## Boundaries and failure modes

- **Read-only outside `state/artifacts/agent-preflight/`.** This
  skill MUST NOT edit `packages/`, `apps/`, `products/`, `docs/`,
  `skills/`, or `.claude/`.
- **No product source inspection.** Do not open Swift, Objective-C,
  `.pbxproj`, or any file under `products/`. The product registry
  in `infra/products.json` is the only product-related read.
- **No external calls.** Filesystem and `git` only. No web, no MCP.
- **Bounded output.** Total report ≤ 4 KB. Truncate the
  trigger-phrase listing if it would push the report over the cap.
- **Verbatim boundaries.** The default-safe / explicit-approval /
  forbidden lists are copied from `docs/preflight-for-agents.md`,
  not paraphrased. If that doc changes, the report changes.

## References

- Anti-drift batch 1: `REPO_MAP.md`, `docs/preflight-for-agents.md`,
  `docs/handoffs/INDEX.md`, `docs/plans/INDEX.md`.
- Sibling skills: `repo-onboarding` (area-specific), `handoff-write`
  (session end), `stale-doc-detector` (doc drift).
- Operating doc: `docs/agent-model.md`.
