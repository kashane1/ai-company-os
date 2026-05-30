"""Tests for the opportunity storage seam (E2).

The inbox must behave identically over the JSON repository (default) and the
DB-backed OpportunityStore, and migration must move records between them.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from packages.config.settings import TEST_REPO_ROOT_ENV_VAR, ensure_runtime_directories
from packages.db.opportunity_store import OpportunityStore
from packages.discovery.connectors.base import RawSignal
from packages.discovery.inbox import OpportunityInbox
from packages.discovery.storage import (
    JsonOpportunityRepository,
    OpportunityRepository,
    migrate_opportunities,
)
from packages.schemas.opportunity import EvidenceKind

FIXED = datetime(2026, 5, 29, tzinfo=timezone.utc)


def _signal(url: str, text: str = "Is there a tool that automates X") -> RawSignal:
    return RawSignal(text=text, url=url, kind=EvidenceKind.REQUEST, quote=text)


def test_db_store_satisfies_repository_protocol(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(TEST_REPO_ROOT_ENV_VAR, str(tmp_path))
    ensure_runtime_directories()
    # runtime_checkable Protocol: the DB store is structurally a repository.
    assert isinstance(OpportunityStore(), OpportunityRepository)
    assert isinstance(JsonOpportunityRepository(tmp_path / "j"), OpportunityRepository)


def test_inbox_over_json_repository_default(tmp_path: Path) -> None:
    inbox = OpportunityInbox(root=tmp_path / "opps", now=lambda: FIXED)
    inbox.ingest_signals("hackernews", "q", [_signal("https://news.ycombinator.com/item?id=1")])
    assert len(inbox.list()) == 1


def test_inbox_over_db_store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(TEST_REPO_ROOT_ENV_VAR, str(tmp_path))
    ensure_runtime_directories()
    inbox = OpportunityInbox(repository=OpportunityStore(), now=lambda: FIXED)

    text = "Is there a tool that automates invoicing"
    inbox.ingest_signals(
        "hackernews", "q", [_signal("https://news.ycombinator.com/item?id=1", text)]
    )
    # Same pain, new evidence -> dedup/merge works through the DB backend too.
    inbox.ingest_signals("github", "q", [_signal("https://github.com/x/y/issues/2", text)])

    records = inbox.list()
    assert len(records) == 1
    assert len(records[0].evidence) == 2


def test_migrate_json_to_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Seed a JSON repository via the inbox.
    json_inbox = OpportunityInbox(root=tmp_path / "json", now=lambda: FIXED)
    json_inbox.ingest_signals(
        "hackernews", "q",
        [
            _signal("https://news.ycombinator.com/item?id=1", "Tool to automate invoicing"),
            _signal("https://news.ycombinator.com/item?id=2", "App to resize photos"),
        ],
    )
    source: OpportunityRepository = JsonOpportunityRepository(tmp_path / "json")

    monkeypatch.setenv(TEST_REPO_ROOT_ENV_VAR, str(tmp_path))
    ensure_runtime_directories()
    dest = OpportunityStore()

    copied = migrate_opportunities(source, dest)
    assert copied == 2
    assert len(dest.list()) == 2
    # Migrated inbox reads identically through the DB store.
    migrated_inbox = OpportunityInbox(repository=dest, now=lambda: FIXED)
    assert len(migrated_inbox.list()) == 2
