#!/usr/bin/env python3
"""Generate ad creative for a client (real photos first, AI fallback).

Real-photo path (preferred) — cover-fit the client's photos to every ad size,
plus promo overlays:

    python scripts/agency/generate_ad_creative.py --product-id joes-plumbing-site \\
        --photo ~/joe/storefront.jpg --photo ~/joe/van.jpg \\
        --headline "Spring Drain Special"

AI fallback path — no client photos; generate from concepts (Gemini):

    python scripts/agency/generate_ad_creative.py --product-id joes-plumbing-site \\
        --concepts-json concepts.json --headline "Free Estimates"

concepts.json: [{"name":"lifestyle","prompt":"...","fallback_prompt":"...","headline":"..."}]

Output: state/clients/<product_id>/ads/creative/ (override with --out). Drafts only —
operator reviews and uploads; go-live stays gated (ad_campaign_go_live).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from packages.agency.ad_creative import (  # noqa: E402
    DEFAULT_ASPECTS,
    CreativeConcept,
    generate_ad_creative,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--product-id", required=True)
    parser.add_argument(
        "--out", type=Path, help="output dir (default: state/clients/<id>/ads/creative)"
    )
    parser.add_argument(
        "--photo", action="append", default=[], type=Path, help="client photo (repeatable)"
    )
    parser.add_argument("--concepts-json", type=Path, help="JSON list of AI concepts (fallback)")
    parser.add_argument(
        "--headline", action="append", default=[], help="promo overlay headline (repeatable)"
    )
    parser.add_argument(
        "--aspect",
        action="append",
        default=[],
        help=f"aspect ratio (default: {', '.join(DEFAULT_ASPECTS)})",
    )
    parser.add_argument("--no-overlays", action="store_true")
    args = parser.parse_args()

    concepts: list[CreativeConcept] = []
    if args.concepts_json:
        raw = json.loads(args.concepts_json.read_text(encoding="utf-8"))
        concepts = [
            CreativeConcept(
                name=str(c.get("name", f"concept-{i + 1}")),
                prompt=str(c["prompt"]),
                fallback_prompt=str(c.get("fallback_prompt", "")),
                headline=str(c.get("headline", "")),
            )
            for i, c in enumerate(raw)
        ]

    out = args.out or (REPO / "state" / "clients" / args.product_id / "ads" / "creative")
    try:
        result = generate_ad_creative(
            product_id=args.product_id,
            out_dir=out,
            concepts=concepts,
            client_photos=args.photo,
            promo_headlines=args.headline,
            aspect_ratios=args.aspect or DEFAULT_ASPECTS,
            make_overlays=not args.no_overlays,
        )
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(result.to_dict(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
