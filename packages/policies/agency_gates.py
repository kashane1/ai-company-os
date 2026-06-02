"""Agency-layer approval gates (Phase 3).

Promoting a prospect into a paying client and sending a proposal are
irreversible, externally-visible commitments. Like the web-deploy lane
(``deploy_readiness``) and App Store releases (``release_readiness``), policy is
owned here — not by the promotion code or a CLI — and a refusal raises
:class:`~packages.policies.approvals.PolicyViolation` with a machine-readable
code.

These gates take an explicit ``approval_granted`` boolean. A future iteration can
swap to the typed approval-token audit (``approvals.is_approval_granted``) once
agency approvals flow through the ``ApprovalStore``; the call sites stay the same.
"""

from __future__ import annotations

from packages.policies.approvals import PolicyViolation, PolicyViolationCode


def assert_promotion_allowed(*, human_verified: bool, approval_granted: bool) -> None:
    """Authorize promoting a prospect into a client engagement, or raise.

    Two preconditions, both surfaced as ``CLIENT_PROMOTION_NOT_APPROVED`` with a
    distinguishing detail:

    * the prospect must be human-verified (the no-owned-website signal still
      holds) — promotion off an unverified prospect is refused;
    * a founder approval must be granted (a client engagement is a commercial
      commitment).
    """
    if not human_verified:
        raise PolicyViolation(
            PolicyViolationCode.CLIENT_PROMOTION_NOT_APPROVED,
            "prospect is not human-verified; refuse to promote until the "
            "no-owned-website signal is confirmed",
        )
    if not approval_granted:
        raise PolicyViolation(
            PolicyViolationCode.CLIENT_PROMOTION_NOT_APPROVED,
            "promoting a prospect into a billing client requires a granted approval",
        )


def assert_proposal_send_allowed(*, approval_granted: bool) -> None:
    """Sending a proposal to a prospect always requires approval."""
    if not approval_granted:
        raise PolicyViolation(
            PolicyViolationCode.PROPOSAL_SEND_NOT_APPROVED,
            "sending a proposal requires a granted approval",
        )
