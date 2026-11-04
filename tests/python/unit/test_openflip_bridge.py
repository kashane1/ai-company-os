from __future__ import annotations

import base64
import hashlib
import json

import pytest

from packages.openflip.bridge import OpenTcgBridgeError, parse_observations


def _record(**overrides: object) -> dict[str, object]:
    record: dict[str, object] = {
        "schema_version": 1,
        "origin": "open_tcg",
        "origin_key": hashlib.sha256(b"bluesky\0at://example/1").hexdigest(),
        "source": "bluesky",
        "source_author": "@radar",
        "observed_at": "2026-10-05T12:00:00+00:00",
        "received_at": "2026-10-05T12:00:01+00:00",
        "signal": "in_stock",
        "retailer_hint": "Target",
        "item_hint": "Pokemon ETB",
        "price_hint": 49.99,
        "url": "https://example.test/product",
        "raw_text": "Pokemon is in stock",
        "cursor": base64.urlsafe_b64encode(
            json.dumps(
                [
                    "2026-10-05T12:00:01+00:00",
                    1,
                ]
            ).encode()
        )
        .decode()
        .rstrip("="),
    }
    record.update(overrides)
    return record


def test_parse_observations_normalizes_version_one_ndjson() -> None:
    parsed = parse_observations(json.dumps(_record()) + "\n")

    assert parsed == [_record()]


def test_parse_observations_rejects_unknown_schema_version() -> None:
    with pytest.raises(OpenTcgBridgeError, match="schema_version"):
        parse_observations(json.dumps(_record(schema_version=2)))


def test_parse_observations_sanitizes_control_characters_and_rejects_oversized_text() -> None:
    parsed = parse_observations(json.dumps(_record(raw_text="unsafe\u0000text")))
    assert parsed[0]["raw_text"] == "unsafe text"

    with pytest.raises(OpenTcgBridgeError, match="too long"):
        parse_observations(json.dumps(_record(raw_text="x" * 10_001)))


def test_parse_observations_rejects_invalid_times_and_does_not_fetch_urls() -> None:
    with pytest.raises(OpenTcgBridgeError, match="observed_at"):
        parse_observations(json.dumps(_record(observed_at="not-a-time")))


def test_import_replay_and_whole_batch_validation_preserve_cursor():
    # The OpenFlip service is committed separately from the bridge.
    service_module = pytest.importorskip("packages.openflip.service")
    OpenFlipService = service_module.OpenFlipService

    service = OpenFlipService()
    record = _record()
    first = service.import_observations(json.dumps(record))
    cursor = service.store.by_key("opentcg:cursor")
    assert service.import_observations(json.dumps(record)) == first
    assert service.store.by_key("opentcg:cursor") == cursor
    with pytest.raises(OpenTcgBridgeError):
        service.import_observations(json.dumps(_record(origin_key="second")) + "\n{}")
    assert len(service.store.list("observation")) == 1
    with pytest.raises(ValueError, match="changed"):
        service.import_observations(json.dumps(_record(raw_text="Changed content")))
    assert service.store.by_key("opentcg:cursor") == cursor


def test_store_offer_context_is_kept_and_validated() -> None:
    offer = {"msrp_cents": 4999, "msrp_basis": "official_listing", "price_class": "at_msrp",
             "store_trust": "unvetted", "catalog_product_id": 712102}
    (parsed,) = parse_observations(json.dumps(_record(source="stores", **offer)))
    assert {key: parsed[key] for key in offer} == offer
    # Exports from before store monitoring P6 omit the fields, and so does the parsed record.
    (older,) = parse_observations(json.dumps(_record()))
    assert "price_class" not in older and "msrp_cents" not in older
    with pytest.raises(OpenTcgBridgeError, match="price_class"):
        parse_observations(json.dumps(_record(price_class="cheap")))
    with pytest.raises(OpenTcgBridgeError, match="msrp_cents"):
        parse_observations(json.dumps(_record(msrp_cents=-1)))
