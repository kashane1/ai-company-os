from __future__ import annotations

import json
from pathlib import Path

import pytest

from engineering import codex_runner


def write_session_index(tmp_path: Path, lines: list[str]) -> None:
    index_path = tmp_path / ".codex" / "session_index.jsonl"
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text("\n".join(lines))


def test_read_latest_codex_session_id_returns_last_id(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    write_session_index(
        tmp_path,
        [
            json.dumps({"id": "session-1"}),
            json.dumps({"id": "session-2"}),
        ],
    )
    monkeypatch.setattr(codex_runner.Path, "home", lambda: tmp_path)

    assert codex_runner._read_latest_codex_session_id() == "session-2"


def test_read_latest_codex_session_id_returns_none_when_file_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(codex_runner.Path, "home", lambda: tmp_path)

    assert codex_runner._read_latest_codex_session_id() is None


def test_read_latest_codex_session_id_returns_none_for_empty_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    write_session_index(tmp_path, [])
    monkeypatch.setattr(codex_runner.Path, "home", lambda: tmp_path)

    assert codex_runner._read_latest_codex_session_id() is None


def test_read_latest_codex_session_id_returns_none_for_corrupt_last_line(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    write_session_index(
        tmp_path,
        [
            json.dumps({"id": "session-1"}),
            "garbage",
        ],
    )
    monkeypatch.setattr(codex_runner.Path, "home", lambda: tmp_path)

    assert codex_runner._read_latest_codex_session_id() is None


def test_read_latest_codex_session_id_returns_none_when_last_entry_has_no_id(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    write_session_index(
        tmp_path,
        [
            json.dumps({"id": "session-1"}),
            json.dumps({"name": "missing-id"}),
        ],
    )
    monkeypatch.setattr(codex_runner.Path, "home", lambda: tmp_path)

    assert codex_runner._read_latest_codex_session_id() is None
