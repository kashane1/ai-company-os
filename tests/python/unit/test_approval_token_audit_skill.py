"""Phase 3.2a — fixture-backed tests for approval-token-audit validator."""

from __future__ import annotations

import importlib.util
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parents[3]
SKILL_DIR = REPO / "skills" / "canonical" / "approval-token-audit"


def _load_validator():
    spec = importlib.util.spec_from_file_location(
        "approval_token_audit_validator", SKILL_DIR / "validator.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.run


class _FakeStore:
    def __init__(self, record: dict) -> None:
        self._record = record

    def load(self, approval_id: str) -> dict:
        return self._record


def _hydrate_record(raw: dict) -> dict:
    """Convert the ``*_offset_sec`` relative timestamps into datetimes."""
    base = datetime(2026, 4, 10, 12, 0, 0, tzinfo=timezone.utc)
    record = dict(raw)
    record["issued_at"] = base + timedelta(seconds=raw["issued_at_offset_sec"])
    record["approved_at"] = base + timedelta(seconds=raw["approved_at_offset_sec"])
    sf = raw.get("second_factor_offset_sec")
    record["second_factor_at"] = (
        base + timedelta(seconds=sf) if sf is not None else None
    )
    return record


def _load_fixture(name: str) -> dict:
    return yaml.safe_load((SKILL_DIR / "fixtures" / name).read_text())


@pytest.mark.parametrize(
    "fixture_name",
    ["happy_path.yaml", "boundary.yaml", "adversarial.yaml"],
)
def test_approval_token_audit_fixtures(fixture_name):
    run = _load_validator()
    fixture = _load_fixture(fixture_name)
    record = _hydrate_record(fixture["input"]["record"])
    payload = {
        "approval_id": fixture["input"]["approval_id"],
        "expected_action": fixture["input"]["expected_action"],
        "expected_subject_id": fixture["input"]["expected_subject_id"],
        "store": _FakeStore(record),
    }
    result = run(payload)
    exp = fixture["expected"]
    assert result["verdict"] == exp["verdict"], result
    if "reason_contains" in exp:
        assert exp["reason_contains"] in result["reason"]


def test_failclosed_on_store_exception():
    run = _load_validator()

    class Broken:
        def load(self, _):
            raise RuntimeError("store down")

    result = run(
        {
            "approval_id": "x",
            "expected_action": "submit_appstore",
            "expected_subject_id": "r1",
            "store": Broken(),
        }
    )
    assert result["verdict"] == "fail"
    assert "exception" in result["reason"]
