from __future__ import annotations

from packages.schemas.task_run import CodexExecutionRecord


def build_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "command": ["codex", "exec"],
        "command_display": "codex exec",
        "cwd": "/tmp/worktree",
        "stdout_path": "/tmp/stdout.log",
        "stderr_path": "/tmp/stderr.log",
        "exit_code": 0,
        "started_at": "2026-04-11T00:00:00+00:00",
        "finished_at": "2026-04-11T00:01:00+00:00",
        "timed_out": False,
    }
    payload.update(overrides)
    return payload


def test_codex_execution_record_defaults_session_id_to_none() -> None:
    record = CodexExecutionRecord(
        command=["codex", "exec"],
        command_display="codex exec",
        cwd="/tmp/worktree",
        stdout_path="/tmp/stdout.log",
        stderr_path="/tmp/stderr.log",
        exit_code=0,
        started_at="2026-04-11T00:00:00+00:00",
        finished_at="2026-04-11T00:01:00+00:00",
    )

    assert record.session_id is None


def test_codex_execution_record_from_dict_handles_missing_session_id() -> None:
    record = CodexExecutionRecord.from_dict(build_payload())

    assert record.session_id is None


def test_codex_execution_record_from_dict_preserves_session_id() -> None:
    record = CodexExecutionRecord.from_dict(build_payload(session_id="session-123"))

    assert record.session_id == "session-123"


def test_codex_execution_record_to_dict_round_trips_session_id() -> None:
    original = CodexExecutionRecord.from_dict(build_payload(session_id="session-123"))
    round_tripped = CodexExecutionRecord.from_dict(original.to_dict())

    assert round_tripped == original
    assert round_tripped.session_id == "session-123"
