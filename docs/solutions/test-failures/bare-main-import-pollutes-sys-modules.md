---
title: "Bare `from main import ...` Pollutes sys.modules Across Multiple apps/*/main.py Files"
category: test-failures
date: 2026-04-15
tags:
  - python
  - pytest
  - sys-modules
  - sys-path
  - test-isolation
  - importlib
  - module-caching
  - runtime-supervisor
  - worker-supervisor
  - phase-1
  - hermes-platform-upgrade
module: tests/python/unit, apps/worker-supervisor, apps/runtime-supervisor, apps/api
symptom: "A new test that imports `plan_goal` from worker-supervisor's `main.py` passes in isolation, but running the full suite produces 11 cascading ImportErrors in `test_runtime_supervisor_cli.py` with `ImportError: cannot import name 'load_supervisor_status' from 'main' (/Users/simons/ai-company-os/apps/worker-supervisor/main.py)`. The CLI test is trying to import from runtime-supervisor's main.py, not worker-supervisor's."
root_cause: "This repo has multiple `apps/*/main.py` files (worker-engineering, worker-ios, worker-appstore, worker-gtm, worker-supervisor, runtime-supervisor). A test using the naive pattern `sys.path.insert(0, str(APP_DIR)); from main import plan_goal` caches the first-loaded `main.py` under the bare `main` key in `sys.modules`. Every subsequent `from main import ...` in a later test — even if that later test's sys.path points at a different app's main.py — gets the cached entry, not a fresh import. pytest runs tests in deterministic alphabetical order, so test_supervisor_goal_decomposition_fixtures.py (loaded first) pinned worker-supervisor's main.py as `main`, and test_runtime_supervisor_cli.py's runtime-supervisor cli.py then tried `from main import load_supervisor_status` and found the worker-supervisor module, which doesn't export that function."
---

# Bare `from main import ...` Pollutes sys.modules Across Multiple apps/*/main.py Files

Shipped during Phase 1 PR-1d of the Hermes platform upgrade plan
(`docs/plans/2026-04-14-feat-hermes-inspired-platform-upgrade-plan.md`).
Fixed at commit `3bef3c0` on `main`.

## Symptom

After adding a new test at
`tests/python/unit/test_supervisor_goal_decomposition_fixtures.py`
that imported `plan_goal` from the worker-supervisor via:

```python
SUPERVISOR_APP = REPO_ROOT / "apps" / "worker-supervisor"
if str(SUPERVISOR_APP) not in sys.path:
    sys.path.insert(0, str(SUPERVISOR_APP))

from main import plan_goal
```

The new test passed cleanly in isolation:

```console
$ pytest tests/python/unit/test_supervisor_goal_decomposition_fixtures.py -q
...                                                                      [100%]
3 passed in 0.56s
```

And the runtime-supervisor CLI test suite passed cleanly in isolation:

```console
$ pytest tests/python/unit/test_runtime_supervisor_cli.py -q
...........                                                              [100%]
11 passed in 1.10s
```

But running the full suite produced **11 cascading failures** in the
runtime-supervisor CLI tests, all with the same shape:

```console
$ pytest tests/python/ -q
...
ImportError: cannot import name 'load_supervisor_status' from 'main'
  (/Users/simons/ai-company-os/apps/worker-supervisor/main.py)

apps/runtime-supervisor/cli.py:18: ImportError
=========================== short test summary info ============================
FAILED tests/python/unit/test_runtime_supervisor_cli.py::test_runtime_supervisor_cli_starts_supervisor_process
FAILED tests/python/unit/test_runtime_supervisor_cli.py::test_runtime_supervisor_cli_requests_clean_shutdown
FAILED tests/python/unit/test_runtime_supervisor_cli.py::test_runtime_supervisor_cli_reports_queued_task_in_work_summary
[... 8 more]
11 failed, 228 passed, 4 skipped in 7.81s
```

The error message is the critical clue: the CLI test's `cli.py` was
trying to import `load_supervisor_status` from a `main` module — but
the path it got was `apps/worker-supervisor/main.py`, not
`apps/runtime-supervisor/main.py`. The wrong `main.py` had been
cached under the key `main` in `sys.modules`.

## Investigation

### What I tried first and why it didn't work

- **Rerunning the failing test in isolation:** 11/11 passed. Classic
  "works alone, breaks together" — meant test state was being polluted
  by an earlier test in the same run.
- **Assuming the test runner was the problem:** I briefly wondered if
  pytest had changed its import mode. It hadn't. The default
  `importmode=prepend` has always worked this way.
- **Looking at the newly-added test first:** correct instinct. The new
  test was the only code change in the PR, and the failing tests were
  downstream consumers of runtime-supervisor CLI imports. Something
  the new test did was leaking into the rest of the session.

### The actual bug

`sys.modules` is keyed by the string name used in the import statement,
not by file path. When Python sees:

```python
from main import plan_goal
```

it looks up the string `"main"` in `sys.modules`. First time through,
it's not there, so Python walks `sys.path` top-down, finds
`apps/worker-supervisor/main.py` (because the test just prepended
that directory), imports it, binds the resulting module object under
the key `"main"` in `sys.modules`, and extracts `plan_goal`.

From that point on, **every other code path in the same Python
process that does `from main import X` or `import main` gets the
worker-supervisor module**, regardless of what's currently at the
front of `sys.path`. `sys.modules` is a process-wide cache; `sys.path`
only controls the *first* lookup for a given module name.

`apps/runtime-supervisor/cli.py` has this line:

```python
from main import load_supervisor_status, request_supervisor_shutdown
```

And a little further up:

```python
APP_ROOT = Path(__file__).resolve().parent
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))
```

When `cli.py` runs first in a pytest session, `sys.modules["main"]`
is empty, the sys.path prepend points at `apps/runtime-supervisor/`,
and the import resolves to runtime-supervisor's main.py (which DOES
export `load_supervisor_status`). Everything works.

When the worker-supervisor test runs first and pins `main` to the
worker-supervisor module, `cli.py`'s import lookup finds the cached
entry immediately, never walks `sys.path` at all, and returns the
wrong module.

pytest's default `importmode=prepend` can't save you from this: the
sys.path prepend happens inside the conftest, but the `sys.modules`
cache is never invalidated between tests. The rootdir / package
detection doesn't kick in here because these are raw scripts at
`apps/*/main.py`, not installed packages.

### Why there are multiple `main.py` files in the first place

Each worker app is a launchd entrypoint:
`apps/worker-engineering/main.py`, `apps/worker-ios/main.py`,
`apps/worker-appstore/main.py`, `apps/worker-gtm/main.py`,
`apps/worker-supervisor/main.py`, `apps/runtime-supervisor/main.py`,
and `apps/api/server.py` (the only non-`main.py` entrypoint). The
convention matches `scripts/runtime`'s expectation and keeps the
launchd plists uniform. None of these are installed packages — they
run directly via `python <path>/main.py`. The multiplicity is a
deliberate product of the runtime-supervisor / worker design, so
this problem will only grow as more workers land.

## Root cause

`sys.modules` is a process-wide, string-keyed cache. When multiple
files in the same project share a short name (`main.py`), the first
`from main import ...` wins for the remainder of the process. Bare
short-name imports in pytest tests that span multiple app
directories are fundamentally unsafe.

## Working solution

Use `importlib.util.spec_from_file_location` with a **unique module
name** per target file. This binds each loaded file under a distinct
key in `sys.modules`, eliminating cross-contamination.

### Before (broken)

```python
# tests/python/unit/test_supervisor_goal_decomposition_fixtures.py
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SUPERVISOR_APP = REPO_ROOT / "apps" / "worker-supervisor"
if str(SUPERVISOR_APP) not in sys.path:
    sys.path.insert(0, str(SUPERVISOR_APP))

from main import plan_goal  # ❌ caches worker-supervisor as `main`
```

### After (correct)

```python
# tests/python/unit/test_supervisor_goal_decomposition_fixtures.py
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
WORKER_SUPERVISOR_MAIN = REPO_ROOT / "apps" / "worker-supervisor" / "main.py"


def _load_worker_supervisor_main() -> Any:
    """Import apps/worker-supervisor/main.py under a unique module name.

    We CANNOT use `from main import plan_goal` because multiple apps in
    this repo have a `main.py` and bare-name imports pollute sys.modules.
    Matches the existing `load_runtime_supervisor_main` helper pattern
    in tests/python/unit/test_default_worker_specs_api.py.
    """
    spec = importlib.util.spec_from_file_location(
        "worker_supervisor_main_goal_decomposition_fixture",
        WORKER_SUPERVISOR_MAIN,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_plan_goal_matches_fixture(case: dict) -> None:
    worker_supervisor_main = _load_worker_supervisor_main()
    goal = Goal(...)
    tasks = worker_supervisor_main.plan_goal(goal)
    ...
```

Key points:

1. **Module name must be unique per target file.** I used
   `"worker_supervisor_main_goal_decomposition_fixture"` — descriptive,
   unlikely to collide with anything else. Shorter unique names work
   too; what matters is that no other test in the suite registers the
   same key.
2. **The helper returns the module, not individual symbols.** Callers
   access functions via `worker_supervisor_main.plan_goal(goal)`. This
   makes the source file obvious at the call site and removes any
   temptation to re-export via a second `from`.
3. **Do not mutate sys.path.** The whole point of
   `spec_from_file_location` is that you give it an absolute path
   directly; sys.path is irrelevant.

### The pattern was already in the repo

`tests/python/unit/test_default_worker_specs_api.py` had been using
exactly this pattern for runtime-supervisor's main.py:

```python
def load_runtime_supervisor_main():
    module_path = (
        Path(__file__).resolve().parents[3]
        / "apps" / "runtime-supervisor" / "main.py"
    )
    spec = importlib.util.spec_from_file_location(
        "runtime_supervisor_main_api_spec", module_path
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module
```

The fix was literally to copy this idiom and specialize it for
worker-supervisor. If I had grepped for `spec_from_file_location`
in tests/python/unit/ before writing the test, I would have skipped
the bug entirely.

## Prevention

### Mechanical rules for any pytest test that imports from `apps/*/main.py`

1. **Never write `from main import X` or `import main` in a test.**
   Both forms bind under the bare `main` key in `sys.modules` and
   will collide with any other test that does the same against a
   different target.
2. **Always use `importlib.util.spec_from_file_location(unique_name, path)`.**
   The `unique_name` should include the target directory name
   (e.g. `worker_supervisor_main_<context>`) so every test in the
   repo registers its own unambiguous key.
3. **Return the module object, not individual symbols.** `return module`,
   then access `module.plan_goal(goal)` at the call site. Callers
   stay explicit about which `main.py` they're talking to.
4. **Do not mutate `sys.path` in tests that load app entrypoints.**
   `spec_from_file_location` takes an absolute path; prepending
   `sys.path` is a redundant footgun that makes it look like bare
   imports should work.

### Reviewer check

Any PR that adds or modifies a file under `tests/python/` which
references `apps/*/main.py` should grep for the anti-pattern before
merge:

```bash
# Should return zero hits in any new or modified test file:
rg 'from main import|^import main' tests/python/
```

If the grep hits, the reviewer should ask why `spec_from_file_location`
wasn't used. Existing hits (that predate this documentation) can be
migrated opportunistically as the tests are touched for other reasons.

### Lint-level enforcement (optional)

A ruff custom rule or a tiny pytest plugin could flag any
`from main import ...` in `tests/python/**/*.py` automatically. Not
worth shipping until this bites a second time, but the hook point is
clear if it does: a `conftest.py` that scans collected test modules
for suspect imports and raises at collection time.

### Debugging playbook for the next time this happens

Symptom pattern: *test passes in isolation, fails only when another
test has run first in the same session, ImportError names a function
that does exist in the file the error message says was loaded*.

Diagnostic:

```python
# Drop into pdb at the failing import site, then:
import sys
print(sys.modules["main"].__file__)
# If this prints the path of a DIFFERENT app's main.py than the
# error message claimed, you have sys.modules pollution.
```

Fix: rewrite the EARLIEST-running offending test (alphabetical by
filename across the entire test suite, not the current directory)
to use `spec_from_file_location`. You do not need to rewrite every
bare `from main import` in the codebase — just the one that gets
loaded first in alphabetical order, since it's the one that pins
the cache. In practice rewriting all of them is safer and cheaper
than reasoning about load order.

## Cross-references

- Commit that introduced the bug: `9dfbad2` (Phase 1 PR-1b — the
  original `test_supervisor_goal_decomposition_fixtures.py` used
  the bare-import pattern)
- Commit that fixed it: `3bef3c0` (Phase 1 PR-1d — the fix was
  bundled with PR-1d because the full-suite run during PR-1d was
  the first place the failures surfaced)
- Existing correct pattern in the same directory:
  `tests/python/unit/test_default_worker_specs_api.py::load_runtime_supervisor_main`
- Hermes platform upgrade plan, Phase 1 PR-1b/1d:
  `docs/plans/2026-04-14-feat-hermes-inspired-platform-upgrade-plan.md`
- Python docs on `sys.modules` as a process-wide cache:
  https://docs.python.org/3/reference/import.html#the-module-cache
- Python docs on `importlib.util.spec_from_file_location`:
  https://docs.python.org/3/library/importlib.html#importlib.util.spec_from_file_location

## Why this compounds

Every new worker lane added to `apps/` ships yet another `main.py`.
Phase 3 of the Hermes platform upgrade adds `apps/worker-skill-evolution/main.py`.
Phase 4 may add more. The blast radius of a bare `from main import`
grows linearly with the number of worker apps, and the probability
that a new test uses the naive pattern stays constant (it's the
pattern a developer reaches for first). Documenting the fix here
means the next person writing a per-worker fixture test finds the
idiom in under 30 seconds and ships correctly the first time
instead of losing the 20 minutes I lost to the cascading-failure
investigation.
