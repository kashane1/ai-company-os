from packages.policies.approvals import (
    requires_human_approval,
    requires_release_action_approval,
)
from packages.schemas.task_packet import RiskLevel, WorkerLane
from tests.python.factories import build_task_packet


def test_requires_human_approval_for_high_risk_tasks() -> None:
    packet = build_task_packet(risk_level=RiskLevel.HIGH)

    assert requires_human_approval(packet) is True


def test_requires_human_approval_when_summary_mentions_protected_action() -> None:
    packet = build_task_packet(
        lane=WorkerLane.SUPERVISOR,
        title="Prepare release plan",
        summary="We need to deploy this to production after review.",
    )

    assert requires_human_approval(packet) is True


def test_does_not_require_human_approval_for_low_risk_engineering_tasks() -> None:
    packet = build_task_packet(
        lane=WorkerLane.ENGINEERING,
        title="Update docs",
        summary="Refresh architecture notes.",
    )

    assert requires_human_approval(packet) is False


def test_release_action_approval_only_for_sensitive_actions() -> None:
    assert requires_release_action_approval("prepare_testflight") is False
    assert requires_release_action_approval("submit_appstore") is True
    assert requires_release_action_approval("release_to_store") is True
    assert requires_release_action_approval("draft_release_notes") is False
