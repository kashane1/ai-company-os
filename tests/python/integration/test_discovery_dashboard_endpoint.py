"""Integration test for the discovery dashboard endpoint (D3).

Mounts only the discovery router on a bare FastAPI app (independent of the full
control-plane app) and drives it with a TestClient against an isolated
control-plane DB, so it verifies the HTTP + store wiring without touching the
heavier control-plane service.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from packages.config.settings import TEST_REPO_ROOT_ENV_VAR, ensure_runtime_directories
from packages.db.discovery_run_store import DiscoveryRunRecordStore
from packages.db.opportunity_store import OpportunityStore
from packages.discovery.run import DiscoveryRunReport, DiscoveryRunStatus
from packages.schemas.opportunity import (
    EvidenceKind,
    EvidenceLink,
    OpportunityRecord,
    OpportunityStatus,
    SourceRef,
)


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv(TEST_REPO_ROOT_ENV_VAR, str(tmp_path))
    ensure_runtime_directories()
    from apps.api.discovery_endpoint import router

    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def _seed() -> None:
    OpportunityStore().save(OpportunityRecord(
        id="opp1",
        title="Automate invoice reminders",
        problem="p",
        audience="freelancers",
        source=SourceRef(connector="hackernews", query="q"),
        status=OpportunityStatus.SCORED,
        evidence=[EvidenceLink(url="https://news.ycombinator.com/item?id=1",
                               kind=EvidenceKind.REQUEST)],
        score=77.0,
        confidence=0.8,
        created_at="2026-05-29T00:00:00+00:00",
        updated_at="2026-05-29T00:00:00+00:00",
    ))
    DiscoveryRunRecordStore().save(DiscoveryRunReport(
        run_id="run_1",
        status=DiscoveryRunStatus.COMPLETED,
        queries=["invoice"],
        sources=["hackernews"],
        signals_ingested=4,
        sources_hit={"hackernews": 4},
        started_at="2026-05-30T11:00:00+00:00",
        finished_at="2026-05-30T11:05:00+00:00",
    ))


def test_html_panel_renders_seeded_state(client: TestClient) -> None:
    _seed()
    resp = client.get("/discovery")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    assert "Automate invoice reminders" in resp.text
    assert "run_1" in resp.text


def test_data_endpoint_returns_json(client: TestClient) -> None:
    _seed()
    resp = client.get("/discovery/data")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_opportunities"] == 1
    assert body["latest_run"]["run_id"] == "run_1"
    assert body["inbox"][0]["title"] == "Automate invoice reminders"


def test_empty_state_is_ok(client: TestClient) -> None:
    resp = client.get("/discovery")
    assert resp.status_code == 200
    assert "Inbox is empty" in resp.text
