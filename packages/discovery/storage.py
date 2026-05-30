"""Opportunity storage seam — one source of truth, pluggable backend.

The inbox owns the *logic* (drafting, dedup, evidence merge); *where* records
live is a separate concern behind ``OpportunityRepository``. Two backends ship:

* ``JsonOpportunityRepository`` — JSON files under the runtime ``state/`` tree.
  Zero-config, single-box default.
* ``OpportunityStore`` (``packages/db/opportunity_store.py``) — the control-plane
  database. Queryable/rankable at scale and replayable; structurally satisfies
  this protocol already.

**Decision (E2):** the JSON repository is the default so discovery works with no
setup. When the control-plane DB is configured, point the inbox at the DB store
and it becomes the single source of truth — don't run both as canonical at once.
``migrate_opportunities`` does the one-time copy when you switch.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

from packages.db.json_store import JsonStore
from packages.schemas.opportunity import OpportunityRecord


@runtime_checkable
class OpportunityRepository(Protocol):
    """Persistence contract for opportunity records."""

    def save(self, record: OpportunityRecord) -> object:
        ...

    def get(self, opportunity_id: str) -> OpportunityRecord:
        ...

    def list(self) -> list[OpportunityRecord]:
        ...

    def exists(self, opportunity_id: str) -> bool:
        ...


class JsonOpportunityRepository:
    """JSON-file repository (the inbox's default, zero-config backend)."""

    def __init__(self, root: Path) -> None:
        self._store = JsonStore(root)

    @property
    def root(self) -> Path:
        return self._store.root

    def save(self, record: OpportunityRecord) -> OpportunityRecord:
        self._store.save(record.id, record.to_dict())
        return record

    def get(self, opportunity_id: str) -> OpportunityRecord:
        return OpportunityRecord.from_dict(self._store.load(opportunity_id))

    def exists(self, opportunity_id: str) -> bool:
        return self._store.path_for(opportunity_id).exists()

    def list(self) -> list[OpportunityRecord]:
        return [
            OpportunityRecord.from_dict(self._store.load(path.stem))
            for path in sorted(self._store.root.glob("*.json"))
        ]


def migrate_opportunities(
    source: OpportunityRepository, dest: OpportunityRepository
) -> int:
    """Copy every record from ``source`` into ``dest`` (idempotent upsert).
    Use this once when switching the inbox's backend. Returns the count copied.
    """
    records = source.list()
    for record in records:
        dest.save(record)
    return len(records)
