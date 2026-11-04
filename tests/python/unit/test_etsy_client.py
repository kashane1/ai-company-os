from __future__ import annotations

import httpx
import pytest

from packages.etsy.client import EtsyDescriptionWriteClient, EtsyReadOnlyClient


def _client(handler):
    return EtsyReadOnlyClient(
        api_key="key:secret",
        access_token="access-token",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )


def test_get_shop_uses_read_only_etsy_route_and_safe_headers() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"shop_id": 123}, request=request)

    assert _client(handler).get_shop(123) == {"shop_id": 123}
    assert seen[0].method == "GET"
    assert str(seen[0].url) == "https://openapi.etsy.com/v3/application/shops/123"
    assert seen[0].headers["x-api-key"] == "key:secret"
    assert seen[0].headers["authorization"] == "Bearer access-token"


def test_description_write_client_uses_only_patch_description_form_field() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"listing_id": 456}, request=request)

    client = EtsyDescriptionWriteClient(
        api_key="key:secret",
        access_token="access-token",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    assert client.update_listing_description(123, 456, "Exact approved copy") == {
        "listing_id": 456
    }
    assert seen[0].method == "PATCH"
    assert seen[0].url.path == "/v3/application/shops/123/listings/456"
    assert seen[0].headers["content-type"].startswith(
        "application/x-www-form-urlencoded"
    )
    assert seen[0].content == b"description=Exact+approved+copy"


@pytest.mark.parametrize("api_key", ["key:", ":secret"])
def test_client_rejects_partial_composite_api_credentials(api_key: str) -> None:
    with pytest.raises(ValueError, match="keystring:shared_secret"):
        EtsyReadOnlyClient(api_key=api_key, access_token="access-token")


def test_active_listings_paginates_through_next_offset() -> None:
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url))
        offset = request.url.params.get("offset")
        if offset == "0":
            return httpx.Response(200, json={"results": [{"listing_id": 1}], "count": 2}, request=request)
        return httpx.Response(200, json={"results": [{"listing_id": 2}], "count": 2}, request=request)

    result = list(_client(handler).iter_active_listings(123, limit=1))
    assert result == [{"listing_id": 1}, {"listing_id": 2}]
    assert len(calls) == 2
    assert "/shops/123/listings/active" in calls[0]
    assert "limit=1" in calls[0]


def test_shipping_profile_destinations_paginate_through_next_offset() -> None:
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        offset = request.url.params.get("offset")
        destination_id = 10 if offset == "0" else 11
        return httpx.Response(
            200,
            json={
                "results": [{"shipping_profile_destination_id": destination_id}],
                "count": 2,
            },
            request=request,
        )

    result = list(
        _client(handler).iter_shipping_profile_destinations(123, 456, limit=1)
    )

    assert [item["shipping_profile_destination_id"] for item in result] == [10, 11]
    assert [request.url.params.get("offset") for request in calls] == ["0", "1"]


def test_shop_name_search_paginates_and_rejects_bad_collection_pages() -> None:
    pages = iter(
        [
            {"results": [{"shop_id": 1}], "count": 2},
            {"results": [{"shop_id": 2}], "count": 2},
        ]
    )
    client = _client(
        lambda request: httpx.Response(200, json=next(pages), request=request)
    )
    assert list(client.iter_shops_by_name("homefromworking", limit=1)) == [
        {"shop_id": 1},
        {"shop_id": 2},
    ]

    malformed = _client(
        lambda request: httpx.Response(
            200,
            json={"results": [], "count": 1},
            request=request,
        )
    )
    with pytest.raises(ValueError, match="shop search page"):
        list(malformed.iter_shops_by_name("homefromworking"))


@pytest.mark.parametrize(
    "page",
    [
        {"results": [{"listing_id": 1}]},
        {"results": [{"listing_id": 1}], "count": "1"},
        {"results": [{"listing_id": 1}], "count": -1},
        {"results": [{"listing_id": 1}], "count": 0},
        {"results": ["not-a-listing"], "count": 1},
        {"results": [], "count": 2},
    ],
)
def test_active_listing_pagination_rejects_malformed_or_nonprogressing_pages(page: dict) -> None:
    client = _client(lambda request: httpx.Response(200, json=page, request=request))
    with pytest.raises(ValueError, match="listing page"):
        list(client.iter_active_listings(123, limit=1))


def test_active_listing_pagination_allows_empty_zero_count() -> None:
    client = _client(lambda request: httpx.Response(200, json={"results": [], "count": 0}, request=request))
    assert list(client.iter_active_listings(123)) == []


@pytest.mark.parametrize(
    "page",
    [
        {"results": [{"shipping_profile_destination_id": 1}]},
        {"results": [{"shipping_profile_destination_id": 1}], "count": True},
        {"results": [], "count": 1},
        {"results": ["not-an-object"], "count": 1},
    ],
)
def test_shipping_destination_pagination_fails_closed(page: dict) -> None:
    client = _client(
        lambda request: httpx.Response(200, json=page, request=request)
    )
    with pytest.raises(ValueError, match="shipping destination page"):
        list(client.iter_shipping_profile_destinations(123, 456))


def test_active_listing_pagination_rejects_count_regression() -> None:
    pages = iter(
        [
            {"results": [{"listing_id": 1}], "count": 2},
            {"results": [{"listing_id": 2}], "count": 1},
        ]
    )
    client = _client(lambda request: httpx.Response(200, json=next(pages), request=request))
    with pytest.raises(ValueError, match="listing page"):
        list(client.iter_active_listings(123, limit=1))


def test_generic_get_rejects_non_get_and_absolute_paths() -> None:
    client = _client(lambda request: httpx.Response(200, json={}, request=request))
    with pytest.raises(ValueError, match="relative"):
        client.get("https://example.invalid")
    assert all(not hasattr(client, verb) for verb in ("post", "put", "patch", "delete"))
    # Etsy receipt access requires transactions_r, deliberately not requested
    # during the first read-only shops_r/listings_r authorization.
    assert not hasattr(client, "get_shop_receipts")


def test_find_shop_by_name_uses_collection_route_query() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"results": [{"shop_id": 123}]}, request=request)

    assert _client(handler).find_shop_by_name("homefromworking") == {"results": [{"shop_id": 123}]}
    assert str(seen[0].url) == "https://openapi.etsy.com/v3/application/shops?shop_name=homefromworking"


def test_inventory_and_shipping_profile_reads_use_get_routes() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"results": []}, request=request)

    client = _client(handler)
    client.get_listing_inventory(88)
    client.get_shop_shipping_profiles(123)
    client.get_shipping_profile_destinations(123, 456)
    assert [request.method for request in requests] == ["GET", "GET", "GET"]
    assert [request.url.path for request in requests] == [
        "/v3/application/listings/88/inventory",
        "/v3/application/shops/123/shipping-profiles",
        "/v3/application/shops/123/shipping-profiles/456/destinations",
    ]


def test_production_partners_uses_shop_read_route() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"results": []}, request=request)

    assert _client(handler).get_shop_production_partners(123) == {"results": []}
    assert seen[0].method == "GET"
    assert seen[0].url.path == "/v3/application/shops/123/production-partners"


def test_client_closes_injected_http_client_and_supports_context_manager() -> None:
    raw_client = httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(200, json={})))
    client = EtsyReadOnlyClient(api_key="key:secret", access_token="access-token", client=raw_client)
    client.close()
    assert raw_client.is_closed

    managed_raw = httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(200, json={})))
    with EtsyReadOnlyClient(
        api_key="key:secret",
        access_token="access-token",
        client=managed_raw,
    ) as managed:
        assert isinstance(managed, EtsyReadOnlyClient)
        managed.get_shop(123)
    assert managed_raw.is_closed
