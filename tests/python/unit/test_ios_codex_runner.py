from __future__ import annotations

from pathlib import Path

from ios import codex_runner
from packages.schemas.task_packet import WorkerLane
from packages.tools.codex_tools.task_packet import PacketPattern, select_packet_pattern
from tests.python.factories.task_data import build_task, build_worktree_metadata


def test_render_task_packet_uses_ios_implementation_defaults(tmp_path: Path) -> None:
    task = build_task(
        lane=WorkerLane.IOS,
        repo_id="fishing-logbook-ios",
        product_id="fishing-logbook",
        title="Seed iOS lane",
        summary="Create the first believable iOS product task.",
        task_type="ios_feature",
        constraints=["Leave all changes uncommitted for manual inspection."],
    )
    worktree = build_worktree_metadata(str(tmp_path))
    (tmp_path / "Sources").mkdir()
    (tmp_path / "Tests").mkdir()
    (tmp_path / "FishingLogbook.xcodeproj").mkdir()

    packet_path = codex_runner.render_task_packet(task, worktree)
    rendered = Path(packet_path).read_text()

    assert select_packet_pattern(task) is PacketPattern.IMPLEMENTATION
    assert "- pattern=implementation" in rendered
    assert "- Sources/" in rendered
    assert "- Tests/" in rendered
    assert "xcodebuild -project FishingLogbook.xcodeproj -scheme FishingLogbook" in rendered
    assert "Use the current iOS worktree contents as the source of truth for this pass." in rendered


def test_render_task_packet_uses_ui_polish_pattern_for_ios_polish_work(tmp_path: Path) -> None:
    task = build_task(
        lane=WorkerLane.IOS,
        repo_id="fishing-logbook-ios",
        product_id="fishing-logbook",
        title="Polish trip detail spacing",
        summary="Fix spacing, alignment, and accessibility polish issues in the trip detail screen.",
        task_type="ios_ui_polish",
    )
    worktree = build_worktree_metadata(str(tmp_path))
    (tmp_path / "Sources").mkdir()
    (tmp_path / "Tests").mkdir()

    packet_path = codex_runner.render_task_packet(task, worktree)
    rendered = Path(packet_path).read_text()

    assert select_packet_pattern(task) is PacketPattern.UI_POLISH
    assert "- pattern=ui-polish" in rendered
    assert "## Review findings to address" in rendered
    assert "spacing, alignment, and accessibility" in rendered
    assert "## Acceptance criteria" in rendered
