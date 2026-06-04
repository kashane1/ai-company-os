"""Owner-friendly monthly retainer reports."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class MonthlyMetrics:
    product_id: str
    month: str
    visits: int = 0
    form_leads: int = 0
    calls_tracked: bool = False
    calls: int | None = None
    completed_work: list[str] = field(default_factory=list)
    recommended_action: str = ""
    billing_status: str = ""

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "MonthlyMetrics":
        return cls(
            product_id=str(payload["product_id"]),
            month=str(payload["month"]),
            visits=int(payload.get("visits", 0)),
            form_leads=int(payload.get("form_leads", 0)),
            calls_tracked=bool(payload.get("calls_tracked", False)),
            calls=(
                int(payload["calls"])
                if payload.get("calls") is not None
                else None
            ),
            completed_work=[str(item) for item in list(payload.get("completed_work", []))],
            recommended_action=str(payload.get("recommended_action", "")),
            billing_status=str(payload.get("billing_status", "")),
        )


def load_monthly_metrics(path: Path) -> MonthlyMetrics:
    return MonthlyMetrics.from_dict(json.loads(path.read_text(encoding="utf-8")))


def render_monthly_report(metrics: MonthlyMetrics, *, client_name: str) -> str:
    calls = str(metrics.calls) if metrics.calls_tracked and metrics.calls is not None else "Not tracked yet"
    completed = "\n".join(f"- {item}" for item in metrics.completed_work) or "- Routine monitoring"
    recommended = metrics.recommended_action or "Keep the current plan running and review next month's lead volume."
    billing = f"\n- **Billing status:** {metrics.billing_status}" if metrics.billing_status else ""
    return "\n".join(
        [
            f"# Monthly Report — {client_name}",
            "",
            f"**Month:** {metrics.month}",
            "",
            "## Results",
            "",
            f"- **Website visits:** {metrics.visits}",
            f"- **Form leads:** {metrics.form_leads}",
            f"- **Calls:** {calls}",
            billing,
            "",
            "## Work completed",
            "",
            completed,
            "",
            "## Recommended next action",
            "",
            recommended,
            "",
            "> Draft report. Operator reviews and forwards manually.",
            "",
        ]
    )


def write_monthly_report(
    docs_root: Path,
    metrics: MonthlyMetrics,
    *,
    client_name: str,
) -> Path:
    reports = docs_root / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    path = reports / f"{metrics.month}.md"
    path.write_text(render_monthly_report(metrics, client_name=client_name), encoding="utf-8")
    return path
