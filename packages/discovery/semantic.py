"""Semantic dedup — fold near-duplicate wedges together by meaning, not wording.

The inbox's default dedup is exact (normalized title). That misses "auto-resize
photos for each store" vs "tool to batch-resize images per marketplace" — same
pain, different words. This adds an *optional* semantic pass behind an injectable
``EmbeddingProvider`` (cosine over vectors), so the embedding model is a
dependency you supply, never one baked in. With no provider, the inbox keeps its
cheap exact dedup; this is strictly an opt-in upgrade.
"""

from __future__ import annotations

import math
from typing import Callable, Sequence

from packages.discovery.connectors.base import RawSignal
from packages.discovery.inbox import OpportunityInbox
from packages.schemas.opportunity import EvidenceLink, OpportunityRecord

# Returns an embedding vector for a piece of text. You supply this (a hosted
# embedding API, a local model, etc.); the dedup logic is provider-agnostic.
EmbeddingProvider = Callable[[str], Sequence[float]]


def cosine(a: Sequence[float], b: Sequence[float]) -> float:
    if len(a) != len(b):
        raise ValueError("vectors must be the same length")
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


class SemanticDeduper:
    def __init__(self, provider: EmbeddingProvider, *, threshold: float = 0.85) -> None:
        self._provider = provider
        self._threshold = threshold

    def find_duplicate(
        self, text: str, candidates: list[OpportunityRecord]
    ) -> OpportunityRecord | None:
        """Return the most similar candidate above the threshold, or None."""
        if not candidates:
            return None
        query = self._provider(text)
        best: OpportunityRecord | None = None
        best_score = self._threshold
        for candidate in candidates:
            score = cosine(query, self._provider(candidate.title))
            if score >= best_score:
                best = candidate
                best_score = score
        return best


def ingest_with_semantic_dedup(
    inbox: OpportunityInbox,
    connector_id: str,
    query: str,
    signals: list[RawSignal],
    *,
    provider: EmbeddingProvider,
    threshold: float = 0.85,
    audience: str = "",
) -> list[OpportunityRecord]:
    """Like ``inbox.ingest_signals``, but folds a signal into an existing record
    when it is *semantically* the same pain, not just the same title."""
    deduper = SemanticDeduper(provider, threshold=threshold)
    stored: list[OpportunityRecord] = []
    for signal in signals:
        if not signal.text.strip() or not signal.url.strip():
            continue
        match = deduper.find_duplicate(signal.text, inbox.list())
        if match is not None:
            record = inbox.merge_evidence(
                match.id,
                [
                    EvidenceLink(
                        url=signal.url,
                        kind=signal.kind,
                        quote=signal.quote,
                        captured_at=signal.captured_at,
                    )
                ],
            )
        else:
            draft = inbox.draft_from_signal(signal, connector_id, query=query, audience=audience)
            _, record = inbox.add(draft)
        stored.append(record)
    return stored
