#!/usr/bin/env python3
"""Offline verification for the G2 lead-activation slice — runs the test subset."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

TESTS = [
    "tests/python/unit/test_agency_inbound.py",
    "tests/python/unit/test_agency_inbound_status.py",
    "tests/python/unit/test_agency_inbound_fulfillment.py",
    "tests/python/unit/test_url_guard.py",
    "tests/python/unit/test_url_guard_fetch.py",
    "tests/python/unit/test_web_deploy_secret_scan.py",
]


def main() -> int:
    return subprocess.run(
        [sys.executable, "-m", "pytest", "-q", *TESTS], cwd=REPO, check=False
    ).returncode


if __name__ == "__main__":
    raise SystemExit(main())
