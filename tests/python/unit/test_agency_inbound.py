"""Tests for the typed inbound website-review capture (todo 068)."""

from __future__ import annotations

from pathlib import Path

import pytest

from packages.agency.inbound import InboundReviewRepository, WebsiteReviewRequest


def _req(**kw) -> WebsiteReviewRequest:
    base = dict(
        submission_id="netlify:abc-123",
        name="Jo Owner",
        contact="jo@example.com",
        business="Jo's Plumbing",
        website="joesplumbing.com",
        received_at="2026-06-02T00:00:00Z",
    )
    base.update(kw)
    return WebsiteReviewRequest(**base)


def test_roundtrip_to_from_dict() -> None:
    r = _req()
    assert WebsiteReviewRequest.from_dict(r.to_dict()) == r


def test_validate_requires_name_and_contact() -> None:
    with pytest.raises(ValueError):
        _req(name=" ").validate()
    with pytest.raises(ValueError):
        _req(contact="").validate()
    with pytest.raises(ValueError):
        _req(submission_id="").validate()


def test_repository_save_and_list(tmp_path: Path) -> None:
    repo = InboundReviewRepository(root=tmp_path / "inbound")
    repo.save(_req(submission_id="netlify:abc-123"))
    repo.save(_req(submission_id="netlify:def-456", name="Sam"))
    assert repo.exists("netlify:abc-123")
    loaded = {r.submission_id: r for r in repo.list()}
    assert set(loaded) == {"netlify:abc-123", "netlify:def-456"}
    assert loaded["netlify:def-456"].name == "Sam"
    # id is filesystem-sanitised (no stray colon files)
    assert repo.get("netlify:abc-123").business == "Jo's Plumbing"


def test_save_rejects_invalid(tmp_path: Path) -> None:
    repo = InboundReviewRepository(root=tmp_path / "inbound")
    with pytest.raises(ValueError):
        repo.save(_req(name=""))
