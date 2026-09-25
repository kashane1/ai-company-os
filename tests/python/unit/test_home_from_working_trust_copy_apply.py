from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest


SCRIPT = Path(__file__).resolve().parents[3] / "scripts/home_from_working_apply_trust_copy.py"
SPEC = importlib.util.spec_from_file_location("home_from_working_apply_trust_copy", SCRIPT)
assert SPEC and SPEC.loader
apply_copy = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(apply_copy)


PARAGRAPH = "This original design was developed with generative-AI tools."


def test_write_credentials_read_etsy_env_only(monkeypatch):
    values = {
        "ETSY_API_CREDENTIAL": "key:secret",
        "ETSY_OAUTH_ACCESS_TOKEN": "access",
        "ETSY_OAUTH_EXPIRES_AT": "2030-01-02T03:04:05+00:00",
    }

    def loader(name, **kwargs):
        assert kwargs == {"source": "etsy_env"}
        return values.get(name)

    monkeypatch.setattr(apply_copy, "get_secret", loader)
    assert apply_copy._load_write_credentials() == ("key:secret", "access")


def _hash(document: object) -> str:
    return hashlib.sha256(
        json.dumps(document, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _snapshot() -> dict:
    return {
        "shop": {"shop_id": 123, "shop_name": "HomeFromWorking"},
        "listings": [
            {
                "listing_id": 456,
                "title": "Approved listing",
                "description": "Original description",
            }
        ],
    }


def _manifest(snapshot: dict) -> dict:
    return {
        "schema_version": 1,
        "status": "draft_awaiting_founder_approval",
        "source_snapshot": {"path": "snapshot.json", "sha256": _hash(snapshot)},
        "change": {
            "field": "description",
            "operation": "append_exact_paragraph_once",
            "paragraph": PARAGRAPH,
        },
        "approval": {
            "required": True,
            "scope": "exact_manifest_revision_only",
            "approved": False,
            "publication_approval_included": False,
        },
        "targets": [
            {
                "listing_id": "456",
                "record_key": "design/one",
                "title": "Approved listing",
            }
        ],
    }


class FakeClient:
    def __init__(self, description: str = "Original description") -> None:
        self.listing = {
            "listing_id": 456,
            "shop_id": 123,
            "title": "Approved listing",
            "description": description,
            "tags": ["tag"],
            "shipping_profile_id": 999,
            "state": "active",
        }
        self.inventory = {"products": [{"product_id": 1, "offerings": [{"price": 19.99}]}]}
        self.updates: list[tuple[int, int, str]] = []

    def get_listing(self, listing_id: int) -> dict:
        assert listing_id == 456
        return dict(self.listing)

    def get_listing_inventory(self, listing_id: int) -> dict:
        assert listing_id == 456
        return json.loads(json.dumps(self.inventory))

    def update_listing_description(self, shop_id: int, listing_id: int, description: str) -> dict:
        self.updates.append((shop_id, listing_id, description))
        self.listing["description"] = description
        return dict(self.listing)


def test_apply_plan_writes_only_exact_description_then_verifies_readback() -> None:
    snapshot = _snapshot()
    plan = apply_copy.build_plan(_manifest(snapshot), snapshot)
    client = FakeClient()

    receipt = apply_copy.apply_plan(client, plan)

    assert client.updates == [
        (123, 456, f"Original description\n\n{PARAGRAPH}")
    ]
    assert receipt["summary"] == {"applied": 1, "already_applied": 0}
    assert receipt["targets"][0]["post_action_description_sha256"] == hashlib.sha256(
        f"Original description\n\n{PARAGRAPH}".encode()
    ).hexdigest()


def test_apply_plan_is_idempotent_only_when_current_description_is_exact_desired() -> None:
    snapshot = _snapshot()
    plan = apply_copy.build_plan(_manifest(snapshot), snapshot)
    client = FakeClient(f"Original description\n\n{PARAGRAPH}")

    receipt = apply_copy.apply_plan(client, plan)

    assert client.updates == []
    assert receipt["summary"] == {"applied": 0, "already_applied": 1}


def test_apply_plan_refuses_description_drift_before_any_write() -> None:
    snapshot = _snapshot()
    plan = apply_copy.build_plan(_manifest(snapshot), snapshot)
    client = FakeClient("Manually changed description")

    with pytest.raises(ValueError, match="description drift"):
        apply_copy.apply_plan(client, plan)

    assert client.updates == []


def test_build_plan_refuses_manifest_that_allows_publication_or_bad_snapshot_hash() -> None:
    snapshot = _snapshot()
    manifest = _manifest(snapshot)
    manifest["approval"]["publication_approval_included"] = True
    with pytest.raises(ValueError, match="publication"):
        apply_copy.build_plan(manifest, snapshot)

    manifest = _manifest(snapshot)
    manifest["source_snapshot"]["sha256"] = "0" * 64
    with pytest.raises(ValueError, match="snapshot hash"):
        apply_copy.build_plan(manifest, snapshot)
