#!/usr/bin/env python3

from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from packages.policies.testing import (  # noqa: E402
    evaluate_testing_policy,
    logic_paths_for_lane,
    parse_name_status_lines,
    parse_testing_metadata,
)
from packages.schemas.testing import TestLane  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--changed-files", required=True, help="Path to a git --name-status file.")
    parser.add_argument(
        "--metadata-file",
        default="",
        help="Optional markdown file containing a ## Testing section, such as a PR body.",
    )
    args = parser.parse_args()

    changed_lines = Path(args.changed_files).read_text().splitlines()
    changes = parse_name_status_lines(changed_lines)
    metadata = None
    if args.metadata_file:
        metadata_path = Path(args.metadata_file)
        if metadata_path.exists():
            metadata = parse_testing_metadata(metadata_path.read_text())

    failures: list[str] = []
    checked_any_lane = False
    for lane in (TestLane.PYTHON, TestLane.IOS):
        logic_paths = logic_paths_for_lane(changes, lane)
        if not logic_paths:
            continue
        checked_any_lane = True
        result = evaluate_testing_policy(lane=lane, changes=changes, testing_metadata=metadata)
        if result.failure_code:
            failures.append(f"{lane.value}: {result.failure_code.value} ({result.details})")
        else:
            print(f"{lane.value}: pass - {result.details}")

    if not checked_any_lane:
        print("No logic-bearing Python or iOS source changes detected.")
        return 0

    if failures:
        for failure in failures:
            print(failure)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
