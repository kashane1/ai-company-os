#!/usr/bin/env python3
"""Download the fixed 6+6 hoodie/crewneck mockup block for an MPL draft."""

import argparse
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import httpx

from packages.config.secrets import require_secret
from packages.pod.runner import PrintifyClient

PICKS = [
    ("hoodie", "front-2", "Sport Grey", "09-hoodie-front-2-sport-grey.jpg"),
    ("hoodie", "lifestyle-2", "Light Blue", "10-hoodie-lifestyle-2-light-blue.jpg"),
    ("hoodie", "lifestyle", "Indigo Blue", "11-hoodie-lifestyle-indigo-blue.jpg"),
    ("hoodie", "person-1", "Light Pink", "12-hoodie-person-1-light-pink.jpg"),
    ("hoodie", "front", "Sand", "13-hoodie-front-sand.jpg"),
    ("hoodie", "size-chart", "White", "14-hoodie-size-chart-white.jpg"),
    ("crew", "folded-2", "Gold", "15-crew-folded-2-gold.jpg"),
    ("crew", "lifestyle", "Light Pink", "16-crew-lifestyle-light-pink.jpg"),
    ("crew", "person-4", "Light Pink", "17-crew-person-4-light-pink.jpg"),
    ("crew", "person-3", "Light Blue", "18-crew-person-3-light-blue.jpg"),
    ("crew", "person-3-back", "Light Blue", "19-crew-person-3-back-light-blue.jpg"),
    ("crew", "size-chart", "White", "20-crew-size-chart-white.jpg"),
]


def camera(image):
    return (parse_qs(urlparse(image["src"]).query).get("camera_label") or [""])[0]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--hoodie", required=True)
    parser.add_argument("--crew", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    client = PrintifyClient(require_secret("PRINTIFY_API_TOKEN", source="keychain"))
    try:
        products = {
            "hoodie": client.get_product(args.hoodie),
            "crew": client.get_product(args.crew),
        }
    finally:
        client.close()

    args.output.mkdir(parents=True, exist_ok=True)
    with httpx.Client(follow_redirects=True, timeout=45) as http:
        for product_name, camera_label, color, filename in PICKS:
            product = products[product_name]
            variant_titles = {v["id"]: v["title"] for v in product["variants"]}
            candidates = []
            for image in product["images"]:
                if camera(image) != camera_label:
                    continue
                variant_id = int(image["mockup_id"].split("_")[1])
                if color in variant_titles.get(variant_id, "").split(" / "):
                    candidates.append(image)
            if len(candidates) != 1:
                raise RuntimeError(
                    f"Expected one {product_name} {camera_label} {color} image, got {len(candidates)}"
                )
            response = http.get(candidates[0]["src"])
            response.raise_for_status()
            output = args.output / filename
            output.write_bytes(response.content)
            print(f"{filename}: {len(response.content)} bytes")


if __name__ == "__main__":
    main()
