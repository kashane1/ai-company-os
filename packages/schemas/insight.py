from dataclasses import asdict, dataclass, field
from enum import Enum


class InsightScope(str, Enum):
    WATERBODY = "waterbody"
    SPOT = "spot"
    SPECIES = "species"
    TRIP_CONTEXT = "trip_context"
    SEASONAL = "seasonal"


class InsightRuleType(str, Enum):
    TOP_LURE = "top_lure"
    BEST_TIME_WINDOW = "best_time_window"
    CATCH_RATE = "catch_rate"
    SIMILAR_CONDITIONS = "similar_conditions"
    PERSONAL_BEST = "personal_best"
    SEASONALITY = "seasonality"


class InsightRuleStatus(str, Enum):
    ACTIVE = "active"
    DRAFT = "draft"


@dataclass(frozen=True)
class InsightRule:
    id: str
    product_id: str
    scope: InsightScope
    rule_type: InsightRuleType
    description: str
    inputs: list[str] = field(default_factory=list)
    output_template: str = ""
    status: InsightRuleStatus = InsightRuleStatus.ACTIVE

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["scope"] = self.scope.value
        payload["rule_type"] = self.rule_type.value
        payload["status"] = self.status.value
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "InsightRule":
        return cls(
            id=str(payload["id"]),
            product_id=str(payload["product_id"]),
            scope=InsightScope(str(payload["scope"])),
            rule_type=InsightRuleType(str(payload["rule_type"])),
            description=str(payload["description"]),
            inputs=list(payload.get("inputs", [])),
            output_template=str(payload.get("output_template", "")),
            status=InsightRuleStatus(str(payload.get("status", InsightRuleStatus.ACTIVE.value))),
        )


@dataclass(frozen=True)
class InsightCardExample:
    rule_id: str
    title: str
    body: str
    confidence_label: str
    supporting_sample_count: int

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "InsightCardExample":
        return cls(
            rule_id=str(payload["rule_id"]),
            title=str(payload["title"]),
            body=str(payload["body"]),
            confidence_label=str(payload["confidence_label"]),
            supporting_sample_count=int(payload["supporting_sample_count"]),
        )
