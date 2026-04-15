"""Phase 0.5d.1 — PolicyViolationCode enum tests.

Verifies:

1. `PolicyViolationCode` is a `str, Enum` subclass whose members compare
   equal to their string values (backward compatibility with existing
   `exc.code == "foo"` call sites).

2. The `PolicyViolation` constructor accepts both enum members and raw
   strings (rollout is additive — old call sites keep working).

3. Every code referenced in the plan's X1 enumerated list has a
   corresponding enum member (byte-completeness check).
"""
from __future__ import annotations

from packages.policies.approvals import PolicyViolation, PolicyViolationCode


def test_code_is_str_enum_and_compares_equal_to_string() -> None:
    # str, Enum subclasses compare equal to their string value.
    assert PolicyViolationCode.FIXTURE_SKILL_DRIFT == "fixture_skill_drift"
    assert PolicyViolationCode.APPROVAL_AUDIT_UNAVAILABLE == "approval_audit_unavailable"


def test_policy_violation_accepts_enum_member() -> None:
    exc = PolicyViolation(PolicyViolationCode.FIXTURE_SKILL_DRIFT)
    assert exc.code == "fixture_skill_drift"
    assert str(exc) == "fixture_skill_drift"


def test_policy_violation_accepts_raw_string_backward_compat() -> None:
    # Existing call sites in release_readiness.py and claude_entrypoint.py
    # raise with bare strings. Those keep working without churn.
    exc = PolicyViolation("approval_audit_unavailable")
    assert exc.code == "approval_audit_unavailable"


def test_policy_violation_accepts_detail_message() -> None:
    exc = PolicyViolation(
        PolicyViolationCode.COMMAND_SCAN_DENIED,
        detail="rm -rf / denied",
    )
    assert exc.code == "command_scan_denied"
    assert "rm -rf /" in str(exc)


def test_code_matches_raw_string_in_equality_check() -> None:
    """Existing callers switch on ``exc.code == "foo"``. Prove that
    still works when the raise site uses the enum member.
    """
    exc = PolicyViolation(PolicyViolationCode.APPROVAL_NOT_GRANTED)
    # Both comparisons must succeed — callers that do enum-aware checks
    # AND callers that do string checks both continue working.
    assert exc.code == "approval_not_granted"
    assert exc.code == PolicyViolationCode.APPROVAL_NOT_GRANTED


def test_x1_plan_codes_all_present() -> None:
    """Byte-completeness check against the plan's X1 enumerated list.

    If a new Phase adds a PolicyViolationCode member and forgets to
    land it here, this test catches the drift.
    """
    required = {
        # Phase 3
        "fixture_skill_drift",
        "regression_against_incumbent",
        "config_mutation_requires_human",
        "runtime_expansion_requires_human",
        "skill_not_self_evolvable",
        "concurrent_evolution_in_progress",
        "third_file_smuggling",
        # Phase 4
        "acp_peer_not_allowed",
        "acp_peer_crash",
        "acp_protocol_error",
        "acp_max_attempts_exceeded",
        # Phase 5
        "command_scan_denied",
        "command_scan_unavailable",
        "command_scan_requires_approval",
        # Phase 6
        "provider_unavailable",
        "provider_not_registered",
        # Cross-cutting
        "dispatch_health_payload_oversized",
    }
    actual = {member.value for member in PolicyViolationCode}
    missing = required - actual
    assert not missing, (
        f"PolicyViolationCode is missing expected members: {missing}. "
        "Either add them to the enum or update this test if the plan "
        "dropped a code."
    )
