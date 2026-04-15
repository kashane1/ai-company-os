---
description: Before implementing a custom solution, look for existing code or patterns. Produces a structured search summary with a reuse | extend | custom recommendation. Invoke for "search first", "find existing solution", "is there already a way to do this", "look before you build".
canonical_source: skills/canonical/search-first/skill.md
---

# Search First (Claude adapter)

You are running the `search-first` skill from
`skills/canonical/search-first/skill.md`. Follow the canonical
definition.

## Quick reference

1. **Validate scope first.** If the caller did not give a
   `scope_hint`, stop and raise `INSUFFICIENT_SCOPE` — an unbounded
   search is not this skill's job.

2. **Search local sources in this order:**
   - `docs/solutions/`
   - `skills/canonical/`
   - `packages/tools/primitives/`
   - `packages/tools/`
   - `packages/policies/`
   - `packages/schemas/`

3. **Check task history.** `git log --grep` + `state/checkpoints/`.

4. **Check the `docs/` tree** for plans, ADRs, gap analyses that may
   already have decided this capability is in-scope or deferred.

5. **Web fallback only on local miss.** Use the `learnings-researcher`
   agent. Max 3 queries. Do not loop.

6. **Write the summary** to
   `state/artifacts/search-first/<task-id>/summary.md`. Include every
   candidate considered, each with source/relevance/excerpt.

7. **Return the structured output.** The caller — not this skill —
   decides whether to follow your `reuse | extend | custom`
   recommendation.

## Disambiguation

If the user's phrasing could apply to another skill, ask which skill
to invoke before proceeding. `documentation-lookup` handles external
library docs. `repo-onboarding` produces a bounded area brief. The
`Explore` agent handles open-ended search. `search-first` is
specifically "does this already exist before I build it".

## Edit boundaries

Read-only outside `state/artifacts/search-first/`. Never write to
`packages/`, `apps/`, `products/`, or `docs/`.
