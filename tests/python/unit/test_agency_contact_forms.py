"""Tests for the contact_forms service: routing record + scaffold/function guards."""

from __future__ import annotations

from pathlib import Path

import pytest

from packages.agency.contact_forms import (
    ContactFormsError,
    ContactFormsSetup,
    load_contact_forms_setup,
    save_contact_forms_setup,
)

REPO = Path(__file__).resolve().parents[3]
SCAFFOLD = REPO / "packages" / "web" / "scaffold" / "astro-landing"
CONTACT_FN = SCAFFOLD / "netlify" / "functions" / "contact.mjs"
INDEX = SCAFFOLD / "src" / "pages" / "index.astro"
THANKS = SCAFFOLD / "src" / "pages" / "thanks.astro"


def test_record_roundtrip_and_defaults(tmp_path: Path) -> None:
    rec = ContactFormsSetup(product_id="acme-site", notify_email="owner@acme.com")
    assert rec.sms_enabled is False and rec.crm == ""
    save_contact_forms_setup(rec, root=tmp_path / "svc")
    assert load_contact_forms_setup("acme-site", root=tmp_path / "svc") == rec


def test_load_missing_returns_none(tmp_path: Path) -> None:
    assert load_contact_forms_setup("nope", root=tmp_path / "svc") is None


def test_validate_requires_product_id() -> None:
    with pytest.raises(ContactFormsError, match="product_id"):
        ContactFormsSetup(product_id="", notify_email="a@b.com").validate()


@pytest.mark.parametrize("bad", ["", "not-an-email", "a@b"])
def test_validate_rejects_bad_email(bad: str) -> None:
    with pytest.raises(ContactFormsError, match="notify_email"):
        ContactFormsSetup(product_id="x", notify_email=bad).validate()


def test_form_to_sms_is_gated() -> None:
    with pytest.raises(ContactFormsError, match="A2P 10DLC"):
        ContactFormsSetup(product_id="x", notify_email="a@b.com", sms_enabled=True).validate()


def test_legacy_dict_loads_with_defaults() -> None:
    rec = ContactFormsSetup.from_dict({"product_id": "x", "notify_email": "a@b.com"})
    assert rec.sms_enabled is False and rec.crm == ""


def test_contact_function_contract() -> None:
    text = CONTACT_FN.read_text(encoding="utf-8")
    assert 'getStore("inbound-leads")' in text
    assert 'field("bot-field")' in text
    assert 'redirect(req, "/thanks/")' in text
    for key in ("name", "contact", "message", "source", "submission_id"):
        assert key in text


def test_scaffold_form_posts_to_function() -> None:
    text = INDEX.read_text(encoding="utf-8")
    assert 'action="/.netlify/functions/contact"' in text
    assert 'method="POST"' in text
    assert 'name="bot-field"' in text
    assert 'name="contact"' in text


def test_thanks_page_exists() -> None:
    assert THANKS.is_file()
