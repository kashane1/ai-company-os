from __future__ import annotations

import json
from pathlib import Path

import pytest

from packages.agency.outreach_store import OutreachStore


def _store(tmp_path: Path) -> OutreachStore:
    return OutreachStore(sqlite_path=tmp_path / "outreach.sqlite3")


def test_append_and_summarize_touches(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.append_touch("p1", "email", sent_at="2026-06-01T00:00:00Z")
    store.append_touch("p1", "email", sent_at="2026-06-03T00:00:00Z")
    store.append_touch("p1", "sms", sent_at="2026-06-02T00:00:00Z")

    touches = store.list_touches("p1")
    assert [t["channel"] for t in touches] == ["email", "sms", "email"]

    summary = store.touch_summary()
    assert summary["p1"]["email"] == {"count": 2, "last_sent_at": "2026-06-03T00:00:00Z"}
    assert summary["p1"]["sms"]["count"] == 1


def test_append_touch_rejects_unknown_channel(tmp_path: Path) -> None:
    store = _store(tmp_path)
    with pytest.raises(ValueError):
        store.append_touch("p1", "carrier_pigeon")


def test_override_upserts_and_reads(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.set_override("p1", "contact_email", "a@example.com")
    store.set_override("p1", "contact_email", "b@example.com")  # overwrite
    store.set_override("p1", "phone", "+15035551234")

    assert store.get_overrides("p1") == {
        "contact_email": "b@example.com",
        "phone": "+15035551234",
    }
    assert store.all_overrides()["p1"]["contact_email"] == "b@example.com"


def test_override_rejects_unknown_field(tmp_path: Path) -> None:
    store = _store(tmp_path)
    with pytest.raises(ValueError):
        store.set_override("p1", "ssn", "nope")


def test_import_legacy_jsonl_normalizes_channels(tmp_path: Path) -> None:
    legacy = tmp_path / "touches.jsonl"
    legacy.write_text(
        "\n".join(
            json.dumps(row)
            for row in [
                {"place_id": "p1", "channel": "instagram", "occurred_at": "2026-05-01T00:00:00Z"},
                {"place_id": "p1", "channel": "phone", "occurred_at": "2026-05-02T00:00:00Z"},
                {"place_id": "", "channel": "email"},  # skipped: no place_id
                {"channel": "email"},  # skipped: no place_id
            ]
        )
        + "\n"
    )
    store = _store(tmp_path)
    imported = store.import_legacy_jsonl(legacy)
    assert imported == 2
    summary = store.touch_summary()
    assert "instagram_dm" in summary["p1"]
    assert "call" in summary["p1"]


def test_import_legacy_jsonl_missing_file_is_noop(tmp_path: Path) -> None:
    store = _store(tmp_path)
    assert store.import_legacy_jsonl(tmp_path / "absent.jsonl") == 0
