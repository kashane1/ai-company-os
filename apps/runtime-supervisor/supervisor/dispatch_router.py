"""Runtime supervisor — target_runtime → Provider resolution call-site.

HARD LOC BUDGET: this module must stay ≤ 50 LOC (excluding docstrings
and blank lines). The budget is enforced by
`tests/python/unit/test_dispatch_router_loc_budget.py`.

Routing POLICY (which provider to use, feature-flag checks, fallback
order, peer allowlist) lives in `packages/policies/provider_resolution.py`
— NOT here. This module is a thin call-site that:

1. Asks the policy which provider slug to use for a given task.
2. Calls `providers.resolve(slug).execute(task)` and returns the result.

Phase 4 (ACP adapter) and Phase 6 (provider overlay) both touch this
module for call-site wiring only. Any PR that grows it past the LOC
budget is a red flag and must move logic into policies or providers.

Phase 0.5c ships this module as a placeholder stub so the three-file
split can land as a pure refactor. Actual dispatch routing wiring
comes in Phases 4 and 6.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from packages.schemas.task_packet import TaskPacket


def route_task(task: "TaskPacket") -> str:
    """Resolve the provider slug for a task.

    Phase 0.5c: stub that returns the legacy default "claude" so
    existing dispatch behavior is unchanged. Phase 4 wires this to
    `packages/policies/provider_resolution.py:resolve_provider()`
    which reads `TaskPacket.provider_hint` and falls back to the
    skill's `target_runtimes`.
    """
    # Phase 0.5c placeholder — Phases 4+6 replace with real routing.
    return "claude"
