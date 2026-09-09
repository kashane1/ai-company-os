from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


@pytest.fixture
def content_policy(repo_root, tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location(
        "repository_content_policy", repo_root / "scripts/ci/token_efficiency_check.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "REPO", tmp_path)
    monkeypatch.setattr(module, "tracked", lambda *globs: list((tmp_path / "state").rglob("*")))
    (tmp_path / "state").mkdir()
    return module


@pytest.mark.parametrize("name,contents", [
    ("approval.json", b'{"status":"approved"}'),
    ("receipt.md", b"# Operator receipt"),
    ("screenshot.png", b"\x89PNG\x00" + b"x" * 100),
])
def test_runtime_records_are_rejected_even_when_small(content_policy, name, contents):
    (content_policy.REPO / "state" / name).write_bytes(contents)
    assert content_policy.check_state_weight()


def test_state_contract_and_empty_directory_markers_are_allowed(content_policy):
    (content_policy.REPO / "state/README.md").write_text("# Runtime state")
    (content_policy.REPO / "state/.gitkeep").touch()
    assert content_policy.check_state_weight() == []


def test_directory_marker_cannot_hide_payload(content_policy):
    (content_policy.REPO / "state/.gitkeep").write_bytes(b"private operator data")
    assert content_policy.check_state_weight()
