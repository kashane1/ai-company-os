"""Stripe monetization + paid-validation experiment (F8).

A "buy"/pre-order button is the strongest willingness-to-pay signal there is —
far stronger than a waitlist email. So a monetized landing page doubles as a
*paid-validation experiment*: checkout conversions feed the same experiment store
the build gate reads.

This module is the platform (Python) side:

* a **gate** — live Stripe mode moves real money, so it's approval-gated like
  billing/pricing (test mode is free to use for validation);
* a **paid-validation experiment** builder (criteria set before running); and
* a way to **record checkout outcomes** back onto that experiment.

The site-side pieces (a Stripe Checkout button + Netlify serverless functions)
ship in the web scaffold under ``netlify/functions/``.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable

from packages.config.settings import (
    STRIPE_SECRET_KEY_ENV_VAR,
    STRIPE_WEBHOOK_SECRET_ENV_VAR,
    get_api_key,
)
from packages.policies.approvals import PolicyViolation, PolicyViolationCode
from packages.schemas.experiment import (
    ExperimentMetric,
    ExperimentRecord,
    ExperimentResults,
    ExperimentStatus,
    ExperimentType,
    SuccessCriteria,
)
from packages.schemas.opportunity import OpportunityRecord

# Stripe test keys are prefixed sk_test_; live keys sk_live_.
_LIVE_KEY_PREFIX = "sk_live_"


def is_live_key(secret_key: str | None) -> bool:
    return bool(secret_key) and secret_key.startswith(_LIVE_KEY_PREFIX)


def assert_live_payments_allowed(*, approval_granted: bool) -> None:
    """Going live with real charges requires a granted approval. Test mode
    (``sk_test_…``) needs no approval — that's the whole point of validation."""
    if not approval_granted:
        raise PolicyViolation(
            PolicyViolationCode.PAYMENTS_LIVE_NOT_APPROVED,
            "enabling live Stripe payments (real charges) requires a granted approval",
        )


def assert_payments_mode_allowed(
    *, secret_key: str | None = None, approval_granted: bool = False
) -> None:
    """Resolve the configured Stripe key and gate it: live keys need approval,
    test keys pass freely."""
    key = secret_key if secret_key is not None else get_api_key(STRIPE_SECRET_KEY_ENV_VAR)
    if is_live_key(key):
        assert_live_payments_allowed(approval_granted=approval_granted)


def webhook_secret_configured() -> bool:
    """True if the webhook signing secret is set (the function verifies events)."""
    return bool(get_api_key(STRIPE_WEBHOOK_SECRET_ENV_VAR))


def paid_validation_experiment(
    opportunity: OpportunityRecord,
    *,
    metric: ExperimentMetric = ExperimentMetric.PREORDERS,
    threshold: float = 10,
    window: str = "30 days",
    now: Callable[[], datetime] | None = None,
) -> ExperimentRecord:
    """A fake-door / pre-order checkout test: does anyone actually pay?

    Criteria are set up front. Status is ``PLANNED`` until the page is live.
    """
    timestamp = (now or (lambda: datetime.now(timezone.utc)))().isoformat()
    return ExperimentRecord(
        id=f"exp_pay_{opportunity.id.removeprefix('opp_')}",
        opportunity_id=opportunity.id,
        type=ExperimentType.FAKE_DOOR,
        hypothesis=(
            f"At least {threshold:g} {metric.value} for “{opportunity.title}” from "
            f"{opportunity.audience} within {window} (real Stripe checkout intent)."
        ),
        success_criteria=SuccessCriteria(metric=metric, threshold=threshold, window=window),
        status=ExperimentStatus.PLANNED,
        created_at=timestamp,
    )


def record_checkout_outcome(
    experiment: ExperimentRecord,
    *,
    conversions: int,
    notes: str = "",
    now: Callable[[], datetime] | None = None,
) -> ExperimentRecord:
    """Fold observed checkout conversions onto the experiment and decide pass/fail
    against its pre-set threshold. Returns the updated record (persist it via the
    experiment store)."""
    timestamp = (now or (lambda: datetime.now(timezone.utc)))().isoformat()
    passed = conversions >= experiment.success_criteria.threshold
    payload = experiment.to_dict()
    payload["results"] = ExperimentResults(
        metric_value=float(conversions),
        passed=passed,
        notes=notes,
    ).to_dict()
    payload["status"] = (
        ExperimentStatus.PASSED.value if passed else ExperimentStatus.FAILED.value
    )
    payload["completed_at"] = timestamp
    return ExperimentRecord.from_dict(payload)
