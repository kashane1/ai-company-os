"""Protocol-based primitive contracts (ECC Gap Recommendations todo 008).

Phase 3's `test_primitive_contracts_pinned.py` needs a way to assert
the surface `verification-loop` consumes cannot be broken silently.
Rather than pin exact `inspect.signature` equality (which breaks on
any additive change — even a new keyword-only arg with a default),
we define `@runtime_checkable` Protocols here. Tests use
`isinstance(primitive_module, ProtocolClass)` which:

- Tolerates additive changes (new kwargs with defaults).
- Breaks on rename, removal, narrowing.
- Is cheap at runtime.

Per the primitives convention this module only defines types — no
state, no I/O, no imports of other primitive modules that could
trigger heavy work.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class RegistryDriftChecker(Protocol):
    """Shape `verification-loop` expects from `registry_drift`.

    The skill composes `check_drift(registry_path=None)` and consumes
    `StocktakeReport` from the returned mapping. `run(payload)` is the
    validator entry point that the skill-loader invokes.
    """

    def check_drift(self, registry_path: Path | None = None) -> dict[str, Any]:
        ...


@runtime_checkable
class TokenCounter(Protocol):
    """Shape `verification-loop` expects from `context_budget`.

    `count_tokens(text)` returns an int. `count_by_lane(registry_path)`
    returns a per-lane total mapping.
    """

    def count_tokens(self, text: str) -> int:
        ...

    def count_by_lane(
        self, registry_path: Path | None = None
    ) -> dict[str, Any]:
        ...
