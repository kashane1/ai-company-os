---
id: skill-stocktake
name: Skill Stocktake
purpose: Walk the skill registry, cross-reference against the filesystem and CLAUDE.md, and surface drift items that reconciliation does not catch (orphan canonical files, dangling project_skill pointers, trigger-phrase drift).
owner_agent: supervisor
target_runtimes: [claude]
stage: active
kind: validator
---

# Skill: skill-stocktake

Kind: validator
Owner: supervisor
Runtimes: claude

## Purpose

`reconcile_registry()` catches structural drift in any skill marked
`fixture_status: passing`. It does not catch:

- orphan canonical files — a `skills/canonical/<id>/skill.md` that
  has no registry entry,
- dangling `project_skill` pointers — a registry entry with
  `project_skill: <path>` whose path does not exist on disk,
- trigger-phrase drift — a `CLAUDE.md` trigger-phrase line pointing
  at an adapter file that does not exist.

This skill is the missing structural check. It walks the registry,
the filesystem, and `CLAUDE.md`, then emits a `StocktakeReport`
enumerating every drift item.

## When to invoke

- CI on every push (via pytest integration in the existing unit-test
  run).
- `verification-loop` as a sub-check.
- Operator via trigger phrases: "audit the skill estate", "run a
  skill stocktake", "check for orphan skills", "find drift in the
  skill registry".

## Contract

Inputs (via the validator `run()` payload):

- `registry_path`: Path | None — override for synthetic tests.
  Defaults to the real `skills/registry.yaml`.
- `known_drift`: tuple[str, ...] — drift-item ids known to be
  pre-existing and tagged so future comparisons don't re-flag them.
- `capture_followups`: bool (future — not in v1 landing) — when True,
  every drift item is also written to `state/followups/` via
  `followup_issue_writer`.

Outputs:

- `verdict`: `"pass" | "fail"` — pass when `drift_items == []`.
- `report`: StocktakeReport as JSON-safe dict.
- `drift_count`: int.

## Drift types (MVP set — 3 of the originally proposed 7)

1. **`orphan_canonical`** — canonical skill.md exists, no registry
   entry points at it.
2. **`dangling_project_skill`** — registry entry references a
   `.claude/skills/<id>.md` file that is not on disk.
3. **`trigger_phrase_drift`** — CLAUDE.md trigger-phrase line points
   at an adapter file (under `skills/adapters/`) that does not
   exist. Targets under `docs/` are valid and not flagged.

Deferred drift types (explicitly out of v1 scope — add only on
evidence of pain): `orphan_adapter`, `orphan_project_skill`,
`registry_schema_drift` (loader already enforces), `draft_stale`
(no drafts exist after Phase 0 rework).

## Procedure

1. Load the registry via direct YAML parse (NOT the cached loader
   path — the stocktake must be able to see malformed entries that
   the loader would reject).
2. Run `orphan_canonical` drift check.
3. Run `dangling_project_skill` drift check.
4. Run `trigger_phrase_drift` check. Targets under `docs/` are
   allowed; only `skills/adapters/` targets are resolved.
5. Assemble a `StocktakeReport` with schema_version, drift_items,
   registry_entries_checked, and known_drift tags.
6. Serialize via `dataclasses.asdict(report, dict_factory=json_safe_factory)`.
7. Return `{verdict, report, drift_count}`.

## Boundaries and failure modes

- **Read-only.** The validator never writes. The `followup_issue_writer`
  integration is a separate opt-in (v2).
- **No LLM round-trip.** Fully deterministic.
- **Path-traversal safe.** Every registry-derived path resolves via
  `_safe_paths.safe_join()` against the skills root.
- **Performance.** < 200 ms on the live registry (tightened from the
  original 500 ms after deepening; no subprocess forks in v1).
- **Pre-existing drift is tagged, not fixed.** The first Phase 2a
  integration run tags `social-post-safety` and `post-run-validation`
  as `known_drift` so comparisons don't regress on them.

## References

- Plan: `docs/plans/2026-04-15-feat-ecc-gap-recommendations-plan.md` Phase 2a.
- Primitive: `packages/tools/primitives/registry_drift.py`.
- Reader: `packages/tools/primitives/skill_stocktake_reader.py`.
- Template: `packages/tools/skills/reconciliation.py` (structural check).
