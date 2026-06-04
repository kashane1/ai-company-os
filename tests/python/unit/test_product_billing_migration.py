"""Migration-safety tests for BillingStatus widening + acceptance fields ([MIG-P0])."""

from __future__ import annotations

from packages.schemas.product import BillingStatus, ClientConfig


def test_known_statuses_load() -> None:
    for status in BillingStatus:
        cfg = ClientConfig.from_dict({"billing_status": status.value})
        assert cfg.billing_status is status


def test_unknown_status_falls_back_to_cancelled_not_active() -> None:
    # A value an older reader can't parse must NOT abort the load, and must NOT
    # become an entitled state.
    cfg = ClientConfig.from_dict({"billing_status": "some_future_status"})
    assert cfg.billing_status is BillingStatus.CANCELLED


def test_legacy_record_without_acceptance_fields_loads() -> None:
    cfg = ClientConfig.from_dict(
        {"bundle": "package_c", "services": ["website"], "billing_status": "active"}
    )
    assert cfg.accepted_by == ""
    assert cfg.accepted_at == ""
    assert cfg.billing_status is BillingStatus.ACTIVE


def test_acceptance_fields_roundtrip() -> None:
    cfg = ClientConfig.from_dict(
        {
            "billing_status": "active",
            "accepted_by": "owner@example.com",
            "accepted_at": "1700000000",
        }
    )
    assert ClientConfig.from_dict(cfg.to_dict()) == cfg
    assert cfg.to_dict()["accepted_by"] == "owner@example.com"


def test_disputed_status_is_parseable_by_strict_loader() -> None:
    # The exact [MIG-P0] regression: a disputed value must load, not raise.
    cfg = ClientConfig.from_dict({"billing_status": "disputed"})
    assert cfg.billing_status is BillingStatus.DISPUTED
