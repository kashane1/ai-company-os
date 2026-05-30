"""Discovery metrics — funnel + source yield over opportunity records.

Implements the measurable parts of ``docs/founder/discovery-evals.md``: where do
wedges die (funnel), and which sources actually produce validated wedges (source
yield). Pure functions over a list of records so they can run against either the
JsonStore inbox or the DB store output.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from packages.schemas.opportunity import OpportunityRecord, OpportunityStatus

# A wedge counts as "validated" once it has cleared the validate gate, i.e. it
# reached validation or anything downstream of it.
VALIDATED_STATUSES = frozenset(
    {
        OpportunityStatus.VALIDATED,
        OpportunityStatus.BUILDING,
        OpportunityStatus.SHIPPED,
    }
)
SHIPPED_STATUSES = frozenset({OpportunityStatus.SHIPPED})


@dataclass(frozen=True)
class SourceYield:
    connector: str
    found: int
    validated: int

    @property
    def yield_ratio(self) -> float:
        return round(self.validated / self.found, 4) if self.found else 0.0


@dataclass(frozen=True)
class DiscoveryMetrics:
    total: int
    by_status: dict[str, int] = field(default_factory=dict)
    killed: int = 0
    validated: int = 0
    shipped: int = 0
    source_yield: list[SourceYield] = field(default_factory=list)

    @property
    def validation_rate(self) -> float:
        return round(self.validated / self.total, 4) if self.total else 0.0

    def to_markdown(self) -> str:
        lines = [
            "# Discovery metrics",
            "",
            f"- total opportunities: **{self.total}**",
            f"- validated: **{self.validated}** ({self.validation_rate:.0%})",
            f"- shipped: **{self.shipped}**",
            f"- killed: **{self.killed}**",
            "",
            "## By status",
            "",
        ]
        for status, count in sorted(self.by_status.items()):
            lines.append(f"- {status}: {count}")
        lines += ["", "## Source yield (validated ÷ found)", "",
                   "| Source | Found | Validated | Yield |",
                   "|--------|------:|----------:|------:|"]
        for item in sorted(self.source_yield, key=lambda s: s.yield_ratio, reverse=True):
            lines.append(
                f"| {item.connector} | {item.found} | {item.validated} | {item.yield_ratio:.0%} |"
            )
        return "\n".join(lines) + "\n"


def funnel_counts(records: list[OpportunityRecord]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for record in records:
        counts[record.status.value] = counts.get(record.status.value, 0) + 1
    return counts


def source_yield(records: list[OpportunityRecord]) -> list[SourceYield]:
    found: dict[str, int] = {}
    validated: dict[str, int] = {}
    for record in records:
        connector = record.source.connector
        found[connector] = found.get(connector, 0) + 1
        if record.status in VALIDATED_STATUSES:
            validated[connector] = validated.get(connector, 0) + 1
    return [
        SourceYield(connector=connector, found=count, validated=validated.get(connector, 0))
        for connector, count in sorted(found.items())
    ]


def compute_metrics(records: list[OpportunityRecord]) -> DiscoveryMetrics:
    by_status = funnel_counts(records)
    validated = sum(1 for r in records if r.status in VALIDATED_STATUSES)
    shipped = sum(1 for r in records if r.status in SHIPPED_STATUSES)
    killed = sum(1 for r in records if r.status is OpportunityStatus.KILLED)
    return DiscoveryMetrics(
        total=len(records),
        by_status=by_status,
        killed=killed,
        validated=validated,
        shipped=shipped,
        source_yield=source_yield(records),
    )
