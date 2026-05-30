"""Discovery advancement gates — the decision rules of the loop.

Two gates, mirroring ``docs/founder/founder-os.md``:

* **Validate gate** (soft): given an opportunity's signals + evidence, decide
  whether it may advance from the inbox to a validation experiment. "Does not
  advance" is a normal outcome, so this returns a structured
  :class:`AdvancementDecision` with reasons rather than raising.

* **Build gate** (hard): an opportunity may only advance to a build after a
  validation experiment has actually *passed*. Violating that is a real policy
  error, so it raises :class:`~packages.policies.approvals.PolicyViolation`,
  consistent with the rest of ``packages/policies/``.

The numeric scoring math lives in ``packages/discovery/scoring.py``; this module
owns the *thresholds and hard gates*, because policy is owned here, not by tools.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from packages.discovery.scoring import ScoringConfig, compute_confidence, compute_score
from packages.policies.approvals import PolicyViolation, PolicyViolationCode
from packages.schemas.experiment import ExperimentRecord, ExperimentStatus, ExperimentType
from packages.schemas.opportunity import (
    ComplianceFlag,
    OpportunityRecord,
    OpportunitySignals,
    OpportunityStatus,
)

# Experiment types that put a message in front of a human and therefore inherit
# the platform's outreach controls (anti-spam, suppression, volume).
SENDING_EXPERIMENT_TYPES = frozenset(
    {ExperimentType.COLD_OUTREACH, ExperimentType.COMMUNITY_POST}
)


@dataclass(frozen=True)
class GateReason:
    code: str  # a PolicyViolationCode value
    message: str


@dataclass(frozen=True)
class AdvancementDecision:
    score: float
    confidence: float
    advance: bool
    reasons: list[GateReason] = field(default_factory=list)

    @property
    def reason_codes(self) -> list[str]:
        return [reason.code for reason in self.reasons]


def evaluate_opportunity(
    signals: OpportunitySignals,
    *,
    evidence_links: int,
    distinct_sources: int,
    compliance_flags: list[ComplianceFlag] | None = None,
    config: ScoringConfig,
) -> AdvancementDecision:
    """Apply the hard gates and advancement thresholds. An opportunity advances
    only if no hard gate trips AND it clears score + confidence + distribution."""
    score = compute_score(signals, config.weights)
    confidence = compute_confidence(evidence_links, distinct_sources, config.confidence)
    flags = compliance_flags or []

    reasons: list[GateReason] = []

    # Hard gates override the numeric score entirely.
    if signals.risk <= config.hard_gates.reject_if_risk_at_or_below:
        reasons.append(
            GateReason(
                PolicyViolationCode.DISCOVERY_RISK_TOO_HIGH.value,
                f"high regulatory/ToS risk (risk={signals.risk:g}) — route to compliance",
            )
        )
    blocked = {flag for flag in config.hard_gates.block_compliance_flags}
    for flag in flags:
        if flag.value in blocked:
            reasons.append(
                GateReason(
                    PolicyViolationCode.DISCOVERY_BLOCKED_COMPLIANCE_FLAG.value,
                    f"blocked compliance flag: {flag.value} — needs a named owner",
                )
            )
    if signals.distribution_path < config.thresholds.min_distribution_score:
        reasons.append(
            GateReason(
                PolicyViolationCode.DISCOVERY_NO_DISTRIBUTION.value,
                "no distribution path — cannot advance to validation",
            )
        )

    # Threshold gates.
    if score < config.thresholds.min_score_to_validate:
        reasons.append(
            GateReason(
                PolicyViolationCode.DISCOVERY_SCORE_BELOW_THRESHOLD.value,
                f"score {score:.0f} below min {config.thresholds.min_score_to_validate:g}",
            )
        )
    if confidence < config.thresholds.min_confidence_to_validate:
        reasons.append(
            GateReason(
                PolicyViolationCode.DISCOVERY_LOW_CONFIDENCE.value,
                (
                    f"confidence {confidence:.2f} below min "
                    f"{config.thresholds.min_confidence_to_validate:g} — gather more evidence"
                ),
            )
        )

    return AdvancementDecision(
        score=round(score, 2),
        confidence=round(confidence, 4),
        advance=not reasons,
        reasons=reasons,
    )


def score_opportunity_record(
    record: OpportunityRecord,
    config: ScoringConfig,
) -> tuple[AdvancementDecision, OpportunityRecord]:
    """Score a record in place: fills ``score``/``confidence`` and sets status to
    ``scored`` (or ``validating`` if it clears the gate). Returns the decision
    and a NEW record (records are frozen)."""
    signals = record.signals or OpportunitySignals()
    decision = evaluate_opportunity(
        signals,
        evidence_links=len(record.evidence),
        distinct_sources=max(1, record.distinct_sources()),
        compliance_flags=record.compliance_flags,
        config=config,
    )
    payload = record.to_dict()
    payload["signals"] = signals.to_dict()
    payload["score"] = decision.score
    payload["confidence"] = decision.confidence
    payload["status"] = (
        OpportunityStatus.VALIDATING.value if decision.advance else OpportunityStatus.SCORED.value
    )
    return decision, OpportunityRecord.from_dict(payload)


def assert_ready_to_build(
    opportunity: OpportunityRecord,
    experiment: ExperimentRecord | None,
) -> None:
    """Hard gate: refuse to advance to a build unless a validation experiment
    has passed. Raises :class:`PolicyViolation` with a machine-readable code.

    Mirrors the "validate before you build — code is the most expensive test"
    rule. The orchestrator calls this before assigning any build task.
    """
    if experiment is None:
        raise PolicyViolation(
            PolicyViolationCode.DISCOVERY_EXPERIMENT_NOT_PASSED,
            detail=f"opportunity {opportunity.id} has no validation experiment",
        )
    if experiment.success_criteria is None:  # pragma: no cover - schema requires it
        raise PolicyViolation(
            PolicyViolationCode.DISCOVERY_MISSING_SUCCESS_CRITERIA,
            detail=f"experiment {experiment.id} has no pre-set success criteria",
        )
    if experiment.status is not ExperimentStatus.PASSED:
        raise PolicyViolation(
            PolicyViolationCode.DISCOVERY_EXPERIMENT_NOT_PASSED,
            detail=(
                f"experiment {experiment.id} status is {experiment.status.value}, not passed — "
                "no build before a passed validation gate"
            ),
        )


def assert_bulk_crawl_allowed(
    *,
    approved_by: str | None,
    robots_checked: bool,
    rate_limited: bool,
) -> None:
    """C1 — gate a bulk crawl. Connectors refuse ``bulk=True`` on their own; the
    orchestrator calls this to authorize a vetted, throttled plan instead. A bulk
    crawl needs a named approver AND its preconditions (robots checked, rate
    limited) before it may run. Raises :class:`PolicyViolation` otherwise."""
    if not approved_by:
        raise PolicyViolation(
            PolicyViolationCode.DISCOVERY_BULK_CRAWL_NOT_APPROVED,
            detail="bulk crawl requires a named human approver",
        )
    missing = [
        name
        for name, ok in (("robots_checked", robots_checked), ("rate_limited", rate_limited))
        if not ok
    ]
    if missing:
        raise PolicyViolation(
            PolicyViolationCode.DISCOVERY_BULK_CRAWL_PRECONDITION,
            detail=f"bulk crawl preconditions unmet: {', '.join(missing)}",
        )


def assert_outreach_ready(experiment: ExperimentRecord) -> None:
    """C3 — gate a validation experiment that *sends*. Cold outreach / community
    posts must be compliance-reviewed with unsubscribe wired and the suppression
    list checked; any experiment that spends must carry an approved budget.
    Raises :class:`PolicyViolation` on the first failing check."""
    spend = experiment.spend
    if spend is not None and spend.budget > 0 and not spend.approved_by:
        raise PolicyViolation(
            PolicyViolationCode.DISCOVERY_OUTREACH_SPEND_UNAPPROVED,
            detail=f"experiment {experiment.id} has unapproved spend of {spend.budget}",
        )

    if experiment.type not in SENDING_EXPERIMENT_TYPES:
        return

    compliance = experiment.compliance
    if compliance is None or not compliance.reviewed_by:
        raise PolicyViolation(
            PolicyViolationCode.DISCOVERY_OUTREACH_NOT_REVIEWED,
            detail=f"sending experiment {experiment.id} has not been compliance-reviewed",
        )
    if not compliance.unsubscribe_wired:
        raise PolicyViolation(
            PolicyViolationCode.DISCOVERY_OUTREACH_UNSUBSCRIBE_MISSING,
            detail=f"experiment {experiment.id} has no working unsubscribe",
        )
    if not compliance.suppression_checked:
        raise PolicyViolation(
            PolicyViolationCode.DISCOVERY_OUTREACH_SUPPRESSION_MISSING,
            detail=f"experiment {experiment.id} did not check the suppression list",
        )
