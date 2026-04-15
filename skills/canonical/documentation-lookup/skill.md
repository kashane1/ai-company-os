---
id: documentation-lookup
name: Documentation Lookup
purpose: Resolve a library/framework name to a Context7 library id, dispatch a docs query, fall back to an allowlisted WebFetch only on miss, and write a structured doc excerpt artifact.
owner_agent: any
target_runtimes: [claude]
stage: active
kind: agentic
allowed_edit_boundaries:
  - state/artifacts/documentation-lookup/
forbidden_areas:
  - packages/
  - apps/
  - products/
  - docs/
---

# Skill: documentation-lookup

Kind: agentic
Owner: any
Runtimes: claude

## Purpose

Looking up framework or library documentation is a frequent enough
operation that it deserves a disciplined procedure. The repo has
Context7 MCP wired up as the primary doc source, with a 3-call-per-question
budget. This skill wraps that MCP tool with (a) input validation to
prevent prompt injection via library names, (b) a strict 1-shot
`resolve-library-id` + 1-shot `query-docs` pattern that never loops,
(c) a fallback to allowlisted WebFetch only on Context7 miss, and
(d) a structured artifact write.

This is **not** a business-logic debugger. Questions like "why is my
query returning NULL" route elsewhere. This skill only answers
"what is the current API for `foo.bar()` in library X".

## When to invoke

Invoke when the user's message matches one of the CLAUDE.md trigger
phrases: "look up the docs", "pull the framework docs", "check the
SDK reference", "what's the current API for". The library name must
be concrete enough to look up.

Do NOT invoke this skill for:
- Business-logic debugging — raises `NOT_A_DOC_LOOKUP`.
- Open-ended "how do I do X" questions without a specific library.
- Questions about this repo's own code (use `search-first` instead).

If two trigger phrases could match, ask the operator which skill to invoke.
Do not guess.

## Contract

Inputs:

- `library_name`: str — must match `^[a-zA-Z0-9._/@-]+$`. Anything
  else raises `NOT_A_DOC_LOOKUP`. The regex is narrow on purpose:
  it accepts real package names like `next.js`, `@anthropic-ai/sdk`,
  `django-rest-framework`, `typing.Protocol`, and rejects anything
  with spaces, URL escapes, or shell metacharacters.
- `specific_question`: str — what the caller actually wants to know.
  Must be phrased as a documentation lookup, not a debugging
  question. A question containing "why doesn't", "error", "broken",
  or similar signals raises `NOT_A_DOC_LOOKUP` unless it is
  bracketed by a clear API surface reference.

Outputs:

- `resolved_library_id`: str — the Context7 id (`/org/project` or
  `/org/project/version`), or the fallback URL.
- `doc_excerpt_path`: str — path under
  `state/artifacts/documentation-lookup/<request-id>/excerpt.md`.
- `source`: `"context7" | "web_fallback"`.
- `confidence`: `"high" | "medium" | "low"`.

## Procedure

1. **Validate `library_name`.** If the regex does not match, raise
   `PolicyViolation(PolicyViolationCode.NOT_A_DOC_LOOKUP)` with a
   one-sentence explanation. Never pass a malformed name through
   to any tool.

2. **Validate `specific_question`.** If the question is phrased as
   a debugging ask rather than a docs lookup, raise
   `NOT_A_DOC_LOOKUP`.

3. **Resolve the library id** via the Context7 MCP tool
   `resolve-library-id` with the library name. **Pick the
   highest-benchmark-score result and proceed — do not loop on
   ambiguity.**
   Context7 has a hard 3-call-per-question budget; looping on the
   resolver burns that budget without getting closer to an answer.

4. **Query docs** via the Context7 MCP tool `query-docs` with the
   resolved id and the specific_question. One call.

5. **On Context7 miss,** fall through to `WebFetch` with an
   allowlisted URL. The allowlist is either:
   - A URL Context7 returned in the resolver step (if any), OR
   - A domain in `{docs.python.org, developer.apple.com,
     developer.mozilla.org, nodejs.org, react.dev}`.
   Any other URL is rejected. Web fallback always marks
   `confidence: "low"`.

6. **Write the excerpt** to
   `state/artifacts/documentation-lookup/<request-id>/excerpt.md`
   with the resolved id, source, the question, and the returned
   content. Copyright rule: the excerpt MUST be ≤ 15 words of direct
   quote per distinct passage; longer material must be summarized.

7. **Return the structured output.** The caller decides what to do
   with the answer — this skill does not apply it.

## Examples

### Example — high-confidence Context7 hit

```
library_name: "anthropic"
specific_question: "What is the current shape of messages.count_tokens?"
→ resolved_library_id: "/anthropic/sdk"
→ source: "context7"
→ confidence: "high"
```

### Example — web fallback

```
library_name: "django-rest-framework"
specific_question: "What does @action(detail=False) do?"
→ (Context7 miss)
→ resolved_library_id: "https://docs.python.org/..."  # allowlisted
→ source: "web_fallback"
→ confidence: "low"
```

### Example — rejected as business-logic debug

```
library_name: "django"
specific_question: "Why is my query returning NULL?"
→ raises NOT_A_DOC_LOOKUP
```

## Boundaries and failure modes

- **Context7 3-call-per-question budget is respected.** Never loop
  on `resolve-library-id`. Highest-benchmark-score wins.
- **No WebFetch off the allowlist.** Ever.
- **Read-only outside `state/artifacts/documentation-lookup/`.** This
  skill MUST NOT edit `packages/`, `apps/`, `products/`, or `docs/`.
- **Copyright.** Max 15 words of direct quote per distinct passage.
  Longer material gets summarized.
- **`library_name` regex is the primary defense against prompt
  injection.** Do not relax it without updating the adversarial
  fixtures in the same commit.

## References

- Gap analysis: `docs/2026-04-14-everything-claude-code-gap-analysis.md` §1.
- Plan: `docs/plans/2026-04-15-feat-ecc-gap-recommendations-plan.md` Phase 1b.
- Context7 MCP instructions: see `CLAUDE.md` MCP Server Instructions
  section for Context7's 3-call budget.
- Sibling skills: `search-first`, `repo-onboarding`.
