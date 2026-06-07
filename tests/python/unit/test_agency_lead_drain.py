"""Lead-drain wiring: client netlify_site_id persistence + drain-target filter."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from packages.agency.registry import (
    RegistryError,
    lead_drain_targets,
    set_client_netlify_site_id,
)
from packages.schemas.product import ClientConfig


def test_client_config_roundtrips_netlify_site_id() -> None:
    cfg = ClientConfig(services=["hosting"], netlify_site_id="abc-123")
    assert cfg.to_dict()["netlify_site_id"] == "abc-123"
    assert ClientConfig.from_dict(cfg.to_dict()).netlify_site_id == "abc-123"


def test_client_config_defaults_site_id_for_legacy_records() -> None:
    # A record written before the field existed must still load.
    assert ClientConfig.from_dict({"services": ["hosting"]}).netlify_site_id == ""


def _registry(tmp_path: Path, records: list[dict]) -> Path:
    path = tmp_path / "products.json"
    path.write_text(json.dumps(records, indent=2) + "\n", encoding="utf-8")
    return path


def test_set_client_netlify_site_id_updates_nested_block(tmp_path: Path) -> None:
    path = _registry(
        tmp_path,
        [{"id": "joe-site", "type": "client-site", "client": {"services": ["hosting"]}}],
    )
    set_client_netlify_site_id("joe-site", "site-xyz", registry_path=path)

    record = json.loads(path.read_text())[0]
    assert record["client"]["netlify_site_id"] == "site-xyz"
    # Existing client fields are preserved by the merge.
    assert record["client"]["services"] == ["hosting"]


def test_set_client_netlify_site_id_unknown_product_raises(tmp_path: Path) -> None:
    path = _registry(tmp_path, [])
    with pytest.raises(RegistryError):
        set_client_netlify_site_id("ghost", "x", registry_path=path)


def test_lead_drain_targets_filters_to_lead_capture_with_site_id(tmp_path: Path) -> None:
    path = _registry(
        tmp_path,
        [
            {
                "id": "joe-site",
                "type": "client-site",
                "client": {
                    "services": ["hosting", "contact_forms"],
                    "netlify_site_id": "joe-1",
                },
            },
            # has a lead form but no site id -> excluded (can't target a store)
            {
                "id": "no-site",
                "type": "client-site",
                "client": {"services": ["contact_forms"], "netlify_site_id": ""},
            },
            # hosted but NO lead form -> excluded (most SMBs; no false "no leads" nags)
            {
                "id": "form-less",
                "type": "client-site",
                "client": {"services": ["hosting", "local_seo"], "netlify_site_id": "ns-1"},
            },
            # not a client-site -> excluded
            {"id": "bbw", "type": "product", "client": {}},
        ],
    )
    targets = lead_drain_targets(registry_path=path)
    assert targets == [{"product_id": "joe-site", "site_id": "joe-1"}]
