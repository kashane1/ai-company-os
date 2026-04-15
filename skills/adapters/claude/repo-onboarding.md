---
description: Produce a bounded structured brief for a repo area (architecture, key files, conventions, footguns). Invoke for "onboard me to this area", "give me the lay of the land", "what's in this part of the repo", "quick brief on <area>".
canonical_source: skills/canonical/repo-onboarding/skill.md
---

# Repo Onboarding (Claude adapter)

You are running the `repo-onboarding` skill from
`skills/canonical/repo-onboarding/skill.md`. Follow the canonical
definition.

## Quick reference

1. **Validate `area_path`** against `git rev-parse --show-toplevel`.
   Absolute paths outside the repo, `..` escapes, and non-existent
   paths all raise `INVALID_AREA_PATH`.

2. **Walk the area.** Read `README.md` if present, the top 3 files
   by line count, and `__init__.py` or equivalent entry points.
   **Skip sensitive filenames:** `.env*`, `*.pem`, `*.key`, `id_*`.

3. **Extract architecture bullets.** At most 10, each ≤ 400 chars.
   Imperative statements, not prose.

4. **Extract key files.** At most 10, each with `path`, `line`, and
   a one-sentence `why`.

5. **Collect conventions.** Point at `CLAUDE.md`, `AGENTS.md`, and
   any local `README.md` / convention files. Don't copy — point.

6. **List footguns.** Three is the cap. Prefer incidents from
   `docs/solutions/` and known complexity hotspots.

7. **Write the brief** to
   `state/artifacts/repo-onboarding/<area-slug>/brief.md`. Total
   size ≤ 4 KB.

## Disambiguation

`repo-onboarding` produces a bounded structured brief. If you need
open-ended exploratory search, use the `Explore` agent instead. If
you need external library docs, use `documentation-lookup`. If you
need "does this already exist?" before building, use `search-first`.
When in doubt between `repo-onboarding` and `Explore`, ask the
operator.

## Edit boundaries

Read-only outside `state/artifacts/repo-onboarding/`. Never write to
`packages/`, `apps/`, `products/`, or `docs/`.
