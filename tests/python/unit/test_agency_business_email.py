"""Tests for business-email setup (G5)."""

from __future__ import annotations

from pathlib import Path

import pytest

from packages.agency.business_email import (
    BusinessEmailSetup,
    derive_domain,
    emit_business_email_runbook,
    load_business_email_setup,
    render_business_email_runbook,
    save_business_email_setup,
)


@pytest.mark.parametrize(
    "url,expected",
    [
        ("https://www.joesplumbing.com/", "joesplumbing.com"),
        ("http://joesplumbing.com", "joesplumbing.com"),
        ("joesplumbing.com", "joesplumbing.com"),
    ],
)
def test_derive_domain(url: str, expected: str) -> None:
    assert derive_domain(url) == expected


def test_runbook_lists_aliases_and_steps() -> None:
    md = render_business_email_runbook("Joe's Plumbing", "joesplumbing.com")
    assert "info@joesplumbing.com" in md
    assert "support@joesplumbing.com" in md
    assert "sales@joesplumbing.com" in md
    assert "MX" in md
    assert "Verify the domain" in md


def test_emit_writes_runbook(tmp_path: Path) -> None:
    path = emit_business_email_runbook("Joe's Plumbing", tmp_path / "joes", domain="joe.com")
    assert path == tmp_path / "joes" / "BUSINESS_EMAIL.md"
    assert "Business Email Setup — Joe's Plumbing" in path.read_text(encoding="utf-8")


def test_completion_record_roundtrip(tmp_path: Path) -> None:
    record = BusinessEmailSetup(
        product_id="joes-plumbing-site", domain="joe.com", verified=True, mx_configured=True,
        completed_at="2026-06-04T00:00:00Z",
    )
    save_business_email_setup(record, root=tmp_path / "svc")
    loaded = load_business_email_setup("joes-plumbing-site", root=tmp_path / "svc")
    assert loaded == record


def test_load_missing_returns_none(tmp_path: Path) -> None:
    assert load_business_email_setup("nope", root=tmp_path / "svc") is None


def test_record_validate_requires_domain() -> None:
    with pytest.raises(ValueError):
        BusinessEmailSetup(product_id="x", domain="").validate()
