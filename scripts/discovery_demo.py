#!/usr/bin/env python3
"""Discovery demo — run the front of the loop end to end, offline by default.

What it shows:

1. DISCOVER  — turn raw source signals into deduped opportunity inbox records
               (offline fixture by default; ``--live`` hits the real HN API).
2. SCORE     — run a worked-example opportunity through the 12-signal scorecard.
3. GATE      — apply the validate gate (thresholds + hard gates) and the
               build gate (no build without a passed experiment).

Run:
    python3 scripts/discovery_demo.py
    python3 scripts/discovery_demo.py --live --query "automate invoicing"

By default it writes the inbox to a throwaway temp dir so it never touches the
real state/ tree. Pass ``--root PATH`` to persist somewhere of your choosing.
"""

from __future__ import annotations

import argparse
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

# Make the demo runnable directly (`python3 scripts/discovery_demo.py`) without
# needing PYTHONPATH set — insert the repo root (parent of scripts/).
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from packages.discovery.connectors.base import FetchOptions, RawSignal  # noqa: E402
from packages.discovery.connectors.registry import build_connectors  # noqa: E402
from packages.discovery.inbox import OpportunityInbox  # noqa: E402
from packages.discovery.scoring import load_scoring_config  # noqa: E402
from packages.policies.approvals import PolicyViolation  # noqa: E402
from packages.policies.discovery_gates import (  # noqa: E402
    assert_ready_to_build,
    score_opportunity_record,
)
from packages.schemas.experiment import (  # noqa: E402
    ExperimentMetric,
    ExperimentRecord,
    ExperimentStatus,
    ExperimentType,
    SuccessCriteria,
)
from packages.schemas.opportunity import (  # noqa: E402
    EvidenceKind,
    EvidenceLink,
    OpportunityRecord,
    OpportunitySignals,
    SourceRef,
)

FIXTURE_SIGNALS = [
    RawSignal(
        text="Is there a tool that automates resizing product photos per marketplace?",
        url="https://news.ycombinator.com/item?id=1001",
        kind=EvidenceKind.REQUEST,
        quote="I hate doing this manually for Etsy, Amazon, and Shopify every time.",
        captured_at=datetime.now(timezone.utc).isoformat(),
    ),
    RawSignal(
        text="Anyone know an app to auto-resize images for multiple stores?",
        url="https://news.ycombinator.com/item?id=1002",
        kind=EvidenceKind.REQUEST,
        quote="Tired of exporting the same photo at five sizes by hand.",
        captured_at=datetime.now(timezone.utc).isoformat(),
    ),
]


def discover(inbox: OpportunityInbox, query: str, live: bool) -> None:
    print("\n=== 1. DISCOVER ===")
    if live:
        connectors = build_connectors()
        total = 0
        for source_id, connector in connectors.items():
            try:
                signals = connector.fetch(FetchOptions(query=query, limit=15))
            except Exception as exc:  # noqa: BLE001 - demo resilience
                print(f"  {source_id}: skipped ({exc})")
                continue
            stored = inbox.ingest_signals(source_id, query, signals)
            total += len(stored)
            print(f"  {source_id}: {len(stored)} signals ingested")
        if total == 0:
            print("  (no live results — falling back to the offline fixture)")
            inbox.ingest_signals("hackernews", query, FIXTURE_SIGNALS)
    else:
        inbox.ingest_signals("hackernews", query, FIXTURE_SIGNALS)

    records = inbox.list()
    print(f"\n  inbox now holds {len(records)} opportunity record(s):")
    for record in records:
        print(f"    [{record.status.value}] {record.title}  ({len(record.evidence)} evidence)")


def score_and_gate() -> None:
    config = load_scoring_config()

    print("\n=== 2. SCORE (worked example) ===")
    opportunity = OpportunityRecord(
        id="opp_etsy_resize",
        title="Etsy sellers manually resize product photos for each marketplace",
        problem="Sellers re-export the same photo at many sizes by hand for every store.",
        audience="Etsy sellers with >100 SKUs who also sell on Amazon/Shopify",
        source=SourceRef(connector="hackernews", query="resize product photos"),
        signals=OpportunitySignals(
            search_volume=5, buyer_intent=7, urgency=6, willingness_to_pay=7,
            competition_weakness=6, community_pain=8, repeated_workflow=9,
            distribution_path=7, expected_margin=8, build_feasibility=8,
            defensibility=3, risk=9,
        ),
        evidence=[
            EvidenceLink(url="https://news.ycombinator.com/item?id=1", kind=EvidenceKind.REQUEST),
            EvidenceLink(url="https://www.reddit.com/r/Etsy/1", kind=EvidenceKind.COMPLAINT),
            EvidenceLink(url="https://etsy-forum.example/2", kind=EvidenceKind.COMPLAINT),
            EvidenceLink(url="https://competitor-reviews.example/3", kind=EvidenceKind.REVIEW),
            EvidenceLink(
                url="https://competitor-reviews.example/4",
                kind=EvidenceKind.WILLINGNESS_TO_PAY,
            ),
        ],
    )
    decision, scored = score_opportunity_record(opportunity, config)
    print(f"  score={decision.score:.0f}/100  confidence={decision.confidence:.2f}  "
          f"advance={decision.advance}  -> status={scored.status.value}")

    print("\n=== 3. GATE ===")
    if decision.advance:
        print("  validate gate: PASS — eligible to run a validation experiment.")
    else:
        for reason in decision.reasons:
            print(f"  validate gate: BLOCK [{reason.code}] {reason.message}")

    # Build gate: no build without a passed experiment.
    planned = ExperimentRecord(
        id="exp_etsy_waitlist",
        opportunity_id=scored.id,
        type=ExperimentType.WAITLIST,
        hypothesis="Etsy sellers will join a waitlist to auto-resize photos.",
        success_criteria=SuccessCriteria(
            metric=ExperimentMetric.SIGNUPS, threshold=50, window="7 days"
        ),
        status=ExperimentStatus.RUNNING,
    )
    try:
        assert_ready_to_build(scored, planned)
        print("  build gate: PASS")
    except PolicyViolation as exc:
        print(f"  build gate: BLOCK [{exc.code}] {exc}")

    passed = ExperimentRecord.from_dict({**planned.to_dict(), "status": "passed"})
    assert_ready_to_build(scored, passed)
    print("  build gate (after experiment passes): PASS — cleared to scaffold an MVP.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Discovery loop demo")
    parser.add_argument("--query", default="automate invoicing", help="discovery search query")
    parser.add_argument(
        "--live", action="store_true", help="hit real source APIs instead of the fixture"
    )
    parser.add_argument("--root", default="", help="inbox root dir (default: a throwaway temp dir)")
    args = parser.parse_args()

    if args.root:
        root = Path(args.root)
    else:
        root = Path(tempfile.mkdtemp(prefix="discovery-demo-")) / "opportunities"
    inbox = OpportunityInbox(root=root)
    print(f"inbox root: {root}")

    discover(inbox, args.query, args.live)
    score_and_gate()
    print("\nDone. See docs/founder/discovery-guide.md for how to wire this into your workflow.")


if __name__ == "__main__":
    main()
