#!/usr/bin/env python3
"""Phase 5 — run the client launch checklist and mark the engagement live.

Examples::

    python scripts/agency/launch_client.py check \\
        --product-id joes-plumbing-site \\
        --dist products/joes-plumbing-site/dist \\
        --gbp-url 'https://maps.google.com/?cid=123' \\
        --analytics-id plausible-joes-plumbing \\
        --deploy-approved --dns-approved

    python scripts/agency/launch_client.py mark-live ...  # same flags; fails closed
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from packages.agency.client_lifecycle import (  # noqa: E402
    LaunchNotReadyError,
    mark_client_live,
    run_client_launch_checklist,
)
from packages.agency.registry import (  # noqa: E402
    get_registry_record,
    set_client_netlify_site_id,
    set_client_plausible_site_id,
)


def _report_dict(report) -> dict:
    return report.to_dict()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="command", required=True)

    for name in ("check", "mark-live"):
        cmd = sub.add_parser(name, help="run checklist" if name == "check" else "check + set phase live")
        cmd.add_argument("--product-id", required=True)
        cmd.add_argument("--dist", type=Path, required=True, help="built site dist/ directory")
        cmd.add_argument("--gbp-url", default="", help="Google Business Profile URL (must appear in HTML)")
        cmd.add_argument("--analytics-id", default="", help="analytics tag id/domain (must appear in HTML)")
        cmd.add_argument(
            "--deploy-approved",
            action="store_true",
            help="record that production deploy approval was granted",
        )
        cmd.add_argument(
            "--dns-approved",
            action="store_true",
            help="record that custom-domain/DNS approval was granted",
        )
        cmd.add_argument("--pass-threshold", type=int, default=70)
        cmd.add_argument(
            "--netlify-site-id",
            default="",
            help="client's Netlify site id; stamped on mark-live for lead-health monitoring",
        )
        cmd.add_argument(
            "--plausible-site-id",
            default="",
            help="client's Plausible site id; stamped on mark-live for the monthly report",
        )

    args = ap.parse_args()
    dist = args.dist if args.dist.is_absolute() else REPO / args.dist
    if not dist.is_dir():
        print(f"ERROR: dist not found: {dist}", file=sys.stderr)
        return 1

    reg = get_registry_record(args.product_id)
    if reg.get("type") != "client-site":
        print(f"ERROR: {args.product_id!r} is not a client-site", file=sys.stderr)
        return 1

    try:
        if args.command == "check":
            report = run_client_launch_checklist(
                dist,
                gbp_url=args.gbp_url,
                analytics_id=args.analytics_id,
                deploy_approved=args.deploy_approved,
                dns_approved=args.dns_approved,
                pass_threshold=args.pass_threshold,
            )
        else:
            report = mark_client_live(
                args.product_id,
                dist,
                gbp_url=args.gbp_url,
                analytics_id=args.analytics_id,
                deploy_approved=args.deploy_approved,
                dns_approved=args.dns_approved,
                pass_threshold=args.pass_threshold,
            )
    except LaunchNotReadyError as exc:
        print(f"NOT READY: {exc}", file=sys.stderr)
        return 2

    print(json.dumps(_report_dict(report), indent=2))
    if report.ready:
        # Persist the client's Netlify site id at launch so the lead-health drain
        # can find their inbound-leads store. Only on mark-live (the live event).
        if args.command == "mark-live" and args.netlify_site_id:
            set_client_netlify_site_id(args.product_id, args.netlify_site_id)
            print(f"recorded netlify_site_id={args.netlify_site_id} for {args.product_id}")
        if args.command == "mark-live" and args.plausible_site_id:
            set_client_plausible_site_id(args.product_id, args.plausible_site_id)
            print(f"recorded plausible_site_id={args.plausible_site_id} for {args.product_id}")
        print(f"\n{'LIVE' if args.command == 'mark-live' else 'READY'} — {args.product_id}")
        return 0
    print("\nFAILED items:", file=sys.stderr)
    for item in report.failures():
        print(f"  - {item.name}: {item.detail}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
