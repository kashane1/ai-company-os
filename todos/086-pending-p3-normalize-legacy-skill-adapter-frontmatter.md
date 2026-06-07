# 086 — Normalize legacy skill-adapter frontmatter

> **TL;DR:** 8 Claude skill adapters have no YAML frontmatter, so their
> `.claude/skills/` pointers can't be generated from the single source. Add
> `description` + `canonical_source` frontmatter to each so
> `scripts/skills/gen_project_skills.py` covers them and CI can enforce sync.

**Priority:** p3 (polish/consistency — current pointers work; they're just
hand-maintained instead of generated).

## Context

`scripts/skills/gen_project_skills.py` (added in the token-efficiency pass)
generates each `.claude/skills/<id>.md` pointer from its adapter's frontmatter
`description` + `canonical_source`, eliminating the description duplication that
used to drift across three files. It already covers the conforming skills and
CI enforces their sync.

These 8 adapters predate the frontmatter convention — they start with a
`# Adapter (claude): ...` heading and mention the canonical only in prose, so
the generator skips them with a warning:

- `skills/adapters/claude/approval-flow-review.md`
- `skills/adapters/claude/client-intake.md`
- `skills/adapters/claude/ios-build-and-sign.md`
- `skills/adapters/claude/landing-page-build.md`
- `skills/adapters/claude/launch-checklist.md`
- `skills/adapters/claude/local-seo-pages.md`
- `skills/adapters/claude/launch-checklist.md`
- `skills/adapters/claude/test-coverage-audit.md`
- `skills/adapters/claude/web-ux-audit.md`

## Acceptance

- [ ] Each adapter above opens with YAML frontmatter carrying `description:`
      (the canonical one-liner) and `canonical_source:` (the existing path from
      its `.claude/skills/` pointer).
- [ ] `python3 scripts/skills/gen_project_skills.py` regenerates all pointers
      with zero remaining warnings.
- [ ] `python3 scripts/skills/gen_project_skills.py --check` is clean.
- [ ] Descriptions match `docs/skills-index.md` / `skills/registry.yaml`.
