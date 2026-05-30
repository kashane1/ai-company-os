"""Opportunity schema — the atomic unit of the discovery layer.

A discovered "wedge": a problem someone might pay to solve, captured with
evidence and scored against the twelve-signal scorecard
(``docs/founder/opportunity-scorecard.md``).

Follows the repo schema convention: frozen dataclasses + ``str`` enums with
explicit ``to_dict`` / ``from_dict`` so records are persistable through the
``JsonStore`` without any framework coupling.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum


class OpportunityStatus(str, Enum):
    INBOX = "inbox"
    SCORED = "scored"
    VALIDATING = "validating"
    VALIDATED = "validated"
    BUILDING = "building"
    SHIPPED = "shipped"
    KILLED = "killed"


class ComplianceFlag(str, Enum):
    TOS_RISK = "tos-risk"
    PII = "pii"
    REGULATED_DATA = "regulated-data"
    SCRAPING_REQUIRED = "scraping-required"
    NEEDS_REVIEW = "needs-review"


class EvidenceKind(str, Enum):
    COMPLAINT = "complaint"
    REQUEST = "request"
    WORKAROUND = "workaround"
    REVIEW = "review"
    SEARCH_TREND = "search-trend"
    COMPETITOR = "competitor"
    WILLINGNESS_TO_PAY = "willingness-to-pay"
    OTHER = "other"


# The twelve scorecard signals. Each is 0-10 (10 = strongest). ``risk`` is
# INVERTED: 10 means LOW regulatory/ToS risk, so "higher is always better" and
# the weighted sum stays monotonic. The field names here are the canonical keys
# used by config/scoring.yaml and packages/discovery/scoring.py.
SIGNAL_KEYS: tuple[str, ...] = (
    "search_volume",
    "buyer_intent",
    "urgency",
    "willingness_to_pay",
    "competition_weakness",
    "community_pain",
    "repeated_workflow",
    "distribution_path",
    "expected_margin",
    "build_feasibility",
    "defensibility",
    "risk",
)


@dataclass(frozen=True)
class OpportunitySignals:
    """Scorecard inputs, each 0-10. ``risk`` is inverted (10 = low risk)."""

    search_volume: float = 0.0
    buyer_intent: float = 0.0
    urgency: float = 0.0
    willingness_to_pay: float = 0.0
    competition_weakness: float = 0.0
    community_pain: float = 0.0
    repeated_workflow: float = 0.0
    distribution_path: float = 0.0
    expected_margin: float = 0.0
    build_feasibility: float = 0.0
    defensibility: float = 0.0
    risk: float = 0.0

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "OpportunitySignals":
        return cls(**{key: float(payload.get(key, 0) or 0) for key in SIGNAL_KEYS})


@dataclass(frozen=True)
class EvidenceLink:
    """A link + short quote that proves the pain is real. Drives confidence."""

    url: str
    kind: EvidenceKind = EvidenceKind.OTHER
    quote: str = ""
    captured_at: str = ""

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["kind"] = self.kind.value
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "EvidenceLink":
        return cls(
            url=str(payload["url"]),
            kind=EvidenceKind(str(payload.get("kind", EvidenceKind.OTHER.value))),
            quote=str(payload.get("quote", "")),
            captured_at=str(payload.get("captured_at", "")),
        )


@dataclass(frozen=True)
class Competitor:
    name: str
    url: str = ""
    pricing: str = ""
    weakness: str = ""

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "Competitor":
        return cls(
            name=str(payload["name"]),
            url=str(payload.get("url", "")),
            pricing=str(payload.get("pricing", "")),
            weakness=str(payload.get("weakness", "")),
        )


@dataclass(frozen=True)
class SourceRef:
    """Which connector found the signal. ``connector`` matches config/sources.yaml."""

    connector: str
    query: str = ""

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "SourceRef":
        return cls(connector=str(payload["connector"]), query=str(payload.get("query", "")))


@dataclass(frozen=True)
class OpportunityRecord:
    """A discovered wedge. ``problem`` + ``audience`` + ``evidence`` are the core;
    ``signals`` / ``score`` / ``confidence`` are filled by the scoring step."""

    id: str
    title: str
    problem: str
    audience: str
    source: SourceRef
    status: OpportunityStatus = OpportunityStatus.INBOX
    evidence: list[EvidenceLink] = field(default_factory=list)
    competitors: list[Competitor] = field(default_factory=list)
    signals: OpportunitySignals | None = None
    score: float | None = None
    confidence: float | None = None
    compliance_flags: list[ComplianceFlag] = field(default_factory=list)
    mvp_idea: str = ""
    distribution_ideas: list[str] = field(default_factory=list)
    next_actions: list[str] = field(default_factory=list)
    kill_reason: str = ""
    created_at: str = ""
    updated_at: str = ""

    def distinct_sources(self) -> int:
        """Count distinct evidence hosts/kinds — feeds the confidence model."""
        hosts = {_host(link.url) for link in self.evidence if link.url}
        return len(hosts)

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "title": self.title,
            "problem": self.problem,
            "audience": self.audience,
            "source": self.source.to_dict(),
            "status": self.status.value,
            "evidence": [link.to_dict() for link in self.evidence],
            "competitors": [competitor.to_dict() for competitor in self.competitors],
            "signals": self.signals.to_dict() if self.signals else None,
            "score": self.score,
            "confidence": self.confidence,
            "compliance_flags": [flag.value for flag in self.compliance_flags],
            "mvp_idea": self.mvp_idea,
            "distribution_ideas": list(self.distribution_ideas),
            "next_actions": list(self.next_actions),
            "kill_reason": self.kill_reason,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "OpportunityRecord":
        signals = payload.get("signals")
        return cls(
            id=str(payload["id"]),
            title=str(payload["title"]),
            problem=str(payload["problem"]),
            audience=str(payload["audience"]),
            source=SourceRef.from_dict(dict(payload["source"])),  # type: ignore[arg-type]
            status=OpportunityStatus(str(payload.get("status", OpportunityStatus.INBOX.value))),
            evidence=[
                EvidenceLink.from_dict(dict(item)) for item in list(payload.get("evidence", []))
            ],
            competitors=[
                Competitor.from_dict(dict(item)) for item in list(payload.get("competitors", []))
            ],
            signals=OpportunitySignals.from_dict(dict(signals)) if signals else None,
            score=_opt_float(payload.get("score")),
            confidence=_opt_float(payload.get("confidence")),
            compliance_flags=[
                ComplianceFlag(str(flag)) for flag in list(payload.get("compliance_flags", []))
            ],
            mvp_idea=str(payload.get("mvp_idea", "")),
            distribution_ideas=[str(item) for item in list(payload.get("distribution_ideas", []))],
            next_actions=[str(item) for item in list(payload.get("next_actions", []))],
            kill_reason=str(payload.get("kill_reason", "")),
            created_at=str(payload.get("created_at", "")),
            updated_at=str(payload.get("updated_at", "")),
        )


def _opt_float(value: object) -> float | None:
    return None if value is None else float(value)  # type: ignore[arg-type]


def _host(url: str) -> str:
    """Best-effort host extraction without importing urllib at call sites."""
    from urllib.parse import urlparse

    netloc = urlparse(url).netloc.lower()
    return netloc[4:] if netloc.startswith("www.") else netloc
