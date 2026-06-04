"""Tests for the inbound status field + _record_id collision guard (G2 [+G2-STATUS]/[+G2-REC])."""

from __future__ import annotations

from pathlib import Path

import pytest

from packages.agency.inbound import (
    InboundReviewRepository,
    ReviewStatus,
    WebsiteReviewRequest,
)


def _req(**kw) -> WebsiteReviewRequest:
    base = dict(submission_id="abc-123", name="Jo", contact="jo@example.com")
    base.update(kw)
    return WebsiteReviewRequest(**base)


def test_status_defaults_to_new() -> None:
    assert _req().status is ReviewStatus.NEW
    assert _req().processed_at == ""
    assert _req().notified_at == ""


def test_legacy_record_without_status_loads_as_new() -> None:
    # A record written before the new fields existed (e.g. the JS function payload).
    legacy = {
        "submission_id": "old-1",
        "name": "Pat",
        "contact": "pat@example.com",
        "business": "Pat Co",
        "website": "patco.com",
        "received_at": "2026-06-01T00:00:00Z",
        "source": "netlify-function",
    }
    loaded = WebsiteReviewRequest.from_dict(legacy)
    assert loaded.status is ReviewStatus.NEW
    assert loaded.processed_at == ""
    assert loaded.notified_at == ""


def test_garbage_status_coerces_to_new_not_raises() -> None:
    payload = _req().to_dict()
    payload["status"] = "not-a-real-status"
    assert WebsiteReviewRequest.from_dict(payload).status is ReviewStatus.NEW


def test_status_roundtrips() -> None:
    r = _req(status=ReviewStatus.PREVIEWED, processed_at="2026-06-04T00:00:00Z")
    assert WebsiteReviewRequest.from_dict(r.to_dict()) == r
    assert r.to_dict()["status"] == "previewed"


def test_record_id_collision_is_refused(tmp_path: Path) -> None:
    repo = InboundReviewRepository(root=tmp_path / "inbound")
    # Both sanitize to the same on-disk stem ("a_b") but are distinct leads.
    repo.save(_req(submission_id="a:b"))
    with pytest.raises(ValueError, match="collision"):
        repo.save(_req(submission_id="a/b", name="Other"))


def test_same_submission_id_update_is_allowed(tmp_path: Path) -> None:
    repo = InboundReviewRepository(root=tmp_path / "inbound")
    repo.save(_req(submission_id="a:b"))
    repo.save(_req(submission_id="a:b", status=ReviewStatus.GUARDED))  # idempotent update
    assert repo.get("a:b").status is ReviewStatus.GUARDED
