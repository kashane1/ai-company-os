#!/usr/bin/env python3
"""Attach a client's own domain to their Netlify site (Phase 2).

Wires the gated attach orchestration to the real Netlify target + registry, and
stamps the live URL into the client's ``intake.json``. Sets www as the primary
custom domain with the apex as an alias, then nudges Let's Encrypt provisioning.

Control-proof is required (the domain is a write to hosting): both
``--dns-approved`` (the policy gate) AND ``--client-confirmed-registrar`` (the
client has completed the registrar step) must be passed, or the attach refuses.

Examples::

    python scripts/agency/attach_domain.py --product-id acme-site --domain acme.com \\
        --dns-approved --client-confirmed-registrar

    # then verify it didn't break their email:
    python scripts/agency/verify_domain.py acme.com --site <site>.netlify.app \\
        --expect-email "Google Workspace"
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from packages.agency.client_lifecycle import client_paths  # noqa: E402
from packages.agency.domain_attach import (  # noqa: E402
    DomainControlError,
    attach_client_domain,
)
from packages.agency.domain_recon import DomainValidationError  # noqa: E402
from packages.agency.intake import load_intake, write_intake  # noqa: E402
from packages.agency.registry import RegistryError, get_registry_record  # noqa: E402
from packages.policies.approvals import PolicyViolation  # noqa: E402
from packages.web.deploy import DeployError, NetlifyDeployTarget  # noqa: E402


def _resolve_site_id(product_id: str, override: str) -> str:
    if override:
        return override
    record = get_registry_record(product_id)
    site_id = str((record.get("client") or {}).get("netlify_site_id", "")).strip()
    if not site_id:
        raise RegistryError(
            f"{product_id!r} has no recorded netlify_site_id — pass --site-id or "
            "stamp it at launch (launch_client.py mark-live --netlify-site-id)"
        )
    return site_id


def _stamp_site_url(product_id: str, domain: str) -> str | None:
    """Stamp intake.site_url = https://www.<domain>, returning the docs path or None."""
    try:
        docs_root, _ = client_paths(product_id)
    except (RegistryError, KeyError):
        return None
    intake = load_intake(docs_root)
    if intake is None:
        return None
    from dataclasses import replace

    write_intake(docs_root, replace(intake, site_url=f"https://www.{domain}"))
    return str(docs_root)


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--product-id", required=True, help="registry product id (client-site)")
    ap.add_argument("--domain", required=True, help="the client's apex domain, e.g. acme.com")
    ap.add_argument("--site-id", default="", help="override the Netlify site id from the registry")
    ap.add_argument("--site-name", default="", help="Netlify site host (for the verify hint)")
    ap.add_argument(
        "--dns-approved",
        action="store_true",
        help="the policy gate: DNS/custom-domain approval granted",
    )
    ap.add_argument(
        "--client-confirmed-registrar",
        action="store_true",
        help="control proof: the client completed the registrar step (pointed the domain)",
    )
    ap.add_argument("--no-cert", action="store_true", help="skip the SSL provisioning nudge")
    args = ap.parse_args()

    try:
        site_id = _resolve_site_id(args.product_id, args.site_id)
        result = attach_client_domain(
            NetlifyDeployTarget(),
            site_id=site_id,
            site_name=args.site_name or args.product_id,
            domain=args.domain,
            dns_approved=args.dns_approved,
            client_confirmed_registrar=args.client_confirmed_registrar,
            provision_cert=not args.no_cert,
        )
    except DomainValidationError as exc:
        print(f"ERROR: invalid domain — {exc}", file=sys.stderr)
        return 1
    except (PolicyViolation, DomainControlError) as exc:
        print(f"BLOCKED: {exc}", file=sys.stderr)
        return 2
    except (RegistryError, DeployError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    docs = _stamp_site_url(args.product_id, result.domain)
    out = result.to_dict()
    out["stamped_site_url_in"] = docs
    print(json.dumps(out, indent=2))
    print(
        f"\nattached {result.primary} (+ alias {result.domain}). "
        f"cert: {result.cert_state or 'not provisioned'}.",
        file=sys.stderr,
    )
    if args.site_name:
        print(
            f"next: python scripts/agency/verify_domain.py {result.domain} "
            f"--site {args.site_name} --expect-email '<email host from recon>'",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
