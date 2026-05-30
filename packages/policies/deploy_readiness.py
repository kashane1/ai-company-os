"""Deploy readiness gates — the web lane's "validate before ship" policy (F5).

Putting a site in front of the public is high blast radius, so the WEBDEPLOY
worker must clear these gates before it calls a ``DeployTarget``. Mirrors
``release_readiness`` (App Store) and ``discovery_gates``: policy is owned here,
not by the worker or the deploy tool, and a refusal raises
:class:`~packages.policies.approvals.PolicyViolation` with a machine-readable
code.

``architecture.md`` already lists "production deploys" and "domain or DNS
modifications" as approval-required; this module is the enforcement.

The asymmetry is deliberate:

* **Preview deploys are cheap and ungated** — they only require that the build
  actually validated (don't ship a broken preview), so iterating stays fast.
* **Production deploys are gated**: validated build + a reviewed preview + a
  granted approval.
* **Custom domain / DNS** and **hosting spend** each require their own approval.
"""

from __future__ import annotations

from packages.policies.approvals import PolicyViolation, PolicyViolationCode


def assert_deploy_ready(
    *,
    production: bool,
    gate_passed: bool,
    preview_reviewed: bool = False,
    approval_granted: bool = False,
) -> None:
    """Authorize a deploy, or raise ``PolicyViolation``.

    ``gate_passed`` is the web validation gate result for the exact ``dist`` about
    to ship (build + links + assets + responsive + a11y). A preview only needs
    that; production additionally needs a reviewed preview and a granted approval.
    """
    if not gate_passed:
        raise PolicyViolation(
            PolicyViolationCode.DEPLOY_BUILD_NOT_VALIDATED,
            "web validation gate has not passed for the build being deployed",
        )
    if not production:
        return  # preview deploys are ungated beyond a valid build
    if not preview_reviewed:
        raise PolicyViolation(
            PolicyViolationCode.DEPLOY_PREVIEW_NOT_REVIEWED,
            "a production deploy requires the preview to be reviewed first",
        )
    if not approval_granted:
        raise PolicyViolation(
            PolicyViolationCode.DEPLOY_APPROVAL_NOT_GRANTED,
            "a production deploy requires a granted human approval",
        )


def assert_custom_domain_allowed(*, approval_granted: bool) -> None:
    """A custom-domain / DNS change always requires approval."""
    if not approval_granted:
        raise PolicyViolation(
            PolicyViolationCode.DEPLOY_DNS_NOT_APPROVED,
            "attaching a custom domain / changing DNS requires a granted approval",
        )


def assert_hosting_spend_allowed(*, approval_granted: bool) -> None:
    """Moving off the free tier / incurring hosting spend requires approval."""
    if not approval_granted:
        raise PolicyViolation(
            PolicyViolationCode.DEPLOY_SPEND_NOT_APPROVED,
            "incurring hosting spend (paid plan / overage) requires a granted approval",
        )
