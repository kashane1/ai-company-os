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
    relevant_test_paths_for_lane,
)
from packages.schemas.testing import TestLane, ValidationFailureCode  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--changed-files", required=True, help="Path to a git --name-status file.")
    parser.add_argument(
        "--metadata-file",
        default="",
        help="Optional markdown file containing a ## Testing section, such as a PR body.",
    )
    parser.add_argument(
        "--event-name",
        default="pull_request",
        help=(
            "GitHub event name. The PR-body `## Testing` metadata gate is "
            "only enforced for `pull_request`; other events (e.g. `push`) "
            "carry no PR body, so that gate is reported but not failed. "
            "Defaults to `pull_request` so the strict path is fail-closed."
        ),
    )
    args = parser.parse_args()

    # The `## Testing` metadata gate is a pull-request-review-time check.
    # A `push` event (e.g. a merge landing on main) has no PR body, so the
    # gate cannot be evaluated — and it was already enforced when the
    # change merged as a pull request. `pull_request` keeps full
    # enforcement; anything else only reports what the diff alone shows.
    pr_context = args.event_name == "pull_request"

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

        if (
            not pr_context
            and result.failure_code is ValidationFailureCode.MISSING_TESTING_METADATA
        ):
            # No PR body on this event. Report what the diff alone shows
            # (matching test files present?) and do not fail — the
            # `## Testing` gate ran when this change merged as a PR.
            test_paths = relevant_test_paths_for_lane(changes, lane)
            if test_paths:
                print(
                    f"{lane.value}: logic change shipped with "
                    f"{len(test_paths)} matching test file(s) in the diff; "
                    f"PR-body metadata check is pull_request-only"
                )
            else:
                print(
                    f"{lane.value}: PR-body `## Testing` metadata check is "
                    f"pull_request-only; not enforced on {args.event_name!r} "
                    f"events (enforced when this change merged as a PR)"
                )
            continue

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
