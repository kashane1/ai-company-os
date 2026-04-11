"""File-backed store for :class:`ApprovalToken` records (Phase 3.1).

Tokens live at ``state/checkpoints/platform/approval_tokens/<token_id>.json``
and are gitignored under the repo's ``state/`` convention. One file per
token; writes are whole-file replacements to keep the single-use burn path
atomic on a local filesystem.
"""

from __future__ import annotations

import json
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
