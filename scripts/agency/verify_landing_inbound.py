#!/usr/bin/env python3
"""Verify BBW landing form + inbound pipeline contracts (offline).

Runs the same assertions as ``tests/python/unit/test_bbw_landing_inbound.py``
and the catalog JSON drift check. Use after editing the landing form, the
Netlify function, or ``packages/agency/catalog.yaml``.

    python scripts/agency/verify_landing_inbound.py
    python scripts/agency/render_catalog_json.py   # if packages drift fails
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def main() -> None:
    tests = [
        "tests/python/unit/test_bbw_landing_inbound.py",
        "tests/python/unit/test_agency_catalog_json.py",
        "tests/python/unit/test_agency_inbound.py",
    ]
    cmd = [sys.executable, "-m", "pytest", "-q", *tests]
    print(" ".join(cmd))
    subprocess.run(cmd, cwd=REPO, check=True)
    print("\nLanding + inbound + catalog JSON: OK")
    print("Live check (optional): POST the form on production, then:")
    print("  node scripts/web/pull-inbound.mjs")


if __name__ == "__main__":
    main()
