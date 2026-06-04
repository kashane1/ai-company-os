"""Tests for the forwarded-Stripe-event receiver handler (G1)."""

from __future__ import annotations

import json
from pathlib import Path

from packages.agency.stripe_receiver import handle_forwarded_event, verify_forward_secret

SECRET = "shhh-forward-secret"


def _registry(path: Path) -> None:
    path.write_text(
        json.dumps(
            [
                {
                    "id": "joes-plumbing-site",
                    "name": "Joe's Plumbing",
                    "slug": "joes-plumbing",
                    "type": "client-site",
                    "platform": "web",
                    "source_path": "products/joes-plumbing-site",
                    "docs_root": "docs/products/joes-plumbing-site",
                    "client": {
                        "bundle": "package_c",
                        "services": ["website"],
                        "billing_status": "trial",
                    },
                }
            ]
        ),
        encoding="utf-8",
    )


def _event(product_id: str = "joes-plumbing-site") -> str:
    return json.dumps(
        {
            "id": "evt_1",
            "type": "invoice.paid",
            "created": 1000,
            "livemode": False,
            "data": {"object": {"id": "in_1", "customer": "cus_1", "subscription": "sub_1",
                                "metadata": {"product_id": product_id, "bundle": "package_c"}}},
        }
    )


def _handle(body, tmp_path, secret=SECRET, provided=SECRET):
    return handle_forwarded_event(
        provided_secret=provided,
        raw_body=body,
        expected_secret=secret,
        billing_root=tmp_path / "billing",
        registry_path=tmp_path / "products.json",
    )


def test_verify_forward_secret_constant_time() -> None:
    assert verify_forward_secret("a", "a") is True
    assert verify_forward_secret("a", "b") is False
    assert verify_forward_secret("a", "") is False  # empty expected never matches


def test_not_configured_returns_503(tmp_path: Path) -> None:
    res = _handle(_event(), tmp_path, secret="")
    assert res.status_code == 503


def test_bad_secret_returns_401(tmp_path: Path) -> None:
    res = _handle(_event(), tmp_path, provided="wrong")
    assert res.status_code == 401


def test_bad_json_returns_400(tmp_path: Path) -> None:
    res = _handle("not json{", tmp_path)
    assert res.status_code == 400


def test_valid_event_reconciles_200(tmp_path: Path) -> None:
    _registry(tmp_path / "products.json")
    res = _handle(_event(), tmp_path)
    assert res.status_code == 200
    assert res.body["reconciled"] is True
    assert res.body["status"] == "active"


def test_unknown_product_dead_letters_200(tmp_path: Path) -> None:
    _registry(tmp_path / "products.json")
    res = _handle(_event(product_id="ghost"), tmp_path)
    assert res.status_code == 200
    assert res.body["dead_lettered"] is True
    assert (tmp_path / "billing" / "dead-letter" / "evt_1.json").exists()


def test_missing_metadata_returns_422(tmp_path: Path) -> None:
    _registry(tmp_path / "products.json")
    body = json.dumps({"id": "evt_2", "type": "invoice.paid", "created": 1,
                       "data": {"object": {"id": "in_1", "metadata": {}}}})
    res = _handle(body, tmp_path)
    assert res.status_code == 422
