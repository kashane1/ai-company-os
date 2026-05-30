"""Experiment schema — a cheap demand test run BEFORE building.

The validate stage of the loop. Success criteria MUST be set before the
experiment runs (no post-hoc goalposts). The advancement policy in
``packages/policies/discovery_gates.py`` will only open the build gate for an
experiment whose status is ``PASSED``.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum


class ExperimentType(str, Enum):
    LANDING_PAGE = "landing-page"
    WAITLIST = "waitlist"
    COLD_OUTREACH = "cold-outreach"
    COMMUNITY_POST = "community-post"
    PAID_AD = "paid-ad"
    FAKE_DOOR = "fake-door"
    CONCIERGE = "concierge"
    MARKETPLACE_LISTING = "marketplace-listing"
    PAID_PILOT = "paid-pilot"


class ExperimentMetric(str, Enum):
    SIGNUPS = "signups"
    CONVERSION_RATE = "conversion-rate"
    REPLY_RATE = "reply-rate"
    PREORDERS = "preorders"
    PAID_PILOTS = "paid-pilots"
    CTR = "ctr"


class ExperimentStatus(str, Enum):
    PLANNED = "planned"
    APPROVED = "approved"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(frozen=True)
class SuccessCriteria:
    """Defined BEFORE running. ``threshold`` is the number that must be met."""

    metric: ExperimentMetric
    threshold: float
    window: str = ""  # time box, e.g. "7 days"

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["metric"] = self.metric.value
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "SuccessCriteria":
        return cls(
            metric=ExperimentMetric(str(payload["metric"])),
            threshold=float(payload["threshold"]),
            window=str(payload.get("window", "")),
        )


@dataclass(frozen=True)
class ExperimentSpend:
    budget: float = 0.0
    currency: str = "USD"
    approved_by: str = ""  # required if budget > 0; spend passes an approval gate

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "ExperimentSpend":
        return cls(
            budget=float(payload.get("budget", 0) or 0),
            currency=str(payload.get("currency", "USD")),
            approved_by=str(payload.get("approved_by", "")),
        )


@dataclass(frozen=True)
class ExperimentCompliance:
    reviewed_by: str = ""
    notes: str = ""
    unsubscribe_wired: bool = False
    suppression_checked: bool = False

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "ExperimentCompliance":
        return cls(
            reviewed_by=str(payload.get("reviewed_by", "")),
            notes=str(payload.get("notes", "")),
            unsubscribe_wired=bool(payload.get("unsubscribe_wired", False)),
            suppression_checked=bool(payload.get("suppression_checked", False)),
        )


@dataclass(frozen=True)
class ExperimentResults:
    metric_value: float | None = None
    passed: bool | None = None
    notes: str = ""
    raw_data_url: str = ""

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "ExperimentResults":
        metric_value = payload.get("metric_value")
        passed = payload.get("passed")
        return cls(
            metric_value=None if metric_value is None else float(metric_value),  # type: ignore[arg-type]
            passed=None if passed is None else bool(passed),
            notes=str(payload.get("notes", "")),
            raw_data_url=str(payload.get("raw_data_url", "")),
        )


@dataclass(frozen=True)
class ExperimentRecord:
    id: str
    opportunity_id: str
    type: ExperimentType
    hypothesis: str
    success_criteria: SuccessCriteria
    status: ExperimentStatus = ExperimentStatus.PLANNED
    spend: ExperimentSpend | None = None
    compliance: ExperimentCompliance | None = None
    results: ExperimentResults | None = None
    created_at: str = ""
    completed_at: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "opportunity_id": self.opportunity_id,
            "type": self.type.value,
            "hypothesis": self.hypothesis,
            "success_criteria": self.success_criteria.to_dict(),
            "status": self.status.value,
            "spend": self.spend.to_dict() if self.spend else None,
            "compliance": self.compliance.to_dict() if self.compliance else None,
            "results": self.results.to_dict() if self.results else None,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "ExperimentRecord":
        spend = payload.get("spend")
        compliance = payload.get("compliance")
        results = payload.get("results")
        return cls(
            id=str(payload["id"]),
            opportunity_id=str(payload["opportunity_id"]),
            type=ExperimentType(str(payload["type"])),
            hypothesis=str(payload["hypothesis"]),
            success_criteria=SuccessCriteria.from_dict(dict(payload["success_criteria"])),  # type: ignore[arg-type]
            status=ExperimentStatus(str(payload.get("status", ExperimentStatus.PLANNED.value))),
            spend=ExperimentSpend.from_dict(dict(spend)) if spend else None,
            compliance=ExperimentCompliance.from_dict(dict(compliance)) if compliance else None,
            results=ExperimentResults.from_dict(dict(results)) if results else None,
            created_at=str(payload.get("created_at", "")),
            completed_at=str(payload.get("completed_at", "")),
        )
