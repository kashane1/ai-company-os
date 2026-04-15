"""Agent-callable context-budget reader (ECC Gap Recommendations Phase 2b).

Parallel to `skill_stocktake_reader.py`. A typed `ContextBudgetReport`
producer for agents / workers / ACP peers that want the report as
data, not as a policy decision. Separate from the skill-loader path
so non-Claude callers can invoke the same measurement Claude does via
trigger phrase.
"""
from __future__ import annotations

from pathlib import Path

from packages.tools.primitives.context_budget import (
    ContextBudgetReport,
    measure,
)


def read(
    registry_path: Path | None = None, *, top_n: int = 10
) -> ContextBudgetReport:
    """Return a fresh `ContextBudgetReport` on the current registry.

    Thin wrapper over `context_budget.measure()` so the primitives
    directory indexes a reader for every validator. No caching.
    """
    return measure(registry_path=registry_path, top_n=top_n)
