"""Opportunity inbox — a persistent, deduped store of discovered wedges.

Connectors produce ``RawSignal``s; the inbox turns them into
``OpportunityRecord`` drafts (status ``inbox``) and persists them as JSON under
the runtime ``state/`` tree, so nothing here pollutes source folders.

Dedup is deterministic: the record id is derived from the normalized title, so
the same pain surfaced on a later run merges its evidence into the existing
record instead of creating a duplicate. That is what makes "run discovery every
day" safe.
"""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from packages.config.settings import load_runtime_paths
from packages.discovery.connectors.base import RawSignal
from packages.discovery.storage import JsonOpportunityRepository, OpportunityRepository
from packages.schemas.opportunity import (
    EvidenceLink,
    OpportunityRecord,
    OpportunityStatus,
    SourceRef,
)

_WHITESPACE = re.compile(r"\s+")
_NON_WORD = re.compile(r"[^a-z0-9 ]+")


def normalize_title(title: str) -> str:
    lowered = _NON_WORD.sub(" ", title.lower())
    return _WHITESPACE.sub(" ", lowered).strip()


def opportunity_id_for(title: str) -> str:
    digest = hashlib.sha1(normalize_title(title).encode("utf-8")).hexdigest()
    return f"opp_{digest[:12]}"


def default_inbox_root(repo_root: Path | None = None) -> Path:
    return load_runtime_paths(repo_root).platform_state_root / "opportunities"


class OpportunityInbox:
    def __init__(
        self,
        root: Path | None = None,
        *,
        now: Callable[[], datetime] | None = None,
        repository: OpportunityRepository | None = None,
    ) -> None:
        # Backward-compatible: ``root`` builds the default JSON repository; pass
        # ``repository`` (e.g. the DB-backed OpportunityStore) to change backend.
        self._repo: OpportunityRepository = repository or JsonOpportunityRepository(
            root or default_inbox_root()
        )
        self._now = now or (lambda: datetime.now(timezone.utc))

    def _timestamp(self) -> str:
        return self._now().isoformat()

    def draft_from_signal(
        self,
        signal: RawSignal,
        connector_id: str,
        *,
        query: str = "",
        audience: str = "",
    ) -> OpportunityRecord:
        timestamp = self._timestamp()
        return OpportunityRecord(
            id=opportunity_id_for(signal.text),
            title=signal.text[:140],
            problem=signal.quote or signal.text,
            audience=audience,
            source=SourceRef(connector=connector_id, query=query),
            status=OpportunityStatus.INBOX,
            evidence=[
                EvidenceLink(
                    url=signal.url,
                    kind=signal.kind,
                    quote=signal.quote,
                    captured_at=signal.captured_at,
                )
            ],
            created_at=timestamp,
            updated_at=timestamp,
        )

    def add(self, record: OpportunityRecord) -> tuple[str, OpportunityRecord]:
        """Persist a record, merging evidence into an existing one with the same
        normalized title. Returns ``("created"|"merged", stored_record)``."""
        if not self._repo.exists(record.id):
            self._repo.save(record)
            return ("created", record)

        existing = self._repo.get(record.id)
        known_urls = {link.url for link in existing.evidence}
        new_links = [link for link in record.evidence if link.url not in known_urls]
        if not new_links:
            return ("merged", existing)

        merged_evidence = list(existing.evidence) + new_links
        updated = _replace_evidence(existing, merged_evidence, updated_at=self._timestamp())
        self._repo.save(updated)
        return ("merged", updated)

    def ingest_signals(
        self,
        connector_id: str,
        query: str,
        signals: list[RawSignal],
        *,
        audience: str = "",
    ) -> list[OpportunityRecord]:
        """Draft + persist a batch of signals, deduped. Returns stored records."""
        stored: list[OpportunityRecord] = []
        for signal in signals:
            if not signal.text.strip() or not signal.url.strip():
                continue
            draft = self.draft_from_signal(signal, connector_id, query=query, audience=audience)
            _, record = self.add(draft)
            stored.append(record)
        return stored

    def get(self, opportunity_id: str) -> OpportunityRecord:
        return self._repo.get(opportunity_id)

    def list(self) -> list[OpportunityRecord]:
        return self._repo.list()

    def save(self, record: OpportunityRecord) -> OpportunityRecord:
        """Persist an updated record verbatim (e.g. after scoring)."""
        self._repo.save(record)
        return record

    def merge_evidence(
        self, target_id: str, links: list[EvidenceLink]
    ) -> OpportunityRecord:
        """Append new evidence links (deduped by URL) onto an existing record.
        Used by semantic dedup to fold a near-duplicate into its match."""
        existing = self.get(target_id)
        known = {link.url for link in existing.evidence}
        new_links = [link for link in links if link.url and link.url not in known]
        if not new_links:
            return existing
        updated = _replace_evidence(
            existing, list(existing.evidence) + new_links, updated_at=self._timestamp()
        )
        self._repo.save(updated)
        return updated


def _replace_evidence(
    record: OpportunityRecord,
    evidence: list[EvidenceLink],
    *,
    updated_at: str,
) -> OpportunityRecord:
    payload = record.to_dict()
    payload["evidence"] = [link.to_dict() for link in evidence]
    payload["updated_at"] = updated_at
    return OpportunityRecord.from_dict(payload)
