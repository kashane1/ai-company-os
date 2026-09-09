"""File-backed store for :class:`ApprovalToken` records (Phase 3.1).

Tokens live at ``state/checkpoints/platform/approval_tokens/<token_id>.json``
and are gitignored under the repo's ``state/`` convention. One file per
token; a per-token advisory file lock serializes load/check/write operations,
and writes are whole-file replacements.
"""

from __future__ import annotations

import fcntl
import json
from collections.abc import Callable
from pathlib import Path

from packages.config.settings import load_runtime_paths
from packages.policies.approval_tokens import (
    ApprovalToken,
    ApprovalTokenStoreProtocol,
)


class ApprovalTokenStore(ApprovalTokenStoreProtocol):
    def __init__(self, root: Path | None = None) -> None:
        paths = load_runtime_paths()
        self._root = root or (paths.platform_state_root / "approval_tokens")
        self._root.mkdir(parents=True, exist_ok=True)

    def _path_for(self, token_id: str) -> Path:
        safe = token_id.replace("/", "_")
        return self._root / f"{safe}.json"

    def save(self, token: ApprovalToken) -> None:
        payload = token.to_dict()
        tmp = self._path_for(token.token_id).with_suffix(".json.tmp")
        tmp.write_text(json.dumps(payload, indent=2, sort_keys=True))
        tmp.replace(self._path_for(token.token_id))

    def load(self, token_id: str) -> ApprovalToken:
        return self._load_unlocked(token_id)

    def update_atomically(
        self,
        token_id: str,
        update: Callable[[ApprovalToken], ApprovalToken],
    ) -> ApprovalToken:
        """Load, validate, and replace one token while holding its file lock."""
        lock_path = self._path_for(token_id).with_suffix(".lock")
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        with lock_path.open("a+") as lock_file:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
            try:
                token = self._load_unlocked(token_id)
                updated = update(token)
                self.save(updated)
                return updated
            finally:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)

    def _load_unlocked(self, token_id: str) -> ApprovalToken:
        path = self._path_for(token_id)
        if not path.exists():
            raise FileNotFoundError(token_id)
        return ApprovalToken.from_dict(json.loads(path.read_text()))

    def list_by_approval(self, approval_id: str) -> list[ApprovalToken]:
        out: list[ApprovalToken] = []
        for entry in self._root.glob("*.json"):
            try:
                record = ApprovalToken.from_dict(json.loads(entry.read_text()))
            except Exception:
                continue
            if record.approval_id == approval_id:
                out.append(record)
        return out
