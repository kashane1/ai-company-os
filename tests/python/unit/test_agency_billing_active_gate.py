"""Tests for the assert_billing_active work-guard (G1 + retainer [E2])."""

from __future__ import annotations

import pytest

from packages.policies.agency_gates import assert_billing_active
from packages.policies.approvals import PolicyViolation
from packages.schemas.product import BillingStatus


def test_active_client_passes() -> None:
    assert_billing_active(BillingStatus.ACTIVE)  # no raise
    assert_billing_active("active")


@pytest.mark.parametrize("status", ["trial", "past_due", "cancelled", "disputed", "refunded"])
def test_non_active_client_is_refused(status: str) -> None:
    with pytest.raises(PolicyViolation) as exc:
        assert_billing_active(status, product_id="joes-plumbing-site")
    assert exc.value.code == "retainer_client_not_active"


def test_unknown_status_is_refused_not_crashes() -> None:
    # Coerces to a work-stopping state, then refuses — never raises ValueError.
    with pytest.raises(PolicyViolation):
        assert_billing_active("some_future_status")
