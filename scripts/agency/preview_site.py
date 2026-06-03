#!/usr/bin/env python3
"""Serve a demo site's build locally so we can preview + iterate BEFORE deploying.

Deploying to Netlify is a separate, explicit step — never part of the build loop.
This serves the static build on localhost so you can open it, give notes, and
we iterate as many times as needed.

USAGE
-----
    python scripts/agency/preview_site.py --place-id <PID>     # serves its dist-v2 (or dist)
    python scripts/agency/preview_site.py --dir <path> --port 8011

Run it in the background, then open the printed http://localhost:<port> URL.
Edit the HTML and just refresh — no rebuild needed for static sites.
"""

from __future__ import annotations

import argparse
import functools
import http.server
import socketserver
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SITES = REPO / "state" / "prospects" / "sites"


def resolve_dir(args) -> Path:
    if args.dir:
        return Path(args.dir).resolve()
    if not args.place_id:
        sys.exit("pass --place-id <PID> or --dir <path>")
    base = SITES / args.place_id
    for candidate in ("dist-v2", "dist"):
        d = base / candidate
        if (d / "index.html").exists():
            return d
    sys.exit(f"no built site found under {base} (expected dist-v2/ or dist/ with index.html)")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--place-id", help="serve state/prospects/sites/<place_id>/dist-v2 (or dist)")
    ap.add_argument("--dir", help="serve an explicit directory")
    ap.add_argument("--port", type=int, default=8011)
    args = ap.parse_args()

    directory = resolve_dir(args)
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(directory))
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("127.0.0.1", args.port), handler) as httpd:
        print(f"Preview: http://localhost:{args.port}")
        print(f"Serving: {directory}")
        print("Edit the HTML and refresh. Ctrl-C / stop the task to quit. (Not deployed.)")
        httpd.serve_forever()


if __name__ == "__main__":
    main()
