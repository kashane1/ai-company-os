"""Unit tests for the loop-stop policy.

Exercises `evaluate()` and the two helpers against each verdict and
reason, plus the hard-stop-over-approval precedence rule.
"""
from __future__ import annotations

from packages.policies.loop_stop import (
    LoopStopContext,
    LoopStopReason,
    LoopStopVerdict,
    action_needs_approval,
    evaluate,
    forbidden_paths_touched,
)


def test_clean_context_allows_continue() -> None:
    decision = evaluate(LoopStopContext())
    assert decision.verdict is LoopStopVerdict.CONTINUE_ALLOWED
    assert decision.reason is LoopStopReason.NONE
    assert decision.may_continue is True
    assert decision.should_stop is False
    assert decision.needs_approval is False


def test_unclean_working_tree_stops() -> None:
    decision = evaluate(LoopStopContext(working_tree_clean=False))
    assert decision.verdict is LoopStopVerdict.STOP_REQUIRED
    assert decision.reason is LoopStopReason.UNCLEAN_WORKING_TREE
    assert decision.should_stop is True


def test_forbidden_path_touched_stops() -> None:
    decision = evaluate(
        LoopStopContext(
            touched_paths=("packages/policies/loop_stop.py", "products/x/y.swift"),
            forbidden_path_prefixes=("products/",),
        )
    )
    assert decision.verdict is LoopStopVerdict.STOP_REQUIRED
    assert decision.reason is LoopStopReason.FORBIDDEN_PATH
    assert "products/x/y.swift" in decision.message


def test_touched_paths_outside_forbidden_set_continue() -> None:
    decision = evaluate(
        LoopStopContext(
            touched_paths=("packages/policies/loop_stop.py",),
            forbidden_path_prefixes=("products/", "state/"),
        )
    )
    assert decision.verdict is LoopStopVerdict.CONTINUE_ALLOWED


def test_validation_failed_stops() -> None:
    decision = evaluate(LoopStopContext(validation_passed=False))
    assert decision.verdict is LoopStopVerdict.STOP_REQUIRED
    assert decision.reason is LoopStopReason.VALIDATION_FAILED


def test_validation_none_or_passed_is_not_a_stop() -> None:
    assert evaluate(LoopStopContext(validation_passed=None)).may_continue
    assert evaluate(LoopStopContext(validation_passed=True)).may_continue


def test_required_ci_red_stops() -> None:
    decision = evaluate(LoopStopContext(required_ci_green=False))
    assert decision.verdict is LoopStopVerdict.STOP_REQUIRED
    assert decision.reason is LoopStopReason.REQUIRED_CI_RED


def test_required_ci_pending_is_not_a_stop() -> None:
    # `None` means unknown / pending — not a hard stop on its own.
    assert evaluate(LoopStopContext(required_ci_green=None)).may_continue


def test_unresolved_risk_stops() -> None:
    decision = evaluate(LoopStopContext(risk_unresolved=True))
    assert decision.verdict is LoopStopVerdict.STOP_REQUIRED
    assert decision.reason is LoopStopReason.UNRESOLVED_RISK


def test_approval_gated_action_unauthorized_needs_approval() -> None:
    decision = evaluate(
        LoopStopContext(proposed_action="merge PR #61", action_authorized=False)
    )
    assert decision.verdict is LoopStopVerdict.APPROVAL_REQUIRED
    assert decision.reason is LoopStopReason.APPROVAL_REQUIRED
    assert decision.needs_approval is True


def test_approval_gated_action_authorized_continues() -> None:
    decision = evaluate(
        LoopStopContext(proposed_action="merge PR #61", action_authorized=True)
    )
    assert decision.verdict is LoopStopVerdict.CONTINUE_ALLOWED


def test_non_gated_action_continues() -> None:
    decision = evaluate(LoopStopContext(proposed_action="edit a source file"))
    assert decision.verdict is LoopStopVerdict.CONTINUE_ALLOWED


def test_hard_stop_takes_precedence_over_approval() -> None:
    """A forbidden-path violation is `stop_required` even though the
    same step also names an unauthorized approval-gated action."""
    decision = evaluate(
        LoopStopContext(
            touched_paths=("state/checkpoints/x.json",),
            forbidden_path_prefixes=("state/",),
            proposed_action="push to origin",
            action_authorized=False,
        )
    )
    assert decision.verdict is LoopStopVerdict.STOP_REQUIRED
    assert decision.reason is LoopStopReason.FORBIDDEN_PATH


def test_decision_to_dict_is_json_friendly() -> None:
    decision = evaluate(LoopStopContext(working_tree_clean=False))
    payload = decision.to_dict()
    assert payload == {
        "verdict": "stop_required",
        "reason": "unclean_working_tree",
        "message": decision.message,
    }
    assert all(isinstance(v, str) for v in payload.values())


def test_forbidden_paths_touched_helper() -> None:
    touched = forbidden_paths_touched(
        ("apps/api/main.py", "packages/policies/loop_stop.py"),
        ("packages/schemas/", "apps/"),
    )
    assert touched == ["apps/api/main.py"]


def test_action_needs_approval_helper() -> None:
    assert action_needs_approval("git push origin main") is True
    assert action_needs_approval("force-push to main") is True
    assert action_needs_approval("submit to App Store") is True
    assert action_needs_approval("reset --hard") is True
    assert action_needs_approval("read a file") is False
    assert action_needs_approval("") is False
