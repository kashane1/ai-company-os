from __future__ import annotations

from pathlib import Path

import pytest

from packages.agency import suppression
from packages.agency.outreach_store import OutreachStore


def _store(tmp_path: Path) -> OutreachStore:
    return OutreachStore(sqlite_path=tmp_path / "outreach.sqlite3")


def _record(**over: object) -> dict[str, object]:
    base = {
        "place_id": "p1",
        "contact_email": "Owner@Shop.com",
        "phone": "(503) 555-0000",
        "contact_instagram": "https://instagram.com/JoeAuto",
        "contact_facebook": "@JoeAutoFB",
    }
    base.update(over)
    return base


def test_keys_for_record_normalizes_every_handle() -> None:
    keys = dict(suppression.keys_for_record(_record()))
    assert keys["place_id"] == "place:p1"
    assert keys["email"] == "email:owner@shop.com"  # lowercased
    assert keys["phone"] == "phone:5035550000"  # digits, normalized
    assert keys["instagram"] == "instagram:joeauto"  # url + @ stripped
    assert keys["facebook"] == "facebook:joeautofb"


def test_is_suppressed_matches_by_place_id(tmp_path: Path) -> None:
    store = _store(tmp_path)
    assert suppression.is_suppressed(_record(), store=store) is False
    store.suppress_key("place:p1", "place_id", "operator call", "operator")
    assert suppression.is_suppressed(_record(), store=store) is True


def test_is_suppressed_matches_by_any_handle(tmp_path: Path) -> None:
    store = _store(tmp_path)
    # Same email surfaces under a different place_id after a re-scan; still caught.
    suppression.suppress(_record(), "unsubscribed", "reply_stop", store=store)
    moved = _record(place_id="p2", phone="", contact_instagram="", contact_facebook="")
    assert suppression.is_suppressed(moved, store=store) is True


def test_is_suppressed_fail_closed_on_empty_record(tmp_path: Path) -> None:
    store = _store(tmp_path)
    empty = {"place_id": "", "contact_email": "", "phone": ""}
    assert suppression.is_suppressed(empty, store=store) is True


def test_is_suppressed_fail_closed_on_store_error() -> None:
    class Boom:
        def suppressed_keys(self) -> set[str]:
            raise RuntimeError("registry down")

    assert suppression.is_suppressed(_record(), store=Boom()) is True


def test_suppress_writes_all_keys(tmp_path: Path) -> None:
    store = _store(tmp_path)
    written = suppression.suppress(_record(), "disqualified", "disqualified", store=store)
    assert len(written) == 5  # place + 4 handles
    assert store.suppressed_keys() == {
        "place:p1",
        "email:owner@shop.com",
        "phone:5035550000",
        "instagram:joeauto",
        "facebook:joeautofb",
    }


def test_suppress_single_handle(tmp_path: Path) -> None:
    store = _store(tmp_path)
    suppression.suppress(("email", "Foo@Bar.com"), "stop", "reply_stop", store=store)
    assert store.is_key_suppressed("email:foo@bar.com") is True
    with pytest.raises(ValueError):
        suppression.suppress(("email", "   "), "x", "operator", store=store)


def test_suppression_reason(tmp_path: Path) -> None:
    store = _store(tmp_path)
    assert suppression.suppression_reason(_record(), store=store) is None
    store.suppress_key("place:p1", "place_id", "owner asked to stop", "operator")
    assert suppression.suppression_reason(_record(), store=store) == "owner asked to stop"
