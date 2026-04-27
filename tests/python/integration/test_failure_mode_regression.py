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


def test_happy_path_emits_postmortem_stub(tmp_path: Path):
    """Phase 2: capturing a fixture also writes a PostMortem stub."""
    validator = _load()
    fixtures_root = tmp_path / "fixtures"
    postmortems_root = tmp_path / "postmortems"
    out = validator.run(
        {
            "failure_code": "needs_followup",
            "lane": "engineering",
            "excerpt": "boom",
            "payload": {},
            "fixtures_root": str(fixtures_root),
            "postmortems_root": str(postmortems_root),
            "now": "2026-04-27T08:00:00+00:00",
        }
    )
    assert out["verdict"] == "ok"
    # One stub written under postmortems_root.
    stubs = [p for p in postmortems_root.glob("*.json") if p.name != "index.json"]
    assert len(stubs) == 1
    body = json.loads(stubs[0].read_text())
    assert body["failure_code"] == "needs_followup"
    assert body["status"] == "open"
    assert body["root_cause_category"] == "unknown"
    assert body["lane"] == "engineering"


def test_postmortem_dedup_within_window(tmp_path: Path):
    """Two captures within 24h for the same code do not produce two stubs."""
    validator = _load()
    fixtures_root = tmp_path / "fixtures"
    postmortems_root = tmp_path / "postmortems"
    args = dict(
        failure_code="dup_code",
        lane="engineering",
        excerpt="x",
        payload={},
        fixtures_root=str(fixtures_root),
        postmortems_root=str(postmortems_root),
    )
    validator.run({**args, "now": "2026-04-27T08:00:00+00:00"})
    # Force-allow second fixture by using a different code entry; we are
    # specifically testing postmortem dedup here, not fixture dedup. The
    # dedup mechanism is the O_EXCL lockfile on (failure_code).
    # First call took the lock; second call's lock attempt should skip.
    # Inject second emit directly via the same code by deleting the
    # fixture index dedup so the validator runs the fixture write again.
    (fixtures_root / "index.json").unlink()
    out = validator.run({**args, "now": "2026-04-27T08:30:00+00:00"})
    assert out["verdict"] == "ok"
    # Should still only be one stub — postmortem dedup held.
    stubs = [p for p in postmortems_root.glob("*.json") if p.name != "index.json"]
    assert len(stubs) == 1


def test_postmortem_emit_disabled_via_env(tmp_path: Path, monkeypatch):
    """Kill-switch: AI_COMPANY_OS_DISABLE_POSTMORTEM_EMIT=1 disables stub emission."""
    monkeypatch.setenv("AI_COMPANY_OS_DISABLE_POSTMORTEM_EMIT", "1")
    validator = _load()
    fixtures_root = tmp_path / "fixtures"
    postmortems_root = tmp_path / "postmortems"
    out = validator.run(
        {
            "failure_code": "kill_switch",
            "lane": "engineering",
            "excerpt": "x",
            "payload": {},
            "fixtures_root": str(fixtures_root),
            "postmortems_root": str(postmortems_root),
            "now": "2026-04-27T08:00:00+00:00",
        }
    )
    assert out["verdict"] == "ok"
    # No stubs written.
    assert not list(postmortems_root.glob("*.json")) or all(
        p.name == "index.json" for p in postmortems_root.glob("*.json")
    )


def test_postmortem_emit_failure_does_not_break_capture(tmp_path: Path, monkeypatch):
    """If stub emission raises, parent verdict is still 'ok' with a warning."""
    from packages.db import postmortem_store

    def _boom(self, *_args, **_kwargs):
        raise RuntimeError("simulated audit log failure")

    monkeypatch.setattr(postmortem_store.PostMortemStore, "save", _boom)
    validator = _load()
    out = validator.run(
        {
            "failure_code": "graceful_fail",
            "lane": "engineering",
            "excerpt": "x",
            "payload": {},
            "fixtures_root": str(tmp_path / "fixtures"),
            "postmortems_root": str(tmp_path / "postmortems"),
            "now": "2026-04-27T08:00:00+00:00",
        }
    )
    assert out["verdict"] == "ok"
    assert "warnings" in out
    assert any("postmortem_emit_failed" in w for w in out["warnings"])


def test_postmortem_redacts_user_path_in_fixture_path(tmp_path: Path):
    """Path leakage check: fixture_path under /Users/<name>/ is sanitized."""
    validator = _load()
    fake_user_dir = tmp_path / "Users" / "alice" / "ai-company-os"
    fixtures_root = fake_user_dir / "state" / "artifacts" / "failure-fixtures"
    fixtures_root.mkdir(parents=True)
    postmortems_root = tmp_path / "postmortems"
    # The fixture validator writes into fixtures_root; the resulting
    # stored path will contain /Users/alice/. We assert the stored
    # fixture_path on the PostMortem stub is redacted.
    validator.run(
        {
            "failure_code": "leaky_path",
            "lane": "engineering",
            "excerpt": "x",
            "payload": {},
            "fixtures_root": str(fixtures_root),
            "postmortems_root": str(postmortems_root),
            "now": "2026-04-27T08:00:00+00:00",
        }
    )
    stubs = [p for p in postmortems_root.glob("*.json") if p.name != "index.json"]
    assert len(stubs) == 1
    body = json.loads(stubs[0].read_text())
    # /Users/alice/ should not appear in the stored path.
    assert "alice" not in body["fixture_path"]
    assert "[REDACTED-USER]" in body["fixture_path"]


def test_path_traversal_failure_code_is_rejected(tmp_path: Path):
    """A failure_code containing path-traversal characters is rejected at the gate."""
    validator = _load()
    out = validator.run(
        {
            "failure_code": "../../etc/evil",
            "lane": "engineering",
            "excerpt": "x",
            "payload": {},
            "fixtures_root": str(tmp_path / "fixtures"),
            "postmortems_root": str(tmp_path / "postmortems"),
            "now": "2026-04-27T08:00:00+00:00",
        }
    )
    assert out["verdict"] == "fail"
    assert out["failure_code"] == "capture_pipeline_self_failure"
    assert "unsafe_failure_code" in out["reason"]
    # No fixture files written.
    assert not list((tmp_path / "fixtures").glob("**/*.json")) if (tmp_path / "fixtures").exists() else True


def test_empty_string_optional_fields_round_trip(tmp_path: Path):
    """from_dict no longer coerces '' to None for optional string fields (kieran C1 fix)."""
    from packages.schemas.postmortem import PostMortem

    payload = {
        "id": "abc1234567",
        "created_at": "2026-04-27T10:00:00+00:00",
        "updated_at": "2026-04-27T10:00:00+00:00",
        "failure_code": "lint_failed",
        "lane": "engineering",
        "task_id": "",
        "owner": "",
    }
    pm = PostMortem.from_dict(payload)
    assert pm.task_id == ""
    assert pm.owner == ""


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
