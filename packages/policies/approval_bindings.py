"""Exact stored-approval bindings for irreversible local actions."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from packages.db.approval_store import ApprovalStore
from packages.policies.approvals import PolicyViolation, PolicyViolationCode
from packages.schemas.approval import ApprovalRecord, ApprovalStatus

WEB_DEPLOY_APPROVAL_TYPE = "web_production_deploy"
WEB_DEPLOY_SUBJECT_TYPE = "web_site"
WEB_DEPLOY_ACTION = "deploy_production"
PROMOTION_APPROVAL_TYPE = "prospect_promotion"
PROMOTION_SUBJECT_TYPE = "prospect"
PROMOTION_ACTION = "promote_prospect"


def canonical_revision(payload: dict[str, object]) -> str:
    """Return a stable SHA-256 revision for reviewable action inputs."""
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return f"sha256:{hashlib.sha256(encoded.encode('utf-8')).hexdigest()}"


def directory_revision(root: Path) -> str:
    """Hash a deploy tree's relative paths and file bytes, rejecting links."""
    if root.is_symlink():
        raise ValueError(f"deploy directory must not be a symlink: {root}")
    if not root.is_dir():
        raise ValueError(f"deploy directory not found: {root}")
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*"), key=lambda entry: entry.relative_to(root).as_posix()):
        relative = path.relative_to(root).as_posix()
        if path.is_symlink():
            raise ValueError(f"deploy directory contains symlink: {relative}")
        if path.is_dir():
            digest.update(b"dir\\0")
            digest.update(relative.encode("utf-8"))
            digest.update(b"\\0")
            continue
        if not path.is_file():
            raise ValueError(f"deploy directory contains unsupported entry: {relative}")
        data = path.read_bytes()
        digest.update(b"file\\0")
        digest.update(relative.encode("utf-8"))
        digest.update(b"\\0")
        digest.update(str(len(data)).encode("ascii"))
        digest.update(b"\\0")
        digest.update(data)
    return f"sha256:{digest.hexdigest()}"


def web_deploy_revision(*, dist_dir: Path, site_name: str) -> str:
    """Bind a production approval to the exact deploy tree and destination."""
    return canonical_revision(
        {
            "action": WEB_DEPLOY_ACTION,
            "destination": {"provider": "netlify", "site_name": site_name},
            "dist_tree": directory_revision(dist_dir),
            "production": True,
        }
    )


def promotion_revision(
    *,
    place_id: str,
    display_name: str,
    formatted_address: str,
    bundle: str,
    product_id: str,
    service_ids: list[str],
) -> str:
    """Bind a promotion to business identity and resulting client configuration."""
    return canonical_revision(
        {
            "action": PROMOTION_ACTION,
            "bundle": bundle,
            "business": {
                "display_name": display_name,
                "formatted_address": formatted_address,
                "place_id": place_id,
            },
            "product_id": product_id,
            "service_ids": sorted(service_ids),
        }
    )


def assert_approval_binding(
    approval_id: str | None,
    *,
    approval_type: str,
    subject_type: str,
    subject_id: str,
    action: str,
    reviewed_revision: str,
    violation_code: PolicyViolationCode,
    store: ApprovalStore | None = None,
) -> ApprovalRecord:
    """Return one approved record only when it matches all reviewed inputs."""
    if not approval_id:
        raise PolicyViolation(violation_code, "a stored approval id is required")
    approvals = store or ApprovalStore()
    try:
        record = approvals.load(approval_id)
    except FileNotFoundError as exc:
        raise PolicyViolation(violation_code, f"approval {approval_id!r} not found") from exc
    if (
        record.status is not ApprovalStatus.APPROVED
        or record.approval_type != approval_type
        or record.subject_type != subject_type
        or record.subject_id != subject_id
        or record.action != action
        or not record.reviewed_revision
        or record.reviewed_revision != reviewed_revision
    ):
        raise PolicyViolation(
            violation_code,
            "approval does not match the requested action, subject, or reviewed revision",
        )
    return record
