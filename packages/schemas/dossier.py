"""Dossier schema — a one-click research brief for a single opportunity.

The artifact the strategist and engineer work from once an opportunity clears
the validate gate. Carries the pain quotes (reused in validation copy), the
competitive map, the thinnest-slice MVP, the monetization model, and the
distribution plan (each channel with its compliance note).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum


class MonetizationModel(str, Enum):
    SUBSCRIPTION = "subscription"
    ONE_TIME = "one-time"
    CREDITS = "credits"
    USAGE_METERED = "usage-metered"
    LEAD_GEN = "lead-gen"
    AFFILIATE = "affiliate"
    DIGITAL_PRODUCT = "digital-product"
    SPONSORED = "sponsored"
    MARKETPLACE_FEE = "marketplace-fee"


@dataclass(frozen=True)
class DossierAudience:
    who: str
    size: str = ""  # rough TAM/SAM estimate with reasoning
    where_they_are: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "DossierAudience":
        return cls(
            who=str(payload["who"]),
            size=str(payload.get("size", "")),
            where_they_are=[str(item) for item in list(payload.get("where_they_are", []))],
        )


@dataclass(frozen=True)
class DossierCompetitor:
    name: str
    url: str = ""
    pricing: str = ""
    strengths: list[str] = field(default_factory=list)
    weaknesses: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "DossierCompetitor":
        return cls(
            name=str(payload["name"]),
            url=str(payload.get("url", "")),
            pricing=str(payload.get("pricing", "")),
            strengths=[str(item) for item in list(payload.get("strengths", []))],
            weaknesses=[str(item) for item in list(payload.get("weaknesses", []))],
        )


@dataclass(frozen=True)
class DossierMvp:
    thinnest_slice: str = ""
    build_kit: str = ""
    estimated_build_days: float | None = None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "DossierMvp":
        days = payload.get("estimated_build_days")
        return cls(
            thinnest_slice=str(payload.get("thinnest_slice", "")),
            build_kit=str(payload.get("build_kit", "")),
            estimated_build_days=None if days is None else float(days),  # type: ignore[arg-type]
        )


@dataclass(frozen=True)
class DossierMonetization:
    model: MonetizationModel
    price_point: str = ""
    rationale: str = ""

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["model"] = self.model.value
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "DossierMonetization":
        return cls(
            model=MonetizationModel(str(payload["model"])),
            price_point=str(payload.get("price_point", "")),
            rationale=str(payload.get("rationale", "")),
        )


@dataclass(frozen=True)
class DossierChannel:
    channel: str
    approach: str = ""
    compliance: str = ""  # ToS/anti-spam constraints for this channel

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "DossierChannel":
        return cls(
            channel=str(payload["channel"]),
            approach=str(payload.get("approach", "")),
            compliance=str(payload.get("compliance", "")),
        )


@dataclass(frozen=True)
class DossierRecord:
    id: str
    opportunity_id: str
    summary: str
    audience: DossierAudience
    pain_quotes: list[str] = field(default_factory=list)
    competitors: list[DossierCompetitor] = field(default_factory=list)
    mvp: DossierMvp | None = None
    monetization: DossierMonetization | None = None
    distribution: list[DossierChannel] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    open_questions: list[str] = field(default_factory=list)
    created_at: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "opportunity_id": self.opportunity_id,
            "summary": self.summary,
            "audience": self.audience.to_dict(),
            "pain_quotes": list(self.pain_quotes),
            "competitors": [competitor.to_dict() for competitor in self.competitors],
            "mvp": self.mvp.to_dict() if self.mvp else None,
            "monetization": self.monetization.to_dict() if self.monetization else None,
            "distribution": [channel.to_dict() for channel in self.distribution],
            "risks": list(self.risks),
            "open_questions": list(self.open_questions),
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "DossierRecord":
        mvp = payload.get("mvp")
        monetization = payload.get("monetization")
        return cls(
            id=str(payload["id"]),
            opportunity_id=str(payload["opportunity_id"]),
            summary=str(payload["summary"]),
            audience=DossierAudience.from_dict(dict(payload["audience"])),  # type: ignore[arg-type]
            pain_quotes=[str(item) for item in list(payload.get("pain_quotes", []))],
            competitors=[
                DossierCompetitor.from_dict(dict(item))
                for item in list(payload.get("competitors", []))
            ],
            mvp=DossierMvp.from_dict(dict(mvp)) if mvp else None,
            monetization=(
                DossierMonetization.from_dict(dict(monetization)) if monetization else None
            ),
            distribution=[
                DossierChannel.from_dict(dict(item))
                for item in list(payload.get("distribution", []))
            ],
            risks=[str(item) for item in list(payload.get("risks", []))],
            open_questions=[str(item) for item in list(payload.get("open_questions", []))],
            created_at=str(payload.get("created_at", "")),
        )
