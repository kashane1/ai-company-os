"""One honest scoreboard for the prospect-to-client funnel.

Every count is measured from a primary source, never from a hand-maintained
tally that can drift:

* **collected** — ``state/prospects/records/*.json`` (every scanned prospect)
* **audited** — distinct ``place_id`` carrying a ``web_verify_verdict`` across
  ``state/prospects/audited/*.csv`` (a subset, ``target_verdicts``, are the
  no-owned-site classes worth building for)
* **built** — ``state/prospects/sites/*/dist-v2/index.html`` on disk
* **deployed** — records carrying a ``mockup_url`` (a live preview to send)
* **sent** — distinct ``place_id`` in the ``outreach_touches`` store
* **replied / won / lost** — the outreach-lane ledger summary
* **active_clients / MRR** — billing ledgers in ``ACTIVE`` state, priced at the
  catalog's current monthly rate

The 587-built / 0-sent imbalance was invisible until measured by hand once; this
module makes that measurement a single fast command whose output is
committed-format-stable so the diff between two runs is readable. It computes
and reports — it changes no prospect, ledger, or site state.
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from packages.agency.billing import BillingLedger, default_billing_root
from packages.agency.catalog import default_catalog
from packages.agency.outreach_lane import (
    default_outreach_lane_root,
    default_records_root,
    load_raw_records,
)
from packages.agency.outreach_store import OutreachStore
from packages.config.settings import load_runtime_paths
from packages.schemas.offer import CatalogError, ServiceCatalog
from packages.schemas.product import BillingStatus

# Verdict classes that mean "no owned website" — the prospects a demo is built
# for. Other verdicts (owned_site, ambiguous, unverified) are not build targets.
TARGET_VERDICTS = frozenset({"none_found", "marketplace_only", "social_only"})

# Minimum gap between dashboard-triggered refreshes. The cooldown is anchored to
# the last report's ``updated_at`` (not a process timer), so it survives a server
# restart and is shared across browser tabs. The scheduled cron run is exempt —
# it calls ``compute_funnel`` directly, never this wrapper.
FUNNEL_REFRESH_COOLDOWN_SECONDS = 120

# The funnel pipeline, in order. Each stage's conversion rate is measured
# against the stage immediately before it.
STAGE_ORDER: tuple[tuple[str, str], ...] = (
    ("collected", "Collected"),
    ("audited", "Audited"),
    ("built", "Built"),
    ("deployed", "Deployed"),
    ("sent", "Sent"),
    ("replied", "Replied"),
    ("won", "Won"),
    ("active_clients", "Active clients"),
)


def _now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True)
class Stage:
    key: str
    label: str
    count: int
    source: str
    available: bool
    delta: int = 0
    conversion_pct: float | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "key": self.key,
            "label": self.label,
            "count": self.count,
            "source": self.source,
            "available": self.available,
            "delta": self.delta,
            "conversion_pct": self.conversion_pct,
        }


@dataclass(frozen=True)
class FunnelReport:
    updated_at: str
    stages: list[Stage]
    verdicts: dict[str, int]
    target_verdicts: int
    outcomes: dict[str, int]
    sent_by_channel: dict[str, int]
    sent_by_variant: dict[str, int]
    active_clients: int
    mrr_cents: int
    zero_data: list[str]
    by: str = ""
    breakdown: dict[str, dict[str, int]] = field(default_factory=dict)

    @property
    def stage_counts(self) -> dict[str, int]:
        return {stage.key: stage.count for stage in self.stages}

    def to_dict(self) -> dict[str, object]:
        return {
            "updated_at": self.updated_at,
            "by": self.by,
            "stage_counts": self.stage_counts,
            "stages": [stage.to_dict() for stage in self.stages],
            "verdicts": dict(self.verdicts),
            "target_verdicts": self.target_verdicts,
            "outcomes": dict(self.outcomes),
            "sent_breakdown": {
                "by_channel": dict(self.sent_by_channel),
                "by_variant": dict(self.sent_by_variant),
            },
            "mrr": {
                "active_clients": self.active_clients,
                "mrr_cents": self.mrr_cents,
                "mrr_usd": round(self.mrr_cents / 100, 2),
            },
            "breakdown": {dim: dict(rows) for dim, rows in self.breakdown.items()},
            "zero_data": list(self.zero_data),
        }


# --------------------------------------------------------------- measurements
def _count_collected(records: list[dict[str, object]]) -> int:
    return len(records)


def read_verdicts(audited_root: Path) -> dict[str, str]:
    """``{place_id: web_verify_verdict}`` deduped across every audited CSV.

    Later files win on conflict (the audit is re-run and refined over time).
    CSVs without both a ``place_id`` and ``web_verify_verdict`` column are
    skipped — they carry no verdict to count.
    """
    verdicts: dict[str, str] = {}
    if not audited_root.is_dir():
        return verdicts
    for path in sorted(audited_root.glob("*.csv")):
        try:
            with path.open(newline="") as handle:
                reader = csv.DictReader(handle)
                fields = set(reader.fieldnames or [])
                if "place_id" not in fields or "web_verify_verdict" not in fields:
                    continue
                for row in reader:
                    place_id = (row.get("place_id") or "").strip()
                    verdict = (row.get("web_verify_verdict") or "").strip().lower()
                    if place_id and verdict:
                        verdicts[place_id] = verdict
        except (OSError, csv.Error):
            continue
    return verdicts


def _count_built(sites_root: Path) -> int:
    if not sites_root.is_dir():
        return 0
    return sum(1 for path in sites_root.glob("*/dist-v2/index.html") if path.is_file())


def _count_deployed(records: list[dict[str, object]]) -> int:
    return sum(1 for rec in records if str(rec.get("mockup_url", "")).strip())


def _lane_summary(lane_root: Path) -> dict[str, int]:
    path = lane_root / "client-status.json"
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text())
    except (OSError, ValueError):
        return {}
    summary = payload.get("summary", {}) if isinstance(payload, dict) else {}
    return {str(k): int(v) for k, v in summary.items()} if isinstance(summary, dict) else {}


def _active_ledgers(billing_root: Path) -> list[BillingLedger]:
    if not billing_root.is_dir():
        return []
    ledgers: list[BillingLedger] = []
    for path in sorted(billing_root.glob("*.json")):
        try:
            ledger = BillingLedger.from_dict(json.loads(path.read_text(encoding="utf-8")))
        except (OSError, ValueError):
            continue
        if ledger.billing_status == BillingStatus.ACTIVE.value:
            ledgers.append(ledger)
    return ledgers


def _ledger_monthly_cents(ledger: BillingLedger, catalog: ServiceCatalog) -> int:
    """Monthly recurring cents for an active client, priced at the catalog.

    Prefer the named bundle (renewals keep the package price); fall back to the
    purchased ``service_ids``. An unknown bundle/service contributes 0 rather
    than crashing the whole report.
    """
    try:
        if ledger.bundle and ledger.bundle in catalog.bundles:
            return catalog.quote_bundle(ledger.bundle).monthly_cents
        if ledger.service_ids:
            return catalog.quote_services(list(ledger.service_ids)).monthly_cents
    except CatalogError:
        return 0
    return 0


# ---------------------------------------------------------------- compute
def compute_funnel(
    *,
    repo_root: Path | None = None,
    by: str = "",
    store: OutreachStore | None = None,
    catalog: ServiceCatalog | None = None,
    previous: dict[str, object] | None = None,
) -> FunnelReport:
    """Measure every funnel stage from its primary source.

    ``by`` ("vertical" | "city") adds a sent/replied breakdown along that
    dimension. ``previous`` is a prior ``to_dict()`` payload used only to
    compute per-stage deltas; pass ``None`` for a first run.
    """
    paths = load_runtime_paths(repo_root)
    prospects_root = paths.state_root / "prospects"
    records_root = default_records_root(repo_root)
    lane_root = default_outreach_lane_root(repo_root)
    audited_root = prospects_root / "audited"
    sites_root = prospects_root / "sites"
    billing_root = default_billing_root(repo_root)

    store = store or OutreachStore()
    catalog = catalog or default_catalog()

    records = load_raw_records(records_root)
    verdicts = read_verdicts(audited_root)
    verdict_counts: dict[str, int] = {}
    for verdict in verdicts.values():
        verdict_counts[verdict] = verdict_counts.get(verdict, 0) + 1
    target_verdicts = sum(n for v, n in verdict_counts.items() if v in TARGET_VERDICTS)

    touch_summary = store.touch_summary()
    sent_place_ids = set(touch_summary.keys())
    sent_by_channel: dict[str, int] = {}
    for channels in touch_summary.values():
        for channel in channels:
            sent_by_channel[channel] = sent_by_channel.get(channel, 0) + 1
    sent_by_variant = store.variant_counts()

    lane = _lane_summary(lane_root)
    active_ledgers = _active_ledgers(billing_root)
    mrr_cents = sum(_ledger_monthly_cents(led, catalog) for led in active_ledgers)

    raw_counts = {
        "collected": _count_collected(records),
        "audited": len(verdicts),
        "built": _count_built(sites_root),
        "deployed": _count_deployed(records),
        "sent": len(sent_place_ids),
        "replied": lane.get("replied", 0),
        "won": lane.get("won", 0),
        "active_clients": len(active_ledgers),
    }
    sources = {
        "collected": "state/prospects/records/*.json",
        "audited": "state/prospects/audited/*.csv (web_verify_verdict)",
        "built": "state/prospects/sites/*/dist-v2/index.html",
        "deployed": "records with mockup_url",
        "sent": "outreach_touches (distinct place_id)",
        "replied": "outreach-lane client-status.json",
        "won": "outreach-lane client-status.json",
        "active_clients": "state/agency/billing/*.json (ACTIVE)",
    }
    # A stage is "unavailable" (not merely empty) when its source is missing —
    # so a fresh checkout reports honestly rather than implying a measured zero.
    available = {
        "collected": records_root.is_dir(),
        "audited": audited_root.is_dir(),
        "built": sites_root.is_dir(),
        "deployed": records_root.is_dir(),
        "sent": True,
        "replied": (lane_root / "client-status.json").exists(),
        "won": (lane_root / "client-status.json").exists(),
        "active_clients": billing_root.is_dir(),
    }

    prev_counts = _previous_stage_counts(previous)
    stages: list[Stage] = []
    prev_count: int | None = None
    for key, label in STAGE_ORDER:
        count = raw_counts[key]
        conversion = (
            round(count / prev_count * 100, 1)
            if prev_count not in (None, 0)
            else None
        )
        delta = count - prev_counts[key] if key in prev_counts else 0
        stages.append(
            Stage(
                key=key,
                label=label,
                count=count,
                source=sources[key],
                available=available[key],
                delta=delta,
                conversion_pct=conversion,
            )
        )
        prev_count = count

    zero_data = [
        f"{label} ({sources[key]})"
        for key, label in STAGE_ORDER
        if not available[key] or raw_counts[key] == 0
    ]

    breakdown: dict[str, dict[str, int]] = {}
    if by in ("vertical", "city"):
        breakdown = _breakdown(by, records, sent_place_ids, lane_root)

    return FunnelReport(
        updated_at=_now_iso(),
        stages=stages,
        verdicts=dict(sorted(verdict_counts.items())),
        target_verdicts=target_verdicts,
        outcomes={
            "replied": lane.get("replied", 0),
            "won": lane.get("won", 0),
            "lost": lane.get("lost", 0),
        },
        sent_by_channel=dict(sorted(sent_by_channel.items())),
        sent_by_variant=dict(sorted(sent_by_variant.items())),
        active_clients=len(active_ledgers),
        mrr_cents=mrr_cents,
        zero_data=zero_data,
        by=by if by in ("vertical", "city") else "",
        breakdown=breakdown,
    )


def _previous_stage_counts(previous: dict[str, object] | None) -> dict[str, int]:
    if not isinstance(previous, dict):
        return {}
    counts = previous.get("stage_counts")
    if isinstance(counts, dict):
        return {str(k): int(v) for k, v in counts.items()}
    return {}


def _breakdown(
    by: str,
    records: list[dict[str, object]],
    sent_place_ids: set[str],
    lane_root: Path,
) -> dict[str, dict[str, int]]:
    field_name = "genre_id" if by == "vertical" else "city_id"
    dim_by_place = {
        str(rec.get("place_id", "")): str(rec.get(field_name, "") or "(unknown)")
        for rec in records
        if rec.get("place_id")
    }
    sent: dict[str, int] = {}
    for place_id in sent_place_ids:
        key = dim_by_place.get(place_id, "(unknown)")
        sent[key] = sent.get(key, 0) + 1

    replied: dict[str, int] = {}
    rows = _lane_rows(lane_root)
    lane_field = "genre_id" if by == "vertical" else "city"
    for row in rows:
        if str(row.get("status", "")) != "replied":
            continue
        key = str(row.get(lane_field, "") or "(unknown)")
        replied[key] = replied.get(key, 0) + 1

    return {
        "sent": dict(sorted(sent.items(), key=lambda kv: (-kv[1], kv[0]))),
        "replied": dict(sorted(replied.items(), key=lambda kv: (-kv[1], kv[0]))),
    }


def _lane_rows(lane_root: Path) -> list[dict[str, object]]:
    path = lane_root / "client-status.json"
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text())
    except (OSError, ValueError):
        return []
    rows = payload.get("rows", []) if isinstance(payload, dict) else []
    return [row for row in rows if isinstance(row, dict)]


# ----------------------------------------------------------------- persist
def default_funnel_report_root(repo_root: Path | None = None) -> Path:
    return load_runtime_paths(repo_root).state_root / "prospects"


def load_funnel_report_payload(repo_root: Path | None = None) -> dict[str, object] | None:
    """The last committed ``funnel-report.json``, or ``None`` if never run.

    The dashboard reads this snapshot rather than recomputing live — fast, and
    honestly timestamped via ``updated_at``.
    """
    path = default_funnel_report_root(repo_root) / "funnel-report.json"
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text())
    except (OSError, ValueError):
        return None
    return payload if isinstance(payload, dict) else None


def write_funnel_report(report: FunnelReport, *, report_root: Path) -> tuple[Path, Path]:
    report_root.mkdir(parents=True, exist_ok=True)
    json_path = report_root / "funnel-report.json"
    md_path = report_root / "funnel-report.md"
    json_path.write_text(json.dumps(report.to_dict(), indent=2, sort_keys=True) + "\n")
    md_path.write_text(render_funnel_markdown(report))
    return json_path, md_path


class FunnelCooldownError(RuntimeError):
    """A dashboard refresh was requested inside the cooldown window."""

    def __init__(self, remaining_seconds: float) -> None:
        self.remaining_seconds = max(0, int(round(remaining_seconds)))
        super().__init__(
            f"funnel report is on cooldown; retry in {self.remaining_seconds}s"
        )


def cooldown_remaining_seconds(
    payload: dict[str, object] | None,
    *,
    cooldown_seconds: int = FUNNEL_REFRESH_COOLDOWN_SECONDS,
    now: datetime | None = None,
) -> int:
    """Seconds left before another refresh is allowed (0 = allowed now).

    Anchored to ``payload['updated_at']``; an absent/unparseable timestamp means
    no prior run, so a refresh is allowed immediately.
    """
    if not isinstance(payload, dict):
        return 0
    stamped = _parse_iso(str(payload.get("updated_at", "")))
    if stamped is None:
        return 0
    now = now or datetime.now(UTC)
    elapsed = (now - stamped).total_seconds()
    return max(0, int(round(cooldown_seconds - elapsed)))


def _parse_iso(value: str) -> datetime | None:
    text = (value or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def refresh_funnel_report(
    *,
    repo_root: Path | None = None,
    by: str = "",
    cooldown_seconds: int = FUNNEL_REFRESH_COOLDOWN_SECONDS,
) -> dict[str, object]:
    """Recompute and persist the report, honoring the refresh cooldown.

    Raises :class:`FunnelCooldownError` if the previous report is younger than
    ``cooldown_seconds``. This is the dashboard's path; the scheduled job calls
    :func:`compute_funnel` directly and is not rate-limited.
    """
    previous = load_funnel_report_payload(repo_root)
    remaining = cooldown_remaining_seconds(previous, cooldown_seconds=cooldown_seconds)
    if remaining > 0:
        raise FunnelCooldownError(remaining)
    report = compute_funnel(repo_root=repo_root, by=by, previous=previous)
    write_funnel_report(report, report_root=default_funnel_report_root(repo_root))
    return report.to_dict()


def _fmt_delta(delta: int) -> str:
    if delta > 0:
        return f"+{delta}"
    if delta < 0:
        return str(delta)
    return "—"


def _fmt_pct(pct: float | None) -> str:
    return "—" if pct is None else f"{pct:g}%"


def render_funnel_markdown(report: FunnelReport) -> str:
    lines = [
        "# Funnel Report",
        "",
        f"_Updated: {report.updated_at}_",
        "",
        "Stage counts measured from primary sources (records, audited CSVs, "
        "built sites, deploy URLs, the outreach touch store, the lane ledger, "
        "and billing). Conversion is each stage as a percent of the one before "
        "it; delta is the change since the previous run.",
        "",
        "## Pipeline",
        "",
        "| Stage | Count | Δ vs last | Conversion | Source |",
        "|---|---|---|---|---|",
    ]
    for stage in report.stages:
        count_cell = str(stage.count) if stage.available else f"{stage.count} (no source)"
        lines.append(
            f"| {stage.label} | {count_cell} | {_fmt_delta(stage.delta)} "
            f"| {_fmt_pct(stage.conversion_pct)} | {stage.source} |"
        )

    lines += [
        "",
        "## Outcomes",
        "",
        f"- Replied: {report.outcomes['replied']}",
        f"- Won: {report.outcomes['won']}",
        f"- Lost: {report.outcomes['lost']}",
        f"- Active clients: {report.active_clients}",
        f"- MRR (catalog prices): ${report.mrr_cents / 100:,.2f}",
        "",
        "## Audited verdicts",
        "",
        f"_{report.target_verdicts} of {sum(report.verdicts.values())} audited "
        "are build targets (no owned site)._",
        "",
        "| Verdict | Count | Target |",
        "|---|---|---|",
    ]
    for verdict, count in report.verdicts.items():
        target = "✓" if verdict in TARGET_VERDICTS else ""
        lines.append(f"| {verdict} | {count} | {target} |")

    lines += ["", "## Sent breakdown", ""]
    if report.sent_by_channel or report.sent_by_variant:
        lines.append("By channel (distinct prospects):")
        lines.append("")
        for channel, count in report.sent_by_channel.items():
            lines.append(f"- {channel}: {count}")
        lines.append("")
        lines.append("By variant (touches):")
        lines.append("")
        for variant, count in report.sent_by_variant.items():
            lines.append(f"- {variant}: {count}")
    else:
        lines.append("_No sends recorded yet._")

    if report.by:
        lines += ["", f"## Breakdown by {report.by}", ""]
        for dim, rows in report.breakdown.items():
            lines.append(f"{dim.capitalize()}:")
            lines.append("")
            if rows:
                for key, count in rows.items():
                    lines.append(f"- {key}: {count}")
            else:
                lines.append("- (none)")
            lines.append("")

    lines += ["", "## Stages with zero data", ""]
    if report.zero_data:
        lines.extend(f"- {item}" for item in report.zero_data)
    else:
        lines.append("_None — every stage has measured data._")

    return "\n".join(lines).rstrip() + "\n"


__all__ = [
    "FunnelReport",
    "Stage",
    "STAGE_ORDER",
    "TARGET_VERDICTS",
    "FUNNEL_REFRESH_COOLDOWN_SECONDS",
    "FunnelCooldownError",
    "compute_funnel",
    "read_verdicts",
    "write_funnel_report",
    "load_funnel_report_payload",
    "default_funnel_report_root",
    "render_funnel_markdown",
    "refresh_funnel_report",
    "cooldown_remaining_seconds",
]
