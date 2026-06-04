"""Agency layer Phase 3 — prospect → client promotion."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from packages.agency.promotion import PromotionError, promote_prospect_to_client
from packages.policies.approvals import PolicyViolation, PolicyViolationCode
from packages.prospecting.storage import ProspectRepository
from packages.schemas.prospect import EngagementStatus, HumanVerified, ProspectRecord


def _prospect(verified: HumanVerified = HumanVerified.TRUE) -> ProspectRecord:
    return ProspectRecord(
        place_id="places/joe123",
        display_name="Joe's Plumbing",
        formatted_address="1 Main St, Seattle, WA",
        phone="",
        types=["plumber"],
        city_id="seattle",
        genre_id="plumber",
        grid_cell_id="seattle:plumber",
        human_verified=verified,
    )


def _paths(tmp_path: Path) -> dict:
    registry = tmp_path / "products.json"
    registry.write_text("[]")
    return {
        "registry_path": registry,
        "docs_root_parent": tmp_path / "docs" / "products",
    }


def test_promotes_verified_approved_prospect(tmp_path: Path) -> None:
    p = _paths(tmp_path)
    record = promote_prospect_to_client(
        _prospect(), "package_a", approval_granted=True, mark_onboarded=False, **p
    )
    assert record["id"] == "joes-plumbing-site"
    assert record["type"] == "client-site"
    assert record["client"]["from_prospect"] == "places/joe123"
    assert record["client"]["bundle"] == "package_a"

    registry = json.loads(p["registry_path"].read_text())
    assert any(r["id"] == "joes-plumbing-site" for r in registry)

    workspace = p["docs_root_parent"] / "joes-plumbing-site"
    assert (workspace / "OFFER.md").exists()
    assert (workspace / "CLIENT_BRIEF.md").exists()
    assert (workspace / "reports").is_dir()
    assert (workspace / "BOOKING.md").exists()
    assert (workspace / "REVIEWS.md").exists()
    # OFFER renders from the catalog bundle.
    assert "Package A" in (workspace / "OFFER.md").read_text()


def test_promotion_marks_prospect_onboarded(tmp_path: Path) -> None:
    p = _paths(tmp_path)
    records_root = tmp_path / "prospects" / "records"
    records_root.mkdir(parents=True)
    repo = ProspectRepository(records_root)
    prospect = _prospect()
    repo.save(prospect)
    promote_prospect_to_client(
        prospect,
        "package_a",
        approval_granted=True,
        prospect_repo=repo,
        mark_onboarded=True,
        **p,
    )
    updated = repo.get(prospect.place_id)
    assert updated.engagement_status is EngagementStatus.ONBOARDED


def test_refuses_unverified_prospect(tmp_path: Path) -> None:
    p = _paths(tmp_path)
    for state in (HumanVerified.UNSET, HumanVerified.FALSE):
        with pytest.raises(PolicyViolation) as exc:
            promote_prospect_to_client(
                _prospect(state),
                "package_a",
                approval_granted=True,
                mark_onboarded=False,
                **p,
            )
        assert exc.value.code == PolicyViolationCode.CLIENT_PROMOTION_NOT_APPROVED.value
    # Nothing written.
    assert json.loads(p["registry_path"].read_text()) == []


def test_refuses_without_approval(tmp_path: Path) -> None:
    p = _paths(tmp_path)
    with pytest.raises(PolicyViolation) as exc:
        promote_prospect_to_client(
            _prospect(), "package_a", approval_granted=False, mark_onboarded=False, **p
        )
    assert exc.value.code == PolicyViolationCode.CLIENT_PROMOTION_NOT_APPROVED.value


def test_unknown_bundle_raises_promotion_error(tmp_path: Path) -> None:
    p = _paths(tmp_path)
    with pytest.raises(PromotionError):
        promote_prospect_to_client(
            _prospect(), "package_z", approval_granted=True, mark_onboarded=False, **p
        )


def test_promotion_is_idempotent(tmp_path: Path) -> None:
    p = _paths(tmp_path)
    first = promote_prospect_to_client(
        _prospect(), "package_a", approval_granted=True, mark_onboarded=False, **p
    )
    second = promote_prospect_to_client(
        _prospect(), "package_a", approval_granted=True, mark_onboarded=False, **p
    )
    assert first["id"] == second["id"]
    registry = json.loads(p["registry_path"].read_text())
    assert sum(1 for r in registry if r["id"] == "joes-plumbing-site") == 1


def test_re_promotion_with_different_bundle_is_refused(tmp_path: Path) -> None:
    p = _paths(tmp_path)
    promote_prospect_to_client(
        _prospect(), "package_a", approval_granted=True, mark_onboarded=False, **p
    )
    with pytest.raises(PromotionError):
        promote_prospect_to_client(
            _prospect(), "package_c", approval_granted=True, mark_onboarded=False, **p
        )
    # Registry + rendered OFFER stay on the original bundle (no silent divergence).
    registry = json.loads(p["registry_path"].read_text())
    record = next(r for r in registry if r["id"] == "joes-plumbing-site")
    assert record["client"]["bundle"] == "package_a"
    offer = (p["docs_root_parent"] / "joes-plumbing-site" / "OFFER.md").read_text()
    assert "Package A" in offer and "Package C" not in offer
