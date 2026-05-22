"""Loop-stop policy — when a worker or agent loop must stop, pause for
approval, or may continue.

Worker and agent loops carry "stop conditions" in prose: prompts say
"if the working tree is not clean, stop", "if a required check is red,
do not merge", "stop and report if any step touches a forbidden path".
That guidance lived only in prompt text and was re-derived each run.
This module makes the classification explicit, pure, and testable so
the same rule is evaluated the same way everywhere.

`evaluate()` is a pure classifier: given a `LoopStopContext` describing
a proposed continuation, it returns a `LoopStopDecision` with one of
three verdicts:

- `continue_allowed`  — no stop condition and no approval gate hit.
- `stop_required`     — a hard stop: the loop must halt and report.
- `approval_required` — the step is allowed only with explicit operator
  approval; the loop must pause, not stop permanently.

Hard stops take precedence over approval gates: a forbidden-path
violation is `stop_required` even if the same step would also need
approval. The policy never raises and never writes state — callers
decide what to do with the decision.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from packages.policies.approvals import APPROVAL_KEYWORDS


class LoopStopVerdict(str, Enum):
    """Outcome of a loop-stop evaluation."""

    CONTINUE_ALLOWED = "continue_allowed"
    STOP_REQUIRED = "stop_required"
    APPROVAL_REQUIRED = "approval_required"


class LoopStopReason(str, Enum):
    """Why the loop must stop or pause. `NONE` pairs with continue."""

    NONE = "none"
    # --- hard stops ---
    UNCLEAN_WORKING_TREE = "unclean_working_tree"
    FORBIDDEN_PATH = "forbidden_path"
    VALIDATION_FAILED = "validation_failed"
    REQUIRED_CI_RED = "required_ci_red"
    UNRESOLVED_RISK = "unresolved_risk"
    # --- approval gate ---
    APPROVAL_REQUIRED = "approval_required"


# Actions irreversible or consequential enough to need explicit operator
# approval. Extends the shared APPROVAL_KEYWORDS set with the
# version-control and destructive-operation verbs the loop-stop policy
# also guards. Reused, not redefined, so the two surfaces stay aligned.
IRREVERSIBLE_ACTION_KEYWORDS: frozenset[str] = frozenset(APPROVAL_KEYWORDS) | {
    "push",
    "force-push",
    "reset",
    "rebase",
    "delete",
    "drop",
    "destroy",
    "overwrite",
}


@dataclass(frozen=True)
class LoopStopContext:
    """A snapshot of the facts a stop/continue decision depends on.

    Every field defaults to a no-signal value, so a caller populates
    only what is relevant to the step it is about to take. A "can I
    start this task?" caller sets `working_tree_clean`; a "can I merge?"
    caller sets `required_ci_green`, `proposed_action`, and
    `action_authorized`.
    """

    working_tree_clean: bool = True
    touched_paths: tuple[str, ...] = ()
    forbidden_path_prefixes: tuple[str, ...] = ()
    validation_passed: bool | None = None
    required_ci_green: bool | None = None
    risk_unresolved: bool = False
    proposed_action: str = ""
    action_authorized: bool = False


@dataclass(frozen=True)
class LoopStopDecision:
    """The classified outcome, with a worker-report-ready message."""

    verdict: LoopStopVerdict
    reason: LoopStopReason
    message: str

    @property
    def should_stop(self) -> bool:
        return self.verdict is LoopStopVerdict.STOP_REQUIRED

    @property
    def needs_approval(self) -> bool:
        return self.verdict is LoopStopVerdict.APPROVAL_REQUIRED

    @property
    def may_continue(self) -> bool:
        return self.verdict is LoopStopVerdict.CONTINUE_ALLOWED

    def to_dict(self) -> dict[str, str]:
        """JSON-friendly form for worker reports / task-run records."""
        return {
            "verdict": self.verdict.value,
            "reason": self.reason.value,
            "message": self.message,
        }


def forbidden_paths_touched(
    touched_paths: tuple[str, ...],
    forbidden_path_prefixes: tuple[str, ...],
) -> list[str]:
    """Return the touched paths that fall under a forbidden prefix."""
    return [
        path
        for path in touched_paths
        if any(
            path.startswith(prefix) for prefix in forbidden_path_prefixes
        )
    ]


def action_needs_approval(proposed_action: str) -> bool:
    """True when `proposed_action` names an irreversible / gated action."""
    action = proposed_action.lower()
    return any(
        keyword in action for keyword in IRREVERSIBLE_ACTION_KEYWORDS
    )


def _stop(reason: LoopStopReason, message: str) -> LoopStopDecision:
    return LoopStopDecision(LoopStopVerdict.STOP_REQUIRED, reason, message)


def evaluate(context: LoopStopContext) -> LoopStopDecision:
    """Classify a proposed continuation into continue / stop / approval.

    Hard stop conditions are checked first and in priority order; any one
    of them is `stop_required`. Only when no hard stop applies does an
    approval-gated action produce `approval_required`. With neither, the
    loop may continue.
    """
    # --- hard stops (the loop must halt and report) ---
    if not context.working_tree_clean:
        return _stop(
            LoopStopReason.UNCLEAN_WORKING_TREE,
            "Working tree is not clean before starting; stop and report "
            "instead of building on unknown local state.",
        )

    forbidden = forbidden_paths_touched(
        context.touched_paths, context.forbidden_path_prefixes
    )
    if forbidden:
        return _stop(
            LoopStopReason.FORBIDDEN_PATH,
            "Proposed step touches forbidden path(s): "
            f"{', '.join(sorted(forbidden))}. Stop and report instead of "
            "crossing the scope boundary.",
        )

    if context.validation_passed is False:
        return _stop(
            LoopStopReason.VALIDATION_FAILED,
            "Validation failed; stop and report the failure instead of "
            "continuing on a broken state.",
        )

    if context.required_ci_green is False:
        return _stop(
            LoopStopReason.REQUIRED_CI_RED,
            "A required CI check is red; stop and report instead of "
            "merging or proceeding past the gate.",
        )

    if context.risk_unresolved:
        return _stop(
            LoopStopReason.UNRESOLVED_RISK,
            "The proposed step carries unresolved or ambiguous risk; "
            "stop and report so a human can decide.",
        )

    # --- approval gate (the loop must pause, not stop permanently) ---
    if (
        context.proposed_action
        and action_needs_approval(context.proposed_action)
        and not context.action_authorized
    ):
        return LoopStopDecision(
            LoopStopVerdict.APPROVAL_REQUIRED,
            LoopStopReason.APPROVAL_REQUIRED,
            f"Proposed action {context.proposed_action!r} is irreversible "
            "or consequential and is not authorized; request explicit "
            "operator approval before continuing.",
        )

    return LoopStopDecision(
        LoopStopVerdict.CONTINUE_ALLOWED,
        LoopStopReason.NONE,
        "No stop condition and no approval gate; the loop may continue.",
    )
