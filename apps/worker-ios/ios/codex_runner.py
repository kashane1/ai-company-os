import json
import shlex
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from packages.config.settings import ensure_runtime_directories
from packages.schemas.task import Task
from packages.schemas.testing import NoTestReasonCode, TestLane
from packages.schemas.task_run import CodexExecutionRecord
from packages.schemas.worktree import WorktreeMetadata
from packages.tools.codex_tools.task_packet import CodexTaskPacket, render_markdown

CODEX_TIMEOUT_SECONDS = 120


def render_task_packet(task: Task, worktree: WorktreeMetadata) -> str:
    packet = CodexTaskPacket(
        task_id=f"iOS Task {task.id}",
        summary=task.summary,
        constraints=[
            "product_id=" + (task.product_id or "unknown"),
            f"repo_id={task.repo_id}",
            "lane=ios",
            "Treat docs/products as the product source of truth before editing code.",
            "Keep the change scoped to the requested iOS task.",
            "Do not introduce release automation, TestFlight automation, or App Store Connect changes.",
            "Prefer the smallest believable structural change.",
            *task.constraints,
        ],
        tests_required=True,
        test_lane=TestLane.IOS,
        allowed_no_test_reason_codes=[
            NoTestReasonCode.COMMENTS_ONLY,
            NoTestReasonCode.VISUAL_ONLY_NON_LOGIC,
            NoTestReasonCode.CONFIG_NO_BEHAVIOR_CHANGE,
            NoTestReasonCode.APPROVED_FOLLOWUP_TEST_TASK,
        ],
    )
    packet_path = Path(worktree.root_path) / "codex_task_packet.md"
    packet_path.write_text(render_markdown(packet) + "\n")
    return str(packet_path)


def execute_codex(
    task: Task,
    worktree: WorktreeMetadata,
    packet_path: str,
) -> tuple[str, CodexExecutionRecord, str, str]:
    paths = ensure_runtime_directories()
    result_path = Path(worktree.root_path) / "codex_last_message.md"
    stdout_path = paths.ios_logs_root / f"{task.id}.stdout.log"
    stderr_path = paths.ios_logs_root / f"{task.id}.stderr.log"

    command = [
        "codex",
        "exec",
        "--skip-git-repo-check",
        "--sandbox",
        "workspace-write",
        "--color",
        "never",
        "-C",
        worktree.root_path,
        "-o",
        str(result_path),
        "-",
    ]

    packet_text = Path(packet_path).read_text()
    started_at = datetime.now(UTC).isoformat()
    timed_out = False

    try:
        completed = subprocess.run(
            command,
            input=packet_text,
            text=True,
            capture_output=True,
            cwd=worktree.root_path,
            timeout=CODEX_TIMEOUT_SECONDS,
        )
        stdout = completed.stdout
        stderr = completed.stderr
        exit_code = completed.returncode
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        stdout = exc.stdout or ""
        stderr = (exc.stderr or "") + f"\niOS Codex execution timed out after {CODEX_TIMEOUT_SECONDS} seconds."
        exit_code = -1

    finished_at = datetime.now(UTC).isoformat()
    stdout_path.parent.mkdir(parents=True, exist_ok=True)
    stdout_path.write_text(stdout)
    stderr_path.write_text(stderr)

    metadata_path = Path(worktree.root_path) / "codex_execution.json"
    metadata_payload = {
        "task_id": task.id,
        "command": command,
        "command_display": shlex.join(command),
        "cwd": worktree.root_path,
        "packet_path": packet_path,
        "stdout_path": str(stdout_path),
        "stderr_path": str(stderr_path),
        "exit_code": exit_code,
        "started_at": started_at,
        "finished_at": finished_at,
        "timed_out": timed_out,
    }
    with metadata_path.open("w") as handle:
        json.dump(metadata_payload, handle, indent=2, sort_keys=True)

    execution = CodexExecutionRecord(
        command=command,
        command_display=shlex.join(command),
        cwd=worktree.root_path,
        stdout_path=str(stdout_path),
        stderr_path=str(stderr_path),
        exit_code=exit_code,
        started_at=started_at,
        finished_at=finished_at,
        timed_out=timed_out,
    )

    artifact_dir = paths.ios_artifacts_root / task.id
    artifact_dir.mkdir(parents=True, exist_ok=True)
    summary_path = artifact_dir / "summary.txt"
    summary_path.write_text(
        "\n".join(
            [
                f"task_id={task.id}",
                f"product_id={task.product_id or ''}",
                f"exit_code={exit_code}",
                f"timed_out={timed_out}",
                f"last_message_path={result_path}",
            ]
        )
        + "\n"
    )

    return str(result_path), execution, str(summary_path), str(metadata_path)
