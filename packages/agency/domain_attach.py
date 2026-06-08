"""Attach a client's own domain to their Netlify site (Phase 2 orchestration).

The thin layer between the launch CLI and the Netlify deploy seam. It enforces the
**control-proof gate** before any write, then drives the www-as-primary +
apex-alias attach and nudges cert provisioning.

The gate is two-part, matching the plan's committed-scope guardrail:

* ``assert_custom_domain_allowed(approval_granted=dns_approved)`` — the existing
  policy gate (a custom-domain change always needs a granted approval); and
* ``client_confirmed_registrar`` — the *workflow-inherent* control proof: the
  client has completed the registrar step (added our records / pointed the
  domain), which is itself evidence they control it. Phase 2 attaches to **our**
  Netlify account and writes nothing to the client's zone, so this is the right
  level of proof — no separate TXT-challenge subsystem is built here.

``DeployTarget`` is injected, so this orchestration is unit-testable with a fake
target — no network, no token.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from packages.agency.domain_recon import validate_domain
from packages.policies.deploy_readiness import assert_custom_domain_allowed
from packages.web.deploy import CertState, DeployTarget, SiteRef


class DomainControlError(RuntimeError):
    """Raised when the client-control proof for a domain attach is missing."""


@dataclass(frozen=True)
class AttachResult:
    domain: str
    primary: str  # www.<domain>
    aliases: list[str] = field(default_factory=list)
    site_url: str = ""
    cert_state: str = ""
    cert_issued: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "domain": self.domain,
            "primary": self.primary,
            "aliases": list(self.aliases),
            "site_url": self.site_url,
            "cert_state": self.cert_state,
            "cert_issued": self.cert_issued,
        }


def attach_client_domain(
    target: DeployTarget,
    *,
    site_id: str,
    site_name: str,
    domain: str,
    dns_approved: bool,
    client_confirmed_registrar: bool,
    provision_cert: bool = True,
) -> AttachResult:
    """Attach ``domain`` to a Netlify site as www-primary + apex-alias, gated.

    Raises :class:`PolicyViolation` if ``dns_approved`` is false, and
    :class:`DomainControlError` if the client hasn't confirmed the registrar step.
    """
    domain = validate_domain(domain)
    assert_custom_domain_allowed(approval_granted=dns_approved)
    if not client_confirmed_registrar:
        raise DomainControlError(
            "control-proof missing: the client must have completed the registrar step "
            "(added our DNS records / pointed the domain) before we attach it"
        )

    ref = SiteRef(site_id, site_name)
    primary = f"www.{domain}"
    site = target.attach_domain(ref, primary, aliases=(domain,))
    cert: CertState = target.provision_ssl(ref) if provision_cert else CertState()
    return AttachResult(
        domain=domain,
        primary=primary,
        aliases=[domain],
        site_url=site.url,
        cert_state=cert.state,
        cert_issued=cert.issued,
    )
