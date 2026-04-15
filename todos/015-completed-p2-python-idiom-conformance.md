---
status: completed
priority: p2
issue_id: "015"
tags: [code-review, python, ecc-gap-plan]
dependencies: []
---

# Problem Statement

Second Kieran python review surfaced five small Python idiom rules that need to be bound into the plan's Phase 2/3 DoD so implementation doesn't drift. Bundled because each is a one-line rule, not its own design work.

## Findings

### 1. `invalidate_registry_cache()` should be an autouse conftest fixture, not ad-hoc teardowns

Plan says "call it in a pytest fixture teardown" but doesn't specify how. Kieran's recommendation:

```python
# tests/python/conftest.py or near phase 2 tests
@pytest.fixture(autouse=True)
def _isolate_registry_cache():
    from packages.tools.skills.loader import invalidate_registry_cache
    invalidate_registry_cache()
    yield
    invalidate_registry_cache()
```

Function-scoped, autouse — every test gets a clean slate. Session-scoped would defeat the purpose.

### 2. `from __future__ import annotations` in every new primitive + validator module

Existing primitives have it. Plan should bind it explicitly to avoid `list[DriftItem]` annotation failures on any older Python matrix.

### 3. Phase 1 → Phase 3 `PolicyViolationCode` sequencing constraint

Python's `Enum` class is closed at class-creation time. Phase 1 adds 4 enum members to `packages/policies/approvals.py`; Phase 3 adds 2 more to the same file. Both phases must edit the same file — merge-conflict risk is real but trivial. Phase 1 lands first; Phase 3 rebases. No `Enum.extend` hacks or split enums — those break `isinstance` checks.

### 4. Test parametrization style binding

Existing skill tests use `@pytest.mark.parametrize("case", _load_cases(<fixtures_dir>), ids=_case_id)`. Plan corrects filenames to `_skill.py` but doesn't specify the parametrize pattern. Bind it as Phase 1/2 DoD.

### 5. `_run_sub_check` in `verification_loop.py` is a module-level function

Existing `skill_evolution.py` uses module-level functions, not classes. Bind `_run_sub_check(skill_id: str, payload: dict[str, Any]) -> dict[str, Any]` at module scope. Keyword-only args if it grows beyond 2 params.

## Proposed Solution

One plan-doc edit adding all five rules to Phase 2/3 DoD as a bullet list under a new "Python idiom conformance" section. No code changes — just constraints on future implementation PRs.

## Acceptance Criteria

- [ ] Phase 2 DoD mentions `autouse=True` function-scoped `conftest.py` fixture for `invalidate_registry_cache()`
- [ ] Phase 2+3 DoD requires `from __future__ import annotations` in every new .py file under `packages/tools/primitives/` and `skills/canonical/**/validator.py`
- [ ] Phase 1 → Phase 3 sequencing constraint on `packages/policies/approvals.py` enum edits stated explicitly
- [ ] Phase 1+2 DoD pins test parametrization pattern to `@pytest.mark.parametrize("case", _load_cases(fixtures_dir), ids=_case_id)`
- [ ] Phase 3 DoD names `_run_sub_check` as a module-level function, not a class method

## Work Log

### 2026-04-15 - Captured during technical review
**By:** Claude (review workflow)
**Actions:** Bundled five small Python idiom rules from Kieran's second-pass review.
