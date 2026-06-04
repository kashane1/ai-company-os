"""Tests for the dist/ secret-leak scan that gates deploys (todo 075)."""

from __future__ import annotations

from pathlib import Path

import pytest

from packages.web.deploy import (
    NetlifyDeployTarget,
    SecretLeakError,
    SiteRef,
    assert_no_secret_leak,
    scan_dist_for_secrets,
)


def _dist(tmp_path: Path, files: dict[str, str]) -> Path:
    dist = tmp_path / "dist"
    for rel, content in files.items():
        path = dist / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    return dist


def test_clean_dist_passes(tmp_path: Path) -> None:
    dist = _dist(
        tmp_path,
        {
            "index.html": "<html><body>Hello, small business!</body></html>",
            "assets/app.js": "const x = 1; // nothing secret here",
            # Google Maps demo key is intentionally client-side — must NOT trip.
            "map.js": "const k='AIzaSyD-1234567890abcdefghijklmnopqrstu';",
        },
    )
    assert scan_dist_for_secrets(dist) == []
    assert_no_secret_leak(dist)  # does not raise


def test_planted_resend_key_is_caught(tmp_path: Path) -> None:
    dist = _dist(tmp_path, {"functions/leak.js": "const k='re_0123456789abcdefABCDEF';"})
    findings = scan_dist_for_secrets(dist)
    assert findings and "resend_api_key" in findings[0]
    with pytest.raises(SecretLeakError):
        assert_no_secret_leak(dist)


@pytest.mark.parametrize(
    "secret",
    [
        "sk_live_abcd1234efgh5678",
        "whsec_abcd1234efgh5678",
        "https://hooks.slack.com/services/T000/B000/xyz",
        "AKIAIOSFODNN7EXAMPLE",
    ],
)
def test_various_secret_shapes_caught(tmp_path: Path, secret: str) -> None:
    dist = _dist(tmp_path, {"index.html": f"<!-- {secret} -->"})
    assert scan_dist_for_secrets(dist)


def test_deploy_refuses_to_ship_a_leak(tmp_path: Path) -> None:
    dist = _dist(tmp_path, {"index.html": "<p>re_0123456789abcdefABCDEF</p>"})
    target = NetlifyDeployTarget(token="t")
    site = SiteRef(site_id="s1", name="bbw")
    # Must fail closed BEFORE any network call.
    with pytest.raises(SecretLeakError):
        target.deploy(site, dist)
