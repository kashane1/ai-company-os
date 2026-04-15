---
status: completed
priority: p2
issue_id: "011"
tags: [code-review, flow-completeness, data-integrity, ecc-gap-plan]
dependencies: []
---

# Problem Statement

The ECC gap plan's Phase 0 adds `state/benchmarks/skill-estate/` and `state/artifacts/verification-loop/` to the `state/README.md` glossary. But the glossary update only *names* the directories — nothing creates them. On a fresh clone (or after a rollback that removes `state/`), the first write from `skill-stocktake`, `context-budget`, or `verification-loop` will crash with `FileNotFoundError`.

## Findings

- Spec-flow-analyzer flow-gap #4: "Brand-new machine, no baseline directory, first `run()` crashes on `FileNotFoundError` unless the validator `mkdir(parents=True, exist_ok=True)`s."
- Data-integrity-guardian gap #7: "State directory creation unspecified. Who creates these directories? If on first write, does the writer handle `FileNotFoundError` or crash?"

## Proposed Solutions

### Option 1: Each writer `mkdir(parents=True, exist_ok=True)` before atomic rename

`atomic_write_json()` (see todo 007) calls `path.parent.mkdir(parents=True, exist_ok=True)` before the temp-file + rename dance. No bootstrap script needed.

Pros:
- Self-healing — any first-write path works
- Single fix in the shared state writer primitive
- No operator intervention required
- Composable with todo 007 (`_state_writer.py`)

Cons:
- Silently creates dirs that operators might not expect on-disk

Effort: trivial
Risk: low

### Option 2: `infra/scripts/bootstrap_state_dirs.sh`

Ship a bootstrap script that creates all known state subdirs from the glossary.

Pros:
- Explicit, visible to operators

Cons:
- Has to be run manually after clone
- Every new state subdir requires updating the script
- Forgets itself — not self-healing

Effort: small
Risk: medium

## Recommended Action

Option 1. Fold into todo 007's `_state_writer.py` — the atomic writer always calls `mkdir(parents=True, exist_ok=True)` before the rename. Add a `boundary_first_run.yaml` fixture exercising the empty-state path.

## Acceptance Criteria

- [ ] `atomic_write_json()` in `_state_writer.py` calls `path.parent.mkdir(parents=True, exist_ok=True)` before temp+rename
- [ ] Fixture `boundary_first_run.yaml` deletes the target directory, runs the validator, asserts the directory is created and JSON lands
- [ ] Test passes on a fresh `tmp_path` fixture without any pre-existing state directory
- [ ] Plan document updated: Phase 2b/3 DoD mentions first-run-safe behavior

## Work Log

### 2026-04-15 - Captured during technical review
**By:** Claude (review workflow)
**Actions:** Spec-flow-analyzer and data-integrity-guardian flagged the same gap — folded into the shared `_state_writer.py` primitive from todo 007.
