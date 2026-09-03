"""Revision-bound permission for the operated Printify draft workflow."""

from packages.policies.approvals import PolicyViolation, PolicyViolationCode
from packages.schemas.approval import ApprovalRecord, ApprovalStatus


def require_draft_approval(record: ApprovalRecord, revision: str) -> None:
    if not (
        record.status is ApprovalStatus.APPROVED
        and record.approval_type == "pod_draft_update"
        and record.subject_type == "pod_manifest"
        and record.subject_id == revision
        and record.action == "update_printify_draft"
    ):
        raise PolicyViolation(
            PolicyViolationCode.APPROVAL_NOT_GRANTED,
            "An approved pod_draft_update record must match this exact manifest revision.",
        )
