"""Tests for post-cutover domain verification, fully offline.

A MockTransport plays both Google and Cloudflare DoH (and the HTTPS liveness
probe). We assert the three states — ok / fail / propagating — and especially the
email-preservation safety check.
"""

from __future__ import annotations

import httpx

from packages.agency.domain_verify import FAIL, PROPAGATING, DomainVerifier

_RTYPE_NAME = {1: "A", 5: "CNAME", 15: "MX", 16: "TXT"}


def _verifier(
    google: dict[tuple[str, str], list[str]],
    cloudflare: dict[tuple[str, str], list[str]] | None = None,
    *,
    https_status: int | None = 200,
) -> DomainVerifier:
    """google/cloudflare are {(name, rtype): [data]} zones. None cf = mirror google."""
    cf = google if cloudflare is None else cloudflare

    def handler(request: httpx.Request) -> httpx.Response:
        host = request.url.host
        if host in ("www.example.test", "example.test", "acme.com", "www.acme.com"):
            if https_status is None:
                raise httpx.ConnectError("refused")
            return httpx.Response(https_status)
        zone = google if host == "dns.google" else cf
        name = request.url.params.get("name", "").rstrip(".").lower()
        rtype = _RTYPE_NAME[int(request.url.params.get("type", "1"))]
        answers = [
            {"name": name, "type": int(request.url.params["type"]), "TTL": 300, "data": d}
            for d in zone.get((name, rtype), [])
        ]
        return httpx.Response(200, json={"Status": 0, "Answer": answers})

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport, follow_redirects=True)
    return DomainVerifier(client=client)


def test_verify_all_ok_with_email_preserved() -> None:
    zone = {
        ("acme.com", "A"): ["75.2.60.5"],
        ("www.acme.com", "CNAME"): ["acme.netlify.app."],
        ("acme.com", "MX"): ["1 smtp.google.com."],
        ("acme.com", "TXT"): ['v=spf1 include:_spf.google.com ~all'],
    }
    result = _verifier(zone).verify(
        "acme.com", netlify_site="acme.netlify.app", expected_email_host="Google Workspace"
    )
    assert result.ok
    assert {c.name for c in result.checks} >= {
        "apex_points_to_netlify",
        "www_points_to_netlify",
        "email_mx_preserved",
        "spf_preserved",
        "https_serving",
    }


def test_verify_detects_broken_email() -> None:
    # apex/www moved to Netlify but the MX was wiped — the disaster we must catch.
    zone = {
        ("acme.com", "A"): ["75.2.60.5"],
        ("www.acme.com", "CNAME"): ["acme.netlify.app."],
        ("acme.com", "MX"): [],  # mail is broken
    }
    result = _verifier(zone).verify(
        "acme.com", netlify_site="acme.netlify.app", expected_email_host="Google Workspace"
    )
    assert not result.ok
    mx_check = next(c for c in result.checks if c.name == "email_mx_preserved")
    assert mx_check.status == FAIL


def test_verify_apex_wrong_is_fail_when_resolvers_agree() -> None:
    zone = {("acme.com", "A"): ["1.2.3.4"], ("www.acme.com", "CNAME"): ["acme.netlify.app."]}
    result = _verifier(zone).verify("acme.com", netlify_site="acme.netlify.app")
    apex = next(c for c in result.checks if c.name == "apex_points_to_netlify")
    assert apex.status == FAIL


def test_verify_resolver_disagreement_is_propagating() -> None:
    google = {("acme.com", "A"): ["75.2.60.5"], ("www.acme.com", "CNAME"): ["acme.netlify.app."]}
    cloudflare = {("acme.com", "A"): ["1.2.3.4"], ("www.acme.com", "CNAME"): ["old.example.com."]}
    result = _verifier(google, cloudflare).verify("acme.com", netlify_site="acme.netlify.app")
    apex = next(c for c in result.checks if c.name == "apex_points_to_netlify")
    assert apex.status == PROPAGATING
    assert not result.ok


def test_verify_https_not_ready_is_propagating() -> None:
    zone = {("acme.com", "A"): ["75.2.60.5"], ("www.acme.com", "CNAME"): ["acme.netlify.app."]}
    result = _verifier(zone, https_status=None).verify(
        "acme.com", netlify_site="acme.netlify.app", check_https=True
    )
    https = next(c for c in result.checks if c.name == "https_serving")
    assert https.status == PROPAGATING
