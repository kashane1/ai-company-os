"""context-budget validator (ECC Gap Recommendations Phase 2b).

Thin wrapper around
`packages.tools.primitives.context_budget.run()`. All counting logic
lives in the primitive so `verification-loop` (Phase 3) and other
composers can import it directly without going through the loader.
"""
from __future__ import annotations

from typing import Any

from packages.tools.primitives.context_budget import run as _run


def run(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """Context-budget entry point — returns `{verdict: "pass", report}`."""
    return _run(payload)
