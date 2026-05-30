"""Tests for the DB-backed opportunity + experiment stores.

Each test gets an isolated repo root so the control-plane SQLite file lives in
tmp, never the real state/ tree.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from packages.config.settings import TEST_REPO_ROOT_ENV_VAR, ensure_runtime_directories
from packages.db.experiment_store import (
    ExperimentStore,
    InvalidExperimentTransition,
    is_valid_transition,
)
from packages.db.opportunity_store import OpportunityStore
from packages.schemas.experiment import (
    ExperimentMetric,
    ExperimentRecord,
    ExperimentStatus,
    ExperimentType,
    SuccessCriteria,
)
from packages.schemas.opportunity import (
    EvidenceKind,
    EvidenceLink,
    OpportunityRecord,
    OpportunitySignals,
    OpportunityStatus,
    SourceRef,
)


@pytest.fixture
def isolated(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv(TEST_REPO_ROOT_ENV_VAR, str(tmp_path))
    ensure_runtime_directories()
    return tmp_path


def _opportunity(opp_id: str, score: float | None, status: OpportunityStatus) -> OpportunityRecord:
    return OpportunityRecord(
        id=opp_id,
        title=f"wedge {opp_id}",
        problem="p",
        audience="a",
        source=SourceRef(connector="hackernews", query="q"),
        status=status,
        evidence=[
            EvidenceLink(url="https://news.ycombinator.com/item?id=1", kind=EvidenceKind.REQUEST)
        ],
        signals=OpportunitySignals(buyer_intent=7) if score is not None else None,
        score=score,
        confidence=0.9 if score is not None else None,
        created_at="2026-05-29T00:00:00+00:00",
        updated_at="2026-05-29T00:00:00+00:00",
    )


def test_opportunity_save_get_round_trip(isolated: Path) -> None:
    store = OpportunityStore()
    record = _opportunity("opp_a", 71.0, OpportunityStatus.SCORED)
    store.save(record)
    assert store.get("opp_a") == record


def test_opportunity_get_missing_raises(isolated: Path) -> None:
    with pytest.raises(FileNotFoundError):
        OpportunityStore().get("nope")


def test_opportunity_list_ranks_by_score_nulls_last(isolated: Path) -> None:
    store = OpportunityStore()
    store.save(_opportunity("low", 40.0, OpportunityStatus.SCORED))
    store.save(_opportunity("high", 80.0, OpportunityStatus.SCORED))
    store.save(_opportunity("unscored", None, OpportunityStatus.INBOX))
    ordered = [record.id for record in store.list()]
    assert ordered[0] == "high"
    assert ordered[1] == "low"
    assert ordered[-1] == "unscored"  # NULL score sorts last


def test_opportunity_list_filters_by_status(isolated: Path) -> None:
    store = OpportunityStore()
    store.save(_opportunity("a", 71.0, OpportunityStatus.SCORED))
    store.save(_opportunity("b", None, OpportunityStatus.INBOX))
    scored = store.list(status=OpportunityStatus.SCORED)
    assert [record.id for record in scored] == ["a"]


def _experiment(status: ExperimentStatus = ExperimentStatus.PLANNED) -> ExperimentRecord:
    return ExperimentRecord(
        id="exp_1",
        opportunity_id="opp_a",
        type=ExperimentType.WAITLIST,
        hypothesis="people sign up",
        success_criteria=SuccessCriteria(
            metric=ExperimentMetric.SIGNUPS, threshold=50, window="7d"
        ),
        status=status,
        created_at="2026-05-29T00:00:00+00:00",
    )


def test_experiment_save_get_round_trip(isolated: Path) -> None:
    store = ExperimentStore()
    record = _experiment()
    store.save(record)
    assert store.get("exp_1") == record


def test_experiment_list_by_opportunity(isolated: Path) -> None:
    store = ExperimentStore()
    store.save(_experiment())
    assert [e.id for e in store.list(opportunity_id="opp_a")] == ["exp_1"]
    assert store.list(opportunity_id="other") == []


def test_valid_transition_helper() -> None:
    assert is_valid_transition(ExperimentStatus.PLANNED, ExperimentStatus.APPROVED)
    assert not is_valid_transition(ExperimentStatus.PLANNED, ExperimentStatus.PASSED)


def test_experiment_lifecycle_to_passed_stamps_completed(isolated: Path) -> None:
    fixed_now_store = ExperimentStore()
    fixed_now_store.save(_experiment())
    fixed_now_store.transition("exp_1", ExperimentStatus.APPROVED)
    fixed_now_store.transition("exp_1", ExperimentStatus.RUNNING)
    passed = fixed_now_store.transition("exp_1", ExperimentStatus.PASSED)
    assert passed.status is ExperimentStatus.PASSED
    assert passed.completed_at  # terminal state stamped


def test_experiment_invalid_transition_raises(isolated: Path) -> None:
    store = ExperimentStore()
    store.save(_experiment())
    with pytest.raises(InvalidExperimentTransition):
        store.transition("exp_1", ExperimentStatus.PASSED)  # planned -> passed not allowed


def test_experiment_transition_to_same_status_is_noop(isolated: Path) -> None:
    store = ExperimentStore()
    store.save(_experiment(ExperimentStatus.RUNNING))
    same = store.transition("exp_1", ExperimentStatus.RUNNING)
    assert same.status is ExperimentStatus.RUNNING
