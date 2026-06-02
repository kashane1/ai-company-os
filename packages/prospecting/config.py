"""Configuration loaders for Phase 1 prospecting catalogs."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover - dependency is declared
    yaml = None  # type: ignore


CONFIG_ROOT = Path(__file__).resolve().parent / "config"


@dataclass(frozen=True)
class CityConfig:
    id: str
    name: str
    lat: float
    lng: float
    radius_m: int = 12000


@dataclass(frozen=True)
class GenreConfig:
    id: str
    label: str
    text_query_template: str
    included_types: list[str] = field(default_factory=list)

    def query_for(self, city: CityConfig) -> str:
        return self.text_query_template.format(label=self.label, city_name=city.name)


@dataclass(frozen=True)
class WeeklyCaps:
    text_search_requests: int = 100
    place_details_essentials: int = 6000
    http_checks: int = 6000
    place_details_pro_reviews: int = 0
    google_search_verifications: int = 0


@dataclass(frozen=True)
class HttpConfig:
    timeout_seconds: float = 5.0
    max_redirects: int = 5
    per_host_rpm: int = 30


def load_cities(path: Path | None = None) -> list[CityConfig]:
    raw = _load_yaml(path or CONFIG_ROOT / "cities.yaml")
    return [
        CityConfig(
            id=str(item["id"]),
            name=str(item["name"]),
            lat=float(item["lat"]),
            lng=float(item["lng"]),
            radius_m=int(item.get("radius_m", 12000)),
        )
        for item in list(raw.get("cities", []))
    ]


def load_genres(path: Path | None = None) -> list[GenreConfig]:
    raw = _load_yaml(path or CONFIG_ROOT / "genres.yaml")
    return [
        GenreConfig(
            id=str(item["id"]),
            label=str(item["label"]),
            text_query_template=str(item.get("text_query_template", "{label} in {city_name}")),
            included_types=[str(value) for value in list(item.get("included_types", []))],
        )
        for item in list(raw.get("genres", []))
    ]


def load_weekly_caps(path: Path | None = None) -> WeeklyCaps:
    raw = _load_yaml(path or CONFIG_ROOT / "weekly_caps.yaml")
    return WeeklyCaps(
        text_search_requests=int(raw.get("text_search_requests", 100)),
        place_details_essentials=int(raw.get("place_details_essentials", 6000)),
        http_checks=int(raw.get("http_checks", 6000)),
        place_details_pro_reviews=int(raw.get("place_details_pro_reviews", 0)),
        google_search_verifications=int(raw.get("google_search_verifications", 0)),
    )


def load_http_config(path: Path | None = None) -> HttpConfig:
    raw = _load_yaml(path or CONFIG_ROOT / "http.yaml")
    return HttpConfig(
        timeout_seconds=float(raw.get("timeout_seconds", 5)),
        max_redirects=int(raw.get("max_redirects", 5)),
        per_host_rpm=int(raw.get("per_host_rpm", 30)),
    )


def _load_yaml(path: Path) -> dict[str, object]:
    if yaml is None:  # pragma: no cover
        raise RuntimeError("pyyaml is required to load prospecting config")
    return dict(yaml.safe_load(path.read_text()) or {})

