"""DataForSEO Business Listings connector for prospect source collection.

Discovery source: given a city + genre, query the DataForSEO **Business
Listings Search** database for businesses of that category in that area and emit
``ProspectCandidate`` rows. This is the *discovery* counterpart to
``DataForSEOSearchVerifier`` (which only *verifies* a known business's website).

Endpoint: ``POST /v3/business_data/business_listings/search/live`` (synchronous;
no task-queue polling). The endpoint filters by ``categories`` /
``location_coordinate`` — it has no general free-text keyword search, so genres
are mapped to DataForSEO category slugs in ``DATAFORSEO_GENRE_CATEGORIES`` below.
Those slugs are the ``category_name`` values from the (free)
``business_listings/categories`` endpoint and were validated live on
2026-06-15. Unmapped genres fall back to their own id.

Pricing (PAYG): ``$0.01`` per request + ``$0.0003`` per returned business.
"""

from __future__ import annotations

import httpx

from packages.config.settings import (
    DATAFORSEO_LOGIN_ENV_VAR,
    DATAFORSEO_PASSWORD_ENV_VAR,
    get_api_key,
)
from packages.discovery.connectors.rate_limiter import RateLimiter
from packages.prospecting.config import CityConfig, GenreConfig
from packages.prospecting.identity import ProspectCandidate
from packages.prospecting.web_presence import ProviderConfigError, SearchProviderError

DATAFORSEO_ENDPOINT = "https://api.dataforseo.com"
BUSINESS_LISTINGS_PATH = "/v3/business_data/business_listings/search/live"
DEFAULT_RADIUS_KM = 12.0
DEFAULT_LIMIT = 100
MAX_LIMIT = 1000

# Genre id -> DataForSEO category slugs (`category_name` values from the free
# business_listings/categories endpoint, validated live 2026-06-15). DataForSEO
# uses Google-My-Business slugs, which differ from Overture's taxonomy — e.g.
# `barber_shop` not `barber`, `plumber` not `plumbing`, `roofing_contractor` not
# `roofing`. Keep keys aligned with packages/prospecting/config/genres.yaml.
DATAFORSEO_GENRE_CATEGORIES: dict[str, tuple[str, ...]] = {
    "accountant": ("accountant", "certified_public_accountant", "tax_preparation_service"),
    "auto_repair": ("auto_repair_shop", "car_repair", "auto_body_shop", "mechanic"),
    "bakery": ("bakery", "donut_shop"),
    "barber_shop": ("barber_shop",),
    "beauty_salon": ("beauty_salon", "hair_salon"),
    "coffee_shop": ("coffee_shop", "cafe", "coffee_roasters"),
    "dog_groomer": ("pet_groomer",),
    "electrician": ("electrician",),
    "garage_door": ("garage_door_supplier",),
    "house_cleaning": ("house_cleaning_service", "cleaning_service"),
    "landscaper": ("landscaper", "landscape_designer"),
    "massage_therapy": ("massage_therapist", "massage_spa", "massage"),
    "music_lessons": ("music_school",),
    "nail_salon": ("nail_salon",),
    "notary": ("notary_public",),
    "plumber": ("plumber",),
    "restaurant": ("restaurant",),
    "roofer": ("roofing_contractor",),
    "tutoring": ("tutoring_service", "private_tutor"),
    "yoga_studio": ("yoga_studio",),
}

# Pay-as-you-go price points (USD), used for pre-spend cost estimates.
COST_PER_REQUEST = 0.01
COST_PER_ITEM = 0.0003


def estimate_cost(*, requests: int, items: int) -> float:
    """Ceiling cost in USD for ``requests`` calls returning up to ``items`` rows."""
    return requests * COST_PER_REQUEST + items * COST_PER_ITEM


def categories_for_genre(genre: GenreConfig) -> list[str]:
    """DataForSEO category slugs for a genre, falling back to the genre id."""
    return list(DATAFORSEO_GENRE_CATEGORIES.get(genre.id, (genre.id,)))


class DataForSEOBusinessConnector:
    source = "dataforseo"

    def __init__(
        self,
        *,
        login: str | None = None,
        password: str | None = None,
        client: httpx.Client | None = None,
        endpoint: str = DATAFORSEO_ENDPOINT,
        radius_km: float = DEFAULT_RADIUS_KM,
        rate_limiter: RateLimiter | None = None,
    ) -> None:
        self._login = login if login is not None else get_api_key(DATAFORSEO_LOGIN_ENV_VAR)
        self._password = (
            password if password is not None else get_api_key(DATAFORSEO_PASSWORD_ENV_VAR)
        )
        if not self._login or not self._password:
            raise ProviderConfigError(
                f"set ${DATAFORSEO_LOGIN_ENV_VAR} and ${DATAFORSEO_PASSWORD_ENV_VAR}"
            )
        self._client = client or httpx.Client(timeout=30.0)
        self._endpoint = endpoint.rstrip("/")
        self._radius_km = radius_km
        self._limiter = rate_limiter or RateLimiter(60)
        self.connector_version = "dataforseo-business-v1"

    def query_for(self, city: CityConfig, genre: GenreConfig) -> str:
        """Deterministic run-key string (drives source-run dedupe)."""
        categories = ",".join(categories_for_genre(genre))
        return (
            f"categories={categories} "
            f"coordinate={city.lat:.5f},{city.lng:.5f},{self._radius_km:g}km"
        )

    def fetch_candidates(
        self, city: CityConfig, genre: GenreConfig, *, limit: int
    ) -> list[ProspectCandidate]:
        self._limiter.acquire()
        response = self._client.post(
            f"{self._endpoint}{BUSINESS_LISTINGS_PATH}",
            json=[
                {
                    "categories": categories_for_genre(genre),
                    "location_coordinate": (
                        f"{city.lat},{city.lng},{self._radius_km:g}"
                    ),
                    "limit": _clamp_limit(limit),
                }
            ],
            auth=httpx.BasicAuth(self._login, self._password),
        )
        if response.status_code in (429, 503):
            self._limiter.backoff()
        _raise_for_status(response)
        self._limiter.reset_backoff()
        return [
            candidate_from_listing(item, city=city, genre=genre)
            for item in _listing_items(response.json())
        ]


def _clamp_limit(limit: int) -> int:
    if limit <= 0:
        return DEFAULT_LIMIT
    return min(limit, MAX_LIMIT)


def _listing_items(payload: dict[str, object]) -> list[dict[str, object]]:
    tasks = _as_list(payload.get("tasks"))
    if not tasks:
        return []
    task = _as_mapping(tasks[0])
    if int(task.get("status_code", 0) or 0) != 20000:
        raise SearchProviderError(
            f"DataForSEO business_listings status {task.get('status_code')}: "
            f"{task.get('status_message')}"
        )
    items: list[dict[str, object]] = []
    for result in _as_list(task.get("result")):
        for item in _as_list(_as_mapping(result).get("items")):
            items.append(_as_mapping(item))
    return items


def candidate_from_listing(
    item: dict[str, object], *, city: CityConfig, genre: GenreConfig
) -> ProspectCandidate:
    return ProspectCandidate(
        source="dataforseo",
        source_id=_source_id(item),
        display_name=str(item.get("title", "") or "").strip(),
        formatted_address=_address(item),
        phone=str(item.get("phone", "") or "").strip(),
        city_id=city.id,
        genre_id=genre.id,
        website_uri=_website(item),
        social_urls=[],
        marketplace_urls=[],
        source_confidence=0.85 if item.get("is_claimed") else 0.55,
    )


def _source_id(item: dict[str, object]) -> str:
    for key in ("place_id", "cid", "feature_id"):
        value = str(item.get(key, "") or "").strip()
        if value:
            return value
    return str(item.get("title", "") or "").strip()


def _website(item: dict[str, object]) -> str:
    url = str(item.get("url", "") or "").strip()
    if url:
        return url
    domain = str(item.get("domain", "") or "").strip()
    return f"https://{domain}" if domain else ""


def _address(item: dict[str, object]) -> str:
    address = str(item.get("address", "") or "").strip()
    if address:
        return address
    info = _as_mapping(item.get("address_info"))
    parts = [
        str(info.get("address", "")).strip(),
        str(info.get("city", "")).strip(),
        " ".join(
            part
            for part in [
                str(info.get("region", "")).strip(),
                str(info.get("zip", "")).strip(),
            ]
            if part
        ),
    ]
    return ", ".join(part for part in parts if part)


def _as_list(value: object) -> list[object]:
    if isinstance(value, list):
        return value
    return []


def _as_mapping(value: object) -> dict[str, object]:
    return dict(value) if isinstance(value, dict) else {}


def _raise_for_status(response: httpx.Response) -> None:
    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise SearchProviderError(_error_detail(response, exc)) from exc


def _error_detail(response: httpx.Response, exc: httpx.HTTPStatusError) -> str:
    """Surface DataForSEO's own status_code/status_message when present.

    DataForSEO often returns an application error (e.g. 40104 "verify your
    account") inside the JSON body alongside a 4xx HTTP status; pull it out so
    the operator sees the actionable message instead of a raw response dump.
    """
    try:
        body = response.json()
    except ValueError:
        body = None
    if isinstance(body, dict) and body.get("status_message"):
        return (
            f"DataForSEO {body.get('status_code')}: {body.get('status_message')} "
            f"(HTTP {response.status_code})"
        )
    detail = response.text[:600].replace("\n", " ")
    return f"{exc}; response={detail}"
