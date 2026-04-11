"""Phase 2.0/2.1 — GTM pre-claim validators.

- ``is_gtm_frozen`` checks the kill-switch flag file.
- ``check_threat_model_drift`` enforces the MCP threat model acknowledgment
  contract: the recorded checksum must match the on-disk file, or the lane
  is blocked until ``scripts/acknowledge_threat_model.sh --read`` is run.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


def is_gtm_frozen(repo_root: Path) -> bool:
    return (repo_root / "state" / "flags" / "gtm_frozen").exists()


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def check_threat_model_drift(repo_root: Path) -> str | None:
    """Return a short reason string if the lane is blocked, else None."""
    tm = repo_root / "docs" / "security" / "mcp-threat-model.md"
    if not tm.exists():
        return "missing"
    state_file = (
        repo_root / "state" / "checkpoints" / "platform" / "security-state.json"
    )
    if not state_file.exists():
        return "unacknowledged"
    try:
        payload = json.loads(state_file.read_text())
    except Exception:
        return "corrupt-state-file"
    recorded = (payload.get("mcp-threat-model") or {}).get("checksum")
    if not recorded:
        return "unacknowledged"
    if recorded != _sha256(tm):
        return "drift"
    return None
