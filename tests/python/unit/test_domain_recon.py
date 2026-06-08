"""Tests for domain readiness recon (RDAP + DoH), fully offline.

A single ``httpx.MockTransport`` stands in for both rdap.org and the Google DoH
resolver, so we exercise validation, classification, and report/instruction
rendering with no network.
"""

from __future__ import annotations

import httpx
import pytest

from packages.agency.domain_recon import (
    DomainRecon,
    DomainValidationError,
    netlify_external_dns_instructions,
    render_report,
    validate_domain,
)

_RTYPE_NAME = {1: "A", 2: "NS", 5: "CNAME", 6: "SOA", 15: "MX", 16: "TXT", 28: "AAAA"}


def _zone_handler(zone: dict[tuple[str, str], list[str]], *, rdap: dict | None) -> object:
    """Build a MockTransport handler from a {(name, rtype): [data,...]} zone."""

    def handler(request: httpx.Request) -> httpx.Response:
        host = request.url.host
        if host == "rdap.org":
            if rdap is None:
                return httpx.Response(404, json={"errorCode": 404})
            return httpx.Response(200, json=rdap)
        if host in ("dns.google", "cloudflare-dns.com"):
            name = request.url.params.get("name", "").rstrip(".").lower()
            rtype = _RTYPE_NAME[int(request.url.params.get("type", "1"))]
            answers = [
                {"name": name, "type": int(request.url.params["type"]), "TTL": 300, "data": d}
                for d in zone.get((name, rtype), [])
            ]
            return httpx.Response(200, json={"Status": 0, "Answer": answers})
        return httpx.Response(404)

    return handler


def _recon(zone: dict, *, rdap: dict | None) -> DomainRecon:
    transport = httpx.MockTransport(_zone_handler(zone, rdap=rdap))
    client = httpx.Client(transport=transport, follow_redirects=True)
    return DomainRecon(client=client)


# ── validate_domain ──────────────────────────────────────────────────────
@pytest.mark.parametrize(
    "raw,expected",
    [
        ("Acme.com", "acme.com"),
        ("  example.org.  ", "example.org"),
        ("sub.domain.co.uk", "sub.domain.co.uk"),
    ],
)
def test_validate_domain_normalizes(raw: str, expected: str) -> None:
    assert validate_domain(raw) == expected


@pytest.mark.parametrize(
    "raw",
    [
        "",
        "localhost",  # no dot → not registrable
        "http://acme.com",  # scheme
        "acme.com/path",  # path
        "acme.com:8080",  # port
        "foo@acme.com",  # userinfo / injection
        "acme.com?x=1",  # query
        "ac me.com",  # whitespace
        "evil.com\nrdap.org",  # CRLF injection
    ],
)
def test_validate_domain_rejects_untrusted_shapes(raw: str) -> None:
    with pytest.raises(DomainValidationError):
        validate_domain(raw)


def test_validate_domain_idn_to_punycode() -> None:
    assert validate_domain("münchen.de") == "xn--mnchen-3ya.de"


# ── recon classification ─────────────────────────────────────────────────
def test_recon_google_workspace_on_cloudflare() -> None:
    zone = {
        ("acme.com", "NS"): ["bob.ns.cloudflare.com.", "lola.ns.cloudflare.com."],
        ("acme.com", "A"): ["75.2.60.5"],
        ("acme.com", "MX"): ["1 smtp.google.com."],
        ("acme.com", "TXT"): ['"v=spf1 include:_spf.google.com ~all"'],
        ("_dmarc.acme.com", "TXT"): ['"v=DMARC1; p=quarantine; rua=mailto:d@acme.com"'],
        ("google._domainkey.acme.com", "TXT"): ['"v=DKIM1; k=rsa; p=AAAA"'],
        ("www.acme.com", "CNAME"): ["acme.netlify.app."],
    }
    rdap = {
        "entities": [
            {
                "roles": ["registrar"],
                "vcardArray": ["vcard", [["fn", {}, "text", "MarkMonitor Inc."]]],
            }
        ],
        "nameservers": [{"ldhName": "BOB.NS.CLOUDFLARE.COM"}],
        "secureDNS": {"delegationSigned": False},
    }
    report = _recon(zone, rdap=rdap).recon("acme.com")

    assert report.registrar == "MarkMonitor Inc."
    assert report.rdap_available is True
    assert report.dns_provider == "Cloudflare"
    assert report.apex_alias_supported is True
    assert report.email_host == "Google Workspace"
    assert report.mx_records == ["1 smtp.google.com"]
    assert report.has_spf and report.has_dkim
    assert report.dmarc_policy == "quarantine"
    assert report.recommended_strategy == "external"
    # The email-preservation hazard must be surfaced.
    assert any("Google Workspace" in n and "preserved" in n for n in report.notes)


def test_recon_no_alias_registrar_flags_a_fallback() -> None:
    zone = {
        ("shop.com", "NS"): ["ns1.domaincontrol.com.", "ns2.domaincontrol.com."],
        ("shop.com", "A"): ["198.51.100.7"],
    }
    report = _recon(zone, rdap=None).recon("shop.com")

    assert report.dns_provider == "GoDaddy"
    assert report.apex_alias_supported is False
    assert report.rdap_available is False  # no RDAP → degrade, don't fail
    assert report.email_host == ""
    assert report.recommended_strategy == "managed"  # no alias + no email to risk
    assert any("RDAP" in n for n in report.notes)
    assert any("A-record fallback" in n for n in report.notes)


def test_recon_dnssec_note() -> None:
    zone = {("secure.com", "NS"): ["ns1.example.net."]}
    rdap = {"entities": [], "nameservers": [], "secureDNS": {"delegationSigned": True}}
    report = _recon(zone, rdap=rdap).recon("secure.com")
    assert report.dnssec is True
    assert any("DNSSEC" in n for n in report.notes)


# ── rendering ────────────────────────────────────────────────────────────
def test_instructions_carry_over_email_and_pick_apex() -> None:
    zone = {
        ("acme.com", "NS"): ["bob.ns.cloudflare.com."],
        ("acme.com", "MX"): ["1 smtp.google.com."],
        ("acme.com", "TXT"): ['"v=spf1 include:_spf.google.com ~all"'],
    }
    report = _recon(zone, rdap=None).recon("acme.com")
    out = netlify_external_dns_instructions(report, "acme.netlify.app")
    assert "apex-loadbalancer.netlify.com" in out  # alias path
    assert "acme.netlify.app" in out
    assert "Do not touch the email records" in out
    assert "Google Workspace" in out


def test_instructions_a_fallback_when_no_alias() -> None:
    zone = {("shop.com", "NS"): ["ns1.domaincontrol.com."]}
    report = _recon(zone, rdap=None).recon("shop.com")
    out = netlify_external_dns_instructions(report, "shop.netlify.app")
    assert "75.2.60.5" in out
    assert "no ALIAS" in out


def test_render_report_is_human_readable() -> None:
    zone = {("acme.com", "NS"): ["bob.ns.cloudflare.com."], ("acme.com", "A"): ["75.2.60.5"]}
    report = _recon(zone, rdap=None).recon("acme.com")
    text = render_report(report)
    assert text.startswith("# Domain readiness — acme.com")
    assert "Recommended strategy" in text
