"""Agent-callable stocktake reader (ECC Gap Recommendations Phase 2a).

Parallel to the Hermes plan's `dispatch_health_reader.py`. A typed
`StocktakeReport` producer that agents / workers / ACP peers can call
without going through the skill-loader path.

Use this when you want the report as data, not as a policy decision.
The skill-loader path is for CI wiring + trigger-phrase invocations;
this reader is for direct programmatic access.
"""
from __future__ import annotations

from pathlib import Path

from packages.tools.primitives.registry_drift import (
    StocktakeReport,
    check_drift,
)


def read(
    registry_path: Path | None = None,
    *,
    known_drift: tuple[str, ...] = (),
) -> StocktakeReport:
    """Return a fresh `StocktakeReport` on the current repo state.

    Thin wrapper over `registry_drift.check_drift()` so the primitives
    directory is a complete index of agent-callable readers. No
    caching — each call re-parses the registry and re-walks the
    canonical tree.
    """
    return check_drift(
        registry_path=registry_path, known_drift=known_drift
    )
