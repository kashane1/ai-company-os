from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from packages.home_from_working.reconcile import build_reconciliation_report


RECEIPT_ROOTS = [
    Path("state/home-from-working/multi-product-listings"),
    Path("state/home-from-working/multi-product-listings-10color"),
]
# Runtime state under state/ is git-ignored, so this check runs only on the operator Mac.
requires_local_state = pytest.mark.skipif(
    not all(root.exists() for root in RECEIPT_ROOTS),
    reason="requires local HomeFromWorking runtime state",
)


def _reconcile_script():
    path = Path("scripts/home_from_working_reconcile.py")
    spec = importlib.util.spec_from_file_location("home_from_working_reconcile_script", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@requires_local_state
def test_default_receipt_discovery_covers_both_known_roots_without_duplicates() -> None:
    script = _reconcile_script()

    paths = script.receipt_paths(script.DEFAULT_RECEIPT_ROOTS)

    assert paths == sorted(paths)
    assert len(paths) == len(set(paths))
    assert {path.parents[1].name for path in paths} == {
        "multi-product-listings",
        "multi-product-listings-10color",
    }


def test_report_counts_and_marks_absent_live_evidence_blocked() -> None:
    registry = {
        "generated_at": "2026-09-06T00:00:00Z",
        "records": [
            {
                "record_id": "a/one",
                "local": {"state": "historical"},
                "live": {"printify": {"state": "unknown"}, "etsy": {"state": "unknown"}},
                "discrepancies": [],
                "next_action": "supply_live_snapshots",
            },
            {
                "record_id": "banana-berries-20260902/banana-berries-1",
                "local": {"state": "historical"},
                "live": {"printify": {"state": "confirmed_missing"}, "etsy": {"state": "unknown"}},
                "discrepancies": ["historical_unresolved"],
                "next_action": "do_not_recreate_automatically",
            },
        ],
        "evidence": {"etsy_snapshot_supplied": False, "printify_snapshot_supplied": True},
    }

    report = build_reconciliation_report(registry)

    assert report["summary"]["record_count"] == 2
    assert report["summary"]["printify_confirmed_missing"] == 1
    assert report["blocked"]["etsy"] == "no Etsy snapshot supplied"
    assert report["automatic_actions"] == []
