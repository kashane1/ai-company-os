"""Agent-callable approval primitives (Phase 3, Option B).

This package wraps the Phase 3.1 HMAC approval-token infrastructure
(:mod:`packages.policies.approval_tokens` +
:class:`packages.db.approval_token_store.ApprovalTokenStore` +
:class:`packages.db.approval_store.ApprovalStore`) in a narrow, typed API that
the skill-self-evolution worker — and any agent that needs a human gate in front
of an action — can consume.

It was a single 1,000-line module; it is now split for readability into:

- ``_models``    — :class:`ApprovalRequest`, :class:`ApprovalDecision`, constants.
- ``_evolution`` — request / poll / submit / reject flow.
- ``_signing``   — HMAC signing-secret loading (env var, macOS Keychain,
  filesystem fallback) and the Keychain error hierarchy.

The split is behaviour-preserving: this ``__init__`` re-exports the exact same
public + tested surface the flat module exposed, so every existing
``from packages.tools.primitives.approvals import X`` keeps working. Import from
this package, not from the private submodules.

Design contract (per ``packages/tools/primitives/__init__.py``): stateless at
module level, side-effect-free to import, typed returns, single operations only.
See ``docs/plans/2026-04-15-macos-keychain-approval-signing-migration.md`` for
the Keychain threat-model rationale.
"""
from __future__ import annotations

# Third-party names that were importable from the flat module (re-exported so
# callers that did `from ...approvals import ApprovalStore` keep working).
from packages.db.approval_store import ApprovalStore
from packages.db.approval_token_store import ApprovalTokenStore
from packages.policies.approval_tokens import (
    ApprovalToken,
    ApprovalTokenError,
    TokenAlreadyBurned,
    TokenExpired,
    TokenNotFound,
    TokenSignatureInvalid,
    issue_token,
    verify_and_burn_token,
)
from packages.schemas.approval import ApprovalRecord, ApprovalStatus

# Evolution flow
from packages.tools.primitives.approvals._evolution import (
    _default_device_binding,
    _now_iso,
    poll_evolution_approval,
    reject_evolution_approval,
    request_evolution_approval,
    submit_evolution_approval,
)

# Data models + evolution constants
from packages.tools.primitives.approvals._models import (
    SKILL_EVOLUTION_ACTION,
    SKILL_EVOLUTION_APPROVAL_TYPE,
    ApprovalDecision,
    ApprovalOutcome,
    ApprovalRequest,
)

# Signing-secret loading + Keychain error hierarchy + signing constants
from packages.tools.primitives.approvals._signing import (
    FORCE_FILE_ENV_VAR,
    KEYCHAIN_ACCOUNT,
    KEYCHAIN_SERVICE,
    SIGNING_KEY_ENV_VAR,
    KeychainAccessDenied,
    KeychainAlreadyExists,
    KeychainError,
    KeychainNotFound,
    KeychainUserCancelled,
    _bootstrap_keychain_secret,
    _decode_env_secret,
    _is_access_denied_stderr,
    _is_user_cancelled_stderr,
    _load_signing_secret,
    _read_filesystem_secret,
    _read_keychain_secret,
    _rotate_keychain_secret,
)

__all__ = [
    "ApprovalDecision",
    "ApprovalOutcome",
    "ApprovalRequest",
    "SKILL_EVOLUTION_ACTION",
    "SKILL_EVOLUTION_APPROVAL_TYPE",
    "poll_evolution_approval",
    "reject_evolution_approval",
    "request_evolution_approval",
    "submit_evolution_approval",
    "_default_device_binding",
    "_now_iso",
    "FORCE_FILE_ENV_VAR",
    "KEYCHAIN_ACCOUNT",
    "KEYCHAIN_SERVICE",
    "SIGNING_KEY_ENV_VAR",
    "KeychainAccessDenied",
    "KeychainAlreadyExists",
    "KeychainError",
    "KeychainNotFound",
    "KeychainUserCancelled",
    "_bootstrap_keychain_secret",
    "_decode_env_secret",
    "_is_access_denied_stderr",
    "_is_user_cancelled_stderr",
    "_load_signing_secret",
    "_read_filesystem_secret",
    "_read_keychain_secret",
    "_rotate_keychain_secret",
    "ApprovalStore",
    "ApprovalTokenStore",
    "ApprovalToken",
    "ApprovalTokenError",
    "TokenAlreadyBurned",
    "TokenExpired",
    "TokenNotFound",
    "TokenSignatureInvalid",
    "issue_token",
    "verify_and_burn_token",
    "ApprovalRecord",
    "ApprovalStatus",
]
