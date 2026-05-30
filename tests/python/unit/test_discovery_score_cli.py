"""Tests for the discovery_score operator CLI.

The CLI is thin glue over ``ScoringPass`` + a ``SignalProvider`` factory, so the
tests cover the two things glue can get wrong: provider selection (including the
llm error path) and end-to-end scoring of a seeded inbox against an isolated
state tree. No network — the heuristic provider is offline and deterministic.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

from packages.discovery.analyst import HeuristicSignalProvider, LLMSignalProvider
from packages.discovery.inbox import OpportunityInbox
from packages.schemas.opportunity import (
    EvidenceKind,
    EvidenceLink,
    OpportunityRecord,
    OpportunityStatus,
    SourceRef,
)


def _load_cli():
    module_path = Path(__file__).resolve().parents[3] / "scripts" / "discovery_score.py"
    spec = importlib.util.spec_from_file_location("discovery_score_cli", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _seed_inbox() -> None:
    """Add one well-evidenced inbox record the heuristic provider can score."""
    inbox = OpportunityInbox()
    record = OpportunityRecord(
        id="opp_seed_0001",
        title="Automate invoice reminders for freelancers",
        problem="Freelancers chase late invoices by hand every month",
        audience="freelancers",
        source=SourceRef(connector="hackernews", query="invoice reminders"),
        status=OpportunityStatus.INBOX,
        evidence=[
            EvidenceLink(
                url="https://news.ycombinator.com/item?id=1",
                kind=EvidenceKind.COMPLAINT,
                quote="I waste hours every month chasing unpaid invoices",
            ),
            EvidenceLink(
                url="https://news.ycombinator.com/item?id=2",
                kind=EvidenceKind.WILLINGNESS_TO_PAY,
                quote="I'd happily pay for something that just did this",
            ),
        ],
        created_at="2026-05-29T00:00:00+00:00",
        updated_at="2026-05-29T00:00:00+00:00",
    )
    inbox.add(record)


def test_build_provider_selects_concrete_providers() -> None:
    cli = _load_cli()
    assert isinstance(cli.build_provider("heuristic"), HeuristicSignalProvider)
    assert isinstance(cli.build_provider("llm"), LLMSignalProvider)


def test_build_provider_rejects_unknown() -> None:
    cli = _load_cli()
    with pytest.raises(ValueError):
        cli.build_provider("magic")


def test_run_scores_seeded_inbox(isolated_repo_root: Path, capsys) -> None:
    _seed_inbox()
    cli = _load_cli()
    code = cli.main(["--provider", "heuristic"])
    out = capsys.readouterr().out
    assert code == 0
    assert "Opportunity scoring pass" in out
    assert "Automate invoice reminders for freelancers" in out


def test_run_reports_empty_inbox(isolated_repo_root: Path, capsys) -> None:
    cli = _load_cli()
    code = cli.main(["--provider", "heuristic"])
    out = capsys.readouterr().out
    assert code == 0
    assert "Inbox is empty" in out


def test_llm_model_error_is_handled(isolated_repo_root: Path, capsys, monkeypatch) -> None:
    _seed_inbox()
    cli = _load_cli()
    from packages.tools.llm.client import ModelError

    class _BoomProvider:
        def __call__(self, record):  # noqa: ANN001
            raise ModelError("no model API key")

    monkeypatch.setattr(cli, "build_provider", lambda name: _BoomProvider())
    code = cli.main(["--provider", "llm"])
    err = capsys.readouterr().err
    assert code == 1
    assert "Model error" in err
