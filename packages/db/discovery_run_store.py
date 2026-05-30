"""Control-plane store for discovery run reports — queryable run history (E3).

Run reports persisted via the file-based ``JsonStore`` (see
``packages/discovery/run.py``) give the operator CLI a "latest run" surface, but
they don't live alongside the opportunity/experiment records or support
history queries. This store gives runs the same home: core columns (status,
signals ingested, timestamps) stay first-class for filtering, and the full
report is kept verbatim in ``record_json`` so a round trip is lossless.

It structurally satisfies the ``DiscoveryRunRepository`` seam in
``packages.discovery.run`` (``save`` + ``latest``), so the CLI can persist to the
control plane instead of JSON files without other code changing. Mirrors the
OpportunityStore/ExperimentStore pattern, so it works on both the SQLite and
Postgres backends without change.
"""

from __future__ import annotations

from packages.db.contracts import DISCOVERY_RUNS_TABLE
from packages.db.control_plane_db import ControlPlaneDatabase
from packages.discovery.run import DiscoveryRunReport


class DiscoveryRunRecordStore:
    def __init__(self) -> None:
        self.db = ControlPlaneDatabase()

    def save(self, report: DiscoveryRunReport) -> DiscoveryRunReport:
        """Upsert a run report by ``run_id``. The same id is written repeatedly
        as a run progresses (the ``on_progress`` snapshots share an id), so an
        upsert keeps exactly one row per run, ending on the terminal snapshot."""
        query = f"""
            INSERT INTO {DISCOVERY_RUNS_TABLE} (
                id, status, signals_ingested, opportunities_touched,
                record_json, started_at, finished_at
            ) VALUES (
                {self.db.placeholder("id")},
                {self.db.placeholder("status")},
                {self.db.placeholder("signals_ingested")},
                {self.db.placeholder("opportunities_touched")},
                {self.db.placeholder("record_json")},
                {self.db.placeholder("started_at")},
                {self.db.placeholder("finished_at")}
            )
            ON CONFLICT(id) DO UPDATE SET
                status = excluded.status,
                signals_ingested = excluded.signals_ingested,
                opportunities_touched = excluded.opportunities_touched,
                record_json = excluded.record_json,
                started_at = excluded.started_at,
                finished_at = excluded.finished_at
        """
        self.db.execute(
            query,
            {
                "id": report.run_id,
                "status": report.status,
                "signals_ingested": report.signals_ingested,
                "opportunities_touched": report.opportunities_touched,
                "record_json": self.db.dump_json(report.to_dict()),
                "started_at": report.started_at,
                # A still-running snapshot has no finish time yet — store NULL,
                # not "", so "finished" runs are cleanly filterable.
                "finished_at": report.finished_at or None,
            },
        )
        return report

    def get(self, run_id: str) -> DiscoveryRunReport:
        placeholder = self.db.placeholder("id")
        query = f"SELECT record_json FROM {DISCOVERY_RUNS_TABLE} WHERE id = {placeholder}"
        payload = self.db.fetch_one(query, {"id": run_id})
        if payload is None:
            raise FileNotFoundError(run_id)
        return DiscoveryRunReport.from_dict(self.db.load_json(str(payload["record_json"])))

    def latest(self) -> DiscoveryRunReport | None:
        """The most recently started run, or None if none recorded yet.
        ``started_at`` is an ISO-8601 timestamp, so lexical ordering is
        chronological; ``id`` is the tiebreaker for identical timestamps."""
        query = f"""
            SELECT record_json
            FROM {DISCOVERY_RUNS_TABLE}
            ORDER BY started_at DESC, id DESC
            LIMIT 1
        """
        payload = self.db.fetch_one(query, {})
        if payload is None:
            return None
        return DiscoveryRunReport.from_dict(self.db.load_json(str(payload["record_json"])))

    def list(self) -> list[DiscoveryRunReport]:
        """Every recorded run, newest first — the queryable history E3 adds."""
        query = f"""
            SELECT record_json
            FROM {DISCOVERY_RUNS_TABLE}
            ORDER BY started_at DESC, id DESC
        """
        rows = self.db.fetch_all(query, {})
        return [
            DiscoveryRunReport.from_dict(self.db.load_json(str(row["record_json"]))) for row in rows
        ]
