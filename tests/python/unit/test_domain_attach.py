"""Tests for the gated domain-attach orchestration (Phase 2), offline.

A fake DeployTarget stands in for Netlify; we assert the control-proof gate and
the www-primary + apex-alias attach shape.
"""

from __future__ import annotations

import pytest

from packages.agency.domain_attach import (
    AttachResult,
    DomainControlError,
    attach_client_domain,
)
from packages.agency.domain_recon import DomainValidationError
from packages.policies.approvals import PolicyViolation
from packages.web.deploy import CertState, SiteRef


class _FakeTarget:
    name = "fake"

    def __init__(self, cert: CertState | None = None) -> None:
        self.calls: list[tuple] = []
        self._cert = cert or CertState(state="issued", domains=["acme.com", "www.acme.com"])

    def attach_domain(
        self, site: SiteRef, primary: str, *, aliases: tuple[str, ...] = ()
    ) -> SiteRef:
        self.calls.append(("attach", site.site_id, primary, aliases))
        return SiteRef(site.site_id, site.name, url=f"https://{primary}")

    def provision_ssl(self, site: SiteRef) -> CertState:
        self.calls.append(("ssl", site.site_id))
        return self._cert


def _attach(target, **kw):
    defaults = dict(
        site_id="s1",
        site_name="acme.netlify.app",
        domain="acme.com",
        dns_approved=True,
        client_confirmed_registrar=True,
    )
    defaults.update(kw)
    return attach_client_domain(target, **defaults)


def test_attach_sets_www_primary_apex_alias_and_provisions_cert() -> None:
    target = _FakeTarget()
    result = _attach(target)
    assert isinstance(result, AttachResult)
    assert result.primary == "www.acme.com"
    assert result.aliases == ["acme.com"]
    assert result.site_url == "https://www.acme.com"
    assert result.cert_issued
    assert ("attach", "s1", "www.acme.com", ("acme.com",)) in target.calls
    assert ("ssl", "s1") in target.calls


def test_attach_blocked_without_dns_approval() -> None:
    target = _FakeTarget()
    with pytest.raises(PolicyViolation):
        _attach(target, dns_approved=False)
    assert target.calls == []  # no write attempted


def test_attach_blocked_without_registrar_confirmation() -> None:
    target = _FakeTarget()
    with pytest.raises(DomainControlError):
        _attach(target, client_confirmed_registrar=False)
    assert target.calls == []


def test_attach_rejects_invalid_domain() -> None:
    target = _FakeTarget()
    with pytest.raises(DomainValidationError):
        _attach(target, domain="http://acme.com/evil")
    assert target.calls == []


def test_attach_no_cert_skips_provisioning() -> None:
    target = _FakeTarget()
    result = _attach(target, provision_cert=False)
    assert not result.cert_issued
    assert all(call[0] != "ssl" for call in target.calls)
