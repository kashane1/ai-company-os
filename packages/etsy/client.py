"""Read-only Etsy Open API v3 client."""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from typing import Any

import httpx

from packages.etsy.auth import EtsyCredentials

BASE_URL = "https://openapi.etsy.com/v3/application"


class EtsyReadOnlyClient:
    """Minimal GET-only client for inventory and reconciliation."""

    def __init__(self, *, api_key: str, access_token: str, client: httpx.Client | None = None) -> None:
        EtsyCredentials.from_composite(api_key)
        if not access_token:
            raise ValueError("access_token is required")
        self._client = client or httpx.Client(timeout=20.0)
        self._headers = {"x-api-key": api_key, "Authorization": f"Bearer {access_token}"}

    def close(self) -> None:
        """Close the underlying GET transport."""
        self._client.close()

    def __enter__(self) -> "EtsyReadOnlyClient":
        return self

    def __exit__(self, _exc_type: object, _exc_value: object, _traceback: object) -> None:
        self.close()

    def get(self, path: str, *, params: Mapping[str, str | int] | None = None) -> dict[str, Any]:
        if not path.startswith("/") or path.startswith("//") or ".." in path:
            raise ValueError("path must be a relative Etsy API route")
        response = self._client.get(f"{BASE_URL}{path}", headers=self._headers, params=params)
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise ValueError("Etsy response must be an object")
        return payload

    def get_shop(self, shop_id: int) -> dict[str, Any]:
        return self.get(f"/shops/{shop_id}")

    def find_shop_by_name(self, shop_name: str) -> dict[str, Any]:
        """Find a shop through Etsy's collection route, not a guessed shop ID."""
        if not shop_name.strip():
            raise ValueError("shop_name is required")
        return self.get("/shops", params={"shop_name": shop_name})

    def iter_shops_by_name(
        self, shop_name: str, *, limit: int = 100
    ) -> Iterator[dict[str, Any]]:
        """Iterate every shop-search result from Etsy's paginated route."""
        if not shop_name.strip():
            raise ValueError("shop_name is required")
        yield from self._iter_paginated(
            "/shops",
            context="shop search",
            limit=limit,
            base_params={"shop_name": shop_name},
        )

    def get_shop_by_name(self, shop_name: str) -> dict[str, Any]:
        """Backward-compatible alias for Etsy's findShops route."""
        return self.find_shop_by_name(shop_name)

    def get_listing(self, listing_id: int) -> dict[str, Any]:
        return self.get(f"/listings/{listing_id}")

    def get_listing_inventory(self, listing_id: int) -> dict[str, Any]:
        return self.get(f"/listings/{listing_id}/inventory")

    def get_shop_shipping_profiles(self, shop_id: int) -> dict[str, Any]:
        return self.get(f"/shops/{shop_id}/shipping-profiles")

    def get_shop_production_partners(self, shop_id: int) -> dict[str, Any]:
        return self.get(f"/shops/{shop_id}/production-partners")

    def get_shipping_profile_destinations(
        self, shop_id: int, shipping_profile_id: int
    ) -> dict[str, Any]:
        return self.get(f"/shops/{shop_id}/shipping-profiles/{shipping_profile_id}/destinations")

    def iter_shipping_profile_destinations(
        self,
        shop_id: int,
        shipping_profile_id: int,
        *,
        limit: int = 100,
    ) -> Iterator[dict[str, Any]]:
        """Iterate every destination associated with one shipping profile."""
        yield from self._iter_paginated(
            f"/shops/{shop_id}/shipping-profiles/{shipping_profile_id}/destinations",
            context="shipping destination",
            limit=limit,
        )

    def iter_active_listings(self, shop_id: int, *, limit: int = 100) -> Iterator[dict[str, Any]]:
        yield from self._iter_paginated(
            f"/shops/{shop_id}/listings/active",
            context="listing",
            limit=limit,
        )

    def _iter_paginated(
        self,
        path: str,
        *,
        context: str,
        limit: int,
        base_params: Mapping[str, str | int] | None = None,
    ) -> Iterator[dict[str, Any]]:
        if not 1 <= limit <= 100:
            raise ValueError("limit must be between 1 and 100")
        offset = 0
        expected_count: int | None = None
        while True:
            params = dict(base_params or {})
            params.update({"limit": limit, "offset": offset})
            page = self.get(path, params=params)
            results = page.get("results")
            if not isinstance(results, list):
                raise ValueError(f"Etsy {context} page has invalid results")
            count = page.get("count")
            if isinstance(count, bool) or not isinstance(count, int) or count < 0:
                raise ValueError(f"Etsy {context} page has invalid count")
            if expected_count is None:
                expected_count = count
            elif count != expected_count:
                raise ValueError(f"Etsy {context} page count changed during pagination")
            if count < offset:
                raise ValueError(f"Etsy {context} page count regressed below offset")
            if not results:
                if count != offset:
                    raise ValueError(
                        f"Etsy {context} page made no progress before count was reached"
                    )
                return
            if len(results) > limit:
                raise ValueError(f"Etsy {context} page exceeded requested limit")
            if not all(isinstance(result, dict) for result in results):
                raise ValueError(f"Etsy {context} page has invalid result")
            next_offset = offset + len(results)
            if next_offset > count:
                raise ValueError(f"Etsy {context} page exceeds declared count")
            yield from results
            if next_offset == count:
                return
            offset = next_offset

    # getShopReceipts is intentionally omitted. Etsy requires the transactions_r
    # scope for receipt data; this first authorization is limited to shops_r and
    # listings_r, so receipt access would violate its least-privilege contract.


class EtsyDescriptionWriteClient:
    """The single Etsy mutation needed for an approved description-only receipt.

    This intentionally exposes no generic PATCH/POST operation, and does not
    offer title, inventory, image, price, publication, or shop mutations.
    """

    def __init__(
        self,
        *,
        api_key: str,
        access_token: str,
        client: httpx.Client | None = None,
    ) -> None:
        EtsyCredentials.from_composite(api_key)
        if not access_token:
            raise ValueError("access_token is required")
        self._client = client or httpx.Client(timeout=20.0)
        self._headers = {"x-api-key": api_key, "Authorization": f"Bearer {access_token}"}

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "EtsyDescriptionWriteClient":
        return self

    def __exit__(self, _exc_type: object, _exc_value: object, _traceback: object) -> None:
        self.close()

    def _get(self, path: str) -> dict[str, Any]:
        response = self._client.get(f"{BASE_URL}{path}", headers=self._headers)
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise ValueError("Etsy response must be an object")
        return payload

    def get_listing(self, listing_id: int) -> dict[str, Any]:
        return self._get(f"/listings/{listing_id}")

    def get_listing_inventory(self, listing_id: int) -> dict[str, Any]:
        return self._get(f"/listings/{listing_id}/inventory")

    def update_listing_description(
        self, shop_id: int, listing_id: int, description: str
    ) -> dict[str, Any]:
        if not isinstance(description, str) or not description.strip():
            raise ValueError("description must be a non-blank string")
        response = self._client.patch(
            f"{BASE_URL}/shops/{shop_id}/listings/{listing_id}",
            headers={**self._headers, "Content-Type": "application/x-www-form-urlencoded"},
            data={"description": description},
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise ValueError("Etsy description update response must be an object")
        return payload
