---
status: pending
priority: p3
issue_id: "063"
tags: [code-review, audit-fork, cooling-off, mechanical-enforcement]
dependencies: []
---

# Problem Statement

Two enforcement rules in the recon-family are honor-system today:

1. **Cross-skill cooling-off (14 days).** The shared scaffold says no sibling should emit a prompt whose slug overlaps any other sibling's recent output — but no helper enumerates the union of all backlog files within 14 days. Each adapter would need to hand-roll the check.

2. **Same-day collision rule (`-2`, `-3` suffix on filename).** Documented in the shared spine but not mechanically implemented. Each skill must check filename existence at write-time and increment.

Both are corner cases the LLM can usually handle correctly, but a mechanical helper would close the silent-failure mode.

## Findings

- **spec-flow-analyzer (NICE-TO-HAVE):** "A small helper that lists all `*-backlog-*.md` files within 14 days, callable from each sibling's quality-checks, would close the silent-overlap risk."

- **spec-flow-analyzer (NICE-TO-HAVE):** "Same-day collision rule (`-2`, `-3` suffix) is prose-only. Adding a one-line 'before write, check existence and increment suffix' to each adapter would prevent silent overwrites."

## Proposed Solutions

### Option 1: Two small Python helpers in `packages/tools/recon_family/`

```python
# packages/tools/recon_family/cooling_off.py
def recent_backlogs(product_id: str, days: int = 14) -> list[Path]:
    """List all recon-family backlog files modified in the last `days` days."""
    ...

# packages/tools/recon_family/filename.py
def collision_safe_path(base_path: Path) -> Path:
    """If base_path exists, return base_path with -2 / -3 suffix appended."""
    ...
```

Each adapter cites these helpers in its quality-checks section.

Pros: mechanical enforcement; reusable across siblings; tests can be unit-tested
Cons: introduces a new tool package
Effort: Small
Risk: Low

### Option 2: Document the manual procedure, leave honor-system

Strengthen the prose in `skills/canonical/shared/recon-scaffolding.md` to give a step-by-step "before write" procedure the LLM follows. No new code.

Pros: simplest
Cons: doesn't actually fix the silent-failure mode
Effort: Trivial
Risk: None

## Recommended Action

**Option 2 now, Option 1 when the first silent-failure is observed.** The recon-family is invoked monthly at most. Two honor-system rules are unlikely to silently fail at that cadence. If a silent overwrite or cooling-off violation is observed in practice, escalate to Option 1.

## Technical Details

- Files affected (Option 2):
  - `skills/canonical/shared/recon-scaffolding.md` (strengthen the procedure prose)
- Files affected (Option 1, future):
  - `packages/tools/recon_family/cooling_off.py` (new)
  - `packages/tools/recon_family/filename.py` (new)
  - `tests/python/unit/test_recon_family_helpers.py` (new)
  - Each recon-family adapter (cite the helpers)

## Acceptance Criteria (Option 2)

- [ ] `skills/canonical/shared/recon-scaffolding.md` § "Same-day collision rule" gives a 3-step procedure
- [ ] Cross-skill cooling-off section explicitly says "list every backlog file before drafting the first prompt"

## Work Log

(empty)
