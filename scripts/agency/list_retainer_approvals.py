#!/usr/bin/env python3
"""List pending retainer approvals grouped by client product."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from packages.agency.approvals import pending_retainer_approvals  # noqa: E402
from packages.db.approval_store import ApprovalStore  # noqa: E402


def _row(approval) -> dict[str, object]:
    return {
        "approval_id": approval.id,
        "product_id": approval.subject_id,
        "approval_type": approval.approval_type,
        "action": approval.action,
        "summary": approval.summary,
        "review_artifact_path": approval.review_artifact_path,
        "created_at": approval.created_at,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--json", action="store_true", help="emit JSON")
    args = parser.parse_args()

    approvals = pending_retainer_approvals(
        ApprovalStore().list_recent(limit=args.limit)
    )
    rows = [_row(approval) for approval in approvals]
    if args.json:
        print(json.dumps(rows, indent=2))
        return 0
    if not rows:
        print("No pending retainer approvals.")
        return 0
    for row in rows:
        print(
            f"{row['product_id']}: {row['approval_type']} "
            f"({row['approval_id']}) — {row['summary']}"
        )
        if row["review_artifact_path"]:
            print(f"  artifact: {row['review_artifact_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
