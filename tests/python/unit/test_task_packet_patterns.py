from __future__ import annotations

from pathlib import Path

from packages.schemas.task_packet import WorkerLane
from packages.schemas.testing import NoTestReasonCode, TestLane as PacketTestLane
from packages.tools.codex_tools.task_packet import PacketPattern, build_task_packet, render_markdown, select_packet_pattern
from tests.python.factories.task_data import build_task


def test_select_packet_pattern_prefers_handoff_safe_when_handoff_language_present() -> None:
    task = build_task(
        title="Prepare handoff-safe output",
        summary="Produce App Store handoff notes for downstream review.",
        task_type="ios_release_handoff",
    )

    assert select_packet_pattern(task) is PacketPattern.HANDOFF_SAFE


def test_build_task_packet_falls_back_to_implementation_for_generic_tasks(tmp_path: Path) -> None:
    task = build_task(
        title="Implement task",
        summary="Add automation safely.",
        task_type="engineering_change",
    )
    (tmp_path / "apps").mkdir()
    (tmp_path / "packages").mkdir()

    packet = build_task_packet(
        task,
        worktree_root=str(tmp_path),
        test_lane=PacketTestLane.PYTHON,
        allowed_no_test_reason_codes=[NoTestReasonCode.COMMENTS_ONLY],
    )
    rendered = render_markdown(packet)

    assert packet.pattern is PacketPattern.IMPLEMENTATION
    assert "## Context" in rendered
    assert "## Acceptance criteria" in rendered


def test_build_task_packet_renders_handoff_sections(tmp_path: Path) -> None:
    task = build_task(
        lane=WorkerLane.IOS,
        repo_id="catchbook-ios",
        title="Prepare TestFlight handoff",
        summary="Prepare release notes for App Store handoff without changing runtime architecture.",
        task_type="ios_release_handoff",
    )
    (tmp_path / "Sources").mkdir()
    (tmp_path / "Tests").mkdir()

    packet = build_task_packet(
        task,
        worktree_root=str(tmp_path),
        test_lane=PacketTestLane.IOS,
        allowed_no_test_reason_codes=[NoTestReasonCode.CONFIG_NO_BEHAVIOR_CHANGE],
    )
    rendered = render_markdown(packet)

    assert packet.pattern is PacketPattern.HANDOFF_SAFE
    assert "## Handoff context" in rendered
    assert "## Output contract" in rendered
    assert "## Do not" in rendered
