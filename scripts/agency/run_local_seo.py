#!/usr/bin/env python3
"""Generate approved local SEO pages for a client Astro site."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from packages.agency.client_lifecycle import client_paths  # noqa: E402
from packages.agency.local_seo import (  # noqa: E402
    LocalSeoMatrixError,
    emit_seo_pages_to_site,
    generate_matrix,
    parse_local_seo_matrix,
)
from packages.agency.registry import get_registry_record  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--product-id", required=True)
    parser.add_argument("--docs-root", type=Path)
    parser.add_argument("--site-root", type=Path)
    parser.add_argument("--site-url", default="https://example.com")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    record = get_registry_record(args.product_id)
    if record.get("type") != "client-site":
        print(f"ERROR: {args.product_id!r} is not a client-site", file=sys.stderr)
        return 1

    docs_root, site_root = client_paths(args.product_id)
    docs_root = args.docs_root or docs_root
    site_root = args.site_root or site_root
    try:
        matrix = parse_local_seo_matrix(docs_root / "LOCAL_SEO.md")
        pages = generate_matrix(
            str(record.get("name", args.product_id)),
            matrix.services,
            matrix.service_area_cities,
        )
    except (FileNotFoundError, LocalSeoMatrixError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if args.dry_run:
        print(json.dumps([page.to_dict() for page in pages], indent=2))
        return 0

    written = emit_seo_pages_to_site(site_root, pages, site_url=args.site_url)
    print(json.dumps({"written": [str(path.relative_to(REPO)) for path in written]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
