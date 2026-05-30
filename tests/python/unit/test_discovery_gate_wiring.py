"""Tests for E5 — gates enforced at the point of action.

* bulk runs in the run controller require the bulk-crawl gate to pass;
* a sending experiment can't reach `running` without the outreach gate.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from packages.config.settings import TEST_REPO_ROOT_ENV_VAR, ensure_runtime_directories
from packages.db.approval_store import ApprovalStore
from packages.db.experiment_store import ExperimentStore
from packages.discovery.connectors.base import ConnectorConfig, FetchOptions, RawSignal
from packages.discovery.gate_audit import GateDecisionRecorder, start_sending_experiment
from packages.discovery.inbox import OpportunityInbox
from packages.discovery.run import DiscoveryRunStatus, run_discovery
from packages.policies.approvals import PolicyViolation
from packages.schemas.approval import ApprovalStatus
from packages.schemas.experiment import (
    ExperimentCompliance,
    ExperimentMetric,
    ExperimentRecord,
    ExperimentStatus,
    ExperimentType,
    SuccessCriteria,
)
from packages.schemas.opportunity import EvidenceKind

FIXED = datetime(2026, 5, 29, tzinfo=timezone.utc)


class RecordingConnector:
    """Captures the FetchOptions it received so we can assert authorization."""

    def __init__(self, cid: str) -> None:
        self.id = cid
        self.config = ConnectorConfig(id=cid)
        self.last_options: FetchOptions | None = None

    def fetch(self, options: FetchOptions) -> list[RawSignal]:
        self.last_options = options
        return [RawSignal(text="tool", url="https://x/1", kind=EvidenceKind.REQUEST)]

    def healthcheck(self) -> tuple[bool, str]:
        return (True, "")


def _inbox(tmp_path: Path) -> OpportunityInbox:
    return OpportunityInbox(root=tmp_path / "opps", now=lambda: FIXED)


# ── C1: bulk runs are gated in the run controller ──────────────────────────────


def test_bulk_run_blocked_without_approval(tmp_path: Path) -> None:
    connector = RecordingConnector("hackernews")
    with pytest.raises(PolicyViolation):
        run_discovery(
            inbox=_inbox(tmp_path), connectors={"hackernews": connector},
            queries=["q"], bulk=True, bulk_approved_by=None, now=lambda: FIXED,
        )
    assert connector.last_options is None  # nothing fetched while the gate is closed


def test_bulk_run_authorized_passes_authorized_flag(tmp_path: Path) -> None:
    connector = RecordingConnector("hackernews")
    report = run_discovery(
        inbox=_inbox(tmp_path), connectors={"hackernews": connector},
        queries=["q"], bulk=True, bulk_approved_by="kashane", now=lambda: FIXED,
    )
    assert report.status == DiscoveryRunStatus.COMPLETED
    assert connector.last_options.bulk is True
    assert connector.last_options.authorized is True  # gate passed -> authorized


def test_non_bulk_run_is_not_authorized(tmp_path: Path) -> None:
    connector = RecordingConnector("hackernews")
    run_discovery(
        inbox=_inbox(tmp_path), connectors={"hackernews": connector},
        queries=["q"], now=lambda: FIXED,
    )
    assert connector.last_options.bulk is False
    assert connector.last_options.authorized is False


def test_bulk_run_uses_recorder_when_provided(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(TEST_REPO_ROOT_ENV_VAR, str(tmp_path))
    ensure_runtime_directories()
    recorder = GateDecisionRecorder(ApprovalStore(), now=lambda: FIXED, id_factory=lambda: "appr_1")
    connector = RecordingConnector("hackernews")

    run_discovery(
        inbox=OpportunityInbox(root=tmp_path / "opps", now=lambda: FIXED),
        connectors={"hackernews": connector},
        queries=["q"],
        bulk=True,
        authorize_bulk=lambda: recorder.record_bulk_crawl(
            source_id="hackernews", approved_by="kashane", robots_checked=True, rate_limited=True
        ),
        now=lambda: FIXED,
    )
    # The bulk decision was recorded for the audit trail.
    assert ApprovalStore().load("appr_1").status is ApprovalStatus.APPROVED


# ── C3: outreach gated at experiment start ─────────────────────────────────────


def _experiment(compliance: ExperimentCompliance | None) -> ExperimentRecord:
    return ExperimentRecord(
        id="exp_1",
        opportunity_id="opp_1",
        type=ExperimentType.COLD_OUTREACH,
        hypothesis="people reply",
        success_criteria=SuccessCriteria(metric=ExperimentMetric.REPLY_RATE, threshold=0.1),
        status=ExperimentStatus.APPROVED,
        compliance=compliance,
        created_at="2026-05-29T00:00:00+00:00",
    )


@pytest.fixture
def store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> ExperimentStore:
    monkeypatch.setenv(TEST_REPO_ROOT_ENV_VAR, str(tmp_path))
    ensure_runtime_directories()
    return ExperimentStore()


def test_start_sending_experiment_transitions_when_compliant(store: ExperimentStore) -> None:
    compliance = ExperimentCompliance(
        reviewed_by="c", unsubscribe_wired=True, suppression_checked=True
    )
    store.save(_experiment(compliance))
    running = start_sending_experiment(store, "exp_1")
    assert running.status is ExperimentStatus.RUNNING


def test_start_sending_experiment_blocks_when_not_reviewed(store: ExperimentStore) -> None:
    store.save(_experiment(None))
    with pytest.raises(PolicyViolation):
        start_sending_experiment(store, "exp_1")
    # The experiment never reached running.
    assert store.get("exp_1").status is ExperimentStatus.APPROVED
