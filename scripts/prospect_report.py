#!/usr/bin/env python3
"""Write the Phase 1 prospect cohort markdown report."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from packages.prospecting.report import write_cohort_report  # noqa: E402
from packages.prospecting.storage import ProspectRepository  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render prospect cohort report")
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args(argv)

    path = write_cohort_report(ProspectRepository().list(), args.output)
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

