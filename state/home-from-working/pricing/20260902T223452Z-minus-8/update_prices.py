"""One-time, baseline-relative price update for the five reviewed shirts."""

import json
import os
import ssl
import sys
import urllib.error
import urllib.request
from pathlib import Path

import certifi

from packages.config.secrets import require_secret


ROOT = Path(__file__).resolve().parent
BASELINE = json.loads((ROOT / "before.json").read_text())
SHOP_ID = BASELINE["shop_id"]
TOKEN = require_secret("PRINTIFY_API_TOKEN", source="keychain")
CONTEXT = ssl.create_default_context(cafile=certifi.where())
WRITABLE_VARIANT_FIELDS = ("id", "sku", "price", "is_enabled", "is_default")


def save(name, value):
    path = ROOT / name
    path.write_text(json.dumps(value, indent=2))
    os.chmod(path, 0o600)


def request(method, path, payload=None):
    req = urllib.request.Request(
        "https://api.printify.com/v1/" + path,
        data=None if payload is None else json.dumps(payload).encode(),
        method=method,
        headers={
            "Authorization": "Bearer " + TOKEN,
            "User-Agent": "HomeFromWorking-Codex-PriceUpdate",
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=40, context=CONTEXT) as response:
            body = response.read()
            return json.loads(body) if body else {}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace").replace(TOKEN, "[REDACTED]")
        raise RuntimeError(f"HTTP {exc.code} for {method} {path}: {detail[:2000]}") from None


def variant_payload(product, *, reduce=False):
    variants = []
    for original in product["variants"]:
        variant = {key: original[key] for key in WRITABLE_VARIANT_FIELDS}
        if reduce and original["is_enabled"]:
            variant["price"] -= 800
            assert variant["price"] > original["cost"], "Target below production cost"
        variants.append(variant)
    return sorted(variants, key=lambda v: v["id"])


def unchanged_product_fields(before, after):
    def stable(value):
        # Printify regenerates a renderer imageId on reads; asset id and
        # every artwork/placement property still participate in comparison.
        if isinstance(value, dict):
            return {key: stable(item) for key, item in value.items() if key != "imageId"}
        if isinstance(value, list):
            return [stable(item) for item in value]
        return value

    fields = (
        "title", "description", "tags", "safety_information", "blueprint_id",
        "print_provider_id", "print_areas", "print_details", "options",
        "images", "external", "visible", "sales_channel_properties",
        "is_printify_express_enabled", "is_economy_shipping_enabled",
    )
    def comparable(product, key):
        value = stable(product.get(key))
        if key == "print_areas":
            for area in value:
                # The variant-only update normalizes these area defaults.
                # All reviewed shirts are white; per-layer font colors,
                # asset IDs, transforms, and mockups remain checked exactly.
                if area.get("background") in (None, "transparent"):
                    area.pop("background", None)
                if area.get("font_color") == "auto":
                    area["font_color"] = "#000"
        return value

    return [key for key in fields if comparable(before, key) != comparable(after, key)]


def update(product):
    assert product["shop_id"] == SHOP_ID and product["blueprint_id"] == 6
    product_id = product["id"]
    path = f"shops/{SHOP_ID}/products/{product_id}.json"
    current = request("GET", path)
    target = variant_payload(product, reduce=True)
    current_variants = variant_payload(current)
    if current_variants == target:
        result = "already_at_target"
    else:
        assert current_variants == variant_payload(product), "Prices or variants changed since snapshot"
        assert not current["is_locked"], "Product is locked"
        assert not unchanged_product_fields(product, current), "Product changed since snapshot"
        save(product_id + "-request.json", {"variants": target})
        request("PUT", path, {"variants": target})
        result = "updated"
    after = request("GET", path)
    save(product_id + "-after.json", after)
    assert variant_payload(after) == target, "Saved prices or variants differ from target"
    changes = unchanged_product_fields(product, after)
    assert not changes, "Unexpected product changes: " + ", ".join(changes)
    summary = {
        "id": product_id,
        "title": product["title"],
        "result": result,
        "verified": True,
        "enabled_variant_count": sum(v["is_enabled"] for v in after["variants"]),
        "prices": {v["title"]: v["price"] for v in after["variants"] if v["is_enabled"]},
        "unchanged_fields_verified": True,
    }
    save(product_id + "-verification.json", summary)
    print(json.dumps(summary), flush=True)


if __name__ == "__main__":
    requested = sys.argv[1:]
    products = {p["id"]: p for p in BASELINE["products"]}
    assert requested and set(requested) <= products.keys(), "Use reviewed product IDs"
    for identifier in requested:
        update(products[identifier])
