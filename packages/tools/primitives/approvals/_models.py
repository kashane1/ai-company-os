"""Approval primitive data models + evolution constants.

Split out of the original single-file ``approvals`` module for readability.
The public API is re-exported from ``approvals/__init__.py`` — import from there,
not from this submodule.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

# Action string stamped on skill-evolution approval requests. Keep in
# sync with the matching reader in
# ``packages/policies/skill_evolution.py:_EVOLUTION_APPROVAL_ACTION``.
SKILL_EVOLUTION_ACTION = "skill_evolution_apply"

# Approval record type (used by ``is_approval_granted``). Workers and
# policies test against this string so any drift is a loud failure,
# not a silent mismatch.
SKILL_EVOLUTION_APPROVAL_TYPE = "skill_evolution"

ApprovalOutcome = Literal["pending", "approved", "rejected", "expired"]


@dataclass(frozen=True)
class ApprovalRequest:
    """Return value of :func:`request_evolution_approval`.

    The reviewer needs the ``token_id`` + ``signature`` pair to sign;
    the worker needs the ``approval_id`` to poll on. Everything else
    exists for auditing.
    """

    approval_id: str
    token_id: str
    signature: str
    action: str
    subject_id: str
    artifact_dir: str
    created_at: str


@dataclass(frozen=True)
class ApprovalDecision:
    """Return value of :func:`poll_evolution_approval`.

    ``outcome`` is the single field callers normally branch on.
    """

    approval_id: str
    outcome: ApprovalOutcome
    decided_by: str | None
    decided_at: str | None
    decision_notes: str | None

