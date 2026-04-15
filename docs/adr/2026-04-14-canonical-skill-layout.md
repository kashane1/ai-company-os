---
title: Canonical Skill Layout — Directory Preferred, Flat Files Grandfathered
date: 2026-04-14
status: accepted
supersedes: (none)
related:
  - docs/plans/2026-04-14-feat-hermes-inspired-platform-upgrade-plan.md
  - skills/WIRING.md
---

# Canonical Skill Layout

## Status

**Accepted** (2026-04-14, Phase 0.5e).

## Context

Two canonical skill layouts coexist in `skills/canonical/`:

1. **Per-skill directory layout** (Phase 2.5+). Each skill is a directory:
   ```
   skills/canonical/<skill-id>/
   ├── skill.md           (required — prompt + frontmatter)
   ├── contract.yaml      (optional — I/O contract for validator-kind)
   ├── validator.py       (required for kind: validator)
   └── fixtures/          (happy/boundary/adversarial yaml/json)
       ├── happy_path.yaml
       ├── boundary.yaml
       └── adversarial.yaml
   ```
   Examples: `post-run-validation`, `social-post-safety`,
   `approval-token-audit`, `failure-mode-regression`,
   `content-voice-guardrail`.

2. **Flat-file layout** (Phase 0). A single markdown file directly under
   `skills/canonical/shared/`, `skills/canonical/handoffs/`, or
   `skills/canonical/products/<product-id>/`:
   ```
   skills/canonical/shared/product-artifact-chain.md
   skills/canonical/shared/supervisor-goal-decomposition.md
   skills/canonical/handoffs/codex-claude-handoff.md
   skills/canonical/products/catchbook/ios-ui-polish-review.md
   ```
   Examples: every `project_skill` registered in CLAUDE.md's
   trigger-phrase table.

The Phase 0 plan Cross-Cutting Enhancements section (X8) required
making a binding layout decision before Phase 1 starts writing fixtures
for the flat files. This ADR records that decision.

## Decision

**New skills use the per-skill-directory layout.** The directory
layout is strictly more capable — it supports fixtures, validators,
and contracts as peer files — and matches the modern shape already
used by Phase 2.5+ skills. All new canonical skills added by Phase 3
(skill self-evolution), Phase 5 (command scan), and any future phase
MUST land as `skills/canonical/<skill-id>/skill.md` + siblings.

**Flat-file Phase 0 skills stay flat.** Migrating `product-artifact-chain`,
`supervisor-goal-decomposition`, `codex-claude-handoff`,
`ios-ui-polish-review`, `ios-to-appstore-handoff`,
`app-store-positioning-pack`, `repo-sync`, `worktree-lifecycle`,
`codex-task-packet-library`, `bounded-codex-implementation`, and
`post-run-validation` (already directory) to the directory layout
would touch ~15 files and every adapter reference without changing
behavior — net cost high, net value low. Phase 1 fixture work for
these skills lands via the sibling-file fixture convention documented
below.

**The loader supports both layouts via dual fixture discovery.**
The canonical resolution order for a flat-file skill's fixtures is:

1. `skills/canonical/<skill-id>/fixtures/*` (directory layout; preferred).
2. `skills/canonical/<parent-dir>/<skill-id>.fixtures.yaml` (sibling file
   alongside the flat skill markdown; supported for Phase 0 skills).
3. `skills/canonical/<parent-dir>/fixtures/<skill-id>/*` (future escape
   hatch — not used today but reserved so a Phase 0 parent directory can
   grow a shared `fixtures/` subdir if needed).

## Rationale

- **Directory layout is the long-term target.** Hermes's own
  `skills.external_dirs` hook (Phase 2 spike) keys on directory name,
  not frontmatter id. Any canonical skill the platform wants to mount
  into Hermes via that hook MUST be a directory. Flat-file skills are
  effectively Claude-only forever unless migrated.

- **Migration has no ROI for stable Phase 0 skills.** The 10 flat-file
  skills are load-bearing routing targets that haven't changed shape
  since Phase 0. Migrating them would touch adapter files, registry
  paths, and CLAUDE.md trigger-phrase entries for zero functional gain.
  Adding sibling-file fixture support is a ~20-line loader change;
  directory migration would be ~150 lines of rename-and-reference-update.

- **Sibling-file fixtures keep the flat skills reviewable.** The fixture
  file for `product-artifact-chain.md` lives at
  `product-artifact-chain.fixtures.yaml` right next to the skill file,
  so a reviewer of a Phase 1 fixture PR sees the skill and its test
  inputs in the same directory listing.

- **Reviewer check:** a single `ls skills/canonical/shared/` shows every
  flat skill and its sibling fixture file. No walking into subdirectories,
  no "where did the fixture go" question.

## Consequences

### Immediate (Phase 0.5e + Phase 1)

- `packages/tools/skills/loader.py` gains dual fixture-discovery logic
  (Phase 0.5e).
- Phase 1 PRs (1b/1c/1d) land fixtures as sibling `.fixtures.yaml` files
  next to the Phase 0 flat skill markdown.
- `skills/WIRING.md` is updated to reference this ADR as the authoritative
  layout contract.

### Forward

- Any future Phase that proposes migrating a Phase 0 flat skill to the
  directory layout MUST supersede this ADR with a new one explaining
  why the migration is worth its ROI.
- Phase 3's skill-self-evolution worker proposes skills in the directory
  layout ONLY (per the allowlist model — self-evolved skills never
  target Phase 0 flat files).

## References

- Original plan section: `docs/plans/2026-04-14-feat-hermes-inspired-platform-upgrade-plan.md`
  → "Cross-Cutting Enhancements" → X8 (State directory hygiene +
  canonical layout decision).
- Repo research ground truth: the loader's dual-layout code path lives
  in `packages/tools/skills/loader.py` around the `validator.py` fallback
  block (already handles per-skill-directory lookups — Phase 0.5e extends
  the same code path for fixtures).
