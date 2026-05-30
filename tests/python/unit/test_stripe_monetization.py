"""Tests for Stripe monetization + paid-validation (F8).

Covers the live-vs-test gate, the paid-validation experiment (criteria set up
front), recording checkout outcomes into pass/fail, and that the scaffold ships
the serverless functions with no leftover tokens. Offline — no Stripe calls.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from packages.policies.approvals import PolicyViolation
from packages.schemas.experiment import ExperimentStatus, ExperimentType
from packages.schemas.opportunity import (
    EvidenceKind,
    EvidenceLink,
    OpportunityRecord,
    OpportunityStatus,
    SourceRef,
)
from packages.web.scaffold import default_context, scaffold_site
from packages.web.stripe_monetization import (
    assert_live_payments_allowed,
    assert_payments_mode_allowed,
    is_live_key,
    paid_validation_experiment,
    record_checkout_outcome,
)

ISO = "2026-05-30T12:00:00+00:00"


def _opp() -> OpportunityRecord:
    return OpportunityRecord(
        id="opp_pay1",
        title="Invoice autopilot",
        problem="Freelancers chase invoices",
        audience="freelancers",
        source=SourceRef(connector="hackernews", query="x"),
        status=OpportunityStatus.SCORED,
        evidence=[EvidenceLink(url="https://news.ycombinator.com/item?id=1",
                               kind=EvidenceKind.WILLINGNESS_TO_PAY)],
        created_at=ISO,
        updated_at=ISO,
    )


def test_is_live_key() -> None:
    assert is_live_key("sk_live_abc") is True
    assert is_live_key("sk_test_abc") is False
    assert is_live_key(None) is False


def test_live_payments_require_approval() -> None:
    with pytest.raises(PolicyViolation) as exc:
        assert_live_payments_allowed(approval_granted=False)
    assert exc.value.code == "payments_live_not_approved"
    assert_live_payments_allowed(approval_granted=True)  # no raise


def test_mode_gate_passes_test_keys_without_approval() -> None:
    assert_payments_mode_allowed(secret_key="sk_test_123", approval_granted=False)  # no raise
    with pytest.raises(PolicyViolation):
        assert_payments_mode_allowed(secret_key="sk_live_123", approval_granted=False)


def test_paid_validation_experiment_sets_criteria() -> None:
    exp = paid_validation_experiment(_opp(), threshold=15, window="21 days")
    assert exp.type is ExperimentType.FAKE_DOOR
    assert exp.status is ExperimentStatus.PLANNED
    assert exp.success_criteria.threshold == 15
    assert exp.success_criteria.window == "21 days"


def test_record_checkout_outcome_pass_and_fail() -> None:
    exp = paid_validation_experiment(_opp(), threshold=10)
    passed = record_checkout_outcome(exp, conversions=12)
    assert passed.status is ExperimentStatus.PASSED
    assert passed.results is not None and passed.results.metric_value == 12
    assert passed.completed_at

    failed = record_checkout_outcome(exp, conversions=3)
    assert failed.status is ExperimentStatus.FAILED
    assert failed.results.passed is False


def test_scaffold_ships_stripe_functions(tmp_path: Path) -> None:
    target = tmp_path / "site"
    written = scaffold_site(target, default_context("Acme"))
    names = {p.relative_to(target).as_posix() for p in written}
    assert "netlify/functions/create-checkout.mjs" in names
    assert "netlify/functions/stripe-webhook.mjs" in names
    # Tokens filled, stripe dependency present.
    checkout = (target / "netlify" / "functions" / "create-checkout.mjs").read_text()
    assert "{{" not in checkout
    assert "price_replace_me" in checkout  # default price id substituted
    assert '"stripe"' in (target / "package.json").read_text()
