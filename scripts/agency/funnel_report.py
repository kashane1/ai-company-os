#!/usr/bin/env python3
"""Write the prospect-to-client funnel scoreboard.

Measures every stage from its primary source and writes
``state/prospects/funnel-report.md`` + ``.json``. Output is
committed-format-stable so the diff between two runs is readable, and the
dashboard reads the JSON snapshot rather than recomputing live.

    python scripts/agency/funnel_report.py
    python scripts/agency/funnel_report.py --by vertical
    python scripts/agency/funnel_report.py --by city --json

Schedule (daily, alongside the runtime supervisor) — add to crontab if not
already wired into infra/launchd:

    0 7 * * *  cd <repo> && python scripts/agency/funnel_report.py
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from packages.agency.funnel import (  # noqa: E402
    compute_funnel,
    default_funnel_report_root,
    load_funnel_report_payload,
    write_funnel_report,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--by",
        choices=["vertical", "city"],
        default="",
        help="add a sent/replied breakdown by vertical (genre) or city",
    )
    parser.add_argument("--json", action="store_true", help="print the report payload as JSON")
    args = parser.parse_args()

    previous = load_funnel_report_payload(REPO)
    report = compute_funnel(repo_root=REPO, by=args.by, previous=previous)
    json_path, md_path = write_funnel_report(report, report_root=default_funnel_report_root(REPO))

    if args.json:
        print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
        return

    print(f"Funnel report written:\n  {md_path}\n  {json_path}\n")
    for stage in report.stages:
        delta = "" if stage.delta == 0 else f"  ({'+' if stage.delta > 0 else ''}{stage.delta})"
        conv = "" if stage.conversion_pct is None else f"  [{stage.conversion_pct:g}% of prev]"
        flag = "" if stage.available else "  (no source)"
        print(f"  {stage.label:<16} {stage.count:>7}{delta}{conv}{flag}")
    print(
        f"\n  MRR (catalog): ${report.mrr_cents / 100:,.2f}"
        f"  ·  active clients: {report.active_clients}"
    )
    if report.zero_data:
        print("\n  Stages with zero data:")
        for item in report.zero_data:
            print(f"    - {item}")


if __name__ == "__main__":
    main()
