# Skill: approval-token-audit

Kind: validator (pure HMAC replay; no LLM call)
Owner: supervisor
Runtimes: claude

## Purpose

Before any P0 action executes, replay the magic-link HMAC chain for the
cited approval and verify: token issuance matches the expected action and
subject, TTL was honored, single-use flag was burned exactly once,
second-factor confirmation exists within the 60-second window, device
fingerprint matches, and the approval record transitioned through expected
states.

Called synchronously from:
- `packages/policies/release_readiness.py::approve_app_store_submission`
- protected-branch merge policy
- billing action policy
- DNS action policy

## Fail-closed

Any exception → `PolicyViolation("approval_audit_unavailable")`. Never
returns "approved" on error. Policy wrapper is responsible for the raise.

## Contract

Input: `{approval_id, expected_action, expected_subject_id, store}`.
`store` is an injectable approval-store-like object with `.load(approval_id)`.

Output: `{verdict: ok | fail, reason: str, events: [str,...]}`.
