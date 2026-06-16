"""Unit tests for the DataForSEO Business Listings discovery connector."""

from __future__ import annotations

import json

import httpx
import pytest

from packages.prospecting.config import CityConfig, GenreConfig
from packages.prospecting.connectors.dataforseo import (
    DataForSEOBusinessConnector,
    candidate_from_listing,
    estimate_cost,
)
from packages.prospecting.web_presence import ProviderConfigError, SearchProviderError

CITY = CityConfig(id="seattle", name="Seattle", lat=47.6062, lng=-122.3321, radius_m=12000)
GENRE = GenreConfig(
    id="barber_shop", label="Barber Shop", text_query_template="{label} in {city_name}"
)


def _listings_response(request: httpx.Request) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "tasks": [
                {
                    "status_code": 20000,
                    "result": [
                        {
                            "items": [
                                {
                                    "type": "business_listing",
                                    "title": "Pioneer Barbers",
                                    "address": "100 1st Ave, Seattle, WA 98104",
                                    "phone": "+12065551212",
                                    "url": "https://pioneerbarbers.com/",
                                    "domain": "pioneerbarbers.com",
                                    "place_id": "ChIJpioneer",
                                    "is_claimed": True,
                                    "rating": {"value": 4.8, "votes_count": 210},
                                },
                                {
                                    "type": "business_listing",
                                    "title": "Corner Cuts",
                                    "address_info": {
                                        "address": "55 Pine St",
                                        "city": "Seattle",
                                        "region": "WA",
                                        "zip": "98101",
                                    },
                                    "phone": "+12065559090",
                                    "domain": "cornercuts.example",
                                    "cid": "cid_corner",
                                    "is_claimed": False,
                                },
                            ]
                        }
                    ],
                }
            ]
        },
        request=request,
    )


def test_fetch_candidates_posts_categories_and_maps_items() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        assert request.headers["Authorization"].startswith("Basic ")
        assert request.url.path == "/v3/business_data/business_listings/search/live"
        body = json.loads(request.content.decode())
        assert body == [
            {
                "categories": ["barber_shop"],
                "location_coordinate": "47.6062,-122.3321,10",
                "limit": 50,
            }
        ]
        return _listings_response(request)

    connector = DataForSEOBusinessConnector(
        login="dfs_login",
        password="dfs_password",
        radius_km=10,
        client=httpx.Client(
            transport=httpx.MockTransport(handler),
            base_url="https://api.dataforseo.com",
        ),
    )

    candidates = connector.fetch_candidates(CITY, GENRE, limit=50)

    assert len(requests) == 1
    assert [c.display_name for c in candidates] == ["Pioneer Barbers", "Corner Cuts"]

    first, second = candidates
    assert first.source == "dataforseo"
    assert first.source_id == "ChIJpioneer"
    assert first.website_uri == "https://pioneerbarbers.com/"
    assert first.formatted_address == "100 1st Ave, Seattle, WA 98104"
    assert first.city_id == "seattle"
    assert first.genre_id == "barber_shop"
    assert first.source_confidence == pytest.approx(0.85)

    # No `url`, no full `address` -> falls back to domain + composed address_info.
    assert second.source_id == "cid_corner"
    assert second.website_uri == "https://cornercuts.example"
    assert second.formatted_address == "55 Pine St, Seattle, WA 98101"
    assert second.source_confidence == pytest.approx(0.55)


def test_fetch_candidates_clamps_default_and_max_limit() -> None:
    seen: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(json.loads(request.content.decode())[0]["limit"])
        return _listings_response(request)

    connector = DataForSEOBusinessConnector(
        login="x",
        password="y",
        client=httpx.Client(
            transport=httpx.MockTransport(handler), base_url="https://api.dataforseo.com"
        ),
    )
    connector.fetch_candidates(CITY, GENRE, limit=0)  # -> default 100
    connector.fetch_candidates(CITY, GENRE, limit=99999)  # -> capped 1000
    assert seen == [100, 1000]


def test_non_success_status_raises() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"tasks": [{"status_code": 40400, "status_message": "Not Found."}]},
            request=request,
        )

    connector = DataForSEOBusinessConnector(
        login="x",
        password="y",
        client=httpx.Client(
            transport=httpx.MockTransport(handler), base_url="https://api.dataforseo.com"
        ),
    )
    with pytest.raises(SearchProviderError):
        connector.fetch_candidates(CITY, GENRE, limit=10)


def test_http_error_surfaces_dataforseo_status_message() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            403,
            json={
                "status_code": 40104,
                "status_message": "Please verify your account before using the API.",
                "tasks": None,
            },
            request=request,
        )

    connector = DataForSEOBusinessConnector(
        login="x",
        password="y",
        client=httpx.Client(
            transport=httpx.MockTransport(handler), base_url="https://api.dataforseo.com"
        ),
    )
    with pytest.raises(SearchProviderError, match="40104.*verify your account"):
        connector.fetch_candidates(CITY, GENRE, limit=10)


def test_missing_credentials_raises_provider_config_error() -> None:
    with pytest.raises(ProviderConfigError):
        DataForSEOBusinessConnector(login="", password="")


def test_query_for_is_deterministic_and_includes_geo() -> None:
    connector = DataForSEOBusinessConnector(login="x", password="y", radius_km=8)
    query = connector.query_for(CITY, GENRE)
    assert query == connector.query_for(CITY, GENRE)
    assert "categories=barber_shop" in query
    assert "47.60620,-122.33210,8km" in query


def test_candidate_from_listing_pure_mapping() -> None:
    candidate = candidate_from_listing(
        {"title": "  Solo Cuts  ", "feature_id": "feat_1", "phone": "555"},
        city=CITY,
        genre=GENRE,
    )
    assert candidate.display_name == "Solo Cuts"
    assert candidate.source_id == "feat_1"
    assert candidate.website_uri == ""
    assert candidate.source_confidence == pytest.approx(0.55)


def test_every_catalog_genre_has_a_dataforseo_category() -> None:
    from packages.prospecting.config import load_genres
    from packages.prospecting.connectors.dataforseo import DATAFORSEO_GENRE_CATEGORIES

    unmapped = [g.id for g in load_genres() if g.id not in DATAFORSEO_GENRE_CATEGORIES]
    assert unmapped == [], f"genres missing a DataForSEO category slug: {unmapped}"


def test_estimate_cost() -> None:
    assert estimate_cost(requests=1, items=1000) == pytest.approx(0.01 + 0.3)
    assert estimate_cost(requests=0, items=0) == 0.0
