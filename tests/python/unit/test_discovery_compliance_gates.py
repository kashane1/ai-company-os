"""Tests for the discovery compliance/approval gates (C1, C2, C3)."""

from __future__ import annotations

import httpx
import pytest

from packages.discovery.connectors.robots import RobotsPolicy
from packages.policies.approvals import PolicyViolation, PolicyViolationCode
from packages.policies.discovery_gates import (
    assert_bulk_crawl_allowed,
    assert_outreach_ready,
)
from packages.schemas.experiment import (
    ExperimentCompliance,
    ExperimentMetric,
    ExperimentRecord,
    ExperimentSpend,
    ExperimentStatus,
    ExperimentType,
    SuccessCriteria,
)

# ── C1: bulk crawl gate ────────────────────────────────────────────────────────


def test_bulk_crawl_allowed_when_approved_and_preconditions_met() -> None:
    assert_bulk_crawl_allowed(approved_by="kashane", robots_checked=True, rate_limited=True)


def test_bulk_crawl_blocked_without_approver() -> None:
    with pytest.raises(PolicyViolation) as exc:
        assert_bulk_crawl_allowed(approved_by=None, robots_checked=True, rate_limited=True)
    assert exc.value.code == PolicyViolationCode.DISCOVERY_BULK_CRAWL_NOT_APPROVED.value


def test_bulk_crawl_blocked_on_unmet_precondition() -> None:
    with pytest.raises(PolicyViolation) as exc:
        assert_bulk_crawl_allowed(approved_by="kashane", robots_checked=False, rate_limited=True)
    assert exc.value.code == PolicyViolationCode.DISCOVERY_BULK_CRAWL_PRECONDITION.value


# ── C2: httpx robots fetcher ───────────────────────────────────────────────────

ROBOTS = "User-agent: *\nDisallow: /private\nAllow: /\n"


def _robots_client(status: int, body: str = ROBOTS) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/robots.txt"
        if status == 404:
            return httpx.Response(404)
        return httpx.Response(status, text=body)

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_httpx_robots_policy_allows_and_blocks() -> None:
    policy = RobotsPolicy.from_httpx(client=_robots_client(200))
    assert policy.can_fetch("https://example.com/public", "bot") is True
    assert policy.can_fetch("https://example.com/private/x", "bot") is False


def test_httpx_robots_missing_file_allows() -> None:
    policy = RobotsPolicy.from_httpx(client=_robots_client(404))
    assert policy.can_fetch("https://example.com/anything", "bot") is True


# ── C3: outreach gate ──────────────────────────────────────────────────────────


def _experiment(
    *,
    type: ExperimentType = ExperimentType.COLD_OUTREACH,
    compliance: ExperimentCompliance | None = None,
    spend: ExperimentSpend | None = None,
) -> ExperimentRecord:
    return ExperimentRecord(
        id="exp_1",
        opportunity_id="opp_1",
        type=type,
        hypothesis="people reply",
        success_criteria=SuccessCriteria(metric=ExperimentMetric.REPLY_RATE, threshold=0.1),
        status=ExperimentStatus.APPROVED,
        compliance=compliance,
        spend=spend,
    )


def _ready_compliance() -> ExperimentCompliance:
    return ExperimentCompliance(
        reviewed_by="compliance-1", unsubscribe_wired=True, suppression_checked=True
    )


def test_outreach_ready_when_compliant() -> None:
    assert_outreach_ready(_experiment(compliance=_ready_compliance()))


def test_outreach_blocked_when_not_reviewed() -> None:
    with pytest.raises(PolicyViolation) as exc:
        assert_outreach_ready(_experiment(compliance=None))
    assert exc.value.code == PolicyViolationCode.DISCOVERY_OUTREACH_NOT_REVIEWED.value


def test_outreach_blocked_without_unsubscribe() -> None:
    compliance = ExperimentCompliance(
        reviewed_by="c", unsubscribe_wired=False, suppression_checked=True
    )
    with pytest.raises(PolicyViolation) as exc:
        assert_outreach_ready(_experiment(compliance=compliance))
    assert exc.value.code == PolicyViolationCode.DISCOVERY_OUTREACH_UNSUBSCRIBE_MISSING.value


def test_outreach_blocked_without_suppression() -> None:
    compliance = ExperimentCompliance(
        reviewed_by="c", unsubscribe_wired=True, suppression_checked=False
    )
    with pytest.raises(PolicyViolation) as exc:
        assert_outreach_ready(_experiment(compliance=compliance))
    assert exc.value.code == PolicyViolationCode.DISCOVERY_OUTREACH_SUPPRESSION_MISSING.value


def test_outreach_blocked_on_unapproved_spend() -> None:
    spend = ExperimentSpend(budget=200, approved_by="")
    with pytest.raises(PolicyViolation) as exc:
        assert_outreach_ready(
            _experiment(type=ExperimentType.PAID_AD, spend=spend)
        )
    assert exc.value.code == PolicyViolationCode.DISCOVERY_OUTREACH_SPEND_UNAPPROVED.value


def test_non_sending_experiment_needs_no_outreach_compliance() -> None:
    # A landing page isn't a send — no compliance object required.
    assert_outreach_ready(_experiment(type=ExperimentType.LANDING_PAGE, compliance=None))
