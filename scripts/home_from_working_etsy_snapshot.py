#!/usr/bin/env python3
"""Capture a sanitized, GET-only Etsy snapshot for HomeFromWorking.

The command intentionally has no Etsy write methods. Token rotation is the
only credential maintenance performed, and is persisted in the repository-root .etsy.env file.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from packages.config.secrets import get_secret
from packages.etsy.auth import (
    ACCESS_TOKEN_NAME,
    API_CREDENTIAL_NAME,
    EXPIRES_AT_NAME,
    READ_SCOPES,
    REFRESH_TOKEN_NAME,
    EtsyCredentials,
    EtsyOAuthToken,
    refresh_oauth_token,
)
from packages.etsy.client import EtsyReadOnlyClient
from packages.etsy.credentials import store_etsy_oauth_material


@dataclass(frozen=True)
class EtsyOAuthMaterial:
    credentials: EtsyCredentials
    token: EtsyOAuthToken
    composite_credential: str


def load_oauth_material(
    *,
    secret_loader: Callable[..., str | None] = get_secret,
) -> EtsyOAuthMaterial:
    def read(account: str) -> str:
        value = secret_loader(account, source="etsy_env")
        if not value:
            raise ValueError(f"missing Etsy .etsy.env value: {account}")
        return value

    composite = read(API_CREDENTIAL_NAME)
    credentials = EtsyCredentials.from_composite(composite)
    access = read(ACCESS_TOKEN_NAME)
    refresh = read(REFRESH_TOKEN_NAME)
    expires_raw = read(EXPIRES_AT_NAME)
    try:
        expires_at = datetime.fromisoformat(expires_raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("invalid Etsy OAuth expiry timestamp") from exc
    return EtsyOAuthMaterial(credentials, EtsyOAuthToken(access, refresh, expires_at), composite)


def maybe_refresh_token(
    token: EtsyOAuthToken,
    *,
    client_id: str,
    composite_credential: str,
    token_refresher: Callable[..., EtsyOAuthToken] = refresh_oauth_token,
    token_persister: Callable[..., None] = store_etsy_oauth_material,
    now: datetime | None = None,
) -> EtsyOAuthToken:
    if not token.is_expired(now=now):
        return token
    rotated = token_refresher(client_id=client_id, refresh_token=token.refresh_token)
    token_persister(
        composite_credential=composite_credential,
        access_token=rotated.access_token,
        refresh_token=rotated.refresh_token,
        expires_at=rotated.expires_at.astimezone(UTC).isoformat(),
    )
    return rotated


def _pick(source: dict[str, Any], *keys: str) -> dict[str, Any]:
    return {key: source[key] for key in keys if key in source and source[key] is not None}


def _results(payload: Any, *, context: str = "Etsy collection") -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        raise ValueError(f"{context} response must be an object")
    if "results" not in payload or not isinstance(payload["results"], list):
        raise ValueError(f"{context} response must contain a list named results")
    if any(not isinstance(item, dict) for item in payload["results"]):
        raise ValueError(f"{context} response contains a non-object result")
    return list(payload["results"])


def _complete_unpaged_results(
    payload: Any, *, context: str
) -> list[dict[str, Any]]:
    """Validate collections whose current Etsy route has no page parameters."""
    results = _results(payload, context=context)
    count = payload.get("count")
    if isinstance(count, bool) or not isinstance(count, int) or count < 0:
        raise ValueError(f"{context} response has an invalid count")
    if count != len(results):
        raise ValueError(
            f"{context} response is incomplete: count does not match results"
        )
    return results


def _sanitize_inventory(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        raise ValueError("Etsy inventory response must be an object")
    if "products" not in payload or not isinstance(payload["products"], list):
        raise ValueError("Etsy inventory response must contain a list named products")
    if any(not isinstance(product, dict) for product in payload["products"]):
        raise ValueError("Etsy inventory response contains a non-object product")
    products = []
    for product in payload["products"]:
        item = _pick(product, "product_id")
        item["property_values"] = []
        property_values = product.get("property_values", [])
        if not isinstance(property_values, list) or any(not isinstance(prop, dict) for prop in property_values):
            raise ValueError("Etsy inventory product property_values must be a list of objects")
        for prop in property_values:
            item["property_values"].append(_pick(prop, "property_id", "property_name", "value_ids", "values", "scale_id"))
        item["offerings"] = []
        offerings = product.get("offerings", [])
        if not isinstance(offerings, list) or any(not isinstance(offering, dict) for offering in offerings):
            raise ValueError("Etsy inventory product offerings must be a list of objects")
        for offering in offerings:
            item["offerings"].append(_pick(offering, "offering_id", "price", "quantity", "is_enabled", "enabled"))
        products.append(item)
    return sorted(products, key=lambda item: (item.get("product_id", 0), json.dumps(item, sort_keys=True)))


def _sanitize_listing(source: dict[str, Any], inventory: dict[str, Any]) -> dict[str, Any]:
    item = _pick(
        source,
        "listing_id", "title", "state", "description", "tags", "shipping_profile_id",
        "return_policy_id", "production_partner_ids", "image_ids", "who_made", "when_made",
        "created_timestamp", "updated_timestamp", "quantity",
    )
    item["inventory"] = _sanitize_inventory(inventory)
    return item


def _sanitize_profile(source: dict[str, Any], destinations: list[dict[str, Any]]) -> dict[str, Any]:
    item = _pick(source, "shipping_profile_id", "title", "origin_country_iso", "origin_postal_code", "processing_min", "processing_max")
    if any(not isinstance(destination, dict) for destination in destinations):
        raise ValueError("Etsy shipping destinations contain a non-object result")
    sanitized_destinations = []
    seen_destination_ids: set[int] = set()
    for destination in destinations:
        destination_id = destination.get("shipping_profile_destination_id")
        if not isinstance(destination_id, int) or isinstance(destination_id, bool) or destination_id <= 0:
            raise ValueError(
                "Etsy shipping destination is missing a positive integer "
                "shipping_profile_destination_id"
            )
        if destination_id in seen_destination_ids:
            raise ValueError(
                f"duplicate Etsy shipping_profile_destination_id: {destination_id}"
            )
        seen_destination_ids.add(destination_id)
        sanitized_destinations.append(
            _pick(
                destination,
                "shipping_profile_destination_id",
                "destination_country_iso",
                "primary_cost",
                "secondary_cost",
                "min_delivery_days",
                "max_delivery_days",
            )
        )
    item["destinations"] = sanitized_destinations
    item["destinations"].sort(key=lambda value: (value.get("shipping_profile_destination_id", 0), value.get("destination_country_iso", "")))
    return item


def resolve_output_path(
    observed_at: str,
    *,
    output: Path | None = None,
    base_dir: Path = Path("state/home-from-working/operations/evidence"),
    overwrite: bool = False,
) -> Path:
    if output is None:
        try:
            date_part = datetime.fromisoformat(observed_at.replace("Z", "+00:00")).date().isoformat()
        except ValueError as exc:
            raise ValueError("observed_at must be an ISO timestamp") from exc
        output = base_dir / date_part / "etsy-shop.json"
    if output.exists() and not overwrite:
        raise FileExistsError(f"snapshot already exists: {output}; pass --overwrite to replace it")
    return output


def collect_snapshot(api: EtsyReadOnlyClient, *, observed_at: str) -> dict[str, Any]:
    shop_results = list(api.iter_shops_by_name("HomeFromWorking"))
    if any(not isinstance(shop, dict) for shop in shop_results):
        raise ValueError("Etsy shop search results contain a non-object result")
    shops = [
        shop
        for shop in shop_results
        if shop.get("shop_name") == "HomeFromWorking"
    ]
    if len(shops) != 1:
        raise ValueError("expected exactly one Etsy shop named HomeFromWorking")
    shop_id = shops[0].get("shop_id")
    if not isinstance(shop_id, int):
        raise ValueError("Etsy shop response has no numeric shop_id")

    raw_shop = api.get_shop(shop_id)
    if not isinstance(raw_shop, dict):
        raise ValueError("Etsy shop response must be an object")
    listings: list[dict[str, Any]] = []
    listing_ids: set[int] = set()
    for listing in api.iter_active_listings(shop_id):
        listing_id = listing.get("listing_id")
        if not isinstance(listing_id, int) or isinstance(listing_id, bool) or listing_id <= 0:
            raise ValueError("Etsy active listing is missing a positive integer listing_id")
        if listing_id in listing_ids:
            raise ValueError(f"duplicate Etsy listing_id: {listing_id}")
        listing_ids.add(listing_id)
        detail = api.get_listing(listing_id)
        if not isinstance(detail, dict):
            raise ValueError("Etsy listing detail response must be an object")
        if detail.get("listing_id") != listing_id:
            raise ValueError("Etsy listing detail response has a mismatched listing_id")
        listings.append(_sanitize_listing(detail, api.get_listing_inventory(listing_id)))
    listings.sort(key=lambda value: value.get("listing_id", 0))

    # Etsy's current OpenAPI specification exposes no limit/offset parameters
    # for these two shop collections, so completeness is checked against count.
    raw_profiles = _complete_unpaged_results(
        api.get_shop_shipping_profiles(shop_id),
        context="Etsy shipping profiles",
    )
    profiles = []
    profile_ids: set[int] = set()
    for profile in raw_profiles:
        profile_id = profile.get("shipping_profile_id")
        if not isinstance(profile_id, int) or isinstance(profile_id, bool) or profile_id <= 0:
            raise ValueError("Etsy shipping profile is missing a positive integer shipping_profile_id")
        if profile_id in profile_ids:
            raise ValueError(f"duplicate Etsy shipping_profile_id: {profile_id}")
        profile_ids.add(profile_id)
        destinations = list(
            api.iter_shipping_profile_destinations(shop_id, profile_id)
        )
        profiles.append(_sanitize_profile(profile, destinations))
    profiles.sort(key=lambda value: value.get("shipping_profile_id", 0))

    partners = []
    partner_ids: set[int] = set()
    for partner in _complete_unpaged_results(
        api.get_shop_production_partners(shop_id),
        context="Etsy production partners",
    ):
        partner_id = partner.get("production_partner_id")
        if not isinstance(partner_id, int) or isinstance(partner_id, bool) or partner_id <= 0:
            raise ValueError("Etsy production partner is missing a positive integer production_partner_id")
        if partner_id in partner_ids:
            raise ValueError(f"duplicate Etsy production_partner_id: {partner_id}")
        partner_ids.add(partner_id)
        partners.append(_pick(partner, "production_partner_id", "partner_name", "location", "is_active", "is_deleted"))
    partners.sort(key=lambda value: value.get("production_partner_id", 0))

    return {
        "observed_at": observed_at,
        "mode": "read_only",
        "external_account_writes": 0,
        "scopes": list(READ_SCOPES),
        "shop": _pick(raw_shop, "shop_id", "shop_name", "title", "currency_code", "listing_active_count", "created_timestamp", "updated_timestamp"),
        "listings": listings,
        "shipping_profiles": profiles,
        "production_partners": partners,
    }


def write_snapshot_atomic(payload: dict[str, Any], target: Path) -> None:
    if not target.parent.exists():
        target.parent.mkdir(parents=True, mode=0o700)
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    fd, temporary = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".tmp", dir=target.parent)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, target)
        os.chmod(target, 0o600)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    observed_at = datetime.now(UTC).replace(microsecond=0).isoformat()
    target = resolve_output_path(observed_at, output=args.output, overwrite=args.overwrite)
    material = load_oauth_material()
    token = maybe_refresh_token(
        material.token,
        client_id=material.credentials.keystring,
        composite_credential=material.composite_credential,
    )
    with EtsyReadOnlyClient(
        api_key=material.credentials.api_key,
        access_token=token.access_token,
    ) as api:
        payload = collect_snapshot(api, observed_at=observed_at)
    write_snapshot_atomic(payload, target)
    print(json.dumps({"output": str(target), "mode": "read_only", "external_account_writes": 0}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
