#!/usr/bin/env python3
"""Render a Conversion Lab report from a JSON payload."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from packages.agency.conversion_lab import write_report  # noqa: E402
from packages.schemas.conversion_lab import ConversionLabReport  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report-json", required=True, type=Path)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--root", type=Path, default=REPO)
    args = parser.parse_args()

    payload = json.loads(args.report_json.read_text(encoding="utf-8"))
    report = ConversionLabReport.from_dict(payload)
    path = write_report(report, root=args.root, run_id=args.run_id)
    print(json.dumps({"report": str(path)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
