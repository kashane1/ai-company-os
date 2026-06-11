"""Search-backed web-presence verification for local SMB prospects."""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Protocol
from urllib.parse import urlparse

import httpx

from packages.config.settings import (
    BRAVE_SEARCH_API_KEY_ENV_VAR,
    DATAFORSEO_LOGIN_ENV_VAR,
    DATAFORSEO_PASSWORD_ENV_VAR,
    get_api_key,
)
from packages.prospecting.connectors.google_places import (
    MARKETPLACE_HOSTS,
    SOCIAL_HOSTS,
    normalized_host,
)
from packages.schemas.prospect import ProspectRecord, WebVerifyVerdict, replace_record

BRAVE_SEARCH_ENDPOINT = "https://api.search.brave.com/res/v1/web/search"
DATAFORSEO_ENDPOINT = "https://api.dataforseo.com"

DIRECTORY_HOSTS = {
    "angi.com",
    "apple.com",
    "bbb.org",
    "bing.com",
    "chamberofcommerce.com",
    "citysearch.com",
    "clutch.co",
    "classpass.com",
    "dexknows.com",
    "foursquare.com",
    "g.page",
    "google.com",
    "greencirclesalons.com",
    "homeadvisor.com",
    "local.yahoo.com",
    "mapquest.com",
    "manta.com",
    "nextdoor.com",
    "superpages.com",
    "thumbtack.com",
    "tripadvisor.com",
    "wheree.com",
    "yellowpages.com",
}

GENERIC_BUSINESS_TOKENS = {
    "and",
    "auto",
    "barber",
    "beauty",
    "business",
    "care",
    "cleaning",
    "company",
    "contractor",
    "electric",
    "electrical",
    "hair",
    "llc",
    "nail",
    "plumbing",
    "repair",
    "salon",
    "service",
    "services",
    "shop",
    "studio",
    "the",
}


class SearchProviderError(RuntimeError):
    """Raised when a search provider cannot return usable results."""


class ProviderConfigError(SearchProviderError):
    """Raised when a search provider is missing required credentials."""


@dataclass(frozen=True)
class SearchResult:
    title: str
    url: str
    description: str = ""


@dataclass(frozen=True)
class WebPresenceResult:
    verdict: WebVerifyVerdict
    url: str = ""
    confidence: float = 0.0
    note: str = ""


class SearchVerifier(Protocol):
    method: str

    def search(self, query: str) -> list[SearchResult]:
        ...


def build_search_query(record: ProspectRecord) -> str:
    locality = _locality_from_address(record.formatted_address) or record.city_id
    return " ".join(part for part in [record.display_name, locality] if part).strip()


def classify_web_presence(
    record: ProspectRecord, results: list[SearchResult]
) -> WebPresenceResult:
    if not results:
        return WebPresenceResult(
            verdict=WebVerifyVerdict.NONE_FOUND,
            confidence=0.65,
            note="no search results returned for the business query",
        )

    owned: list[SearchResult] = []
    social: list[SearchResult] = []
    marketplace: list[SearchResult] = []
    matched: list[SearchResult] = []

    for result in results:
        if not result.url:
            continue
        if not _looks_like_same_business(record, result):
            continue
        matched.append(result)
        host = _normalized_result_host(result.url)
        if _host_in(host, SOCIAL_HOSTS):
            social.append(result)
        elif _host_in(host, MARKETPLACE_HOSTS) or _host_in(host, DIRECTORY_HOSTS):
            marketplace.append(result)
        elif _owned_host_matches_business(record, host):
            owned.append(result)
        else:
            continue

    if owned:
        result = owned[0]
        return WebPresenceResult(
            verdict=WebVerifyVerdict.OWNED_SITE,
            url=result.url,
            confidence=0.88,
            note=f"matched likely owned website: {result.title}",
        )
    if social:
        result = social[0]
        note = "matched social profile"
        if marketplace:
            note += " plus directory or marketplace results"
        return WebPresenceResult(
            verdict=WebVerifyVerdict.SOCIAL_ONLY,
            url=result.url,
            confidence=0.74 if marketplace else 0.78,
            note=note,
        )
    if marketplace:
        result = marketplace[0]
        return WebPresenceResult(
            verdict=WebVerifyVerdict.MARKETPLACE_ONLY,
            url=result.url,
            confidence=0.76,
            note="matched only directory or marketplace results",
        )

    first = matched[0] if matched else results[0]
    return WebPresenceResult(
        verdict=WebVerifyVerdict.AMBIGUOUS,
        url=first.url,
        confidence=0.35,
        note="search results did not clearly prove owned, social, or marketplace presence",
    )


def verify_record_web_presence(
    record: ProspectRecord,
    verifier: SearchVerifier,
    *,
    now: Callable[[], datetime] | None = None,
) -> ProspectRecord:
    clock = now or (lambda: datetime.now(timezone.utc))
    result = classify_web_presence(record, verifier.search(build_search_query(record)))
    timestamp = clock().isoformat()
    return replace_record(
        record,
        web_verify_class="web_search",
        web_verify_verdict=result.verdict.value,
        web_verify_url=result.url,
        web_verify_confidence=result.confidence,
        web_verify_note=result.note,
        web_verified_at=timestamp,
        web_verify_method=verifier.method,
        updated_at=timestamp,
    )


class BraveSearchVerifier:
    method = "brave"

    def __init__(
        self,
        *,
        api_key: str | None = None,
        client: httpx.Client | None = None,
        endpoint: str = BRAVE_SEARCH_ENDPOINT,
        country: str = "US",
        search_lang: str = "en",
        count: int = 10,
    ) -> None:
        self._api_key = (
            api_key if api_key is not None else get_api_key(BRAVE_SEARCH_API_KEY_ENV_VAR)
        )
        if not self._api_key:
            raise ProviderConfigError(f"set ${BRAVE_SEARCH_API_KEY_ENV_VAR} to use Brave")
        self._client = client or httpx.Client(timeout=10.0)
        self._endpoint = endpoint
        self._country = country
        self._search_lang = search_lang
        self._count = count

    def search(self, query: str) -> list[SearchResult]:
        response = self._client.get(
            self._endpoint,
            params={
                "q": query,
                "country": self._country,
                "search_lang": self._search_lang,
                "count": min(max(self._count, 1), 20),
                "result_filter": "web",
                "text_decorations": "false",
            },
            headers={
                "Accept": "application/json",
                "Accept-Encoding": "gzip",
                "X-Subscription-Token": self._api_key,
            },
        )
        _raise_provider_status(response, "Brave Search")
        web = response.json().get("web", {})
        return [_search_result_from_mapping(item) for item in list(web.get("results", []))]


class DataForSEOSearchVerifier:
    method = "dataforseo"

    def __init__(
        self,
        *,
        login: str | None = None,
        password: str | None = None,
        client: httpx.Client | None = None,
        endpoint: str = DATAFORSEO_ENDPOINT,
        location_code: int = 2840,
        language_code: str = "en",
        device: str = "desktop",
        os_name: str = "windows",
        depth: int = 10,
        poll_interval_seconds: float = 5.0,
        max_polls: int = 12,
    ) -> None:
        self._login = login if login is not None else get_api_key(DATAFORSEO_LOGIN_ENV_VAR)
        self._password = (
            password if password is not None else get_api_key(DATAFORSEO_PASSWORD_ENV_VAR)
        )
        if not self._login or not self._password:
            raise ProviderConfigError(
                f"set ${DATAFORSEO_LOGIN_ENV_VAR} and ${DATAFORSEO_PASSWORD_ENV_VAR}"
            )
        self._client = client or httpx.Client(timeout=20.0)
        self._endpoint = endpoint.rstrip("/")
        self._location_code = location_code
        self._language_code = language_code
        self._device = device
        self._os_name = os_name
        self._depth = depth
        self._poll_interval_seconds = poll_interval_seconds
        self._max_polls = max_polls

    def search(self, query: str) -> list[SearchResult]:
        task_id = self._post_task(query)
        for attempt in range(max(self._max_polls, 1)):
            response = self._client.get(
                f"{self._endpoint}/v3/serp/google/organic/task_get/regular/{task_id}",
                auth=httpx.BasicAuth(self._login, self._password),
            )
            _raise_provider_status(response, "DataForSEO")
            results = _dataforseo_results(response.json())
            if results is not None:
                return results
            if attempt < self._max_polls - 1 and self._poll_interval_seconds:
                time.sleep(self._poll_interval_seconds)
        raise SearchProviderError(f"DataForSEO task {task_id} was not ready")

    def _post_task(self, query: str) -> str:
        response = self._client.post(
            f"{self._endpoint}/v3/serp/google/organic/task_post",
            json=[
                {
                    "keyword": query,
                    "language_code": self._language_code,
                    "location_code": self._location_code,
                    "device": self._device,
                    "os": self._os_name,
                    "depth": self._depth,
                }
            ],
            auth=httpx.BasicAuth(self._login, self._password),
        )
        _raise_provider_status(response, "DataForSEO")
        tasks = list(response.json().get("tasks", []))
        if not tasks or not tasks[0].get("id"):
            raise SearchProviderError("DataForSEO did not return a task id")
        return str(tasks[0]["id"])


def _dataforseo_results(payload: dict[str, object]) -> list[SearchResult] | None:
    if "results" in payload:
        return [_search_result_from_mapping(item) for item in list(payload.get("results", []))]

    tasks = list(payload.get("tasks", []))
    if not tasks:
        return []
    task = dict(tasks[0])
    if int(task.get("status_code", 0) or 0) != 20000:
        return None
    parsed: list[SearchResult] = []
    for result in list(task.get("result", [])):
        for item in list(dict(result).get("items", [])):
            item_dict = dict(item)
            if item_dict.get("type") not in {None, "organic"}:
                continue
            parsed.append(_search_result_from_mapping(item_dict))
    return parsed


def _search_result_from_mapping(item: object) -> SearchResult:
    data = dict(item)
    return SearchResult(
        title=str(data.get("title", "")),
        url=str(data.get("url", "")),
        description=str(data.get("description", data.get("snippet", "")) or ""),
    )


def _looks_like_same_business(record: ProspectRecord, result: SearchResult) -> bool:
    important_tokens = _important_business_tokens(record.display_name)
    if not important_tokens:
        return False
    haystack = " ".join([result.title, result.url, result.description]).lower()
    return any(token in haystack for token in important_tokens)


def _owned_host_matches_business(record: ProspectRecord, host: str) -> bool:
    host_text = host.lower()
    return any(token in host_text for token in _important_business_tokens(record.display_name))


def _important_business_tokens(name: str) -> set[str]:
    tokens = {
        token
        for token in "".join(char.lower() if char.isalnum() else " " for char in name).split()
        if len(token) > 2
    }
    important = tokens - GENERIC_BUSINESS_TOKENS
    return important or tokens


def _locality_from_address(address: str) -> str:
    parts = [part.strip() for part in address.split(",") if part.strip()]
    if len(parts) >= 3:
        state = parts[2].split()[0] if parts[2].split() else ""
        return " ".join(part for part in [parts[1], state] if part)
    if len(parts) >= 2:
        return parts[1]
    return ""


def _normalized_result_host(url: str) -> str:
    parsed = urlparse(url)
    if not parsed.netloc and "://" not in url:
        return normalized_host(f"https://{url}")
    return normalized_host(url)


def _host_in(host: str, candidates: set[str]) -> bool:
    return any(host == candidate or host.endswith(f".{candidate}") for candidate in candidates)


def _raise_provider_status(response: httpx.Response, provider: str) -> None:
    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        detail = response.text[:600].replace("\n", " ")
        raise SearchProviderError(f"{provider} request failed: {exc}; response={detail}") from exc
