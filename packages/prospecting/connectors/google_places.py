"""Google Places API (New) connector for prospecting.

Uses official Places endpoints only:

* ``POST /v1/places:searchText`` to get place ids for a city/genre cell.
* ``GET /v1/places/{place_id}`` to fetch the minimal fields required for Phase 1.

No Google Maps HTML, no browser automation, no review text fields.
"""

from __future__ import annotations

import os
from urllib.parse import urlparse

import httpx

from packages.discovery.connectors.base import CompliancePolicyError
from packages.discovery.connectors.rate_limiter import RateLimiter
from packages.prospecting.config import CityConfig, GenreConfig
from packages.schemas.prospect import MapsWebsiteClass, ProspectRecord, ProspectStatus

GOOGLE_PLACES_API_KEY_ENV_VAR = "GOOGLE_PLACES_API_KEY"
DEFAULT_ENDPOINT = "https://places.googleapis.com/v1"
SEARCH_FIELD_MASK = "places.id"
DETAILS_FIELD_MASK = ",".join(
    [
        "id",
        "displayName",
        "formattedAddress",
        "internationalPhoneNumber",
        "types",
        "rating",
        "userRatingCount",
        "websiteUri",
    ]
)

SOCIAL_HOSTS = {
    "facebook.com",
    "fb.com",
    "instagram.com",
    "linktr.ee",
    "bio.site",
    "tiktok.com",
    "x.com",
    "twitter.com",
}

# Booking / directory platforms: a listing here is NOT an owned website. These
# are weak-presence signals and route to the A2_marketplace_review bucket for
# manual review (often the best WAAS targets — a bare booking page begging for a
# real site). NOTE: true website builders (squarespace, wix, weebly, webs,
# godaddysites) are deliberately EXCLUDED here — a business on those has a real
# owned site and should classify as `present` (E_has_site).
MARKETPLACE_HOSTS = {
    "yelp.com",
    "fresha.com",
    "opentable.com",
    "toasttab.com",
    "square.site",
    "vagaro.com",
    "mindbodyonline.com",
    "booksy.com",
    "schedulicity.com",
    "setmore.com",
    "acuityscheduling.com",
}


class GooglePlacesConnector:
    def __init__(
        self,
        *,
        api_key: str | None = None,
        endpoint: str = DEFAULT_ENDPOINT,
        client: httpx.Client | None = None,
        rate_limiter: RateLimiter | None = None,
    ) -> None:
        self._api_key = api_key if api_key is not None else os.environ.get(
            GOOGLE_PLACES_API_KEY_ENV_VAR, ""
        )
        self._endpoint = endpoint.rstrip("/")
        self._client = client or httpx.Client(timeout=10.0)
        self._limiter = rate_limiter or RateLimiter(60)

    def search_cell(self, city: CityConfig, genre: GenreConfig, *, limit: int) -> list[str]:
        self._require_key()
        self._limiter.acquire()
        body: dict[str, object] = {
            "textQuery": genre.query_for(city),
            "pageSize": max(1, min(limit, 20)),
            "locationBias": {
                "circle": {
                    "center": {"latitude": city.lat, "longitude": city.lng},
                    "radius": city.radius_m,
                }
            },
        }
        if genre.included_types:
            # Text Search (New) accepts one includedType. The catalog keeps a
            # list for future expansion; Phase 1 uses the first value.
            body["includedType"] = genre.included_types[0]
        response = self._client.post(
            f"{self._endpoint}/places:searchText",
            json=body,
            headers=self._headers(SEARCH_FIELD_MASK),
        )
        if response.status_code in (429, 503):
            self._limiter.backoff()
            return []
        _raise_for_status(response)
        self._limiter.reset_backoff()
        return [str(place["id"]) for place in response.json().get("places", []) if place.get("id")]

    def fetch_details(self, place_id: str) -> ProspectRecord:
        self._require_key()
        self._limiter.acquire()
        resource_path = place_id if place_id.startswith("places/") else f"places/{place_id}"
        response = self._client.get(
            f"{self._endpoint}/{resource_path}",
            headers=self._headers(DETAILS_FIELD_MASK),
        )
        if response.status_code in (429, 503):
            self._limiter.backoff()
            _raise_for_status(response)
        _raise_for_status(response)
        self._limiter.reset_backoff()
        return prospect_from_place(response.json())

    def _headers(self, field_mask: str) -> dict[str, str]:
        return {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self._api_key,
            "X-Goog-FieldMask": field_mask,
        }

    def _require_key(self) -> None:
        if not self._api_key:
            raise CompliancePolicyError(
                f"prospecting Places connector needs ${GOOGLE_PLACES_API_KEY_ENV_VAR}"
            )


def prospect_from_place(payload: dict[str, object]) -> ProspectRecord:
    website = str(payload.get("websiteUri", "") or "")
    host = normalized_host(website)
    return ProspectRecord(
        place_id=str(payload["id"]),
        display_name=_display_name(payload.get("displayName")),
        formatted_address=str(payload.get("formattedAddress", "")),
        phone=str(payload.get("internationalPhoneNumber", "")),
        types=[str(item) for item in list(payload.get("types", []))],
        city_id="",
        genre_id="",
        grid_cell_id="",
        maps_website_uri=website,
        maps_website_host=host,
        maps_website_class=classify_maps_website(website),
        rating=_opt_float(payload.get("rating")),
        user_ratings_total=int(payload.get("userRatingCount", 0) or 0),
        status=ProspectStatus.MAPS_ENRICHED,
    )


def classify_maps_website(url: str) -> MapsWebsiteClass:
    if not url:
        return MapsWebsiteClass.ABSENT
    host = normalized_host(url)
    if _host_in(host, SOCIAL_HOSTS):
        return MapsWebsiteClass.SOCIAL_ONLY
    if _host_in(host, MARKETPLACE_HOSTS):
        return MapsWebsiteClass.MARKETPLACE
    return MapsWebsiteClass.PRESENT


def normalized_host(url: str) -> str:
    host = urlparse(url).netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    return host


def _host_in(host: str, candidates: set[str]) -> bool:
    return any(host == candidate or host.endswith(f".{candidate}") for candidate in candidates)


def _display_name(value: object) -> str:
    if isinstance(value, dict):
        return str(value.get("text", ""))
    return str(value or "")


def _opt_float(value: object) -> float | None:
    return None if value is None else float(value)  # type: ignore[arg-type]


def _raise_for_status(response: httpx.Response) -> None:
    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        detail = response.text[:600].replace("\n", " ")
        raise CompliancePolicyError(f"{exc}; response={detail}") from exc
