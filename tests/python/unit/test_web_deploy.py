"""Tests for the web deploy seam + Netlify adapter (F4).

Offline: a single ``httpx.MockTransport`` stands in for the Netlify API, so we
exercise site creation, zip deploy (preview vs production), custom-domain, and
ownership-transfer (the handoff hook) without network or a token.
"""

from __future__ import annotations

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


def test_preview_deploy_sends_draft(tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<h1>hi</h1>", encoding="utf-8")
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["query"] = dict(request.url.params)
        captured["ctype"] = request.headers.get("content-type")
        return httpx.Response(
            200,
            json={"id": "d1", "ssl_url": "https://draft--acme.netlify.app", "state": "ready"},
        )

    result = _make_target(handler).deploy(SiteRef("s1", "acme"), dist, production=False)
    assert result.production is False
    assert captured["query"].get("draft") == "true"   # preview = draft
    assert captured["ctype"] == "application/zip"
    assert result.url.startswith("https://")


def test_production_deploy_has_no_draft_flag(tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<h1>hi</h1>", encoding="utf-8")
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["query"] = dict(request.url.params)
        return httpx.Response(
            200, json={"id": "d2", "ssl_url": "https://acme.netlify.app", "state": "ready"}
        )

    result = _make_target(handler).deploy(SiteRef("s1", "acme"), dist, production=True)
    assert result.production is True
    assert "draft" not in captured["query"]


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


def test_http_error_becomes_deploy_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, text="unauthorized")

    with pytest.raises(DeployError):
        _make_target(handler).ensure_site("acme")
