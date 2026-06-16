"""Cross-source prospect identity matching.

Google Places IDs are stable only inside Google. Open POI sources use different
ids, so every future connector should pass candidates through this index before
writing a new prospect record.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from packages.prospecting.connectors.google_places import normalized_host
from packages.schemas.prospect import ProspectRecord

BUSINESS_SUFFIXES = {
    "co",
    "company",
    "corp",
    "corporation",
    "inc",
    "llc",
    "ltd",
    "pllc",
    "the",
}

STREET_ABBREVIATIONS = {
    "avenue": "ave",
    "boulevard": "blvd",
    "drive": "dr",
    "lane": "ln",
    "place": "pl",
    "road": "rd",
    "street": "st",
    "suite": "ste",
}


@dataclass(frozen=True)
class ProspectCandidate:
    source: str
    source_id: str
    display_name: str
    formatted_address: str
    phone: str
    city_id: str
    genre_id: str
    website_uri: str = ""
    social_urls: list[str] = field(default_factory=list)
    marketplace_urls: list[str] = field(default_factory=list)
    source_confidence: float = 0.0
    rating: float | None = None
    review_count: int = 0


@dataclass(frozen=True)
class IdentityMatch:
    place_id: str
    match_type: str
    confidence: float
    reason: str


class IdentityIndex:
    def __init__(
        self,
        *,
        by_phone: dict[str, str],
        by_name_address: dict[str, str],
        by_url: dict[str, str],
    ) -> None:
        self._by_phone = by_phone
        self._by_name_address = by_name_address
        self._by_url = by_url

    @classmethod
    def from_records(cls, records: list[ProspectRecord]) -> "IdentityIndex":
        by_phone: dict[str, str] = {}
        by_name_address: dict[str, str] = {}
        by_url: dict[str, str] = {}
        for record in records:
            _index_record(record, by_phone, by_name_address, by_url)
        return cls(by_phone=by_phone, by_name_address=by_name_address, by_url=by_url)

    def add_record(self, record: ProspectRecord) -> None:
        _index_record(record, self._by_phone, self._by_name_address, self._by_url)

    def match(self, candidate: ProspectCandidate) -> IdentityMatch | None:
        phone = normalize_phone(candidate.phone)
        if phone and phone in self._by_phone:
            return IdentityMatch(
                place_id=self._by_phone[phone],
                match_type="phone",
                confidence=0.98,
                reason=f"normalized phone matched {phone}",
            )

        for url in candidate_urls(candidate):
            normalized = normalize_url(url)
            if normalized and normalized in self._by_url:
                return IdentityMatch(
                    place_id=self._by_url[normalized],
                    match_type="url",
                    confidence=0.94,
                    reason=f"normalized URL matched {normalized}",
                )

        name_address = name_address_key(candidate.display_name, candidate.formatted_address)
        if name_address and name_address in self._by_name_address:
            return IdentityMatch(
                place_id=self._by_name_address[name_address],
                match_type="name_address",
                confidence=0.9,
                reason=f"normalized name/address matched {name_address}",
            )
        return None


def candidate_urls(candidate: ProspectCandidate) -> list[str]:
    return [
        url
        for url in [
            candidate.website_uri,
            *candidate.social_urls,
            *candidate.marketplace_urls,
        ]
        if url
    ]


def normalize_phone(value: str) -> str:
    digits = re.sub(r"\D+", "", value)
    if not digits:
        return ""
    if len(digits) == 10:
        return f"1{digits}"
    return digits


def normalize_url(value: str) -> str:
    if not value:
        return ""
    url = value if "://" in value else f"https://{value}"
    host = normalized_host(url)
    if not host:
        return ""
    path = re.sub(r"/+$", "", re.sub(r"^https?://[^/]+", "", url.lower()))
    return f"{host}{path}"


def name_address_key(name: str, address: str) -> str:
    normalized_name = normalize_name(name)
    normalized_address = normalize_address(address)
    if not normalized_name or not normalized_address:
        return ""
    return f"{normalized_name}|{normalized_address}"


def normalize_name(value: str) -> str:
    tokens = _tokens(value)
    filtered = [token for token in tokens if token not in BUSINESS_SUFFIXES]
    return " ".join(filtered or tokens)


def normalize_address(value: str) -> str:
    first_line = value.split(",", 1)[0]
    tokens = [STREET_ABBREVIATIONS.get(token, token) for token in _tokens(first_line)]
    return " ".join(tokens)


def _tokens(value: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", value.lower())


def _index_record(
    record: ProspectRecord,
    by_phone: dict[str, str],
    by_name_address: dict[str, str],
    by_url: dict[str, str],
) -> None:
    phone = normalize_phone(record.phone)
    if phone:
        by_phone.setdefault(phone, record.place_id)
    name_address = name_address_key(record.display_name, record.formatted_address)
    if name_address:
        by_name_address.setdefault(name_address, record.place_id)
    url = normalize_url(record.maps_website_uri)
    if url:
        by_url.setdefault(url, record.place_id)
