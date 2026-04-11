"""Phase 4.3 — observability rollup.

Aggregates log tails + event store counts into a single summary the
morning / evening / weekly scheduled sessions attach to their briefings.
Every string produced by this module is routed through
:mod:`packages.tools.observability.redaction` before it leaves the
function boundary, so credential fragments never reach a briefing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from packages.config.settings import load_runtime_paths
from packages.tools.observability.redaction import redact


LANE_LOG_DIRS = {
    "engineering": "engineering",
    "ios": "ios",
    "appstore": "appstore",
    "gtm": "gtm",
    "runtime-supervisor": "runtime-supervisor",
}


@dataclass(frozen=True)
class LaneRollup:
    lane: str
    log_lines_scanned: int
    top_failure_codes: tuple[tuple[str, int], ...]  # (code, count)
    tail_excerpt: tuple[str, ...]
    preflight_status: str  # "unknown" | "green" | "blocked"
    redaction_hits: tuple[str, ...]


@dataclass(frozen=True)
class Rollup:
    generated_at: str
    lanes: tuple[LaneRollup, ...]
    dispatched_by_lane: dict[str, int]
    completed_by_lane: dict[str, int]
    failed_by_lane: dict[str, int]
    redaction_hits: tuple[str, ...]

    def to_markdown(self) -> str:
        lines: list[str] = ["## Observability rollup", ""]
        lines.append(f"_generated_at_: {self.generated_at}")
        lines.append("")
        lines.append("| Lane | dispatched | completed | failed | preflight |")
        lines.append("|---|---:|---:|---:|---|")
        for lane in self.lanes:
            lines.append(
                f"| {lane.lane} "
                f"| {self.dispatched_by_lane.get(lane.lane, 0)} "
                f"| {self.completed_by_lane.get(lane.lane, 0)} "
                f"| {self.failed_by_lane.get(lane.lane, 0)} "
                f"| {lane.preflight_status} |"
            )
        lines.append("")
        for lane in self.lanes:
            if not lane.top_failure_codes:
                continue
            lines.append(f"### Top failure codes — {lane.lane}")
            for code, count in lane.top_failure_codes:
                lines.append(f"- `{code}` × {count}")
            lines.append("")
            if lane.tail_excerpt:
                lines.append(f"Tail (redacted):")
                lines.append("```")
                lines.extend(lane.tail_excerpt)
                lines.append("```")
                lines.append("")
        if self.redaction_hits:
            lines.append(
                f"_{len(self.redaction_hits)} credential fragment(s) redacted._"
            )
        return "\n".join(lines)


def _tail_lines(path: Path, limit: int) -> list[str]:
    if not path.exists():
        return []
    try:
        raw = path.read_text(errors="replace").splitlines()
    except OSError:
        return []
    return raw[-limit:]


def _extract_failure_codes(lines: Iterable[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for line in lines:
        marker = "failure_code="
        idx = line.find(marker)
        if idx < 0:
            continue
        tail = line[idx + len(marker):]
        # Grab the token up to first whitespace, comma, or closing brace.
        stop = len(tail)
        for ch in (" ", ",", "}", "\"", "'", "\n", "]"):
            pos = tail.find(ch)
            if 0 <= pos < stop:
                stop = pos
        code = tail[:stop].strip()
        if code:
            counts[code] = counts.get(code, 0) + 1
    return counts


def _rollup_lane(
    lane: str,
    logs_root: Path,
    *,
    tail_limit: int = 20,
) -> LaneRollup:
    lane_dir = logs_root / LANE_LOG_DIRS.get(lane, lane)
    lines: list[str] = []
    if lane_dir.exists():
        for log_file in sorted(lane_dir.glob("*.log")):
            lines.extend(_tail_lines(log_file, 200))
    codes = _extract_failure_codes(lines)
    top = tuple(sorted(codes.items(), key=lambda kv: (-kv[1], kv[0]))[:5])
    tail_text = "\n".join(lines[-tail_limit:])
    redaction = redact(tail_text)
    preflight = _preflight_status(logs_root, lane)
    return LaneRollup(
        lane=lane,
        log_lines_scanned=len(lines),
        top_failure_codes=top,
        tail_excerpt=tuple(redaction.text.splitlines()),
        preflight_status=preflight,
        redaction_hits=redaction.hits,
    )


def _preflight_status(logs_root: Path, lane: str) -> str:
    preflight_log = logs_root / "runtime-supervisor" / "preflight.log"
    if not preflight_log.exists():
        return "unknown"
    text = preflight_log.read_text(errors="replace").splitlines()[-200:]
    lane_tokens = {lane, f"lane={lane}", f"preflight_{lane}"}
    for line in reversed(text):
        if not any(tok in line for tok in lane_tokens):
            continue
        if "status=green" in line or "ok" in line.lower():
            return "green"
        if "blocked" in line.lower() or "fail" in line.lower():
            return "blocked"
    return "unknown"


def _count_events_by_lane(
    events: Iterable[object],
    *,
    event_type: str,
) -> dict[str, int]:
    out: dict[str, int] = {}
    for event in events:
        if getattr(event, "event_type", None) != event_type:
            continue
        payload = getattr(event, "payload", {}) or {}
        lane = str(payload.get("lane") or payload.get("worker_lane") or "")
        if not lane:
            continue
        out[lane] = out.get(lane, 0) + 1
    return out


def build_rollup(
    *,
    events: Iterable[object] | None = None,
    logs_root: Path | None = None,
    now: str | None = None,
) -> Rollup:
    """Construct a :class:`Rollup` ready to attach to a briefing.

    ``events`` defaults to an empty list so tests can call this without
    touching the event store; the scheduled sessions pass
    ``ControlPlaneService().list_events()``.
    """
    from datetime import datetime, timezone

    paths = load_runtime_paths()
    logs = logs_root or paths.logs_root
    events = list(events or [])
    lanes = tuple(_rollup_lane(lane, logs) for lane in LANE_LOG_DIRS)
    hits: list[str] = []
    for lane in lanes:
        hits.extend(lane.redaction_hits)
    return Rollup(
        generated_at=now or datetime.now(timezone.utc).isoformat(),
        lanes=lanes,
        dispatched_by_lane=_count_events_by_lane(events, event_type="task_created"),
        completed_by_lane=_count_events_by_lane(events, event_type="task_completed"),
        failed_by_lane=_count_events_by_lane(events, event_type="task_failed"),
        redaction_hits=tuple(hits),
    )
