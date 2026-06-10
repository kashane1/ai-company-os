from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from apps.api.main import app
from packages.agency import outreach_actions, outreach_lane, outreach_store
from packages.agency.outreach_lane import refresh_client_status


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    records_root = tmp_path / "records"
    lane_root = tmp_path / "lane"
    records_root.mkdir()
    record = {
        "place_id": "p1",
        "display_name": "Joe Auto",
        "phone": "+15035550000",
        "city_id": "los_angeles",
        "genre_id": "auto_repair",
        "composite_cohort": "A_gold",
        "user_ratings_total": 40,
        "mockup_url": "https://preview-p1.example.test",
        "mockup_version": "v2-bespoke",
    }
    (records_root / "p1.json").write_text(json.dumps(record))
    refresh_client_status(records_root=records_root, lane_root=lane_root)

    monkeypatch.setattr(outreach_actions, "default_outreach_lane_root", lambda *a, **k: lane_root)
    monkeypatch.setattr(outreach_lane, "default_outreach_lane_root", lambda *a, **k: lane_root)
    monkeypatch.setattr(
        outreach_store, "default_outreach_db_path", lambda *a, **k: tmp_path / "o.sqlite3"
    )
    return TestClient(app)


def test_panel_html_renders(client: TestClient) -> None:
    res = client.get("/dashboard/outreach")
    assert res.status_code == 200
    assert "Joe Auto" in res.text


def test_contact_edit_then_touch_then_status(client: TestClient) -> None:
    data = client.get("/dashboard/outreach/data").json()
    email = next(b for b in data["rows"][0]["buttons"] if b["channel"] == "email")
    assert email["enabled"] is False  # no email scanned

    assert client.post(
        "/dashboard/outreach/contact",
        json={"place_id": "p1", "field": "contact_email", "value": "joe@example.com"},
    ).status_code == 200

    data = client.get("/dashboard/outreach/data").json()
    email = next(b for b in data["rows"][0]["buttons"] if b["channel"] == "email")
    assert email["enabled"] is True

    touch = client.post(
        "/dashboard/outreach/touch", json={"place_id": "p1", "channel": "email"}
    )
    assert touch.status_code == 200
    assert touch.json()["status"] == "sent"

    assert client.post(
        "/dashboard/outreach/status", json={"place_id": "p1", "status": "replied"}
    ).status_code == 200
    data = client.get("/dashboard/outreach/data").json()
    assert data["rows"][0]["status"] == "replied"


def test_bad_channel_is_rejected(client: TestClient) -> None:
    res = client.post("/dashboard/outreach/touch", json={"place_id": "p1", "channel": "telegram"})
    assert res.status_code == 400
