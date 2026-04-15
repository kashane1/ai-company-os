---
description: Look up framework/library documentation via Context7 MCP with a 3-call-per-question budget, with fall-through to allowlisted WebFetch on miss. Invoke for "look up the docs", "pull the framework docs", "check the SDK reference", "what's the current API for".
canonical_source: skills/canonical/documentation-lookup/skill.md
---

# Documentation Lookup (Claude adapter)

You are running the `documentation-lookup` skill from
`skills/canonical/documentation-lookup/skill.md`. Follow the canonical
definition.

## Quick reference

1. **Validate `library_name`** against `^[a-zA-Z0-9._/@-]+$`. This is
   the primary defense against prompt injection. Raise
   `NOT_A_DOC_LOOKUP` on failure.

2. **Validate `specific_question`** — if it is a debugging ask ("why
   doesn't my query return results"), raise `NOT_A_DOC_LOOKUP`.

3. **Resolve the library id** via Context7 MCP
   `mcp__plugin_compound-engineering_context7__resolve-library-id`.
   **Pick the highest-benchmark-score result and proceed — do NOT
   loop on ambiguity.** Context7's 3-call-per-question budget is a
   hard cap.

4. **Query docs** via
   `mcp__plugin_compound-engineering_context7__query-docs` with the
   resolved id and the specific question. One call.

5. **Web fallback only on Context7 miss.** Allowlisted domains:
   `{docs.python.org, developer.apple.com, developer.mozilla.org,
   nodejs.org, react.dev}`, or a URL Context7's resolver step
   returned. Web fallback is always `confidence: "low"`.

6. **Write the excerpt** to
   `state/artifacts/documentation-lookup/<request-id>/excerpt.md`.
   Copyright: ≤ 15 words of direct quote per distinct passage.

## Context7 MCP is authoritative

This adapter composes the Context7 MCP tools exposed by the
`compound-engineering:context7` plugin. The MCP server instructions
in CLAUDE.md set the 3-call-per-question budget; this skill wraps
that budget with a fixed-shape procedure and a structured artifact.
If the Context7 MCP instruction block and this adapter ever drift,
the adapter is authoritative for this skill's invocations —
`skill-stocktake` will flag the drift.

## Disambiguation

If the user's phrasing could apply to `search-first` (for repo-local
code) or a debugging question, ask which skill to invoke before
proceeding.

## Edit boundaries

Read-only outside `state/artifacts/documentation-lookup/`. Never
write to `packages/`, `apps/`, `products/`, or `docs/`.
