---
description: Emit a structured preflight report for a fresh agent session — git state, edit boundaries, read-first docs, product-app scope — so the first action is informed. Invoke for "preflight", "agent preflight", "what can I touch", "orient me before I start".
canonical_source: skills/canonical/agent-preflight/skill.md
---

# Agent Preflight (Claude adapter)

You are running the `agent-preflight` skill from
`skills/canonical/agent-preflight/skill.md`. Follow the canonical
definition.

## Quick reference

1. **Capture git state.** `git rev-parse --abbrev-ref HEAD` and
   `git status --porcelain` (paths only). Set `branch`, `dirty`, and
   `dirty_files`.

2. **Check read-first presence.** Verify these four files exist:
   - `REPO_MAP.md`
   - `docs/preflight-for-agents.md`
   - `CLAUDE.md`
   - `docs/skills-index.md`
   Any missing file → add a warning naming it.

3. **Derive boundaries verbatim** from `docs/preflight-for-agents.md`:
   - Default-safe areas
   - Explicit-approval areas
   - Forbidden areas
   Do not paraphrase. Copy.

4. **Classify product scope.** Read `infra/products.json` for product
   ids. Set `product_in_scope` only when `task_scope` clearly names a
   product implementation task. Borderline → false.

5. **Trigger surface (optional).** If `include_skills_index` is true,
   include the trigger-phrase list from `docs/skills-index.md` so the
   agent knows what's routable.

6. **Write the report** to
   `state/artifacts/agent-preflight/<session-slug>/preflight.md`.
   `<session-slug>` = current branch with `/` → `-` plus a UTC
   timestamp. Size ≤ 4 KB.

## Disambiguation

- Area-specific architecture brief → `repo-onboarding`.
- Doc-drift scan → `stale-doc-detector`.
- Session end → `handoff-write`.
- Open-ended search → `Explore` agent.

If two trigger phrases could match, ask the operator. Do not guess.

## Edit boundaries

Read-only outside `state/artifacts/agent-preflight/`. Never write to
`packages/`, `apps/`, `products/`, `docs/`, `skills/`, or `.claude/`.
Never open files under `products/*`.
