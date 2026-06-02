from __future__ import annotations

import httpx
import pytest

from packages.discovery.connectors.base import CompliancePolicyError
from packages.prospecting.config import CityConfig, GenreConfig
from packages.prospecting.connectors.google_places import GooglePlacesConnector


def _client(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_google_places_search_and_details_use_minimal_field_masks() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        field_mask = request.headers.get("X-Goog-FieldMask", "")
        assert "reviews" not in field_mask.lower()
        assert request.headers["X-Goog-Api-Key"] == "key_123"
        if request.url.path.endswith("/places:searchText"):
            return httpx.Response(200, json={"places": [{"id": "abc123"}]})
        assert request.url.path.endswith("/places/abc123")
        return httpx.Response(
            200,
            json={
                "id": "abc123",
                "displayName": {"text": "Tonic Salon"},
                "formattedAddress": "Seattle, WA",
                "internationalPhoneNumber": "+1 206-555-0100",
                "types": ["beauty_salon"],
                "rating": 4.7,
                "userRatingCount": 26,
                "websiteUri": "https://facebook.com/tonic",
            },
        )

    connector = GooglePlacesConnector(api_key="key_123", client=_client(handler))
    city = CityConfig(id="seattle", name="Seattle", lat=47.6062, lng=-122.3321)
    genre = GenreConfig(
        id="beauty_salon",
        label="beauty salon",
        text_query_template="{label} in {city_name}",
    )

    place_ids = connector.search_cell(city, genre, limit=5)
    place = connector.fetch_details(place_ids[0])

    assert place.place_id == "abc123"
    assert place.maps_website_class.value == "social_only"
    assert len(requests) == 2


def test_google_places_fails_closed_without_api_key() -> None:
    connector = GooglePlacesConnector(api_key="", client=_client(lambda r: httpx.Response(200)))
    with pytest.raises(CompliancePolicyError, match="GOOGLE_PLACES_API_KEY"):
        connector.search_cell(
            CityConfig(id="x", name="X", lat=0, lng=0),
            GenreConfig(id="g", label="g", text_query_template="{label} in {city_name}"),
            limit=1,
        )
