#!/usr/bin/env python3
"""Rich Place Details gather for a demo-site build (Checkpoint A).

Fetches the full Place Details payload for a single lead — including review TEXT
and photo references (the demo-site posture per docs/demo-site-build-playbook.md:
Google/owner photos + 5 review texts are fine for a private owner preview) — then
downloads up to N photos via the Places photo-media endpoint.

Writes, mirroring the proven Skyline layout:
  state/prospects/sites/<PID>/source/place-details.json
  state/prospects/sites/<PID>/source/photos/photo_NN.jpg
  state/prospects/sites/<PID>/source/photos/_meta.json   (dims, bytes, attribution)

USAGE
-----
  python scripts/agency/gather_place.py --place-id <PID> [--max-photos 10]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import httpx

REPO = Path(__file__).resolve().parents[2]
SITES = REPO / "state" / "prospects" / "sites"
ENDPOINT = "https://places.googleapis.com/v1"

# Rich mask for an on-demand single-lead demo build: facts + attributes + the up
# to 5 review texts + up to 10 photo refs Google returns. (Broader than the
# cohort/prospecting mask, which deliberately omits review text & photos.)
RICH_MASK = ",".join(
    [
        "id",
        "displayName",
        "formattedAddress",
        "shortFormattedAddress",
        "nationalPhoneNumber",
        "internationalPhoneNumber",
        "types",
        "primaryTypeDisplayName",
        "rating",
        "userRatingCount",
        "websiteUri",
        "googleMapsUri",
        "location",
        "businessStatus",
        "priceLevel",
        "priceRange",
        "regularOpeningHours",
        "currentOpeningHours",
        "editorialSummary",
        "reviews",
        "photos",
        "paymentOptions",
        "parkingOptions",
        "accessibilityOptions",
        "outdoorSeating",
        "servesCoffee",
        "servesBreakfast",
        "servesBrunch",
        "servesLunch",
        "servesVegetarianFood",
        "servesDessert",
        "takeout",
        "dineIn",
        "delivery",
        "goodForChildren",
        "goodForGroups",
        "restroom",
        "allowsDogs",
        "menuForChildren",
        "reservable",
    ]
)


def load_env_key() -> str:
    key = os.environ.get("GOOGLE_PLACES_API_KEY", "")
    if key:
        return key
    envf = REPO / ".env"
    if envf.exists():
        for line in envf.read_text().splitlines():
            line = line.strip()
            if line.startswith("GOOGLE_PLACES_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--place-id", required=True)
    ap.add_argument("--max-photos", type=int, default=10)
    args = ap.parse_args()

    key = load_env_key()
    if not key:
        print("ERROR: GOOGLE_PLACES_API_KEY not set (.env or env)", file=sys.stderr)
        return 1

    pid = args.place_id
    out = SITES / pid / "source"
    photos_dir = out / "photos"
    photos_dir.mkdir(parents=True, exist_ok=True)

    client = httpx.Client(timeout=30.0)

    # 1. Rich details
    resp = client.get(
        f"{ENDPOINT}/places/{pid}",
        headers={
            "Content-Type": "application/json",
            "X-Goog-Api-Key": key,
            "X-Goog-FieldMask": RICH_MASK,
        },
    )
    if resp.status_code != 200:
        print(f"ERROR details {resp.status_code}: {resp.text[:500]}", file=sys.stderr)
        return 1
    data = resp.json()
    (out / "place-details.json").write_text(json.dumps(data, indent=2, ensure_ascii=False))
    name = (data.get("displayName") or {}).get("text", pid)
    print(f"✓ {name}  rating={data.get('rating')} ({data.get('userRatingCount')})")
    print(f"  reviews={len(data.get('reviews', []))}  photos={len(data.get('photos', []))}")

    # 2. Download photos via the media endpoint
    meta = []
    for i, ph in enumerate(data.get("photos", [])[: args.max_photos]):
        name_ref = ph.get("name")  # places/PID/photos/REF
        if not name_ref:
            continue
        media = client.get(
            f"{ENDPOINT}/{name_ref}/media",
            params={"maxHeightPx": 1600, "maxWidthPx": 1600, "skipHttpRedirect": "true"},
            headers={"X-Goog-Api-Key": key},
        )
        if media.status_code != 200:
            print(f"  photo {i} meta {media.status_code}", file=sys.stderr)
            continue
        uri = media.json().get("photoUri")
        if not uri:
            continue
        img = client.get(uri)
        if img.status_code != 200:
            continue
        fp = photos_dir / f"photo_{i:02d}.jpg"
        fp.write_bytes(img.content)
        attrs = [a.get("displayName", "") for a in ph.get("authorAttributions", [])]
        meta.append(
            {
                "i": i,
                "file": str(fp.relative_to(REPO)),
                "w": ph.get("widthPx"),
                "h": ph.get("heightPx"),
                "bytes": len(img.content),
                "attr": attrs,
            }
        )
        print(f"  ↓ photo_{i:02d}.jpg  {ph.get('widthPx')}x{ph.get('heightPx')}  {len(img.content)//1024}KB  {attrs}")

    (photos_dir / "_meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False))
    print(f"✓ {len(meta)} photos → {photos_dir.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
