#!/usr/bin/env python3
"""Operate the human-gated outreach lane.

Drafting and tracking are automated. Sending email, SMS, Instagram, or Facebook
messages is not automated here.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from packages.agency.outreach_lane import (  # noqa: E402
    OutreachLaneStatus,
    default_outreach_lane_root,
    load_existing_rows,
    log_manual_touch,
    refresh_client_status,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    refresh = sub.add_parser("refresh", help="refresh client-status.json and client-status.md")
    refresh.add_argument("--json", action="store_true", help="print JSON summary")

    listing = sub.add_parser("list", help="list ledger rows")
    listing.add_argument("--status", choices=[s.value for s in OutreachLaneStatus])
    listing.add_argument("--limit", type=int, default=0)
    listing.add_argument("--json", action="store_true", help="print rows as JSON")

    log = sub.add_parser("log", help="log a manual outreach touch")
    log.add_argument("--place-id", required=True)
    log.add_argument("--channel", required=True, help="email, sms_or_call, instagram_dm, facebook_dm, phone")
    log.add_argument("--outcome", required=True, help="sent, replied, follow_up_due, won, lost, do_not_contact, blocked")
    log.add_argument("--occurred-at", default="")
    log.add_argument("--next-follow-up", default="")
    log.add_argument("--notes", default="")
    log.add_argument("--json", action="store_true", help="print updated row as JSON")

    args = parser.parse_args()

    if args.command == "refresh":
        rows = refresh_client_status(repo_root=REPO)
        summary = {
            "rows": len(rows),
            "client_status_json": str(default_outreach_lane_root(REPO) / "client-status.json"),
            "client_status_md": str(default_outreach_lane_root(REPO) / "client-status.md"),
        }
        print(json.dumps(summary, indent=2) if args.json else _refresh_text(summary))
        return

    if args.command == "list":
        rows = [row for row in load_existing_rows(default_outreach_lane_root(REPO)).values()]
        if args.status:
            rows = [row for row in rows if row.get("status") == args.status]
        if args.limit:
            rows = rows[: args.limit]
        if args.json:
            print(json.dumps(rows, indent=2, sort_keys=True))
        else:
            for row in rows:
                print(
                    "{status:16} {name:42} {city:18} {channel:16} {action}".format(
                        status=str(row.get("status", "")),
                        name=str(row.get("business_name", ""))[:42],
                        city=str(row.get("city", ""))[:18],
                        channel=str(row.get("manual_channel") or row.get("recommended_channel", ""))[:16],
                        action=str(row.get("next_action", "")),
                    )
                )
        return

    if args.command == "log":
        row = log_manual_touch(
            args.place_id,
            channel=args.channel,
            outcome=args.outcome,
            lane_root=default_outreach_lane_root(REPO),
            occurred_at=args.occurred_at,
            next_follow_up_at=args.next_follow_up,
            notes=args.notes,
        )
        print(json.dumps(row.to_dict(), indent=2, sort_keys=True) if args.json else f"updated {row.place_id}: {row.status.value}")


def _refresh_text(summary: dict[str, object]) -> str:
    return "\n".join(
        [
            f"refreshed {summary['rows']} outreach client rows",
            f"status list: {summary['client_status_md']}",
            f"machine ledger: {summary['client_status_json']}",
        ]
    )


if __name__ == "__main__":
    main()
