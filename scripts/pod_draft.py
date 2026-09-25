#!/usr/bin/env python3
"""Operate one native Printify duplicate; see docs/founder/printify-shirt-workflow.md."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from packages.config.secrets import require_secret  # noqa: E402
from packages.db.approval_store import ApprovalStore  # noqa: E402
from packages.pod.runner import (  # noqa: E402
    TEMPLATE_ID, PrintifyClient, apply_copy_run, apply_run, prepare_copy_run, prepare_run, read_json,
)
from packages.pod.template import mockup_signature  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    inspect = sub.add_parser("inspect", help="read the current template; no account writes")
    inspect.add_argument("--product-id", default=TEMPLATE_ID)
    prepare = sub.add_parser("prepare", help="prepare a native duplicate; no account writes")
    prepare.add_argument("--template-id", default=TEMPLATE_ID)
    prepare.add_argument("--draft-id", required=True)
    prepare.add_argument("--artwork", required=True, type=Path)
    prepare.add_argument("--copy", required=True, type=Path)
    prepare.add_argument("--run-dir", required=True, type=Path)
    prepare.add_argument("--scale-percent", type=float,
                         help="editor scale relative to original pixels at 300 DPI; centers and fits within print area")
    apply = sub.add_parser("apply", help="apply an exact approved draft revision; never publish")
    apply.add_argument("--run-dir", required=True, type=Path)
    apply.add_argument("--approval-id", required=True)
    prepare_copy = sub.add_parser(
        "prepare-copy", help="prepare copy after artwork was placed in the Printify editor"
    )
    prepare_copy.add_argument("--template-id", default=TEMPLATE_ID)
    prepare_copy.add_argument("--draft-id", required=True)
    prepare_copy.add_argument("--artwork", required=True, type=Path)
    prepare_copy.add_argument("--copy", required=True, type=Path)
    prepare_copy.add_argument("--run-dir", required=True, type=Path)
    prepare_copy.add_argument("--scale-percent", type=float)
    apply_copy = sub.add_parser("apply-copy", help="apply approved copy after a browser artwork edit")
    apply_copy.add_argument("--run-dir", required=True, type=Path)
    apply_copy.add_argument("--approval-id", required=True)
    args = parser.parse_args()
    client = PrintifyClient(require_secret("PRINTIFY_API_TOKEN", source="keychain"))
    try:
        if args.command == "inspect":
            product = client.get_product(args.product_id)
            result = {"id": product["id"], "title": product["title"],
                      "shop_id": product["shop_id"], "blueprint_id": product["blueprint_id"],
                      "print_provider_id": product["print_provider_id"],
                      "selected_mockups": len(mockup_signature(product)),
                      "linked_listing": bool((product.get("external") or {}).get("id")),
                      "prices": {v["title"]: v["price"] / 100 for v in product["variants"]
                                 if v["is_enabled"]}}
        elif args.command == "prepare":
            review = prepare_run(client, args.template_id, args.draft_id, args.artwork,
                                 read_json(args.copy), args.run_dir, scale_percent=args.scale_percent)
            result = {"status": "prepared", "revision": review["revision"],
                      "review": str(args.run_dir / "review.json"),
                      "approval_request": str(args.run_dir / "approval-request.json"),
                      "dpi": review["artwork"]["dpi"], "account_writes": 0}
        elif args.command == "prepare-copy":
            review = prepare_copy_run(client, args.template_id, args.draft_id, args.artwork,
                                      read_json(args.copy), args.run_dir,
                                      scale_percent=args.scale_percent)
            result = {"status": "prepared", "revision": review["revision"],
                      "review": str(args.run_dir / "review.json"),
                      "approval_request": str(args.run_dir / "approval-request.json"),
                      "dpi": review["artwork"]["dpi"], "account_writes": 0}
        elif args.command == "apply":
            result = apply_run(client, args.run_dir, ApprovalStore().load(args.approval_id))
        else:
            result = apply_copy_run(client, args.run_dir, ApprovalStore().load(args.approval_id))
        print(json.dumps(result, indent=2))
        return 0
    except (ValueError, RuntimeError, FileNotFoundError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    finally:
        client.close()


if __name__ == "__main__":
    raise SystemExit(main())
