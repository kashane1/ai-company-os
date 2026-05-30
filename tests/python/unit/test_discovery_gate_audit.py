"""Tests for D4 — discovery gate decisions persisted to the approvals store."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from packages.config.settings import TEST_REPO_ROOT_ENV_VAR, ensure_runtime_directories
from packages.db.approval_store import ApprovalStore
from packages.discovery.gate_audit import GateDecisionRecorder
from packages.policies.approvals import PolicyViolation, PolicyViolationCode
from packages.schemas.approval import ApprovalStatus
from packages.schemas.experiment import (
    ExperimentCompliance,
    ExperimentMetric,
    ExperimentRecord,
    ExperimentStatus,
    ExperimentType,
    SuccessCriteria,
)

FIXED = datetime(2026, 5, 29, tzinfo=timezone.utc)


@pytest.fixture
def recorder(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> GateDecisionRecorder:
    monkeypatch.setenv(TEST_REPO_ROOT_ENV_VAR, str(tmp_path))
    ensure_runtime_directories()
    counter = {"n": 0}

    def ids() -> str:
        counter["n"] += 1
        return f"appr_{counter['n']}"

    return GateDecisionRecorder(ApprovalStore(), now=lambda: FIXED, id_factory=ids)


def test_bulk_crawl_approval_is_persisted(recorder: GateDecisionRecorder) -> None:
    record = recorder.record_bulk_crawl(
        source_id="hackernews", approved_by="kashane", robots_checked=True, rate_limited=True
    )
    assert record.status is ApprovalStatus.APPROVED
    assert record.action == "discovery_bulk_crawl"
    # It's replayable: load it straight back from the store.
    reloaded = ApprovalStore().load(record.id)
    assert reloaded.status is ApprovalStatus.APPROVED
    assert reloaded.subject_id == "hackernews"
    assert reloaded.decided_by == "kashane"


def test_bulk_crawl_block_persists_rejection_and_reraises(recorder: GateDecisionRecorder) -> None:
    with pytest.raises(PolicyViolation):
        recorder.record_bulk_crawl(
            source_id="hackernews", approved_by=None, robots_checked=True, rate_limited=True
        )
    # A rejection was still recorded for the audit trail.
    rejected = ApprovalStore().load("appr_1")
    assert rejected.status is ApprovalStatus.REJECTED
    notes = rejected.decision_notes or ""
    assert PolicyViolationCode.DISCOVERY_BULK_CRAWL_NOT_APPROVED.value in notes


def _outreach_experiment(compliance: ExperimentCompliance | None) -> ExperimentRecord:
    return ExperimentRecord(
        id="exp_1",
        opportunity_id="opp_1",
        type=ExperimentType.COLD_OUTREACH,
        hypothesis="people reply",
        success_criteria=SuccessCriteria(metric=ExperimentMetric.REPLY_RATE, threshold=0.1),
        status=ExperimentStatus.APPROVED,
        compliance=compliance,
    )


def test_outreach_approval_is_persisted(recorder: GateDecisionRecorder) -> None:
    compliance = ExperimentCompliance(
        reviewed_by="compliance-1", unsubscribe_wired=True, suppression_checked=True
    )
    record = recorder.record_outreach(_outreach_experiment(compliance))
    assert record.status is ApprovalStatus.APPROVED
    assert record.subject_id == "exp_1"
    assert record.decided_by == "compliance-1"
    assert ApprovalStore().load(record.id).action == "discovery_outreach"


def test_outreach_block_persists_rejection_and_reraises(recorder: GateDecisionRecorder) -> None:
    with pytest.raises(PolicyViolation):
        recorder.record_outreach(_outreach_experiment(None))  # not compliance-reviewed
    rejected = ApprovalStore().load("appr_1")
    assert rejected.status is ApprovalStatus.REJECTED
    notes = rejected.decision_notes or ""
    assert PolicyViolationCode.DISCOVERY_OUTREACH_NOT_REVIEWED.value in notes
