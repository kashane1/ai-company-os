from __future__ import annotations

import pytest

from packages.db.event_store import EventStore
from packages.db.goal_store import GoalStore
from packages.schemas.event import EventRecord
from packages.schemas.goal import GoalRecord


def test_shared_transaction_rolls_back_writes_from_separate_store_instances():
    goals = GoalStore()
    events = EventStore()
    with pytest.raises(RuntimeError, match="injected"):
        with goals.db.transaction():
            goals.save(GoalRecord(id="rollback-goal", title="Test", summary="Test"))
            events.append(EventRecord(
                id="rollback-event", event_type="goal_created", subject_type="goal",
                subject_id="rollback-goal", payload={}, created_at="2026-09-09T00:00:00Z",
            ))
            raise RuntimeError("injected failure after both writes")
    with pytest.raises(FileNotFoundError):
        goals.load("rollback-goal")
    assert events.list() == []


def test_nested_transactions_share_one_commit_boundary():
    goals = GoalStore()
    with goals.db.transaction():
        goals.save(GoalRecord(id="committed-goal", title="Test", summary="Test"))
        with GoalStore().db.transaction():
            assert GoalStore().load("committed-goal").id == "committed-goal"
    assert GoalStore().load("committed-goal").id == "committed-goal"


def test_rollback_does_not_poison_next_transaction():
    goals = GoalStore()
    with pytest.raises(RuntimeError):
        with goals.db.transaction():
            raise RuntimeError("injected")
    with goals.db.transaction():
        goals.save(GoalRecord(id="next-goal", title="Test", summary="Test"))
    assert goals.load("next-goal").id == "next-goal"
