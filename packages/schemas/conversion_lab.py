from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum


class ConversionAction(str, Enum):
    CALL = "call"
    FORM = "form"
    BOOKING = "booking"
    PURCHASE = "purchase"
    REPLY = "reply"


@dataclass(frozen=True)
class ConversionLabInput:
    product_id: str
    vertical: str
    target_action: ConversionAction
    url: str = ""
    page_copy: str = ""
    known_objections: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "product_id": self.product_id,
            "vertical": self.vertical,
            "target_action": self.target_action.value,
            "url": self.url,
            "page_copy": self.page_copy,
            "known_objections": list(self.known_objections),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "ConversionLabInput":
        return cls(
            product_id=str(payload["product_id"]),
            vertical=str(payload["vertical"]),
            target_action=ConversionAction(str(payload["target_action"])),
            url=str(payload.get("url", "")),
            page_copy=str(payload.get("page_copy", "")),
            known_objections=[str(item) for item in list(payload.get("known_objections", []))],
        )


@dataclass(frozen=True)
class PersonaReview:
    persona_id: str
    likely_action: str
    objections: list[str] = field(default_factory=list)
    trust_gaps: list[str] = field(default_factory=list)
    useful_rewrites: list[str] = field(default_factory=list)
    clarity_notes: list[str] = field(default_factory=list)
    confidence: str = "medium"

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "PersonaReview":
        return cls(
            persona_id=str(payload["persona_id"]),
            likely_action=str(payload["likely_action"]),
            objections=[str(item) for item in list(payload.get("objections", []))],
            trust_gaps=[str(item) for item in list(payload.get("trust_gaps", []))],
            useful_rewrites=[str(item) for item in list(payload.get("useful_rewrites", []))],
            clarity_notes=[str(item) for item in list(payload.get("clarity_notes", []))],
            confidence=str(payload.get("confidence", "medium")),
        )


@dataclass(frozen=True)
class Scorecard:
    clarity: int
    trust: int
    offer_strength: int
    friction: int
    local_relevance: int
    conversion_action: int

    def __post_init__(self) -> None:
        for field_name, value in asdict(self).items():
            if int(value) < 1 or int(value) > 10:
                raise ValueError(f"{field_name} score must be between 1 and 10")

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "Scorecard":
        return cls(
            clarity=int(payload["clarity"]),
            trust=int(payload["trust"]),
            offer_strength=int(payload["offer_strength"]),
            friction=int(payload["friction"]),
            local_relevance=int(payload["local_relevance"]),
            conversion_action=int(payload["conversion_action"]),
        )


@dataclass(frozen=True)
class ConversionLabReport:
    product_id: str
    vertical: str
    scorecard: Scorecard
    persona_reviews: list[PersonaReview] = field(default_factory=list)
    top_blockers: list[str] = field(default_factory=list)
    top_trust_gaps: list[str] = field(default_factory=list)
    recommended_rewrites: dict[str, str] = field(default_factory=dict)
    confidence_label: str = "medium"

    def to_dict(self) -> dict[str, object]:
        return {
            "product_id": self.product_id,
            "vertical": self.vertical,
            "scorecard": self.scorecard.to_dict(),
            "persona_reviews": [review.to_dict() for review in self.persona_reviews],
            "top_blockers": list(self.top_blockers),
            "top_trust_gaps": list(self.top_trust_gaps),
            "recommended_rewrites": dict(self.recommended_rewrites),
            "confidence_label": self.confidence_label,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "ConversionLabReport":
        rewrites = dict(payload.get("recommended_rewrites", {}))
        return cls(
            product_id=str(payload["product_id"]),
            vertical=str(payload["vertical"]),
            scorecard=Scorecard.from_dict(dict(payload["scorecard"])),
            persona_reviews=[
                PersonaReview.from_dict(dict(review))
                for review in list(payload.get("persona_reviews", []))
            ],
            top_blockers=[str(item) for item in list(payload.get("top_blockers", []))],
            top_trust_gaps=[str(item) for item in list(payload.get("top_trust_gaps", []))],
            recommended_rewrites={str(key): str(value) for key, value in rewrites.items()},
            confidence_label=str(payload.get("confidence_label", "medium")),
        )
