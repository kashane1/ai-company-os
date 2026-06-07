# 087 — Extract skill-evolution worker core out of the 828-line entrypoint

> **TL;DR:** `apps/worker-skill-evolution/main.py` is 828 lines. Splitting it
> needs care because the integration test loads it via
> `importlib.util.spec_from_file_location` (the `apps/` dir is not a package),
> so sibling-file splits break. The right move is to extract the reusable core
> (sidecar validation, staging, execution) into a real `packages/` module the
> entrypoint and tests import normally. Architectural — wants its own plan.

**Priority:** p3 (entrypoints are edited far less often than shared primitives;
the high-value monolith, `packages/tools/primitives/approvals`, was already
split in the token-efficiency pass).

## Why it wasn't done inline

`tests/python/integration/test_skill_evolution_worker.py` imports the worker as:

```python
spec = importlib.util.spec_from_file_location(
    "skill_evolution_worker_main", REPO_ROOT / "apps/worker-skill-evolution/main.py")
```

Loaded that way the module has no package parent, so `from . import _x` or
sibling `import _x` would fail without sys.path hacks. A clean split therefore
means moving logic into an importable package, not adding sibling files.

## Suggested shape

- New `packages/tools/skill_evolution/` (real package) holding the cohesive
  blocks currently in `main.py`:
  - `sidecar.py` — `ProposalSidecar`, `load_sidecar`, `_require_safe_id`,
    `_require_safe_path`, `SidecarValidationError` (lines ~128–307)
  - `staging.py` — `stage_proposal`, `_quarantine_artifact`, `_artifact_dir_for`
  - `execution.py` — `execute_claimed_task`, `_run_one`, poll/complete/fail/block
- `apps/worker-skill-evolution/main.py` keeps only CLI wiring + `run_worker_loop`
  and imports from the package.
- The integration test imports from the package directly (drop the importlib
  hack for the moved pieces).

## Acceptance

- [ ] `main.py` under ~250 lines (CLI + loop only).
- [ ] Core logic in an importable `packages/` module with unit tests.
- [ ] `make test-python` green; behaviour unchanged.
