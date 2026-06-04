"""Tests for inbound lead fulfilment (G2b)."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from packages.agency.inbound import (
    InboundReviewRepository,
    ReviewStatus,
    WebsiteReviewRequest,
)
from packages.agency.inbound_fulfillment import process_inbound_review
from packages.policies.url_guard import FetchedPage, UnsafeUrlError

FIXED = lambda: datetime(2026, 6, 4, 12, 0, tzinfo=timezone.utc)  # noqa: E731


def _repo(tmp_path: Path) -> InboundReviewRepository:
    return InboundReviewRepository(root=tmp_path / "inbound")


def _save(repo: InboundReviewRepository, **kw) -> str:
    base = dict(submission_id="lead-1", name="Jo", contact="jo@example.com")
    base.update(kw)
    repo.save(WebsiteReviewRequest(**base))
    return base["submission_id"]


def _ok_fetcher(url, **kw):
    return FetchedPage(
        final_url=url, status=200, bytes_read=42, text="<html>ok</html>", redirects=0
    )


def test_no_website_skips_audit(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    sid = _save(repo, website="none")
    called = {"n": 0}

    def fetcher(url, **kw):
        called["n"] += 1
        return _ok_fetcher(url)

    result = process_inbound_review(sid, repo=repo, fetcher=fetcher, clock=FIXED)
    assert called["n"] == 0
    assert result.audit.attempted is False
    assert result.status is ReviewStatus.GUARDED
    assert repo.get(sid).processed_at == "2026-06-04T12:00:00+00:00"


def test_website_audited_with_fake_fetcher(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    sid = _save(repo, website="joesplumbing.com")
    seen = {}

    def fetcher(url, **kw):
        seen["url"] = url
        return _ok_fetcher(url)

    result = process_inbound_review(sid, repo=repo, fetcher=fetcher, clock=FIXED)
    assert seen["url"] == "https://joesplumbing.com"  # schemeless → one https:// attempt
    assert result.audit.ok is True
    assert result.audit.status_code == 200
    assert result.status is ReviewStatus.GUARDED  # no city/genre → preview deferred


def test_ssrf_refusal_is_non_fatal(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    sid = _save(repo, website="http://169.254.169.254/")

    def fetcher(url, **kw):
        raise UnsafeUrlError("non-public address")

    result = process_inbound_review(sid, repo=repo, fetcher=fetcher, clock=FIXED)
    assert result.audit.attempted is True
    assert result.audit.ok is False
    assert "non-public" in result.audit.error
    assert result.status is ReviewStatus.GUARDED  # audited (refused), not crashed


def test_preview_built_when_city_and_genre_given(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    sid = _save(repo, website="none", business="Jo's Plumbing")
    built = {}

    def fake_builder(request, *, city, genre, out_dir):
        built["city"], built["genre"] = city, genre
        out_dir.mkdir(parents=True, exist_ok=True)
        index = out_dir / "index.html"
        index.write_text("<html>preview</html>", encoding="utf-8")
        return index

    result = process_inbound_review(
        sid, city="Austin, TX", genre="plumber", repo=repo,
        fetcher=_ok_fetcher, preview_builder=fake_builder, out_root=tmp_path / "prev", clock=FIXED,
    )
    assert built == {"city": "Austin, TX", "genre": "plumber"}
    assert result.status is ReviewStatus.PREVIEWED
    assert result.preview_path.endswith("index.html")
    assert repo.get(sid).status is ReviewStatus.PREVIEWED


def test_preview_error_falls_back_to_guarded(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    sid = _save(repo, website="none")

    def bad_builder(request, *, city, genre, out_dir):
        raise ValueError("intake: city is required")

    result = process_inbound_review(
        sid, city="x", genre="y", repo=repo, fetcher=_ok_fetcher,
        preview_builder=bad_builder, out_root=tmp_path / "prev", clock=FIXED,
    )
    assert result.status is ReviewStatus.GUARDED
    assert "city is required" in result.preview_error


def test_idempotent_noop_unless_force(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    sid = _save(repo, website="x.com", status=ReviewStatus.PREVIEWED)
    calls = {"n": 0}

    def fetcher(url, **kw):
        calls["n"] += 1
        return _ok_fetcher(url)

    noop = process_inbound_review(sid, repo=repo, fetcher=fetcher, clock=FIXED)
    assert calls["n"] == 0
    assert "already processed" in noop.detail

    forced = process_inbound_review(sid, repo=repo, fetcher=fetcher, force=True, clock=FIXED)
    assert calls["n"] == 1
    assert forced.detail == "forced re-run"


def test_missing_id_raises_filenotfound(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    with pytest.raises(FileNotFoundError):
        process_inbound_review("does-not-exist", repo=repo, clock=FIXED)
