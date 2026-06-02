#!/usr/bin/env python3
"""Write prospect cohort markdown reports."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from packages.prospecting.report import (  # noqa: E402
    parse_phase1_cohort_counts,
    write_cohort_report,
    write_phase2_cohort_report,
)
from packages.prospecting.storage import ProspectRepository  # noqa: E402
from packages.prospecting.verification import default_exports_root  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render prospect cohort report")
    parser.add_argument("--phase", choices=["1", "2"], default="1")
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args(argv)

    records = ProspectRepository().list()
    if args.phase == "2":
        path = write_phase2_cohort_report(
            records,
            before_counts=parse_phase1_cohort_counts(),
            exported_count=_latest_export_count(),
            path=args.output,
        )
    else:
        path = write_cohort_report(records, args.output)
    print(path)
    return 0


def _latest_export_count() -> int:
    exports = sorted(default_exports_root().glob("seattle-cohortA-*.csv"))
    if not exports:
        return 0
    return max(0, len(exports[-1].read_text().splitlines()) - 1)


if __name__ == "__main__":
    raise SystemExit(main())
