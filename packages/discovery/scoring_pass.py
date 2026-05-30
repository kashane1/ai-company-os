"""Scoring pass — the daily "rank the inbox" step.

Discovery fills the inbox with `inbox`-status records (problem + audience +
evidence, no signals yet). The scoring pass turns those into *ranked* records:
it fills the twelve signals, runs the scorecard, applies the validate gate, and
persists the result — then hands you a short ranked report for review.

Filling the signals is the one genuinely analytical step, so it sits behind a
``SignalProvider`` interface: in production it's an analyst agent (LLM); in
tests it's a deterministic stub. Everything else here is plain, testable
orchestration owned by the platform — connectors surface facts, the analyst
scores, and policy (`discovery_gates`) decides. The pass itself invents nothing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable

from packages.discovery.inbox import OpportunityInbox
from packages.discovery.scoring import ScoringConfig, load_scoring_config
from packages.policies.discovery_gates import (
    AdvancementDecision,
    score_opportunity_record,
)
from packages.schemas.opportunity import (
    OpportunityRecord,
    OpportunitySignals,
    OpportunityStatus,
)

# Given an opportunity (problem, audience, evidence), return the twelve signals
# 0-10, or None if there is not enough evidence to score it yet (send it back
# for more research rather than guessing).
SignalProvider = Callable[[OpportunityRecord], "OpportunitySignals | None"]


@dataclass(frozen=True)
class ScoredOpportunity:
    record: OpportunityRecord
    decision: AdvancementDecision

    @property
    def top_reason(self) -> str:
        return self.decision.reasons[0].message if self.decision.reasons else "clears the gate"


@dataclass(frozen=True)
class ScoringPassReport:
    scored: list[ScoredOpportunity] = field(default_factory=list)  # ranked, best first
    advanced: int = 0
    held: int = 0
    skipped_no_signals: int = 0
    generated_at: str = ""

    def top(self, n: int = 5) -> list[ScoredOpportunity]:
        return self.scored[:n]

    def to_markdown(self, top_n: int = 5) -> str:
        lines = [
            f"# Opportunity scoring pass — {self.generated_at}",
            "",
            (
                f"Scored {len(self.scored)} opportunit"
                f"{'y' if len(self.scored) == 1 else 'ies'}: "
                f"**{self.advanced} advanced** to validation, {self.held} held, "
                f"{self.skipped_no_signals} skipped (not enough evidence to score)."
            ),
            "",
            f"## Top {min(top_n, len(self.scored))}",
            "",
            "| # | Score | Conf | Advance | Title | Top reason |",
            "|---|------:|-----:|:-------:|-------|------------|",
        ]
        for index, item in enumerate(self.top(top_n), start=1):
            advance = "✅" if item.decision.advance else "—"
            title = item.record.title.replace("|", "\\|")
            reason = item.top_reason.replace("|", "\\|")
            lines.append(
                f"| {index} | {item.decision.score:.0f} | {item.decision.confidence:.2f} "
                f"| {advance} | {title} | {reason} |"
            )
        return "\n".join(lines) + "\n"


def _with_signals(record: OpportunityRecord, signals: OpportunitySignals) -> OpportunityRecord:
    payload = record.to_dict()
    payload["signals"] = signals.to_dict()
    return OpportunityRecord.from_dict(payload)


class ScoringPass:
    def __init__(
        self,
        inbox: OpportunityInbox,
        *,
        config: ScoringConfig | None = None,
        signal_provider: SignalProvider | None = None,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        self._inbox = inbox
        self._config = config or load_scoring_config()
        self._provider = signal_provider
        self._now = now or (lambda: datetime.now(timezone.utc))

    def _needs_scoring(self, record: OpportunityRecord) -> bool:
        return record.status is OpportunityStatus.INBOX

    def run(self, *, limit: int | None = None) -> ScoringPassReport:
        """Score every unscored inbox record, persist the result, and return a
        ranked report. Records whose signals can't be determined yet are left in
        the inbox (counted as skipped) rather than scored on a guess."""
        candidates = [record for record in self._inbox.list() if self._needs_scoring(record)]
        if limit is not None:
            candidates = candidates[:limit]

        scored: list[ScoredOpportunity] = []
        skipped = 0
        for record in candidates:
            signals = record.signals
            if signals is None and self._provider is not None:
                signals = self._provider(record)
            if signals is None:
                skipped += 1
                continue
            prepared = record if record.signals is not None else _with_signals(record, signals)
            decision, scored_record = score_opportunity_record(prepared, self._config)
            self._inbox.save(scored_record)
            scored.append(ScoredOpportunity(record=scored_record, decision=decision))

        scored.sort(key=lambda item: (item.decision.score, item.decision.confidence), reverse=True)
        advanced = sum(1 for item in scored if item.decision.advance)
        return ScoringPassReport(
            scored=scored,
            advanced=advanced,
            held=len(scored) - advanced,
            skipped_no_signals=skipped,
            generated_at=self._now().isoformat(),
        )
