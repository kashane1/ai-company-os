#!/usr/bin/env python3
"""On-demand discovery run — operator CLI (start / status / stop).

Discovery is human-triggered and stoppable, mirroring `./scripts/runtime`:

    python3 scripts/discovery_run.py start --query "automate invoicing" --query "etsy resize"
    python3 scripts/discovery_run.py status     # in another terminal
    python3 scripts/discovery_run.py stop        # halts a running sweep

`start` runs in the foreground and stops cleanly on Ctrl-C or when another
terminal runs `stop` (which drops a STOP file the run polls between sources).
Without a `SignalProvider` wired in, a run only *fills the inbox*; score it
afterwards with the scoring pass (see docs/founder/discovery-guide.md).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from packages.discovery.connectors.registry import build_connectors  # noqa: E402
from packages.discovery.inbox import OpportunityInbox  # noqa: E402
from packages.discovery.run import (  # noqa: E402
    DiscoveryRunRepository,
    DiscoveryRunStore,
    FileStopSignal,
    run_discovery,
)


def build_run_store(name: str) -> DiscoveryRunRepository:
    """Map a ``--store`` name to a run-report repository.

    ``db`` (default) persists to the control plane so runs are queryable
    alongside the opportunity/experiment records (E3); ``file`` keeps the
    zero-dependency JSON store. Both satisfy ``DiscoveryRunRepository``.
    """
    if name == "file":
        return DiscoveryRunStore()
    if name == "db":
        # Imported lazily so the file store stays usable without the db package.
        from packages.db.discovery_run_store import DiscoveryRunRecordStore

        return DiscoveryRunRecordStore()
    raise ValueError(f"unknown store {name!r} (choose from db, file)")


def _cmd_start(args: argparse.Namespace) -> int:
    stop = FileStopSignal()
    stop.clear()  # fresh run
    store = build_run_store(args.store)
    connectors = build_connectors()
    if not connectors:
        print("No enabled connectors. Enable a source in config/sources.yaml first.")
        return 1
    print(f"Starting discovery run over {list(connectors)} for queries={args.query} …")
    print("(Ctrl-C, or `discovery_run stop` from another terminal, to halt.)")
    try:
        report = run_discovery(
            inbox=OpportunityInbox(),
            connectors=connectors,
            queries=args.query,
            limit=args.limit,
            should_stop=stop,
            on_progress=store.save,
        )
    except KeyboardInterrupt:
        print("\nInterrupted — marking run stopped.")
        stop.request()
        return 130
    store.save(report)
    stop.clear()
    print(
        f"\nRun {report.run_id}: {report.status} — "
        f"{report.signals_ingested} signals ingested across {report.sources_hit}."
    )
    if report.errors:
        print("Errors:", "; ".join(report.errors))
    return 0


def _cmd_status(args: argparse.Namespace) -> int:
    report = build_run_store(args.store).latest()
    if report is None:
        print("No discovery runs recorded yet.")
        return 0
    print(
        f"Latest run {report.run_id}: {report.status}\n"
        f"  queries: {report.queries}\n"
        f"  sources hit: {report.sources_hit}\n"
        f"  signals ingested: {report.signals_ingested}\n"
        f"  started: {report.started_at}  finished: {report.finished_at or '(running)'}"
    )
    return 0


def _cmd_stop(_: argparse.Namespace) -> int:
    FileStopSignal().request()
    print("Stop requested. A running sweep will halt after its current source.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="On-demand discovery runs")
    sub = parser.add_subparsers(dest="command", required=True)

    def _add_store_arg(p: argparse.ArgumentParser) -> None:
        p.add_argument(
            "--store",
            choices=("db", "file"),
            default="db",
            help="where run reports persist: db (control plane, default) or file (JSON)",
        )

    start = sub.add_parser("start", help="run a discovery sweep in the foreground")
    start.add_argument(
        "--query", action="append", required=True, help="a search query (repeatable)"
    )
    start.add_argument("--limit", type=int, default=25, help="max signals per source per query")
    _add_store_arg(start)
    start.set_defaults(func=_cmd_start)

    status = sub.add_parser("status", help="show the latest run")
    _add_store_arg(status)
    status.set_defaults(func=_cmd_status)
    sub.add_parser("stop", help="request a running sweep to halt").set_defaults(func=_cmd_stop)

    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
