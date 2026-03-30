from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from engineering import codex_runner
from packages.schemas.task_run import CodexExecutionRecord
from tests.python.factories.task_data import build_task, build_worktree_metadata


def test_render_task_packet_writes_packet_to_worktree(tmp_path: Path) -> None:
    task = build_task(constraints=["Do not commit changes."])
    worktree = build_worktree_metadata(str(tmp_path))

    packet_path = codex_runner.render_task_packet(task, worktree)

    assert packet_path == str(tmp_path / "codex_task_packet.md")
    assert (tmp_path / "codex_task_packet.md").read_text() == (
        "# Task task-123\n\n"
        "## Objective\n\n"
        "Add automation safely\n\n"
        "## Execution Rules\n\n"
        "- Work only inside the provided isolated worktree.\n"
        "- Use the current repository contents as the source of truth.\n"
        "- Do not create commits, rewrite history, push branches, or open PRs.\n"
        "- Leave all file changes uncommitted for manual inspection.\n"
        "- Prefer the smallest change that satisfies the task.\n\n"
        "## Constraints\n"
        "- Do not commit changes.\n\n"
        "## Testing Contract\n\n"
        "- tests_required=true\n"
        "- test_lane=python\n"
        "- Every logic-bearing change must ship with created or modified lane-matching tests unless a valid exception applies.\n"
        "- Your final message must include a `## Testing` section.\n"
        "- In that section, either list tests added or updated, or include `no_test_reason_code=<enum>` with a short reason.\n"
        "- If you use `approved_followup_test_task`, also include `followup_task_id=<task-id>`.\n"
        "- allowed_no_test_reason_codes=comments_only, config_no_behavior_change, approved_followup_test_task\n"
    )


def test_execute_codex_writes_deterministic_artifact_shape(
    isolated_repo_root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    worktree_root = isolated_repo_root / "worktree"
    worktree_root.mkdir()
    packet_path = worktree_root / "codex_task_packet.md"
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
    packet_path = worktree_root / "codex_task_packet.md"
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
