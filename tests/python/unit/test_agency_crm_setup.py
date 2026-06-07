"""Tests for the crm_setup service: HubSpot-default record + guards."""

from __future__ import annotations

from pathlib import Path

import pytest

from packages.agency.crm_setup import (
    DEFAULT_STAGES,
    CrmSetup,
    CrmSetupError,
    load_crm_setup,
    save_crm_setup,
)


def test_defaults_to_hubspot_with_standard_pipeline() -> None:
    rec = CrmSetup(product_id="acme-site")
    assert rec.platform == "hubspot"
    assert tuple(rec.stages) == DEFAULT_STAGES


def test_roundtrip(tmp_path: Path) -> None:
    rec = CrmSetup(product_id="acme-site", pipeline_name="Sales", handoff_doc="HANDOFF.md")
    save_crm_setup(rec, root=tmp_path / "svc")
    assert load_crm_setup("acme-site", root=tmp_path / "svc") == rec


def test_load_missing_returns_none(tmp_path: Path) -> None:
    assert load_crm_setup("nope", root=tmp_path / "svc") is None


def test_gohighlevel_is_supported_upgrade() -> None:
    CrmSetup(product_id="x", platform="gohighlevel").validate()  # no raise


def test_unsupported_platform_rejected() -> None:
    with pytest.raises(CrmSetupError, match="unsupported platform"):
        CrmSetup(product_id="x", platform="salesforce").validate()


def test_requires_product_id_and_stages() -> None:
    with pytest.raises(CrmSetupError, match="product_id"):
        CrmSetup(product_id="").validate()
    with pytest.raises(CrmSetupError, match="stage"):
        CrmSetup(product_id="x", stages=[]).validate()


def test_legacy_dict_loads_with_defaults() -> None:
    rec = CrmSetup.from_dict({"product_id": "x"})
    assert rec.platform == "hubspot" and tuple(rec.stages) == DEFAULT_STAGES
