"""On-demand discovery runs — operator-triggered, stoppable, audited.

Discovery is something a human *starts*, not a cron job. A run sweeps the enabled
connectors across one or more queries into the inbox, checking a stop signal
between each unit of work so it can be halted at any time (Ctrl-C, or a `stop`
command from another terminal). Every run writes a ``DiscoveryRunReport`` so you
can see what a run did — which sources it hit, how many signals it ingested, and
whether it finished or was stopped early.

The core ``run_discovery`` is pure orchestration with an injectable
``should_stop`` hook, so it's fully testable without timers or signals. The
file-based stop signal + run persistence are the thin operator surface the CLI
(`scripts/discovery_run.py`) wires up, mirroring `./scripts/runtime start|stop`.
"""

from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from packages.config.settings import load_runtime_paths
from packages.db.json_store import JsonStore
from packages.discovery.connectors.base import Connector, FetchOptions
from packages.discovery.inbox import OpportunityInbox
from packages.policies.discovery_gates import assert_bulk_crawl_allowed

# Returns True when the run should halt after the current unit of work.
StopSignal = Callable[[], bool]

STOP_FILE_NAME = "STOP"
CURRENT_RUN_ID = "current"


class DiscoveryRunStatus:
    RUNNING = "running"
    COMPLETED = "completed"
    STOPPED = "stopped"


@dataclass(frozen=True)
class DiscoveryRunReport:
    run_id: str
    status: str
    queries: list[str] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)
    signals_ingested: int = 0
    opportunities_touched: int = 0
    sources_hit: dict[str, int] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    started_at: str = ""
    finished_at: str = ""

    @property
    def stopped_early(self) -> bool:
        return self.status == DiscoveryRunStatus.STOPPED

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "DiscoveryRunReport":
        return cls(
            run_id=str(payload["run_id"]),
            status=str(payload["status"]),
            queries=[str(q) for q in payload.get("queries", [])],
            sources=[str(s) for s in payload.get("sources", [])],
            signals_ingested=int(payload.get("signals_ingested", 0)),
            opportunities_touched=int(payload.get("opportunities_touched", 0)),
            sources_hit={str(k): int(v) for k, v in dict(payload.get("sources_hit", {})).items()},
            errors=[str(e) for e in payload.get("errors", [])],
            started_at=str(payload.get("started_at", "")),
            finished_at=str(payload.get("finished_at", "")),
        )


def run_discovery(
    *,
    inbox: OpportunityInbox,
    connectors: dict[str, Connector],
    queries: list[str],
    limit: int = 25,
    should_stop: StopSignal | None = None,
    now: Callable[[], datetime] | None = None,
    run_id: str | None = None,
    on_progress: Callable[["DiscoveryRunReport"], None] | None = None,
    bulk: bool = False,
    bulk_approved_by: str | None = None,
    authorize_bulk: Callable[[], None] | None = None,
) -> DiscoveryRunReport:
    """Sweep every (source, query) pair into the inbox, checking ``should_stop``
    before each unit so the run can be halted at any time.

    A ``bulk`` run (beyond normal per-domain limits) is a gated action (C1). The
    gate runs ONCE up front, before any fetch: pass ``authorize_bulk`` (e.g. a
    ``GateDecisionRecorder.record_bulk_crawl`` partial that records the decision)
    or just ``bulk_approved_by`` to use the bare policy check. If the gate
    blocks, this raises ``PolicyViolation`` and nothing is fetched. Only once the
    gate passes do connectors receive ``authorized=True`` and run in bulk."""
    clock = now or (lambda: datetime.now(timezone.utc))
    stop = should_stop or (lambda: False)
    rid = run_id or f"run_{uuid.uuid4().hex[:12]}"
    started = clock().isoformat()

    if bulk:
        # Enforce the bulk-crawl gate at the point of action — fail fast.
        if authorize_bulk is not None:
            authorize_bulk()
        else:
            assert_bulk_crawl_allowed(
                approved_by=bulk_approved_by, robots_checked=True, rate_limited=True
            )

    signals_ingested = 0
    touched: set[str] = set()
    sources_hit: dict[str, int] = {}
    errors: list[str] = []
    status = DiscoveryRunStatus.COMPLETED

    def snapshot(current_status: str, finished: str = "") -> DiscoveryRunReport:
        return DiscoveryRunReport(
            run_id=rid,
            status=current_status,
            queries=list(queries),
            sources=list(connectors),
            signals_ingested=signals_ingested,
            opportunities_touched=len(touched),
            sources_hit=dict(sources_hit),
            errors=list(errors),
            started_at=started,
            finished_at=finished,
        )

    units = [(sid, conn, query) for sid, conn in connectors.items() for query in queries]
    for source_id, connector, query in units:
        if stop():
            status = DiscoveryRunStatus.STOPPED
            break
        try:
            signals = connector.fetch(
                FetchOptions(query=query, limit=limit, bulk=bulk, authorized=bulk)
            )
        except Exception as exc:  # noqa: BLE001 - one bad source shouldn't kill the run
            errors.append(f"{source_id}: {exc}")
            continue
        stored = inbox.ingest_signals(source_id, query, signals)
        signals_ingested += len(stored)
        sources_hit[source_id] = sources_hit.get(source_id, 0) + len(stored)
        for record in stored:
            touched.add(record.id)
        if on_progress is not None:
            on_progress(snapshot(DiscoveryRunStatus.RUNNING))

    return snapshot(status, finished=clock().isoformat())


# ── File-based operator surface (used by the CLI) ──────────────────────────────


def default_runs_root(repo_root: Path | None = None) -> Path:
    return load_runtime_paths(repo_root).platform_state_root / "discovery_runs"


class DiscoveryRunStore:
    """Persists run reports and exposes the latest one for `status`."""

    def __init__(self, root: Path | None = None) -> None:
        self._store = JsonStore(root or default_runs_root())

    def save(self, report: DiscoveryRunReport) -> DiscoveryRunReport:
        self._store.save(report.run_id, report.to_dict())
        self._store.save(CURRENT_RUN_ID, report.to_dict())
        return report

    def latest(self) -> DiscoveryRunReport | None:
        path = self._store.path_for(CURRENT_RUN_ID)
        if not path.exists():
            return None
        return DiscoveryRunReport.from_dict(self._store.load(CURRENT_RUN_ID))


class FileStopSignal:
    """A stop signal backed by the presence of a STOP file, so a separate
    `discovery_run stop` process can halt a running sweep."""

    def __init__(self, root: Path | None = None) -> None:
        self._path = (root or default_runs_root()) / STOP_FILE_NAME

    def request(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text("stop\n")

    def clear(self) -> None:
        self._path.unlink(missing_ok=True)

    def requested(self) -> bool:
        return self._path.exists()

    def __call__(self) -> bool:
        return self.requested()
