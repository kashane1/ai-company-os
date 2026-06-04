from enum import Enum

from packages.db.approval_store import ApprovalStore
from packages.schemas.approval import ApprovalRecord, ApprovalStatus
from packages.schemas.task_packet import RiskLevel, TaskPacket, WorkerLane


class PolicyViolationCode(str, Enum):
    """Canonical policy-violation codes (Phase 0.5d.1).

    Every new raise site in ``packages/policies/`` SHOULD use an enum
    member instead of a bare string. Backward compatibility: the
    ``PolicyViolation`` constructor still accepts raw strings so this
    rollout is additive and existing call sites keep working without
    churn. The ``test_policy_violation_codes_enumerated`` guard in
    ``tests/python/unit/test_approvals.py`` flags any new bare-string
    raise site so the enum becomes the default by convention.

    Members are grouped by the Phase that introduces them per
    docs/plans/2026-04-14-feat-hermes-inspired-platform-upgrade-plan.md
    section X1. Existing codes used in release_readiness.py and
    claude_entrypoint.py are enumerated so the whole surface is
    discoverable from one place.

    Enum members inherit ``str`` so ``PolicyViolationCode.FOO == "foo"``
    is True — callers that switch on ``exc.code`` keep working with
    either the enum or the string form.
    """

    # --- Existing codes (kept for enum coverage of current raise sites) ---

    # release_readiness.py
    SUBMISSION_CHECKLIST_MISSING = "submission_checklist_missing"
    SUBMISSION_CHECKLIST_INCOMPLETE = "submission_checklist_incomplete"
    APPROVAL_AUDIT_UNAVAILABLE = "approval_audit_unavailable"
    APPROVAL_AUDIT_FAILED = "approval_audit_failed"
    APPROVAL_NOT_GRANTED = "approval_not_granted"
    RELEASE_NOT_FOUND = "release_not_found"
    RELEASE_NOT_READY = "release_not_ready"

    # supervisor claude_entrypoint.py
    INVALID_STRATEGIC_TASK_TYPE = "invalid_strategic_task_type"
    STRATEGIC_TASK_LOST = "strategic_task_lost"
    STRATEGIC_TASK_TYPE_DRIFT = "strategic_task_type_drift"

    # --- Phase 3 (skill self-evolution loop) ---
    FIXTURE_SKILL_DRIFT = "fixture_skill_drift"
    REGRESSION_AGAINST_INCUMBENT = "regression_against_incumbent"
    CONFIG_MUTATION_REQUIRES_HUMAN = "config_mutation_requires_human"
    RUNTIME_EXPANSION_REQUIRES_HUMAN = "runtime_expansion_requires_human"
    SKILL_NOT_SELF_EVOLVABLE = "skill_not_self_evolvable"
    CONCURRENT_EVOLUTION_IN_PROGRESS = "concurrent_evolution_in_progress"
    THIRD_FILE_SMUGGLING = "third_file_smuggling"

    # --- Phase 4 (ACP peer-runtime dispatch) ---
    ACP_PEER_NOT_ALLOWED = "acp_peer_not_allowed"
    ACP_PEER_CRASH = "acp_peer_crash"
    ACP_PROTOCOL_ERROR = "acp_protocol_error"
    ACP_MAX_ATTEMPTS_EXCEEDED = "acp_max_attempts_exceeded"

    # --- Phase 5 (command-scan policy) ---
    COMMAND_SCAN_DENIED = "command_scan_denied"
    COMMAND_SCAN_UNAVAILABLE = "command_scan_unavailable"
    COMMAND_SCAN_REQUIRES_APPROVAL = "command_scan_requires_approval"

    # --- Phase 6 (provider overlay registry) ---
    PROVIDER_UNAVAILABLE = "provider_unavailable"
    PROVIDER_NOT_REGISTERED = "provider_not_registered"

    # --- Cross-cutting dispatch health ---
    DISPATCH_HEALTH_PAYLOAD_OVERSIZED = "dispatch_health_payload_oversized"

    # --- ECC Gap Recommendations Phase 1 (research-first skills) ---
    INSUFFICIENT_SCOPE = "insufficient_scope"
    NOT_A_DOC_LOOKUP = "not_a_doc_lookup"
    INVALID_AREA_PATH = "invalid_area_path"

    # --- ECC Gap Recommendations Phase 3 (verification-loop) ---
    VERIFICATION_LOOP_HARD_FAIL = "verification_loop_hard_fail"

    # --- Discovery layer (opportunity → validate → build gates) ---
    # Soft validate-gate reasons (surfaced in AdvancementDecision, not raised):
    DISCOVERY_RISK_TOO_HIGH = "discovery_risk_too_high"
    DISCOVERY_BLOCKED_COMPLIANCE_FLAG = "discovery_blocked_compliance_flag"
    DISCOVERY_NO_DISTRIBUTION = "discovery_no_distribution"
    DISCOVERY_SCORE_BELOW_THRESHOLD = "discovery_score_below_threshold"
    DISCOVERY_LOW_CONFIDENCE = "discovery_low_confidence"
    # Hard build-gate reasons (raised as PolicyViolation):
    DISCOVERY_OPPORTUNITY_NOT_VALIDATED = "discovery_opportunity_not_validated"
    DISCOVERY_EXPERIMENT_NOT_PASSED = "discovery_experiment_not_passed"
    DISCOVERY_MISSING_SUCCESS_CRITERIA = "discovery_missing_success_criteria"
    # Bulk-crawl gate (C1):
    DISCOVERY_BULK_CRAWL_NOT_APPROVED = "discovery_bulk_crawl_not_approved"
    DISCOVERY_BULK_CRAWL_PRECONDITION = "discovery_bulk_crawl_precondition"
    # Outreach gate for sending experiments (C3):
    DISCOVERY_OUTREACH_NOT_REVIEWED = "discovery_outreach_not_reviewed"
    DISCOVERY_OUTREACH_UNSUBSCRIBE_MISSING = "discovery_outreach_unsubscribe_missing"
    DISCOVERY_OUTREACH_SUPPRESSION_MISSING = "discovery_outreach_suppression_missing"
    DISCOVERY_OUTREACH_SPEND_UNAPPROVED = "discovery_outreach_spend_unapproved"

    # --- Web deploy lane (Section F): publishing a site is high blast radius ---
    DEPLOY_BUILD_NOT_VALIDATED = "deploy_build_not_validated"
    DEPLOY_PREVIEW_NOT_REVIEWED = "deploy_preview_not_reviewed"
    DEPLOY_APPROVAL_NOT_GRANTED = "deploy_approval_not_granted"
    DEPLOY_DNS_NOT_APPROVED = "deploy_dns_not_approved"
    DEPLOY_SPEND_NOT_APPROVED = "deploy_spend_not_approved"
    # Live Stripe payments move real money — gated like billing/pricing.
    PAYMENTS_LIVE_NOT_APPROVED = "payments_live_not_approved"

    # --- Agency layer (Phase 3): client engagements are commercial commitments ---
    # Promoting a prospect into a billing client and sending a proposal are both
    # irreversible, externally-visible actions — gated like deploy/payments.
    CLIENT_PROMOTION_NOT_APPROVED = "client_promotion_not_approved"
    PROPOSAL_SEND_NOT_APPROVED = "proposal_send_not_approved"
    RETAINER_APPROVAL_NOT_GRANTED = "retainer_approval_not_granted"
    RETAINER_APPROVAL_ARTIFACT_MISSING = "retainer_approval_artifact_missing"
    REVIEW_SMS_COMPLIANCE_MISSING = "review_sms_compliance_missing"
    REVIEW_SMS_TEMPLATE_NOT_APPROVED = "review_sms_template_not_approved"
    REVIEW_SMS_CADENCE_INVALID = "review_sms_cadence_invalid"
    # Paid client work (retainer fulfilment) is refused unless the client is
    # actively billed — closes the dispute/refund → keeps-working loop (G1+E2).
    RETAINER_CLIENT_NOT_ACTIVE = "retainer_client_not_active"


class PolicyViolation(RuntimeError):
    """Raised when a policy check refuses to authorize an action.

    Always carries a short machine-readable ``code`` alongside the human
    message so callers can switch on the reason without string parsing.

    Accepts either a :class:`PolicyViolationCode` enum member (preferred
    for new code) or a raw string (backward compat for existing call
    sites and dynamic codes like ``f"claude_output_{exc.code}"``).
    """

    def __init__(
        self,
        code: "PolicyViolationCode | str",
        detail: str | None = None,
    ) -> None:
        # Store the string value so existing ``exc.code == "foo"`` checks
        # keep working. PolicyViolationCode(str, Enum) auto-coerces.
        self.code = code.value if isinstance(code, PolicyViolationCode) else code
        super().__init__(detail or self.code)


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
