---
id: repo-onboarding
name: Repo Onboarding
purpose: Given a repo area (path or lane), produce a bounded structured brief — architecture, key files, conventions, footguns — for a supervisor or engineering lane starting work in that area.
owner_agent: supervisor
target_runtimes: [claude]
stage: active
kind: agentic
allowed_edit_boundaries:
  - state/artifacts/repo-onboarding/
forbidden_areas:
  - packages/
  - apps/
  - products/
  - docs/
---

# Skill: repo-onboarding

Kind: agentic
Owner: supervisor
Runtimes: claude

## Purpose

When a new task lands in a part of the repo the caller hasn't touched
recently — or hasn't touched at all — the caller needs a bounded brief
before any non-trivial work begins. This skill produces that brief in
a structured, fixed shape: architecture, key files, conventions,
footguns. It is the "lay of the land" procedure for onboarding to a
subtree.

This is explicitly **not** an open-ended search. The `Explore` agent
handles open-ended search. `repo-onboarding` produces a 10-bullet
structured brief and nothing more.

## When to invoke

Trigger phrases in CLAUDE.md: "onboard me to this area", "give me the
lay of the land", "what's in this part of the repo", "quick brief on
<area>".

Do NOT invoke this skill for:
- Open-ended exploratory search (use the `Explore` agent).
- Looking up external library docs (use `documentation-lookup`).
- Finding prior art for a task (use `search-first`).

If two trigger phrases could match, ask the operator which skill to invoke.
Do not guess.

## Contract

Inputs:

- `area_path`: str — a repo-relative path, resolved against
  `git rev-parse --show-toplevel`. Absolute paths outside the repo
  and `..` escapes raise `INVALID_AREA_PATH`. Non-existent paths
  also raise `INVALID_AREA_PATH` (single enum member covering both
  cases — see todo 017).
- `max_bullets`: int = 10 — architecture bullets cap. The contract
  caps this at 10; higher values are clamped.

Outputs:

- `brief_path`: str — path under
  `state/artifacts/repo-onboarding/<area-slug>/brief.md`.
- `architecture_bullets`: list[str] — at most 10. Each ≤ 400 chars.
- `key_files`: list[{path, line, why}] — at most 10. Filenames on
  the sensitive blocklist (`.env*`, `*.pem`, `*.key`, `id_*`) are
  excluded.
- `conventions_refs`: list[str] — references to `CLAUDE.md`,
  `AGENTS.md`, and any local convention docs under
  `docs/conventions/` or the area's own `README.md`.
- `footguns`: list[str] — three likely footguns, sourced from
  `docs/solutions/`, known incidents, and obvious complexity
  hotspots. Each ≤ 400 chars.

Total brief size ≤ 4 KB (enforced at write time).

## Procedure

1. **Validate `area_path`.** Resolve against
   `git rev-parse --show-toplevel`. If the resolved path is outside
   the repo root, or if it contains `..` escapes, or if it does not
   exist, raise
   `PolicyViolation(PolicyViolationCode.INVALID_AREA_PATH)`. The
   single enum member covers all three failure modes — the operator
   remedy is identical: "fix your path".

2. **Walk the area.** Read `README.md` if present; read the top 3
   files by line count; read `__init__.py` or equivalent entry points.
   Do NOT read files matching the sensitive blocklist (`.env*`,
   `*.pem`, `*.key`, `id_*`).

3. **Extract architecture bullets.** At most 10, each ≤ 400 chars.
   Lead with the subtree's purpose, then its top-level components,
   then its external dependencies. Bullets are imperative
   statements, not prose.

4. **Extract key files.** At most 10 files, each with its path, a
   line number anchor, and a one-sentence "why this file matters"
   note.

5. **Collect conventions.** Reference `CLAUDE.md`, `AGENTS.md`, and
   any local README / convention files. Do not copy them — just
   point at them.

6. **List footguns.** Three is the cap. Each should reference a past
   incident (`docs/solutions/`), a known complexity hotspot, or a
   structural pitfall observed during the walk.

7. **Write the brief** to
   `state/artifacts/repo-onboarding/<area-slug>/brief.md`. Assert
   the total file size is ≤ 4 KB at write time.

8. **Return the structured output.** The caller (not this skill)
   decides how to apply the brief.

## Examples

### Example — `packages/policies/`

```
area_path: "packages/policies/"
→ architecture_bullets: [
    "Policy wrappers live here; workers do not own policy",
    "Every raise site SHOULD use PolicyViolationCode enum, not bare string",
    ...
  ]
→ key_files: [
    {path: "packages/policies/approvals.py", line: 8,
     why: "PolicyViolationCode enum lives here"},
    ...
  ]
→ conventions_refs: ["CLAUDE.md", "AGENTS.md"]
→ footguns: [
    "release_readiness.py still uses bare-string raises — pre-existing debt",
    ...
  ]
```

### Example — rejected as outside the repo

```
area_path: "/Users/simons/.ssh"
→ raises INVALID_AREA_PATH
```

## Boundaries and failure modes

- **Bounded output.** Architecture ≤ 10 bullets × 400 chars;
  key_files ≤ 10; footguns ≤ 3. Total brief ≤ 4 KB. Any overflow
  is truncated with a note.
- **Sensitive files are never read or listed.** Blocklist:
  `.env*`, `*.pem`, `*.key`, `id_*`. Never relax this without
  updating the adversarial fixture in the same commit.
- **No external calls.** This skill reads the local filesystem
  only. No web, no MCP.
- **Read-only outside `state/artifacts/repo-onboarding/`.** MUST NOT
  edit `packages/`, `apps/`, `products/`, or `docs/`.

## References

- Gap analysis: `docs/2026-04-14-everything-claude-code-gap-analysis.md` §1.
- Plan: `docs/plans/2026-04-15-feat-ecc-gap-recommendations-plan.md` Phase 1c.
- Sibling skills: `search-first`, `documentation-lookup`.
- Complementary: `Explore` agent (for open-ended search).
