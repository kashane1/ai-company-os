"""Phase 5.2 — strategic task type enum assertions."""

from __future__ import annotations

from packages.schemas.task_packet import STRATEGIC_TASK_TYPES


EXPECTED = {
    "PRODUCT_BRIEF_UPDATE",
    "MVP_SPEC_UPDATE",
    "APPSTORE_POSITIONING_REFRESH",
    "APPSTORE_METADATA_DRAFT",
    "SCREENSHOT_PLAN_REFRESH",
    "ARTIFACT_CHAIN_REVIEW",
    "FOUNDER_BRIEF_INTAKE",
    "GTM_CAMPAIGN_BRIEF",
    "FAILURE_REGRESSION_FIXTURE",
}


def test_strategic_task_types_contains_phase_5_set():
    missing = EXPECTED - STRATEGIC_TASK_TYPES
    assert not missing, f"missing strategic task types: {missing}"


def test_strategic_task_types_is_frozenset():
    assert isinstance(STRATEGIC_TASK_TYPES, frozenset)
