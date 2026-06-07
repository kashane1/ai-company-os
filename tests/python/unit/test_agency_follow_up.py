"""Tests for follow_up_automation: email-first record, gated SMS, retainer wiring."""

from __future__ import annotations

from pathlib import Path

import pytest

from packages.agency.follow_up import (
    DEFAULT_STEPS,
    FollowUpError,
    FollowUpSetup,
    load_follow_up_setup,
    save_follow_up_setup,
)
from packages.agency.retainer_ops import plan_retainer_run


def test_defaults_email_first_on_hubspot() -> None:
    rec = FollowUpSetup(product_id="acme-site")
    assert rec.platform == "hubspot"
    assert rec.email_enabled is True and rec.sms_enabled is False
    assert tuple(rec.steps) == DEFAULT_STEPS
    rec.validate()  # no raise


def test_roundtrip(tmp_path: Path) -> None:
    rec = FollowUpSetup(product_id="acme-site")
    save_follow_up_setup(rec, root=tmp_path / "svc")
    assert load_follow_up_setup("acme-site", root=tmp_path / "svc") == rec


def test_sms_on_hubspot_is_rejected() -> None:
    with pytest.raises(FollowUpError, match="compliant SMS-capable platform"):
        FollowUpSetup(product_id="x", platform="hubspot", sms_enabled=True).validate()


def test_sms_allowed_on_gohighlevel() -> None:
    FollowUpSetup(product_id="x", platform="gohighlevel", sms_enabled=True).validate()  # no raise


def test_requires_a_channel() -> None:
    with pytest.raises(FollowUpError, match="at least one channel"):
        FollowUpSetup(product_id="x", email_enabled=False, sms_enabled=False).validate()


def test_unsupported_platform_rejected() -> None:
    with pytest.raises(FollowUpError, match="unsupported platform"):
        FollowUpSetup(product_id="x", platform="salesforce").validate()


def test_legacy_dict_loads_email_first() -> None:
    rec = FollowUpSetup.from_dict({"product_id": "x"})
    assert rec.email_enabled is True and rec.sms_enabled is False


def test_retainer_plans_review_follow_up() -> None:
    client = {"billing_status": "active", "services": ["follow_up_automation"]}
    record = {"id": "acme-site", "client": client}
    run = plan_retainer_run(record, month="2026-06")
    assert "review_follow_up" in run.planned_actions
