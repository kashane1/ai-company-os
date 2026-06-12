#!/usr/bin/env python3
"""Start the local operator outreach dashboard and open it in the browser.

Run from anywhere:  python scripts/start_dash.py  (or `make dash` / `./start dash`).

Why this exists instead of `apps/api/server.py`: running that script directly
puts `apps/api/` on sys.path[0], where `apps/api/platform.py` shadows the stdlib
`platform` module and crashes the import chain. Launching from `scripts/` (this
file's dir lands on sys.path[0]) avoids the collision entirely.

The server binds to 127.0.0.1 only — this is a local operator tool, never
exposed. A background thread waits for the server to answer, then opens the
outreach action panel in the default browser. If the port is already serving,
it just opens the browser and exits.
"""

from __future__ import annotations

import socket
import sys
import threading
import time
import urllib.request
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

HOST = "127.0.0.1"
PORT = 8765
PATH = "/dashboard/outreach"
URL = f"http://{HOST}:{PORT}{PATH}"


def _port_in_use() -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.4)
        return sock.connect_ex((HOST, PORT)) == 0


def _open_when_ready() -> None:
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        try:
            urllib.request.urlopen(URL, timeout=0.5)  # noqa: S310 - localhost only
            break
        except Exception:  # noqa: BLE001 - server not up yet, keep polling
            time.sleep(0.25)
    webbrowser.open(URL)


def main() -> int:
    if _port_in_use():
        print(f"Dashboard already running. Opening {URL}")
        webbrowser.open(URL)
        return 0

    import uvicorn  # imported late so a stale port check is cheap

    from apps.api.main import app

    print(f"Starting outreach dashboard at {URL}  (Ctrl-C to stop)")
    threading.Thread(target=_open_when_ready, daemon=True).start()
    uvicorn.run(app, host=HOST, port=PORT, log_level="warning")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
