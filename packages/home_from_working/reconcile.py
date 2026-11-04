"""Reporting for the read-only HomeFromWorking reconciliation registry."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def build_reconciliation_report(registry: Mapping[str, Any]) -> dict[str, Any]:
    records = list(registry.get("records", []))
    evidence = dict(registry.get("evidence", {}))
    printify_states = [record.get("live", {}).get("printify", {}).get("state") for record in records]
    etsy_states = [record.get("live", {}).get("etsy", {}).get("state") for record in records]
    blocked: dict[str, str] = {}
    if not evidence.get("printify_snapshot_supplied"):
        blocked["printify"] = "no Printify snapshot supplied"
    if not evidence.get("etsy_snapshot_supplied"):
        blocked["etsy"] = "no Etsy snapshot supplied"
    return {
        "schema_version": 1,
        "generated_at": registry.get("generated_at"),
        "source_registry_schema_version": registry.get("schema_version"),
        "summary": {
            "record_count": len(records),
            "printify_present": printify_states.count("present"),
            "printify_missing": printify_states.count("missing"),
            "printify_confirmed_missing": printify_states.count("confirmed_missing"),
            "etsy_present": etsy_states.count("present"),
            "etsy_missing": etsy_states.count("missing"),
            "etsy_only": sum("etsy_only_record" in record.get("discrepancies", []) for record in records),
            "unresolved": sum("historical_unresolved" in record.get("discrepancies", []) for record in records),
        },
        "blocked": blocked,
        "review_queue": [
            {"record_id": record["record_id"], "next_action": record["next_action"], "discrepancies": record["discrepancies"]}
            for record in records
            if record.get("discrepancies") or record.get("next_action") != "review_discrepancies"
        ],
        "automatic_actions": [],
    }
