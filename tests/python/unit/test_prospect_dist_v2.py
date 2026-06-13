"""Prospect deploy policy: dist-v2 required, no silent dist/ fallback."""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest

from packages.agency.prospect_site import (
    PREVIEW_SITE_NAME,
    ProspectBuildError,
    deploy_preview_dist,
    resolve_prospect_dist_dir,
)
from packages.web.deploy import NetlifyDeployTarget

RECORD = {
    "place_id": "ChIJtest123",
    "display_name": "Joe's Plumbing",
    "genre_id": "plumber",
    "city_id": "oklahoma_city",
    "formatted_address": "100 Main St, Oklahoma City, OK 73119, USA",
    "phone": "+1 405-555-0100",
    "rating": 4.8,
    "user_ratings_total": 57,
    "web_verify_verdict": "none_found",
}


def test_resolve_prefers_dist_v2(tmp_path: Path) -> None:
    site = tmp_path / "place"
    (site / "dist-v2").mkdir(parents=True)
    (site / "dist-v2" / "index.html").write_text("<html></html>")
    (site / "dist").mkdir(parents=True)
    (site / "dist" / "index.html").write_text("<html>legacy</html>")
    assert resolve_prospect_dist_dir(site) == site / "dist-v2"


def test_resolve_rejects_legacy_dist_only(tmp_path: Path) -> None:
    site = tmp_path / "place"
    (site / "dist").mkdir(parents=True)
    (site / "dist" / "index.html").write_text("<html>legacy</html>")
    with pytest.raises(ProspectBuildError, match="playbook"):
        resolve_prospect_dist_dir(site)


def test_resolve_missing_build(tmp_path: Path) -> None:
    with pytest.raises(ProspectBuildError, match="playbook"):
        resolve_prospect_dist_dir(tmp_path / "empty")


def test_deploy_preview_dist_draft(tmp_path: Path) -> None:
    dist = tmp_path / "dist-v2"
    dist.mkdir()
    (dist / "index.html").write_text("<!doctype html><title>Joe</title>")

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "GET" and request.url.path.endswith("/sites"):
            return httpx.Response(200, json=[])
        if request.method == "POST" and request.url.path.endswith("/sites"):
            return httpx.Response(201, json={"id": "site_shared", "name": PREVIEW_SITE_NAME})
        if request.method == "POST" and "/deploys" in request.url.path:
            import json

            body = json.loads(request.content)
            assert body.get("draft") is True
            return httpx.Response(
                200,
                json={
                    "id": "dep_v2",
                    "state": "ready",
                    "deploy_ssl_url": "https://dep_v2--better-business-web-previews.netlify.app",
                },
            )
        return httpx.Response(404)

    client = httpx.Client(transport=httpx.MockTransport(handler), base_url="https://api.netlify.com/api/v1")
    target = NetlifyDeployTarget(token="test-token", client=client)
    result = deploy_preview_dist(RECORD, dist, target=target)
    assert result.deployed is True
    assert result.mockup_url == "https://dep_v2--better-business-web-previews.netlify.app"
    assert result.dist_dir == dist
