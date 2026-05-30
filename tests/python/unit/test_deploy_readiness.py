"""Tests for deploy-readiness gates + the webdeploy orchestration (F5).

The policy is asymmetric: preview deploys need only a valid build; production
deploys need a reviewed preview + a granted approval; DNS/spend each need their
own approval. The runner must enforce all of that before touching the target,
and must deploy nothing when the gate refuses.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

from packages.policies.approvals import PolicyViolation
from packages.policies.deploy_readiness import (
    assert_custom_domain_allowed,
    assert_deploy_ready,
    assert_hosting_spend_allowed,
)
from packages.web.deploy import DeployAccount, DeployResult, SiteRef
from packages.web.scaffold import default_context, render_landing_html


def _load_runner():
    path = (
        Path(__file__).resolve().parents[3]
        / "apps" / "worker-webdeploy" / "webdeploy" / "runner.py"
    )
    spec = importlib.util.spec_from_file_location("webdeploy_runner", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


# ── policy ──────────────────────────────────────────────────────────────────


def test_preview_deploy_only_needs_valid_build() -> None:
    assert_deploy_ready(production=False, gate_passed=True)  # no raise


def test_preview_deploy_blocked_when_build_invalid() -> None:
    with pytest.raises(PolicyViolation) as exc:
        assert_deploy_ready(production=False, gate_passed=False)
    assert exc.value.code == "deploy_build_not_validated"


def test_production_requires_review_and_approval() -> None:
    with pytest.raises(PolicyViolation) as e1:
        assert_deploy_ready(production=True, gate_passed=True, preview_reviewed=False)
    assert e1.value.code == "deploy_preview_not_reviewed"

    with pytest.raises(PolicyViolation) as e2:
        assert_deploy_ready(production=True, gate_passed=True, preview_reviewed=True,
                            approval_granted=False)
    assert e2.value.code == "deploy_approval_not_granted"

    # All conditions met → no raise.
    assert_deploy_ready(production=True, gate_passed=True, preview_reviewed=True,
                        approval_granted=True)


def test_dns_and_spend_require_approval() -> None:
    with pytest.raises(PolicyViolation) as dns:
        assert_custom_domain_allowed(approval_granted=False)
    assert dns.value.code == "deploy_dns_not_approved"
    assert_custom_domain_allowed(approval_granted=True)  # no raise

    with pytest.raises(PolicyViolation) as spend:
        assert_hosting_spend_allowed(approval_granted=False)
    assert spend.value.code == "deploy_spend_not_approved"


# ── runner orchestration ─────────────────────────────────────────────────────


class FakeTarget:
    name = "fake"

    def __init__(self) -> None:
        self.deploys: list[dict] = []
        self.domains: list[str] = []

    def ensure_site(self, name, *, account=None):  # noqa: ANN001
        return SiteRef(site_id="s1", name=name, url=f"https://{name}.example")

    def deploy(self, site, dist_dir, *, production=False):  # noqa: ANN001
        self.deploys.append({"production": production, "dist": str(dist_dir)})
        return DeployResult(site=site, deploy_id="d1", url=site.url, production=production,
                            state="ready")

    def set_custom_domain(self, site, domain):  # noqa: ANN001
        self.domains.append(domain)
        return site

    def transfer_ownership(self, site, to_account):  # noqa: ANN001
        return site


def _good_project(tmp_path: Path) -> Path:
    project = tmp_path / "proj"
    (project / "dist").mkdir(parents=True)
    html = render_landing_html(default_context("Acme"))
    (project / "dist" / "index.html").write_text(html, encoding="utf-8")
    return project


def test_runner_preview_deploys_when_build_valid(tmp_path: Path) -> None:
    runner = _load_runner()
    target = FakeTarget()
    outcome = runner.run_webdeploy(_good_project(tmp_path), "acme", target=target, production=False)
    assert outcome.report.passed
    assert outcome.result.production is False
    assert len(target.deploys) == 1


def test_runner_blocks_production_without_approval(tmp_path: Path) -> None:
    runner = _load_runner()
    target = FakeTarget()
    with pytest.raises(PolicyViolation):
        runner.run_webdeploy(
            _good_project(tmp_path), "acme", target=target,
            production=True, preview_reviewed=True, approval_granted=False,
        )
    assert target.deploys == []  # nothing shipped


def test_runner_blocks_deploy_when_build_invalid(tmp_path: Path) -> None:
    runner = _load_runner()
    target = FakeTarget()
    project = tmp_path / "proj"
    (project / "dist").mkdir(parents=True)
    # Missing viewport + lang + h1 → gate fails.
    (project / "dist" / "index.html").write_text(
        "<html><body><p>hi</p></body></html>", encoding="utf-8"
    )
    with pytest.raises(PolicyViolation):
        runner.run_webdeploy(project, "acme", target=target, production=False)
    assert target.deploys == []


def test_runner_production_with_full_approval_attaches_domain(tmp_path: Path) -> None:
    runner = _load_runner()
    target = FakeTarget()
    outcome = runner.run_webdeploy(
        _good_project(tmp_path), "acme", target=target,
        production=True, preview_reviewed=True, approval_granted=True,
        custom_domain="acme.com", domain_approval_granted=True,
        account=DeployAccount("team_x"),
    )
    assert outcome.result.production is True
    assert target.domains == ["acme.com"]


def test_runner_blocks_domain_without_domain_approval(tmp_path: Path) -> None:
    runner = _load_runner()
    target = FakeTarget()
    with pytest.raises(PolicyViolation) as exc:
        runner.run_webdeploy(
            _good_project(tmp_path), "acme", target=target,
            production=True, preview_reviewed=True, approval_granted=True,
            custom_domain="acme.com", domain_approval_granted=False,
        )
    assert exc.value.code == "deploy_dns_not_approved"
    # The deploy itself happened, but the domain was not attached.
    assert target.domains == []
