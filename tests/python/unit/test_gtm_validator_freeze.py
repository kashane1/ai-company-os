"""Phase 2.0 — tests for the GTM freeze flag and threat-model drift check.

We don't import apps/worker-gtm directly (hyphen in dir name) — we load the
validator module via its file path.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
VALIDATOR = REPO / "apps" / "worker-gtm" / "gtm" / "validator.py"


def _load():
    spec = importlib.util.spec_from_file_location(
        "_worker_gtm_validator", VALIDATOR
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _seed_acked_threat_model(root: Path, *, content: str = "tm\n") -> None:
    tm = root / "docs" / "security" / "mcp-threat-model.md"
    tm.parent.mkdir(parents=True, exist_ok=True)
    tm.write_text(content)
    state = root / "state" / "checkpoints" / "platform" / "security-state.json"
    state.parent.mkdir(parents=True, exist_ok=True)
    state.write_text(
        json.dumps(
            {
                "mcp-threat-model": {
                    "checksum": hashlib.sha256(tm.read_bytes()).hexdigest(),
                    "acknowledged_at": "2026-04-10T00:00:00Z",
                }
            }
        )
    )


def test_freeze_flag(tmp_path):
    v = _load()
    assert v.is_gtm_frozen(tmp_path) is False
    (tmp_path / "state" / "flags").mkdir(parents=True)
    (tmp_path / "state" / "flags" / "gtm_frozen").write_text("x")
    assert v.is_gtm_frozen(tmp_path) is True


def test_threat_model_missing(tmp_path):
    v = _load()
    assert v.check_threat_model_drift(tmp_path) == "missing"


def test_threat_model_unacked(tmp_path):
    v = _load()
    tm = tmp_path / "docs" / "security" / "mcp-threat-model.md"
    tm.parent.mkdir(parents=True)
    tm.write_text("x")
    assert v.check_threat_model_drift(tmp_path) == "unacknowledged"


def test_threat_model_ok(tmp_path):
    v = _load()
    _seed_acked_threat_model(tmp_path)
    assert v.check_threat_model_drift(tmp_path) is None


def test_threat_model_drift(tmp_path):
    v = _load()
    _seed_acked_threat_model(tmp_path, content="original\n")
    tm = tmp_path / "docs" / "security" / "mcp-threat-model.md"
    tm.write_text("mutated\n")
    assert v.check_threat_model_drift(tmp_path) == "drift"
