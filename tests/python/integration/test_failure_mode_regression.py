"""Phase 4.6 — failure-mode-regression skill tests.

Exercises the dedupe window, redaction, and self-failure meta code.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from packages.tools.skills.loader import load_validator


def _load():
    return load_validator("failure-mode-regression")


def test_happy_path_writes_fixture(tmp_path: Path):
    validator = _load()
    out = validator.run(
        {
            "failure_code": "lint_failed",
            "lane": "engineering",
            "excerpt": "token=sk-abcdefghij0123456789ABCDEF boom",
            "payload": {"secret": "ghp_" + "A" * 24, "safe": "hello"},
            "fixtures_root": str(tmp_path),
            "now": "2026-04-10T08:00:00+00:00",
        }
    )
    assert out["verdict"] == "ok"
    assert out["failure_code"] == "lint_failed"
    fixture_path = Path(out["fixture_path"])
    assert fixture_path.exists()
    body = json.loads(fixture_path.read_text())
    # Credentials must be redacted
    assert "sk-abcdefghij0123456789ABCDEF" not in fixture_path.read_text()
    assert "ghp_" not in body["payload"].get("secret", "")
    assert body["redaction_hits"] >= 2
    # Index must be updated
    idx = json.loads((tmp_path / "index.json").read_text())
    assert idx["lint_failed"]["count"] == 1


def test_dedupe_within_window(tmp_path: Path):
    validator = _load()
    validator.run(
        {
            "failure_code": "duped",
            "lane": "gtm",
            "excerpt": "first",
            "payload": {},
            "fixtures_root": str(tmp_path),
            "now": "2026-04-10T08:00:00+00:00",
        }
    )
    second = validator.run(
        {
            "failure_code": "duped",
            "lane": "gtm",
            "excerpt": "second",
            "payload": {},
            "fixtures_root": str(tmp_path),
            "now": "2026-04-10T12:00:00+00:00",
        }
    )
    assert second["verdict"] == "skipped"
    assert second["fixture_path"] == ""


def test_capture_after_window(tmp_path: Path):
    validator = _load()
    validator.run(
        {
            "failure_code": "stale",
            "lane": "ios",
            "excerpt": "first",
            "payload": {},
            "fixtures_root": str(tmp_path),
            "now": "2026-04-09T08:00:00+00:00",
        }
    )
    later = validator.run(
        {
            "failure_code": "stale",
            "lane": "ios",
            "excerpt": "second",
            "payload": {},
            "fixtures_root": str(tmp_path),
            "now": "2026-04-10T09:00:00+00:00",
        }
    )
    assert later["verdict"] == "ok"


def test_self_failure_does_not_recurse(tmp_path: Path):
    validator = _load()
    # failure_code is required — passing None through raises KeyError.
    out = validator.run(
        {
            "lane": "engineering",
            "excerpt": "",
            "payload": {},
            "fixtures_root": str(tmp_path),
            "now": "2026-04-10T08:00:00+00:00",
        }
    )
    assert out["verdict"] == "fail"
    assert out["failure_code"] == "capture_pipeline_self_failure"
    # No fixture file should have been written.
    assert not any(tmp_path.glob("*.json")) or (tmp_path / "index.json").exists() is False
