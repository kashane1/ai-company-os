from __future__ import annotations

from pathlib import Path

import pytest

from packages.db.approval_store import ApprovalStore
from packages.policies.approval_bindings import (
    assert_approval_binding,
    directory_revision,
    web_deploy_revision,
)
from packages.policies.approvals import PolicyViolation, PolicyViolationCode
from packages.schemas.approval import ApprovalRecord, ApprovalStatus


def _approval(**overrides: object) -> ApprovalRecord:
    payload: dict[str, object] = {
        "id": "approval-1",
        "status": ApprovalStatus.APPROVED,
        "summary": "Approve production deploy",
        "created_at": "2026-09-08T00:00:00+00:00",
        "approval_type": "web_production_deploy",
        "subject_type": "web_site",
        "subject_id": "example-site",
        "action": "deploy_production",
        "reviewed_revision": "sha256:expected",
    }
    payload.update(overrides)
    return ApprovalRecord(**payload)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "overrides",
    [
        {"status": ApprovalStatus.REJECTED},
        {"subject_id": "other-site"},
        {"action": "deploy_preview"},
        {"reviewed_revision": "sha256:stale"},
    ],
)
def test_binding_rejects_denied_or_mismatched_approval(
    isolated_repo_root: Path, overrides: dict[str, object]
) -> None:
    store = ApprovalStore()
    store.save(_approval(**overrides))

    with pytest.raises(PolicyViolation) as exc:
        assert_approval_binding(
            "approval-1",
            approval_type="web_production_deploy",
            subject_type="web_site",
            subject_id="example-site",
            action="deploy_production",
            reviewed_revision="sha256:expected",
            violation_code=PolicyViolationCode.DEPLOY_APPROVAL_NOT_GRANTED,
            store=store,
        )

    assert exc.value.code == PolicyViolationCode.DEPLOY_APPROVAL_NOT_GRANTED.value


def test_binding_rejects_missing_approval(isolated_repo_root: Path) -> None:
    with pytest.raises(PolicyViolation) as exc:
        assert_approval_binding(
            "missing",
            approval_type="web_production_deploy",
            subject_type="web_site",
            subject_id="example-site",
            action="deploy_production",
            reviewed_revision="sha256:expected",
            violation_code=PolicyViolationCode.DEPLOY_APPROVAL_NOT_GRANTED,
        )

    assert exc.value.code == PolicyViolationCode.DEPLOY_APPROVAL_NOT_GRANTED.value


def test_directory_revision_covers_paths_and_file_bytes(tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("first", encoding="utf-8")
    first = directory_revision(dist)

    (dist / "index.html").write_text("second", encoding="utf-8")
    changed_bytes = directory_revision(dist)
    assert changed_bytes != first

    (dist / "renamed.html").write_text("second", encoding="utf-8")
    (dist / "index.html").unlink()
    assert directory_revision(dist) != changed_bytes

    before_empty_directory = directory_revision(dist)
    (dist / "empty-directory").mkdir()
    assert directory_revision(dist) != before_empty_directory


def test_directory_revision_rejects_symlinks(tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    dist.mkdir()
    target = tmp_path / "outside"
    target.write_text("outside", encoding="utf-8")
    (dist / "linked.html").symlink_to(target)

    with pytest.raises(ValueError, match="symlink"):
        directory_revision(dist)


def test_directory_revision_rejects_a_symlinked_root(tmp_path: Path) -> None:
    real_dist = tmp_path / "real-dist"
    real_dist.mkdir()
    dist = tmp_path / "dist"
    dist.symlink_to(real_dist, target_is_directory=True)

    with pytest.raises(ValueError, match="symlink"):
        directory_revision(dist)


def test_web_deploy_revision_binds_destination_and_dist_tree(tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("first", encoding="utf-8")

    baseline = web_deploy_revision(dist_dir=dist, site_name="site-a")
    assert web_deploy_revision(dist_dir=dist, site_name="site-b") != baseline

    (dist / "index.html").write_text("changed", encoding="utf-8")
    assert web_deploy_revision(dist_dir=dist, site_name="site-a") != baseline
