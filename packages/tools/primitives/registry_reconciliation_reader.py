"""Registry reconciliation reader (ECC Gap Recommendations Phase 3).

Re-exports `reconcile_registry()` from `packages.tools.skills.reconciliation`
so the primitives directory is a complete index of agent-callable
readers. This is a single-line import, not a logic duplication —
the reconciliation implementation stays authoritative in its original
location. (Agent-native reviewer finding #7.)

Callers that want the reconciliation report as data should use this
reader. Callers that want the reconciliation gate with a raise on
drift should continue to invoke `reconcile_registry()` directly or
go through the existing test.
"""
from __future__ import annotations

from packages.tools.skills.reconciliation import (
    ReconciliationReport,
    reconcile_registry,
)


def read() -> ReconciliationReport:
    """Return a fresh `ReconciliationReport` on the current registry."""
    return reconcile_registry()
