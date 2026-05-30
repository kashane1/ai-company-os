"""D4 — persist discovery gate decisions to the approvals store.

The bulk-crawl (C1) and outreach (C3) gates are pure functions: they raise or
return, but leave no trace. For consequential, human-gated actions that's not
enough — the platform's principle is that every gated decision is *recorded and
replayable* (the approvals store + approval-reviewer surface, same as task and
release approvals).

This recorder wraps those gate functions: it runs the gate, writes an
``ApprovalRecord`` capturing the outcome (approved or rejected, with the reason
code), and then preserves enforcement by re-raising on a block. So nothing
changes about *whether* an action is allowed — we just leave an audit trail of
who decided what, when, and why.

The ``ApprovalStore`` is injectable so the recorder is testable against an
isolated DB (or a fake) with no global state.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Callable

from packages.db.approval_store import ApprovalStore
from packages.db.experiment_store import ExperimentStore
from packages.policies.approvals import PolicyViolation
from packages.policies.discovery_gates import (
    assert_bulk_crawl_allowed,
    assert_outreach_ready,
)
from packages.schemas.approval import ApprovalRecord, ApprovalStatus
from packages.schemas.experiment import ExperimentRecord, ExperimentStatus

BULK_CRAWL_ACTION = "discovery_bulk_crawl"
OUTREACH_ACTION = "discovery_outreach"


class GateDecisionRecorder:
    def __init__(
        self,
        store: ApprovalStore | None = None,
        *,
        now: Callable[[], datetime] | None = None,
        id_factory: Callable[[], str] | None = None,
    ) -> None:
        self._store = store or ApprovalStore()
        self._now = now or (lambda: datetime.now(timezone.utc))
        self._id_factory = id_factory or (lambda: f"appr_{uuid.uuid4().hex[:12]}")

    def _persist(
        self,
        *,
        action: str,
        subject_id: str,
        summary: str,
        status: ApprovalStatus,
        decided_by: str | None,
        notes: str | None,
    ) -> ApprovalRecord:
        timestamp = self._now().isoformat()
        record = ApprovalRecord(
            id=self._id_factory(),
            status=status,
            summary=summary,
            created_at=timestamp,
            approval_type="discovery",
            subject_type=action,
            subject_id=subject_id,
            action=action,
            decided_by=decided_by,
            decided_at=timestamp,
            decision_notes=notes,
        )
        self._store.save(record)
        return record

    def record_bulk_crawl(
        self,
        *,
        source_id: str,
        approved_by: str | None,
        robots_checked: bool,
        rate_limited: bool,
    ) -> ApprovalRecord:
        """Run the bulk-crawl gate and record the decision. Re-raises
        :class:`PolicyViolation` (after recording a rejection) if blocked."""
        try:
            assert_bulk_crawl_allowed(
                approved_by=approved_by,
                robots_checked=robots_checked,
                rate_limited=rate_limited,
            )
        except PolicyViolation as exc:
            self._persist(
                action=BULK_CRAWL_ACTION,
                subject_id=source_id,
                summary=f"bulk crawl of {source_id} blocked",
                status=ApprovalStatus.REJECTED,
                decided_by=approved_by,
                notes=f"{exc.code}: {exc}",
            )
            raise
        return self._persist(
            action=BULK_CRAWL_ACTION,
            subject_id=source_id,
            summary=f"bulk crawl of {source_id} approved",
            status=ApprovalStatus.APPROVED,
            decided_by=approved_by,
            notes=None,
        )

    def record_outreach(self, experiment: ExperimentRecord) -> ApprovalRecord:
        """Run the outreach gate for a sending experiment and record the decision.
        Re-raises :class:`PolicyViolation` (after recording a rejection) if
        blocked."""
        reviewed_by = experiment.compliance.reviewed_by if experiment.compliance else None
        try:
            assert_outreach_ready(experiment)
        except PolicyViolation as exc:
            self._persist(
                action=OUTREACH_ACTION,
                subject_id=experiment.id,
                summary=f"outreach for experiment {experiment.id} blocked",
                status=ApprovalStatus.REJECTED,
                decided_by=reviewed_by,
                notes=f"{exc.code}: {exc}",
            )
            raise
        return self._persist(
            action=OUTREACH_ACTION,
            subject_id=experiment.id,
            summary=f"outreach for experiment {experiment.id} approved",
            status=ApprovalStatus.APPROVED,
            decided_by=reviewed_by,
            notes=None,
        )


def start_sending_experiment(
    store: ExperimentStore,
    experiment_id: str,
    *,
    recorder: GateDecisionRecorder | None = None,
) -> ExperimentRecord:
    """E5 — gate an experiment's send at the point it goes live.

    Runs the outreach gate (recording the decision when a ``recorder`` is given)
    and only then transitions the experiment ``approved -> running``. If the gate
    blocks, it raises :class:`PolicyViolation` and the experiment stays put — a
    non-compliant send can never reach ``running``.
    """
    experiment = store.get(experiment_id)
    if recorder is not None:
        recorder.record_outreach(experiment)  # records + raises on block
    else:
        assert_outreach_ready(experiment)
    return store.transition(experiment_id, ExperimentStatus.RUNNING)
