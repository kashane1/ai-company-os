from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from apps.api.control_plane import ControlPlaneService
from packages.config.settings import TEST_REPO_ROOT_ENV_VAR, ensure_runtime_directories
from packages.schemas.task_packet import WorkerLane


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv(TEST_REPO_ROOT_ENV_VAR, str(tmp_path))
    ensure_runtime_directories()
    from apps.api.dashboard_endpoint import router

    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def _seed() -> None:
    service = ControlPlaneService()
    goal = service.create_goal(title="Operate", summary="Run the system.")
    service.create_task_for_goal(
        goal_id=goal.id,
        repo_id="ai-company-os",
        lane=WorkerLane.ENGINEERING,
        title="Inspect queue",
        summary="Make the queue visible.",
        task_type="engineering_change",
    )


def test_dashboard_html_renders_control_plane_state(client: TestClient) -> None:
    _seed()

    resp = client.get("/dashboard")

    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    assert "Inspect queue" in resp.text
    assert "engineering" in resp.text


def test_dashboard_data_returns_json(client: TestClient) -> None:
    _seed()

    resp = client.get("/dashboard/data")

    assert resp.status_code == 200
    body = resp.json()
    assert body["queued_tasks"] == 1
    assert body["tasks"][0]["title"] == "Inspect queue"
