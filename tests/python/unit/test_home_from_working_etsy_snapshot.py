from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from packages.config import etsy_env
from packages.config import secrets as secret_config
from packages.etsy.auth import EtsyOAuthToken
from scripts.home_from_working_etsy_snapshot import (
    _results,
    collect_snapshot,
    load_oauth_material,
    maybe_refresh_token,
    resolve_output_path,
    write_snapshot_atomic,
)


class FakeEtsy:
    def find_shop_by_name(self, name):
        assert name == "HomeFromWorking"
        return {"results": [{"shop_id": 42, "shop_name": name, "user_id": 9999, "login_name": "secret"}]}

    def iter_shops_by_name(self, name):
        return iter(_results(self.find_shop_by_name(name), context="Etsy shop lookup"))

    def get_shop(self, shop_id):
        return {"shop_id": shop_id, "shop_name": "HomeFromWorking", "user_id": 9999, "title": "Work"}

    def iter_active_listings(self, shop_id):
        return iter(
            [
                {
                    "listing_id": 2,
                    "title": "Second",
                    "state": "active",
                    "description": "A useful description",
                    "tags": ["work"],
                    "shipping_profile_id": 7,
                    "return_policy_id": 8,
                    "production_partner_ids": [4],
                    "image_ids": [12],
                    "who_made": "i_did",
                    "when_made": "made_to_order",
                    "created_timestamp": 10,
                    "updated_timestamp": 11,
                    "quantity": 3,
                    "sku": "DO_NOT_EXPORT",
                    "user_id": 9999,
                }
            ]
        )

    def get_listing(self, listing_id):
        assert listing_id == 2
        return next(self.iter_active_listings(42))

    def get_listing_inventory(self, listing_id):
        return {
            "products": [
                {
                    "product_id": 2,
                    "property_values": [{"property_name": "Color", "value_ids": [1], "values": ["Black"]}],
                    "offerings": [{"offering_id": 3, "price": {"amount": 2500, "divisor": 100}, "quantity": 4, "is_enabled": True, "sku": "NO"}],
                }
            ],
            "listing_id": listing_id,
        }

    def get_shop_shipping_profiles(self, shop_id):
        return {
            "count": 1,
            "results": [
                {"shipping_profile_id": 7, "title": "US Standard", "user_id": 9}
            ],
        }

    def get_shipping_profile_destinations(self, shop_id, profile_id):
        return {"results": [{"shipping_profile_destination_id": 1, "destination_country_iso": "US", "primary_cost": {"amount": 495, "divisor": 100}, "min_delivery_days": 3, "max_delivery_days": 7, "user_id": 9}]}

    def iter_shipping_profile_destinations(self, shop_id, profile_id):
        return iter(
            _results(
                self.get_shipping_profile_destinations(shop_id, profile_id),
                context="Etsy shipping profile destinations",
            )
        )

    def get_shop_production_partners(self, shop_id):
        return {
            "count": 1,
            "results": [
                {
                    "production_partner_id": 4,
                    "partner_name": "Printify",
                    "location": "US",
                    "is_active": True,
                    "email": "never@example.com",
                }
            ],
        }


def test_collect_snapshot_is_sanitized_and_deterministic():
    observed = "2026-09-06T12:00:00Z"
    first = collect_snapshot(FakeEtsy(), observed_at=observed)
    second = collect_snapshot(FakeEtsy(), observed_at=observed)
    assert first == second
    encoded = json.dumps(first)
    for forbidden in ("9999", "secret", "DO_NOT_EXPORT", "NO", "never@example.com"):
        assert forbidden not in encoded
    assert first["mode"] == "read_only"
    assert first["external_account_writes"] == 0
    assert first["listings"][0]["listing_id"] == 2
    assert first["listings"][0]["inventory"][0]["offerings"][0]["price"] == {"amount": 2500, "divisor": 100}


def test_collect_snapshot_uses_listing_detail_for_live_listing_fields():
    class DetailOnlyEtsy(FakeEtsy):
        def iter_active_listings(self, shop_id):
            return iter(
                [
                    {
                        "listing_id": 2,
                        "title": "Second",
                        "state": "active",
                    }
                ]
            )

        def get_listing(self, listing_id):
            assert listing_id == 2
            return {
                "listing_id": listing_id,
                "title": "Second",
                "state": "active",
                "description": "Detail description",
                "shipping_profile_id": 7,
                "return_policy_id": 8,
                "production_partner_ids": [4],
            }

    snapshot = collect_snapshot(DetailOnlyEtsy(), observed_at="2026-09-06T12:00:00Z")

    assert snapshot["listings"] == [
        {
            "description": "Detail description",
            "inventory": [
                {
                    "offerings": [
                        {
                            "is_enabled": True,
                            "offering_id": 3,
                            "price": {"amount": 2500, "divisor": 100},
                            "quantity": 4,
                        }
                    ],
                    "product_id": 2,
                    "property_values": [
                        {
                            "property_name": "Color",
                            "value_ids": [1],
                            "values": ["Black"],
                        }
                    ],
                }
            ],
            "listing_id": 2,
            "production_partner_ids": [4],
            "return_policy_id": 8,
            "shipping_profile_id": 7,
            "state": "active",
            "title": "Second",
        }
    ]


def test_load_oauth_material_reads_etsy_env_only():
    values = {
        "ETSY_API_CREDENTIAL": "key:secret",
        "ETSY_OAUTH_ACCESS_TOKEN": "access",
        "ETSY_OAUTH_REFRESH_TOKEN": "refresh",
        "ETSY_OAUTH_EXPIRES_AT": "2026-09-06T13:00:00+00:00",
    }

    def loader(name, **kwargs):
        assert kwargs == {"source": "etsy_env"}
        return values.get(name)

    material = load_oauth_material(secret_loader=loader)
    assert material.credentials.api_key == "key:secret"
    assert material.token.refresh_token == "refresh"


def test_maybe_refresh_token_persists_rotated_tokens():
    old = EtsyOAuthToken("old-access", "old-refresh", datetime.now(UTC) - timedelta(minutes=5))
    refreshed = EtsyOAuthToken("new-access", "new-refresh", datetime.now(UTC) + timedelta(hours=1))
    calls = []

    def refresher(**kwargs):
        calls.append(kwargs)
        return refreshed

    def persister(**kwargs):
        calls.append(kwargs)

    result = maybe_refresh_token(
        old,
        client_id="key",
        composite_credential="key:secret",
        token_refresher=refresher,
        token_persister=persister,
        now=datetime.now(UTC),
    )
    assert result == refreshed
    assert calls[0]["refresh_token"] == "old-refresh"
    assert calls[1]["access_token"] == "new-access"
    assert calls[1]["refresh_token"] == "new-refresh"


def test_default_refresh_persister_updates_file_and_next_load(monkeypatch, tmp_path):
    path = tmp_path / ".etsy.env"
    monkeypatch.setattr(etsy_env, "etsy_env_path", lambda: path)
    monkeypatch.setattr(secret_config, "_repo_root", lambda: tmp_path)
    monkeypatch.chdir(tmp_path.parent)
    old = EtsyOAuthToken("old-access", "old-refresh", datetime(2020, 1, 1, tzinfo=UTC))
    refreshed = EtsyOAuthToken("new-access", "new-refresh", datetime(2030, 1, 1, tzinfo=UTC))
    result = maybe_refresh_token(
        old, client_id="key", composite_credential="key:secret",
        token_refresher=lambda **kwargs: refreshed,
    )
    assert result == refreshed
    assert load_oauth_material().token == refreshed
    assert path.stat().st_mode & 0o777 == 0o600


def test_write_snapshot_atomic_restricts_permissions(tmp_path: Path):
    target = tmp_path / "nested" / "snapshot.json"
    write_snapshot_atomic({"b": 2, "a": 1}, target)
    assert json.loads(target.read_text()) == {"a": 1, "b": 2}
    assert target.stat().st_mode & 0o777 == 0o600
    assert not list(target.parent.glob("*.tmp"))


def test_write_snapshot_atomic_preserves_existing_parent_mode(tmp_path: Path):
    parent = tmp_path / "existing"
    parent.mkdir(mode=0o755)
    parent.chmod(0o755)
    target = parent / "snapshot.json"

    write_snapshot_atomic({"ok": True}, target)

    assert parent.stat().st_mode & 0o777 == 0o755
    assert target.stat().st_mode & 0o777 == 0o600


def test_load_oauth_material_rejects_missing_values():
    with pytest.raises(ValueError, match="missing"):
        load_oauth_material(secret_loader=lambda *args, **kwargs: None)


@pytest.mark.parametrize("bad_id", [0, -1, "7", None])
def test_listing_without_positive_integer_id_fails_closed(bad_id):
    class Malformed(FakeEtsy):
        def iter_active_listings(self, shop_id):
            return iter([{"listing_id": bad_id, "title": "Bad"}])

    with pytest.raises(ValueError, match="listing_id"):
        collect_snapshot(Malformed(), observed_at="2026-09-06T12:00:00Z")


def test_shipping_profile_without_positive_integer_id_fails_closed():
    class Malformed(FakeEtsy):
        def get_shop_shipping_profiles(self, shop_id):
            return {"count": 1, "results": [{"shipping_profile_id": 0}]}

    with pytest.raises(ValueError, match="shipping_profile_id"):
        collect_snapshot(Malformed(), observed_at="2026-09-06T12:00:00Z")


def test_production_partner_without_positive_integer_id_fails_closed():
    class Malformed(FakeEtsy):
        def get_shop_production_partners(self, shop_id):
            return {"count": 1, "results": [{"production_partner_id": -1}]}

    with pytest.raises(ValueError, match="production_partner_id"):
        collect_snapshot(Malformed(), observed_at="2026-09-06T12:00:00Z")


@pytest.mark.parametrize(
    "collection, duplicate_id, message",
    [
        ("listings", 2, "duplicate Etsy listing_id"),
        ("shipping_profiles", 7, "duplicate Etsy shipping_profile_id"),
        ("production_partners", 4, "duplicate Etsy production_partner_id"),
    ],
)
def test_duplicate_live_identifiers_fail_closed(
    collection: str, duplicate_id: int, message: str
) -> None:
    class Duplicate(FakeEtsy):
        def iter_active_listings(self, shop_id):
            values = list(super().iter_active_listings(shop_id))
            return iter(values + values) if collection == "listings" else iter(values)

        def get_shop_shipping_profiles(self, shop_id):
            payload = super().get_shop_shipping_profiles(shop_id)
            return (
                {"count": 2, "results": payload["results"] + payload["results"]}
                if collection == "shipping_profiles"
                else payload
            )

        def get_shop_production_partners(self, shop_id):
            payload = super().get_shop_production_partners(shop_id)
            return (
                {"count": 2, "results": payload["results"] + payload["results"]}
                if collection == "production_partners"
                else payload
            )

    assert duplicate_id > 0
    with pytest.raises(ValueError, match=message):
        collect_snapshot(Duplicate(), observed_at="2026-09-06T12:00:00Z")


@pytest.mark.parametrize(
    "method, message",
    [
        ("get_shop_shipping_profiles", "incomplete"),
        ("get_shop_production_partners", "incomplete"),
    ],
)
def test_unpaged_shop_collections_require_count_to_match_results(
    method: str, message: str
) -> None:
    class Incomplete(FakeEtsy):
        def __getattribute__(self, name):
            if name == method:
                return lambda *args: {"count": 2, "results": []}
            return super().__getattribute__(name)

    with pytest.raises(ValueError, match=message):
        collect_snapshot(Incomplete(), observed_at="2026-09-06T12:00:00Z")


def test_duplicate_shipping_destination_id_fails_closed() -> None:
    class Duplicate(FakeEtsy):
        def iter_shipping_profile_destinations(self, shop_id, profile_id):
            destination = super().get_shipping_profile_destinations(
                shop_id, profile_id
            )["results"][0]
            return iter([destination, destination])

    with pytest.raises(
        ValueError, match="duplicate Etsy shipping_profile_destination_id"
    ):
        collect_snapshot(Duplicate(), observed_at="2026-09-06T12:00:00Z")


def test_resolve_output_path_uses_observed_date_and_refuses_existing(tmp_path: Path):
    observed = "2026-09-06T12:00:00+00:00"
    target = resolve_output_path(observed, base_dir=tmp_path)
    assert target == tmp_path / "2026-09-06" / "etsy-shop.json"
    target.parent.mkdir()
    target.write_text("existing")
    with pytest.raises(FileExistsError):
        resolve_output_path(observed, base_dir=tmp_path)
    assert resolve_output_path(observed, base_dir=tmp_path, overwrite=True) == target


@pytest.mark.parametrize(
    "method, message",
    [
        ("find_shop_by_name", "results"),
        ("get_shop_shipping_profiles", "results"),
        ("get_shipping_profile_destinations", "results"),
        ("get_shop_production_partners", "results"),
    ],
)
def test_malformed_collection_envelopes_fail_closed(method, message):
    class Malformed(FakeEtsy):
        def __getattribute__(self, name):
            if name == method:
                return lambda *args: {"results": "not-a-list"}
            return super().__getattribute__(name)

    with pytest.raises(ValueError, match=message):
        collect_snapshot(Malformed(), observed_at="2026-09-06T12:00:00Z")


def test_malformed_shop_envelope_fails_closed():
    class Malformed(FakeEtsy):
        def find_shop_by_name(self, name):
            return []

    with pytest.raises(ValueError, match="object"):
        collect_snapshot(Malformed(), observed_at="2026-09-06T12:00:00Z")


def test_malformed_inventory_envelope_and_members_fail_closed():
    class MalformedInventory(FakeEtsy):
        def get_listing_inventory(self, listing_id):
            return {"products": "not-a-list"}

    with pytest.raises(ValueError, match="products"):
        collect_snapshot(MalformedInventory(), observed_at="2026-09-06T12:00:00Z")

    class MalformedMember(FakeEtsy):
        def get_listing_inventory(self, listing_id):
            return {"products": [{"product_id": 1}, "not-an-object"]}

    with pytest.raises(ValueError, match="product"):
        collect_snapshot(MalformedMember(), observed_at="2026-09-06T12:00:00Z")
