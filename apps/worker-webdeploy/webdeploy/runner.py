"""WEBDEPLOY runner — gate, then publish a built site (F5).

The deploy lane is intentionally separate from the build lane (mirrors
IOS → APPSTORE). This runner is the composition point: it re-validates the exact
``dist`` about to ship, enforces the deploy-readiness policy, and only then calls
the ``DeployTarget``. It never decides policy itself — that lives in
``packages/policies/deploy_readiness.py``.

Pure orchestration over injectable parts (a ``DeployTarget`` and the validation
gate), so it's unit-testable with a fake target and a temp ``dist`` — no network.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from packages.policies.deploy_readiness import assert_custom_domain_allowed, assert_deploy_ready
from packages.web.deploy import DeployAccount, DeployResult, DeployTarget
from packages.web.validation import WebValidationReport, validate_web_dist


@dataclass(frozen=True)
class WebDeployOutcome:
    result: DeployResult
    report: WebValidationReport


def run_webdeploy(
    project_dir: Path,
    site_name: str,
    *,
    target: DeployTarget,
    production: bool = False,
    preview_reviewed: bool = False,
    approval_granted: bool = False,
    account: DeployAccount | None = None,
    custom_domain: str | None = None,
    domain_approval_granted: bool = False,
    dist: str = "dist",
) -> WebDeployOutcome:
    """Validate the built site, enforce the deploy gate, then publish.

    Raises ``PolicyViolation`` (and deploys nothing) if the gate refuses. A
    custom domain is attached only after its own approval check passes.
    """
    dist_dir = project_dir / dist
    report = validate_web_dist(dist_dir)

    assert_deploy_ready(
        production=production,
        gate_passed=report.passed,
        preview_reviewed=preview_reviewed,
        approval_granted=approval_granted,
    )

    site = target.ensure_site(site_name, account=account)
    result = target.deploy(site, dist_dir, production=production)

    if custom_domain:
        assert_custom_domain_allowed(approval_granted=domain_approval_granted)
        target.set_custom_domain(site, custom_domain)

    return WebDeployOutcome(result=result, report=report)
