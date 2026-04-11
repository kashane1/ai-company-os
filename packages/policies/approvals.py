from packages.db.approval_store import ApprovalStore
from packages.schemas.approval import ApprovalRecord, ApprovalStatus
from packages.schemas.task_packet import RiskLevel, TaskPacket, WorkerLane


class PolicyViolation(RuntimeError):
    """Raised when a policy check refuses to authorize an action.

    Always carries a short machine-readable ``code`` alongside the human
    message so callers can switch on the reason without string parsing.
    """

    def __init__(self, code: str, detail: str | None = None) -> None:
        self.code = code
        super().__init__(detail or code)


APPROVAL_KEYWORDS = {
    "merge",
    "deploy",
    "submit",
    "release",
    "billing",
    "dns",
    "pricing",
    "production",
}

SAFE_RELEASE_ACTIONS = {"prepare_testflight"}
APPROVAL_REQUIRED_RELEASE_ACTIONS = {
    "submit_testflight",
    "submit_appstore",
    "release_to_store",
}


def requires_human_approval(task: TaskPacket) -> bool:
    if task.risk_level is RiskLevel.HIGH:
        return True

    summary = f"{task.title} {task.summary}".lower()
    if any(keyword in summary for keyword in APPROVAL_KEYWORDS):
        return True

    return task.lane is WorkerLane.APPSTORE and "submit" in summary


def requires_release_action_approval(action: str) -> bool:
    if action in SAFE_RELEASE_ACTIONS:
        return False
    return action in APPROVAL_REQUIRED_RELEASE_ACTIONS


def is_approval_granted(
    approval_id: str,
    expected_type: str,
    *,
    store: ApprovalStore | None = None,
) -> bool:
    """Phase 3.2 helper — true iff the referenced approval is approved and
    matches ``expected_type``.

    Used by ``packages.policies.release_readiness`` and any other policy
    that blocks on a typed approval. Never raises for a missing record;
    returns ``False`` instead so callers can produce a single uniform
    PolicyViolation path.
    """
    approvals = store or ApprovalStore()
    try:
        record: ApprovalRecord = approvals.load(approval_id)
    except FileNotFoundError:
        return False
    if record.status is not ApprovalStatus.APPROVED:
        return False
    return record.approval_type == expected_type
