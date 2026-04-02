from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from engineering import codex_runner
from packages.schemas.task_run import CodexExecutionRecord
from packages.tools.codex_tools.task_packet import PacketPattern, select_packet_pattern
from tests.python.factories.task_data import build_task, build_worktree_metadata


def test_render_task_packet_writes_implementation_packet_to_worktree(tmp_path: Path) -> None:
    task = build_task(
        title="Trace the first engineering task flow",
        summary="Update docs/engineering-flow.md with one short sentence noting that task runs persist artifacts.",
        constraints=["Keep the change minimal."],
    )
    worktree = build_worktree_metadata(str(tmp_path))
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "engineering-flow.md").write_text("placeholder")

    packet_path = codex_runner.render_task_packet(task, worktree)
    rendered = (tmp_path / "TASK_PACKET.md").read_text()

    assert packet_path == str(tmp_path / "TASK_PACKET.md")
    assert select_packet_pattern(task) is PacketPattern.IMPLEMENTATION
    assert "# Task: Trace the first engineering task flow" in rendered
    assert "- pattern=implementation" in rendered
    assert "## Context" in rendered
    assert "- docs/engineering-flow.md" in rendered
    assert "## Target files" in rendered
    assert "## Verification" in rendered
    assert "python3 -m pytest tests/python" not in rendered
    assert "No additional verification command required for docs-only scope." in rendered
    assert "## Acceptance criteria" in rendered


def test_render_task_packet_uses_validation_pattern_for_test_work(tmp_path: Path) -> None:
    task = build_task(
        title="Add validation coverage for engineering runner",
        summary="Create tests for the runner flow.",
        task_type="validation",
    )
    worktree = build_worktree_metadata(str(tmp_path))
    (tmp_path / "tests" / "python").mkdir(parents=True)
    (tmp_path / "apps").mkdir()
    (tmp_path / "packages").mkdir()

    codex_runner.render_task_packet(task, worktree)
    rendered = (tmp_path / "TASK_PACKET.md").read_text()

    assert select_packet_pattern(task) is PacketPattern.VALIDATION
    assert "- pattern=validation" in rendered
    assert "## Coverage target" in rendered
    assert "## Validation commands" in rendered
    assert "- python3 -m pytest tests/python" in rendered
    assert "- tests/python/" in rendered


def test_execute_codex_writes_deterministic_artifact_shape(
    isolated_repo_root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    worktree_root = isolated_repo_root / "worktree"
    worktree_root.mkdir()
    packet_path = worktree_root / "TASK_PACKET.md"
    packet_path.write_text("packet body")
    task = build_task()
    worktree = build_worktree_metadata(str(worktree_root))

    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args=kwargs.get("args", args[0] if args else []),
            returncode=0,
            stdout="execution stdout",
            stderr="execution stderr",
        ),
    )

    result_path, execution, summary_path, metadata_path = codex_runner.execute_codex(
        task, worktree, str(packet_path)
    )

    stdout_log = isolated_repo_root / "state" / "logs" / "engineering" / "task-123.stdout.log"
    stderr_log = isolated_repo_root / "state" / "logs" / "engineering" / "task-123.stderr.log"
    metadata = json.loads(Path(metadata_path).read_text())
    summary_lines = Path(summary_path).read_text().splitlines()

    assert result_path == str(worktree_root / "codex_last_message.md")
    assert isinstance(execution, CodexExecutionRecord)
    assert execution.exit_code == 0
    assert execution.timed_out is False
    assert stdout_log.read_text() == "execution stdout"
    assert stderr_log.read_text() == "execution stderr"
    assert set(metadata) == {
        "command",
        "command_display",
        "cwd",
        "exit_code",
        "finished_at",
        "packet_path",
        "started_at",
        "stderr_path",
        "stdout_path",
        "task_id",
        "timed_out",
    }
    assert metadata["task_id"] == "task-123"
    assert metadata["packet_path"] == str(packet_path)
    assert metadata["stdout_path"] == str(stdout_log)
    assert metadata["stderr_path"] == str(stderr_log)
    assert metadata["cwd"] == str(worktree_root)
    assert metadata["exit_code"] == 0
    assert metadata["timed_out"] is False
    assert summary_lines == [
        "task_id=task-123",
        "exit_code=0",
        "timed_out=False",
        f"last_message_path={worktree_root / 'codex_last_message.md'}",
    ]


def test_execute_codex_timeout_marks_execution_and_appends_timeout_note(
    isolated_repo_root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    worktree_root = isolated_repo_root / "worktree"
    worktree_root.mkdir()
    packet_path = worktree_root / "TASK_PACKET.md"
    packet_path.write_text("packet body")
    task = build_task()
    worktree = build_worktree_metadata(str(worktree_root))

    def raise_timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(
            cmd=["codex", "exec"],
            timeout=codex_runner.CODEX_TIMEOUT_SECONDS,
            output="partial stdout",
            stderr="partial stderr",
        )

    monkeypatch.setattr(subprocess, "run", raise_timeout)

    _, execution, summary_path, metadata_path = codex_runner.execute_codex(
        task, worktree, str(packet_path)
    )

    stderr_log = isolated_repo_root / "state" / "logs" / "engineering" / "task-123.stderr.log"
    metadata = json.loads(Path(metadata_path).read_text())

    assert execution.exit_code == -1
    assert execution.timed_out is True
    assert "Codex execution timed out after 120 seconds." in stderr_log.read_text()
    assert metadata["exit_code"] == -1
    assert metadata["timed_out"] is True
    assert Path(summary_path).read_text().splitlines()[1:3] == [
        "exit_code=-1",
        "timed_out=True",
    ]
