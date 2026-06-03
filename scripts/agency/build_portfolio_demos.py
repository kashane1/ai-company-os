#!/usr/bin/env python3
"""Build the fictional portfolio demos for the Better Business Web landing page.

These are NOT prospects. They are invented businesses (no real Places data,
no real names) used as honest "concept demo" samples in the agency's own
portfolio — one per unique genre planned for the landing page
(see docs/products/better-business-web/LANDING_PAGE_PLAN.md).

Each demo is rendered with the same per-genre theme engine as the prospect
previews (so the portfolio shows real variety) and carries a visible
concept-demo footer so nobody mistakes it for a live client site.

    python scripts/agency/build_portfolio_demos.py            # build locally
    python scripts/agency/build_portfolio_demos.py --deploy    # + draft-deploy to shared site
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from packages.agency.demo_theme import apply_theme, theme_for_record  # noqa: E402
from packages.agency.prospect_site import intake_from_record  # noqa: E402
from packages.web.deploy import NetlifyDeployTarget  # noqa: E402
from packages.web.scaffold import render_landing_html, unfilled_tokens  # noqa: E402

OUT_ROOT = REPO / "products" / "better-business-web" / "portfolio"
PREVIEW_SITE_NAME = "bbw-portfolio"  # shared site; drafts give per-demo permalinks

CONCEPT_NOTE = "Concept demo — illustrative sample design by Better Business Web. Not a real business."

# Fictional businesses (invented names/towns/phones). One per planned genre.
DEMOS: list[dict] = [
    {
        "place_id": "bbw-demo-auto_repair",
        "genre_id": "auto_repair",
        "display_name": "Ironside Auto Works",
        "city_id": "maplewood",
        "formatted_address": "1200 Birch Ave, Maplewood, OR 97000, USA",
        "phone": "(503) 555-0142",
    },
    {
        "place_id": "bbw-demo-barber_shop",
        "genre_id": "barber_shop",
        "display_name": "Kingsway Barber Co.",
        "city_id": "brighton",
        "formatted_address": "88 Harbor St, Brighton, MA 02135, USA",
        "phone": "(617) 555-0188",
    },
    {
        "place_id": "bbw-demo-bakery",
        "genre_id": "bakery",
        "display_name": "Goldenrod Bakehouse",
        "city_id": "sutton",
        "formatted_address": "5 Mill Lane, Sutton, VT 05867, USA",
        "phone": "(802) 555-0119",
    },
    {
        "place_id": "bbw-demo-dog_groomer",
        "genre_id": "dog_groomer",
        "display_name": "Wagtail Grooming Studio",
        "city_id": "cedar_falls",
        "formatted_address": "210 Cedar Rd, Cedar Falls, IA 50613, USA",
        "phone": "(319) 555-0173",
    },
    {
        "place_id": "bbw-demo-plumber",
        "genre_id": "plumber",
        "display_name": "TrueLine Plumbing",
        "city_id": "westbrook",
        "formatted_address": "47 Forest Ave, Westbrook, ME 04092, USA",
        "phone": "(207) 555-0151",
    },
    {
        "place_id": "bbw-demo-nail_salon",
        "genre_id": "nail_salon",
        "display_name": "Lumière Nail Lounge",
        "city_id": "park_hill",
        "formatted_address": "1330 Aspen Way, Park Hill, CO 80220, USA",
        "phone": "(720) 555-0166",
    },
]


def render_demo_html(record: dict) -> str:
    """Render a themed, concept-labeled demo page (no real Places data)."""
    context = intake_from_record(record).to_site_context()
    context["FOOTER_NOTE"] = CONCEPT_NOTE  # honest labeling
    html = render_landing_html(context)
    leftover = unfilled_tokens(html)
    if leftover:
        raise ValueError(f"unfilled template tokens: {leftover}")
    return apply_theme(html, theme_for_record(record))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--deploy", action="store_true", help="draft-deploy each demo to the shared portfolio site")
    args = ap.parse_args()

    target = NetlifyDeployTarget() if args.deploy else None
    site = target.ensure_site(PREVIEW_SITE_NAME) if target else None

    manifest = []
    for demo in DEMOS:
        genre = demo["genre_id"]
        out_dir = OUT_ROOT / genre / "dist"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_dir.joinpath("index.html").write_text(render_demo_html(demo), encoding="utf-8")
        theme = theme_for_record(demo)
        entry = {
            "genre_id": genre,
            "business": demo["display_name"],
            "dist": str(out_dir),
            "theme": theme.to_dict(),
            "url": "",
        }
        if target and site:
            result = target.deploy(site, out_dir, production=False)  # draft preview
            entry["url"] = result.url
            print(f"  ✓ {demo['display_name']:24s} ({genre})  →  {result.url}")
        else:
            print(f"  ✓ {demo['display_name']:24s} ({genre})  →  {out_dir / 'index.html'}")
        manifest.append(entry)

    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    (OUT_ROOT / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"\n{len(manifest)} portfolio demo(s). Manifest: {OUT_ROOT / 'manifest.json'}")


if __name__ == "__main__":
    main()
