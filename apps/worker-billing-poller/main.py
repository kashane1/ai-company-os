"""Runtime-supervised billing-event poller (agency layer, G1).

Drains the BBW Netlify Blobs ``stripe-events`` store (written by the production
``netlify/functions/stripe-webhook.mjs``) into ``state/agency/stripe-events/`` via
``scripts/web/pull-stripe-events.mjs``, then applies the events to the local ledger
via ``scripts/agency/reconcile_stripe_billing.py``. Loops forever on an interval.

This is the steady-state drain half of the production webhook design. It is run by
the **runtime-supervisor** (per ``infra/launchd/README.md``, launchd runs *only* the
supervisor — never a standalone poller plist). The supervisor restarts it on exit.

Manual / single cycle:  ``python apps/worker-billing-poller/main.py --once``
Interval env:           ``AGENCY_BILLING_POLL_INTERVAL_SECS`` (default 120).
"""

from __future__ import annotations

import glob
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PULL_SCRIPT = ROOT / "scripts" / "web" / "pull-stripe-events.mjs"
RECONCILE_SCRIPT = ROOT / "scripts" / "agency" / "reconcile_stripe_billing.py"

DEFAULT_INTERVAL = 120


def _log(msg: str) -> None:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    print(f"[billing-poller {ts}] {msg}", flush=True)


def _find_node() -> str | None:
    """Resolve the node binary. The launchd PATH often lacks nvm, so fall back to
    common install locations rather than failing silently."""
    found = shutil.which("node")
    if found:
        return found
    candidates: list[str] = []
    nvm = Path.home() / ".nvm" / "versions" / "node"
    if nvm.is_dir():
        # pick the highest installed version's node
        candidates += sorted((str(p / "bin" / "node") for p in nvm.iterdir() if p.is_dir()), reverse=True)
    candidates += ["/opt/homebrew/bin/node", "/usr/local/bin/node"]
    for c in candidates:
        if Path(c).exists():
            return c
    return None


def _run(cmd: list[str], label: str) -> None:
    try:
        proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, timeout=120)
    except subprocess.TimeoutExpired:
        _log(f"{label}: TIMEOUT")
        return
    out = (proc.stdout or "").strip().splitlines()
    tail = out[-1] if out else ""
    if proc.returncode != 0:
        _log(f"{label}: exit {proc.returncode} — {(proc.stderr or tail).strip()[:300]}")
    elif tail:
        _log(f"{label}: {tail}")


def poll_once() -> None:
    """One drain cycle: pull verified events from Blobs, then reconcile to ledger."""
    node = _find_node()
    if node:
        _run([node, str(PULL_SCRIPT)], "pull")
    else:
        _log("node not found on PATH or in nvm/homebrew — skipping Blobs pull this cycle")
    # Reconcile any drained events (idempotent; safe even if pull was skipped).
    if list(glob.glob(str(ROOT / "state" / "agency" / "stripe-events" / "*.json"))):
        _run([sys.executable, str(RECONCILE_SCRIPT)], "reconcile")


def main() -> int:
    once = "--once" in sys.argv
    interval = int(os.environ.get("AGENCY_BILLING_POLL_INTERVAL_SECS", DEFAULT_INTERVAL))
    if once:
        poll_once()
        return 0
    _log(f"starting; interval={interval}s")
    while True:
        try:
            poll_once()
        except Exception as exc:  # never let one bad cycle kill the loop
            _log(f"cycle error (continuing): {exc!r}")
        time.sleep(interval)


if __name__ == "__main__":
    raise SystemExit(main())
