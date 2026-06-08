"""Tests for the web deploy seam + Netlify adapter (F4).

Offline: a single ``httpx.MockTransport`` stands in for the Netlify API, so we
exercise site creation, zip deploy (preview vs production), custom-domain, and
ownership-transfer (the handoff hook) without network or a token.
"""

from __future__ import annotations

import hashlib
import json
import zipfile
from io import BytesIO
from pathlib import Path

import httpx
import pytest

from packages.web.deploy import (
    DeployAccount,
    DeployError,
    DeployTarget,
    NetlifyDeployTarget,
    SiteRef,
    zip_dist,
)


def _make_target(handler) -> NetlifyDeployTarget:
    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport, base_url="https://api.netlify.com/api/v1")
    return NetlifyDeployTarget(token="test-token", client=client)


def test_adapter_satisfies_protocol() -> None:
    assert isinstance(NetlifyDeployTarget(token="t"), DeployTarget)


def test_missing_token_raises() -> None:
    target = NetlifyDeployTarget(token=None)
    with pytest.raises(DeployError):
        target.ensure_site("acme")


def test_zip_dist_packs_files(tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("<h1>hi</h1>", encoding="utf-8")
    (dist / "assets" / "app.css").write_text("body{}", encoding="utf-8")
    data = zip_dist(dist)
    names = set(zipfile.ZipFile(BytesIO(data)).namelist())
    assert names == {"index.html", "assets/app.css"}


def test_ensure_site_reuses_existing() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/sites")
        return httpx.Response(
            200, json=[{"id": "s1", "name": "acme", "ssl_url": "https://acme.netlify.app"}]
        )

    site = _make_target(handler).ensure_site("acme")
    assert site.site_id == "s1"
    assert site.url == "https://acme.netlify.app"


def test_ensure_site_creates_when_absent_under_account() -> None:
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "GET":
            return httpx.Response(200, json=[])
        seen["path"] = request.url.path
        seen["body"] = json.loads(request.content)
        return httpx.Response(201, json={"id": "s2", "name": "acme", "account_slug": "team_x"})

    target = NetlifyDeployTarget(
        token="t",
        account=DeployAccount(id="team_x", name="Team X"),
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    site = target.ensure_site("acme")
    assert site.site_id == "s2"
    assert seen["path"].endswith("/team_x/sites")  # created under the account
    assert seen["body"] == {"name": "acme"}


def test_preview_deploy_marks_draft_in_digest(tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<h1>hi</h1>", encoding="utf-8")
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content)
        # required empty => no file upload round-trip needed
        return httpx.Response(
            200,
            json={"id": "d1", "deploy_ssl_url": "https://d1--acme.netlify.app",
                  "state": "ready", "required": []},
        )

    result = _make_target(handler).deploy(SiteRef("s1", "acme"), dist, production=False)
    assert result.production is False
    assert captured["body"].get("draft") is True       # preview = draft (in body, not query)
    assert "/index.html" in captured["body"]["files"]   # digest method declares paths
    assert result.url == "https://d1--acme.netlify.app"  # draft → deploy-specific URL


def test_production_deploy_has_no_draft_flag(tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<h1>hi</h1>", encoding="utf-8")
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content)
        return httpx.Response(
            200, json={"id": "d2", "ssl_url": "https://acme.netlify.app",
                       "state": "ready", "required": []}
        )

    result = _make_target(handler).deploy(SiteRef("s1", "acme"), dist, production=True)
    assert result.production is True
    assert "draft" not in captured["body"]
    assert result.url == "https://acme.netlify.app"     # production → site URL


def test_deploy_uploads_only_required_files(tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<h1>hi</h1>", encoding="utf-8")
    sha = hashlib.sha1(b"<h1>hi</h1>").hexdigest()
    uploaded = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST" and request.url.path.endswith("/deploys"):
            return httpx.Response(200, json={"id": "d3", "ssl_url": "https://acme.netlify.app",
                                             "state": "uploading", "required": [sha]})
        if request.method == "PUT":
            uploaded.append(request.url.path)
            assert request.headers.get("content-type") == "application/octet-stream"
            return httpx.Response(200, json={"id": "f1"})
        return httpx.Response(404)

    _make_target(handler).deploy(SiteRef("s1", "acme"), dist, production=True)
    assert uploaded == ["/api/v1/deploys/d3/files/index.html"]


def test_set_custom_domain_patches_site() -> None:
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["method"] = request.method
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json={"id": "s1", "name": "acme", "custom_domain": "acme.com",
                                         "ssl_url": "https://acme.com"})

    site = _make_target(handler).set_custom_domain(SiteRef("s1", "acme"), "acme.com")
    assert captured["method"] == "PATCH"
    assert captured["body"] == {"custom_domain": "acme.com"}
    assert site.url == "https://acme.com"


def test_transfer_ownership_moves_account() -> None:
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json={"id": "s1", "name": "acme", "account_slug": "client_co"})

    site = _make_target(handler).transfer_ownership(
        SiteRef("s1", "acme"), DeployAccount("client_co")
    )
    assert captured["body"] == {"account_slug": "client_co"}
    assert site.account_id == "client_co"


def test_attach_domain_merges_aliases_www_primary() -> None:
    """www-as-primary + apex alias; GET-merge-PATCH must not clobber existing aliases."""
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "GET":
            # Site already has an unrelated alias that must survive the merge.
            return httpx.Response(200, json={"id": "s1", "domain_aliases": ["old.acme.com"]})
        captured["body"] = json.loads(request.content)
        return httpx.Response(
            200, json={"id": "s1", "name": "acme", "ssl_url": "https://www.acme.com"}
        )

    site = _make_target(handler).attach_domain(
        SiteRef("s1", "acme"), "www.acme.com", aliases=("acme.com",)
    )
    assert captured["body"]["custom_domain"] == "www.acme.com"
    # apex + the pre-existing alias are both present; primary isn't duplicated.
    assert captured["body"]["domain_aliases"] == ["acme.com", "old.acme.com"]
    assert site.url == "https://www.acme.com"


def test_provision_and_get_ssl() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/ssl")
        return httpx.Response(
            200,
            json={
                "state": "issued",
                "domains": ["acme.com", "www.acme.com"],
                "expires_at": "2026-09-01",
            },
        )

    target = _make_target(handler)
    cert = target.provision_ssl(SiteRef("s1", "acme"))
    assert cert.issued
    assert cert.covers("www.acme.com") and cert.covers("ACME.COM")
    assert target.get_ssl(SiteRef("s1", "acme")).expires_at == "2026-09-01"


def test_ssl_pending_is_not_issued() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"state": "pending", "domains": []})

    assert not _make_target(handler).get_ssl(SiteRef("s1", "acme")).issued


def test_http_error_becomes_deploy_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, text="unauthorized")

    with pytest.raises(DeployError):
        _make_target(handler).ensure_site("acme")
