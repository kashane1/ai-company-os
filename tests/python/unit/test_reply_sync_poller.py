"""F3.3: poller hardening — the reply-sync state file must round-trip (cursor +
bounded processed-thread set) and the Gmail worker must refresh an expired access
token via its refresh token instead of dying.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "reply_sync_worker", Path("apps/worker-reply-sync/main.py")
)
worker = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(worker)


# ------------------------------------------------------------- state roundtrip
def test_state_roundtrip_preserves_cursor_and_threads(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("BBW_REPLY_SYNC_STATE", str(tmp_path / "state.json"))
    assert worker._load_state() == {"history_id": None, "processed_thread_ids": []}

    worker._save_state({"history_id": "98765", "processed_thread_ids": ["t1", "t2", "t3"]})
    loaded = worker._load_state()
    assert loaded["history_id"] == "98765"
    assert loaded["processed_thread_ids"] == ["t1", "t2", "t3"]


def test_state_processed_threads_bounded_at_2000(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("BBW_REPLY_SYNC_STATE", str(tmp_path / "state.json"))
    worker._save_state({"history_id": "1", "processed_thread_ids": [str(i) for i in range(2500)]})
    loaded = worker._load_state()
    assert len(loaded["processed_thread_ids"]) == 2000
    assert loaded["processed_thread_ids"][-1] == "2499"  # newest kept


def test_load_state_tolerates_corrupt_file(tmp_path, monkeypatch) -> None:
    state_file = tmp_path / "state.json"
    state_file.write_text("{ not json")
    monkeypatch.setenv("BBW_REPLY_SYNC_STATE", str(state_file))
    assert worker._load_state() == {"history_id": None, "processed_thread_ids": []}


# --------------------------------------------------------------- token refresh
class _FakeCreds:
    def __init__(self, *, valid: bool, expired: bool, refresh_token: str | None) -> None:
        self.valid = valid
        self.expired = expired
        self.refresh_token = refresh_token
        self.refreshed = False

    def refresh(self, request) -> None:
        assert request is not None
        self.refreshed = True
        self.valid = True
        self.expired = False

    def to_json(self) -> str:
        return '{"token": "refreshed"}'


def test_expired_token_is_refreshed_and_persisted(tmp_path) -> None:
    token_path = tmp_path / "token.json"
    creds = _FakeCreds(valid=False, expired=True, refresh_token="r-token")
    out = worker._refresh_if_needed(creds, token_path, request_factory=lambda: object())
    assert out.refreshed is True
    assert token_path.read_text() == '{"token": "refreshed"}'  # persisted


def test_valid_token_is_not_refreshed(tmp_path) -> None:
    token_path = tmp_path / "token.json"
    creds = _FakeCreds(valid=True, expired=False, refresh_token="r-token")
    worker._refresh_if_needed(creds, token_path, request_factory=lambda: object())
    assert creds.refreshed is False
    assert not token_path.exists()  # nothing written


def test_expired_without_refresh_token_does_not_crash(tmp_path) -> None:
    token_path = tmp_path / "token.json"
    creds = _FakeCreds(valid=False, expired=True, refresh_token=None)
    worker._refresh_if_needed(creds, token_path, request_factory=lambda: object())
    assert creds.refreshed is False  # nothing to refresh with, but no exception
