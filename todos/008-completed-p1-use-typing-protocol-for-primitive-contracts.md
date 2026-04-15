---
status: completed
priority: p1
issue_id: "008"
tags: [code-review, python, testing, ecc-gap-plan]
dependencies: []
---

# Problem Statement

The plan's Phase 3 adds `tests/python/unit/test_primitive_contracts_pinned.py` asserting the exact signatures `verification-loop` imports from `packages/tools/primitives/registry_drift.py` and `context_budget.py`. But `inspect.signature` equality is brittle across keyword-only reordering, default-value formatting, and `from __future__ import annotations` string-vs-object drift. The test will false-positive on safe extensions (adding a new keyword-only arg with a default) while missing real breaks. The right primitive for "lock an import surface" is `typing.Protocol`, not signature introspection.

## Findings

- Architecture strategist second pass finding #1: "Python signature assertion is brittle — keyword-only args, default values, return annotations all drift. Define a `typing.Protocol` in `packages/tools/primitives/_contracts.py`, have primitives structurally satisfy it, and assert `isinstance`-via-`runtime_checkable` plus a frozen set of required attribute names."
- Simplicity reviewer second pass finding #2: wanted to delete this test entirely as change-detector testing. Protocol-based approach is the compromise: keeps the intent (lock the contract verification-loop imports) while shedding the brittleness.

## Proposed Solutions

### Option 1: `typing.Protocol` with `runtime_checkable`

New file `packages/tools/primitives/_contracts.py` defines:
```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class RegistryDriftChecker(Protocol):
    def check_drift(self, registry_path: Path | None = None) -> list[DriftItem]: ...

@runtime_checkable
class TokenCounter(Protocol):
    def count_tokens(self, text: str) -> tuple[int, str]: ...
```

`test_primitive_contracts_pinned.py` asserts the concrete functions satisfy the Protocol at import time. Structural typing tolerates safe extensions; breaks on rename/removal/narrowing.

Pros:
- Idiomatic Python 3.8+
- Self-documenting — the Protocol IS the contract
- Tolerates additive changes
- Catches real breaks
- `runtime_checkable` gives `isinstance()` semantics for the test

Cons:
- One new file

Effort: small
Risk: low

### Option 2: Delete the test entirely

Drop `test_primitive_contracts_pinned.py`. Rely on the fact that Phase 2 and Phase 3 ship sequentially with a functioning CI, and that any signature break will manifest as a Phase 3 test failure on the next push.

Pros:
- Zero code
- Simplicity reviewer preference

Cons:
- Silent break between Phase 2 refactor and Phase 3 test run
- Architecture strategist's Phase-2-to-Phase-3 drift channel stays open

Effort: trivial
Risk: medium

## Recommended Action

Option 1. Replace the signature-introspection approach with `typing.Protocol` before Phase 3 PR starts. New file lives alongside existing primitives.

## Acceptance Criteria

- [ ] `packages/tools/primitives/_contracts.py` defines `RegistryDriftChecker` and `TokenCounter` as `@runtime_checkable` Protocols
- [ ] `tests/python/unit/test_primitive_contracts_pinned.py` uses `isinstance(primitive, ProtocolClass)` assertions, not `inspect.signature` equality
- [ ] Test passes against the Phase 2 primitives
- [ ] Test fails if any protocol method is renamed, removed, or has a required arg added
- [ ] Test passes if a new keyword-only arg with default is added (proving tolerance)
- [ ] Plan document updated to cite Protocol approach in Phase 3 DoD

## Work Log

### 2026-04-15 - Captured during technical review
**By:** Claude (review workflow)
**Actions:** Architecture strategist and simplicity reviewer converged on Protocol as the right primitive; replaces the signature-pinning approach.
