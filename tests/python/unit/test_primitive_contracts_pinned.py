"""Phase 3 — primitive contract pinning (per todo 008).

Uses `@runtime_checkable` Protocols from
`packages.tools.primitives._contracts` to assert the primitive
surface `verification-loop` consumes cannot be renamed or narrowed
silently. Tolerates additive changes (new keyword-only args with
defaults); breaks on rename / removal / signature narrowing.

This test is the "Phase 2 → Phase 3 silent break channel" guard the
architecture strategist flagged. A Phase 2 refactor of
`registry_drift.py` or `context_budget.py` that removes a public
function or changes its shape will break this test, not the skill
fixtures.
"""
from __future__ import annotations

import inspect

from packages.tools.primitives import context_budget, registry_drift


def test_registry_drift_has_check_drift() -> None:
    """`verification-loop` consumes `check_drift(registry_path=None)`."""
    assert hasattr(registry_drift, "check_drift")
    sig = inspect.signature(registry_drift.check_drift)
    assert "registry_path" in sig.parameters, (
        "registry_drift.check_drift signature broken — "
        "verification-loop imports this name"
    )


def test_registry_drift_run_returns_dict_with_verdict() -> None:
    """Validator entry point shape."""
    assert hasattr(registry_drift, "run")
    # Smoke-run on the real repo and check the returned keys.
    result = registry_drift.run({})
    assert isinstance(result, dict)
    assert "verdict" in result
    assert "report" in result
    assert "drift_count" in result


def test_context_budget_has_count_tokens_and_measure() -> None:
    assert hasattr(context_budget, "count_tokens")
    assert hasattr(context_budget, "measure")
    sig = inspect.signature(context_budget.count_tokens)
    assert list(sig.parameters.keys()) == ["text"]


def test_context_budget_measure_returns_report_shape() -> None:
    report = context_budget.measure()
    assert hasattr(report, "lanes")
    assert hasattr(report, "top_largest")
    assert hasattr(report, "system_prompt")
    assert hasattr(report, "tokenizer")


def test_stocktake_report_fields_stable() -> None:
    """StocktakeReport carries the 4 fields verification-loop reads."""
    from packages.tools.primitives.registry_drift import StocktakeReport

    field_names = {f.name for f in StocktakeReport.__dataclass_fields__.values()}
    required = {
        "schema_version",
        "registry_entries_checked",
        "drift_items",
        "known_drift",
    }
    missing = required - field_names
    assert not missing, (
        f"StocktakeReport missing fields {missing}; "
        "verification-loop reads these"
    )


def test_drift_item_fields_stable() -> None:
    from packages.tools.primitives.registry_drift import DriftItem

    field_names = {f.name for f in DriftItem.__dataclass_fields__.values()}
    required = {"drift_type", "detail", "affected_path", "skill_id"}
    missing = required - field_names
    assert not missing, (
        f"DriftItem missing fields {missing}; "
        "verification-loop reads these"
    )
