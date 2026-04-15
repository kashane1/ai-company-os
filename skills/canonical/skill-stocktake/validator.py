"""skill-stocktake validator (ECC Gap Recommendations Phase 2a).

Thin wrapper around `packages.tools.primitives.registry_drift.run()`
so the skill-loader path (`load_validator()`) can discover this
module via the existing `validator.py` convention. All the drift
logic lives in the primitive so that `verification-loop` and other
composers can import it directly without going through the loader.
"""
from __future__ import annotations

from typing import Any

from packages.tools.primitives.registry_drift import run as _run


def run(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """Stocktake entry point — returns `{verdict, report, drift_count}`."""
    return _run(payload)
