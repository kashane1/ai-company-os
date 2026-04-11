"""Phase 3.2 — release-readiness policy.

Gates App Store submission (and any other P0 release action) behind the
intersection of three facts:

1. The product's ``submission-checklist.md`` has zero unchecked items.
2. A typed approval record exists and is in ``approved`` state.
3. The release record itself is in the ``ready`` status (see
   :class:`packages.schemas.release.ReleaseStatus`).

Phase 3.2a wires the ``approval-token-audit`` validator into this policy
so that the magic-link HMAC chain is replayed on every call. The
validator is loaded via ``packages.tools.skills.loader.load_validator``
and runs fail-closed: any exception from the validator is caught by the
wrapper below and converted to ``PolicyViolation("approval_audit_unavailable")``.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from packages.config.settings import load_runtime_paths
from packages.db.approval_store import ApprovalStore
from packages.db.approval_token_store import ApprovalTokenStore
from packages.db.release_store import ReleaseStore
from packages.policies.approvals import PolicyViolation, is_approval_granted
from packages.policies.approval_tokens import ApprovalToken
from packages.schemas.release import ReleaseRecord, ReleaseStatus
from packages.tools.skills.loader import load_validator


APP_STORE_SUBMISSION_APPROVAL_TYPE = "app_store_submission"
PROTECTED_BRANCH_MERGE_APPROVAL_TYPE = "protected_branch_merge"
BILLING_APPROVAL_TYPE = "billing_action"
DNS_APPROVAL_TYPE = "dns_change"


class _TokenAuditStoreAdapter:
    """Adapter that presents :class:`ApprovalTokenStore` entries in the
    shape expected by ``skills/canonical/approval-token-audit/validator.py``.

    The validator treats ``approval_id`` as its lookup key, so this
    adapter resolves the most recent token for a given approval and
    projects its fields into the validator's contract.
    """

    def __init__(
        self,
        token_store: ApprovalTokenStore,
        approval_store: ApprovalStore,
    ) -> None:
        self._tokens = token_store
        self._approvals = approval_store

    def load(self, approval_id: str) -> dict[str, Any]:
        tokens = self._tokens.list_by_approval(approval_id)
        if not tokens:
            raise FileNotFoundError(f"no token for approval {approval_id}")
        token: ApprovalToken = sorted(
            tokens, key=lambda t: t.issued_at, reverse=True
        )[0]
        approval = self._approvals.load(approval_id)
        return {
            "action": token.action,
            "subject_id": token.subject_id,
            "status": approval.status.value,
            "issued_at": datetime.fromisoformat(token.issued_at),
            "approved_at": (
                datetime.fromisoformat(token.approved_at)
                if token.approved_at
                else None
            ),
            "burn_count": token.burn_count,
            "p0": token.action_class == "p0",
            "second_factor_at": (
                datetime.fromisoformat(token.second_factor_at)
                if token.second_factor_at
                else None
            ),
            "expected_device_fingerprint": token.expected_device_fingerprint,
            "device_fingerprint": token.device_fingerprint,
            "transitions": list(token.transitions),
        }


def _submission_checklist_path(product_id: str) -> Path:
    root = load_runtime_paths().repo_root
    return root / "docs" / "products" / product_id / "submission-checklist.md"


def _unchecked_items(checklist_path: Path) -> list[str]:
    if not checklist_path.exists():
        raise PolicyViolation(
            "submission_checklist_missing",
            f"checklist not found at {checklist_path}",
        )
    unchecked: list[str] = []
    for line in checklist_path.read_text().splitlines():
        stripped = line.strip()
        if stripped.startswith("- [ ]"):
            unchecked.append(stripped[5:].strip())
    return unchecked


def _run_token_audit(
    *,
    approval_id: str,
    expected_action: str,
    expected_subject_id: str,
    token_store: ApprovalTokenStore | None,
    approval_store: ApprovalStore | None,
) -> None:
    """Phase 3.2a — call the validator and fail closed on any error."""
    adapter = _TokenAuditStoreAdapter(
        token_store=token_store or ApprovalTokenStore(),
        approval_store=approval_store or ApprovalStore(),
    )
    try:
        validator = load_validator("approval-token-audit")
        result = validator.run(
            {
                "approval_id": approval_id,
                "expected_action": expected_action,
                "expected_subject_id": expected_subject_id,
                "store": adapter,
            }
        )
    except Exception as exc:  # noqa: BLE001 — fail closed
        raise PolicyViolation(
            "approval_audit_unavailable",
            f"validator raised: {type(exc).__name__}: {exc}",
        ) from exc

    if not isinstance(result, dict) or result.get("verdict") != "ok":
        reason = (
            result.get("reason", "unknown") if isinstance(result, dict) else "unknown"
        )
        raise PolicyViolation(
            "approval_audit_failed",
            f"approval-token-audit reported {reason!r}",
        )


def approve_app_store_submission(
    release_id: str,
    approval_id: str,
    *,
    product_id: str = "catchbook",
    expected_action: str = "submit_appstore",
    release_store: ReleaseStore | None = None,
    approval_store: ApprovalStore | None = None,
    token_store: ApprovalTokenStore | None = None,
) -> ReleaseRecord:
    """Gate App Store submission for ``release_id``.

    Raises :class:`PolicyViolation` with one of the machine-readable codes
    below, otherwise returns the loaded :class:`ReleaseRecord`:

    - ``submission_checklist_missing`` — no checklist file.
    - ``submission_checklist_incomplete`` — unchecked items remain.
    - ``approval_not_granted`` — approval record absent / not approved /
      wrong type.
    - ``release_not_ready`` — release record is not in ``ready``.
    - ``approval_audit_unavailable`` — the ``approval-token-audit``
      validator errored (fail-closed).
    - ``approval_audit_failed`` — validator ran but reported mismatch.
    """
    unchecked = _unchecked_items(_submission_checklist_path(product_id))
    if unchecked:
        raise PolicyViolation(
            "submission_checklist_incomplete",
            f"{len(unchecked)} unchecked item(s): {unchecked[:3]}",
        )

    if not is_approval_granted(
        approval_id,
        APP_STORE_SUBMISSION_APPROVAL_TYPE,
        store=approval_store,
    ):
        raise PolicyViolation(
            "approval_not_granted",
            f"approval {approval_id} missing or wrong type",
        )

    release_store = release_store or ReleaseStore()
    try:
        release = release_store.load_release_record(release_id)
    except FileNotFoundError as exc:
        raise PolicyViolation(
            "release_not_found",
            f"release {release_id} not found",
        ) from exc

    if release.status is not ReleaseStatus.READY_FOR_REVIEW:
        raise PolicyViolation(
            "release_not_ready",
            f"release status={release.status.value}",
        )

    _run_token_audit(
        approval_id=approval_id,
        expected_action=expected_action,
        expected_subject_id=release_id,
        token_store=token_store,
        approval_store=approval_store,
    )
    return release
