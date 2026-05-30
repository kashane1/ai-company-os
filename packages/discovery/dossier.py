"""Dossier generation — project a validated opportunity into a research brief.

The dossier is what the build lane works from. This builds the deterministic
*skeleton* from what the opportunity already carries (pain quotes, competitors,
distribution ideas, the MVP idea) plus the validation result. An analyst/agent
can then enrich the open questions — but the brief is never empty, and every
field traces back to evidence on the record rather than invention.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable

from packages.schemas.dossier import (
    DossierAudience,
    DossierChannel,
    DossierCompetitor,
    DossierMvp,
    DossierRecord,
)
from packages.schemas.experiment import ExperimentRecord, ExperimentStatus
from packages.schemas.opportunity import OpportunityRecord


def _dossier_id(opportunity_id: str) -> str:
    suffix = opportunity_id.removeprefix("opp_")
    return f"dos_{suffix}"


def build_dossier(
    opportunity: OpportunityRecord,
    experiment: ExperimentRecord | None = None,
    *,
    now: Callable[[], datetime] | None = None,
) -> DossierRecord:
    timestamp = (now or (lambda: datetime.now(timezone.utc)))().isoformat()

    pain_quotes = [link.quote for link in opportunity.evidence if link.quote][:8]
    competitors = [
        DossierCompetitor(
            name=competitor.name,
            url=competitor.url,
            pricing=competitor.pricing,
            weaknesses=[competitor.weakness] if competitor.weakness else [],
        )
        for competitor in opportunity.competitors
    ]
    distribution = [
        DossierChannel(channel=idea) for idea in opportunity.distribution_ideas
    ]
    mvp = DossierMvp(thinnest_slice=opportunity.mvp_idea) if opportunity.mvp_idea else None

    risks: list[str] = [f"compliance flag: {flag.value}" for flag in opportunity.compliance_flags]
    open_questions: list[str] = []
    if experiment is None:
        open_questions.append("No validation experiment on record — define success criteria first.")
    elif experiment.status is not ExperimentStatus.PASSED:
        open_questions.append(
            f"Validation experiment {experiment.id} is {experiment.status.value}, not passed."
        )

    return DossierRecord(
        id=_dossier_id(opportunity.id),
        opportunity_id=opportunity.id,
        summary=opportunity.problem,
        audience=DossierAudience(
            who=opportunity.audience,
            where_they_are=list(opportunity.distribution_ideas),
        ),
        pain_quotes=pain_quotes,
        competitors=competitors,
        mvp=mvp,
        distribution=distribution,
        risks=risks,
        open_questions=open_questions,
        created_at=timestamp,
    )
