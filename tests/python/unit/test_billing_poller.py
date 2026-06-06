"""Tests for the runtime-supervised billing-event poller daemon."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


def _load_poller():
    module_path = Path(__file__).resolve().parents[3] / "apps" / "worker-billing-poller" / "main.py"
    spec = importlib.util.spec_from_file_location("billing_poller_main", module_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_poll_once_pulls_then_reconciles_when_events_present(monkeypatch, tmp_path) -> None:
    poller = _load_poller()
    calls: list[list[str]] = []

    monkeypatch.setattr(poller, "_find_node", lambda: "/usr/bin/node")
    # Pretend there is a drained event so reconcile runs.
    monkeypatch.setattr(poller.glob, "glob", lambda pattern: ["evt_1.json"])

    class _Result:
        returncode = 0
        stdout = "ok"
        stderr = ""

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        return _Result()

    monkeypatch.setattr(poller.subprocess, "run", fake_run)
    poller.poll_once()

    # First the node pull, then the python reconcile.
    assert calls[0][0] == "/usr/bin/node"
    assert calls[0][1].endswith("scripts/web/pull-stripe-events.mjs")
    assert calls[1][1].endswith("scripts/agency/reconcile_stripe_billing.py")


def test_poll_once_skips_pull_when_node_missing(monkeypatch) -> None:
    poller = _load_poller()
    monkeypatch.setattr(poller, "_find_node", lambda: None)
    monkeypatch.setattr(poller.glob, "glob", lambda pattern: [])  # no events → no reconcile either
    ran: list[list[str]] = []
    monkeypatch.setattr(poller.subprocess, "run", lambda cmd, **k: ran.append(cmd))
    poller.poll_once()  # must not raise
    assert ran == []


def test_find_node_prefers_path(monkeypatch) -> None:
    poller = _load_poller()
    monkeypatch.setattr(poller.shutil, "which", lambda name: "/somewhere/node")
    assert poller._find_node() == "/somewhere/node"
