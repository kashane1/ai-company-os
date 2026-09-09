from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
from ios import codex_runner

from packages.schemas.task_packet import WorkerLane
from packages.tools.codex_tools.task_packet import PacketPattern, select_packet_pattern
from tests.python.factories.task_data import build_task, build_worktree_metadata


def test_render_task_packet_uses_ios_implementation_defaults(tmp_path: Path) -> None:
    task = build_task(
        lane=WorkerLane.IOS,
        repo_id="catchbook-ios",
        product_id="catchbook",
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
        repo_id="catchbook-ios",
        product_id="catchbook",
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


def test_execute_codex_redacts_canaries_from_ios_persisted_diagnostics(
    isolated_repo_root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    canary = "sk-IOSCANARY0123456789ABCDEFG"
    worktree_root = isolated_repo_root / "token=ios_metadata_canary_123456789"
    worktree_root.mkdir()
    packet_path = worktree_root / "TASK_PACKET.md"
    packet_path.write_text("packet body")
    task = build_task(lane=WorkerLane.IOS)
    worktree = build_worktree_metadata(str(worktree_root))

    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args=kwargs.get("args", args[0] if args else []),
            returncode=1,
            stdout=f"useful ios stdout diagnostic token={canary}",
            stderr=f"useful ios stderr diagnostic bearer {canary}",
        ),
    )

    _, execution, _, metadata_path = codex_runner.execute_codex(task, worktree, str(packet_path))

    stdout_log = isolated_repo_root / "state" / "logs" / "ios" / "task-123.stdout.log"
    stderr_log = isolated_repo_root / "state" / "logs" / "ios" / "task-123.stderr.log"
    metadata = json.loads(Path(metadata_path).read_text())
    persisted = "\n".join([stdout_log.read_text(), stderr_log.read_text(), json.dumps(metadata)])

    assert canary not in persisted
    assert "ios_metadata_canary_123456789" not in persisted
    assert "useful ios stdout diagnostic" in persisted
    assert "useful ios stderr diagnostic" in persisted
    assert canary not in execution.command_display
