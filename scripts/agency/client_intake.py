#!/usr/bin/env python3
"""Phase 4 — apply client intake and scaffold the paid client Astro project.

After promotion (Phase 3), capture business details and materialize
``products/<slug>-site/`` from the web scaffold.

Examples::

    # From warehouse prospect (genre defaults + phone):
    python scripts/agency/client_intake.py --product-id joes-plumbing-site \\
        --from-prospect places/joe123

    # From explicit fields:
    python scripts/agency/client_intake.py --product-id joes-plumbing-site \\
        --business "Joe's Plumbing" --category plumbing --city Seattle \\
        --phone 206-555-0100 --service "Drain cleaning" --service "Leak repair"
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from packages.agency.client_lifecycle import (  # noqa: E402
    apply_client_intake,
    client_paths,
    intake_from_prospect,
    scaffold_client_product,
)
from packages.agency.intake import ClientIntake  # noqa: E402
from packages.agency.registry import get_registry_record  # noqa: E402
from packages.prospecting.storage import ProspectRepository  # noqa: E402


def _intake_from_args(args: argparse.Namespace) -> ClientIntake:
    if args.from_prospect:
        record = ProspectRepository().get(args.from_prospect)
        intake = intake_from_prospect(record)
        if args.business:
            intake = ClientIntake(
                business_name=args.business,
                service_category=args.category or intake.service_category,
                city=args.city or intake.city,
                services=args.services or intake.services,
                service_area_cities=args.service_area_cities or intake.service_area_cities,
                travel_radius_miles=(
                    args.travel_radius_miles
                    if args.travel_radius_miles is not None
                    else intake.travel_radius_miles
                ),
                service_area_notes=args.service_area_notes or intake.service_area_notes,
                matrix_approved=args.matrix_approved or intake.matrix_approved,
                phone=args.phone or intake.phone,
                hours=args.hours or intake.hours,
                ideal_customer=args.ideal_customer or intake.ideal_customer,
                site_url=args.site_url or intake.site_url,
            )
        return intake
    if not args.business or not args.category or not args.city:
        sys.exit("provide --from-prospect or --business, --category, and --city")
    return ClientIntake(
        business_name=args.business,
        service_category=args.category,
        city=args.city,
        services=args.services,
        service_area_cities=args.service_area_cities,
        travel_radius_miles=args.travel_radius_miles,
        service_area_notes=args.service_area_notes or "",
        matrix_approved=args.matrix_approved,
        phone=args.phone or "",
        hours=args.hours or "",
        ideal_customer=args.ideal_customer or "",
        site_url=args.site_url or "https://example.com",
    )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--product-id", required=True, help="client-site id from infra/products.json")
    ap.add_argument("--from-prospect", help="warehouse place_id to seed intake")
    ap.add_argument("--business")
    ap.add_argument("--category", help="service category, e.g. plumbing")
    ap.add_argument("--city")
    ap.add_argument("--phone")
    ap.add_argument("--hours")
    ap.add_argument("--ideal-customer")
    ap.add_argument("--site-url", default="https://example.com")
    ap.add_argument("--service", action="append", default=[], dest="services")
    ap.add_argument("--service-area-city", action="append", default=[], dest="service_area_cities")
    ap.add_argument("--travel-radius-miles", type=int)
    ap.add_argument("--service-area-notes", default="")
    ap.add_argument("--matrix-approved", action="store_true")
    ap.add_argument(
        "--scaffold-only",
        action="store_true",
        help="only write products/<id>-site/ (skip docs workspace refresh)",
    )
    ap.add_argument(
        "--docs-only",
        action="store_true",
        help="only refresh docs workspace (skip Astro scaffold)",
    )
    args = ap.parse_args()

    reg = get_registry_record(args.product_id)
    if reg.get("type") != "client-site":
        print(f"ERROR: {args.product_id!r} is not a client-site record", file=sys.stderr)
        return 1

    intake = _intake_from_args(args)
    try:
        intake.validate()
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    client = reg.get("client") or {}
    bundle_id = str(client.get("bundle", ""))
    from_prospect = str(client.get("from_prospect", ""))

    docs_root, source_root = client_paths(args.product_id)

    if not args.scaffold_only:
        written = apply_client_intake(
            docs_root,
            intake,
            bundle_id=bundle_id,
            from_prospect=from_prospect,
        )
        print(f"docs workspace → {docs_root}")
        for p in written[:5]:
            print(f"  · {p.relative_to(REPO)}")
        if len(written) > 5:
            print(f"  · … +{len(written) - 5} more")

    if not args.docs_only:
        product_dir = scaffold_client_product(args.product_id, intake)
        print(f"product scaffold → {product_dir}")
        print("  next: cd products/.../site && npm install && npm run build")
        print("  then: python scripts/agency/launch_client.py check --product-id ... --dist ...")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
