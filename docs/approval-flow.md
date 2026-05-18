# Approval Flow

This document explains the review and approval boundary for the platform.

## When A Run Becomes Reviewable

An engineering run becomes reviewable only when:

- Codex execution finishes successfully
- validator checks pass
- the worktree contains tracked file changes worth inspecting

That result is classified as `safe_for_review`.

If execution fails, the result is `execution_failed`.

If execution succeeds but validation fails, the result is `validation_failed`.

If execution succeeds and there are no tracked file changes, the result is `no_change`.

## Artifacts Available For Inspection

For each run, the system persists:

- task record
- task run record
- worktree metadata
- rendered Codex packet
- Codex stdout and stderr logs
- diff artifact
- review summary artifact

These are intended to make manual inspection explicit instead of guesswork.

## What Approval Gates

Approval records gate consequential actions such as:

- commit creation
- branch updates
- push
- pull request creation
- merge
- App Store submission
- public release actions
- billing, DNS, and other P0 operations

The gate is intentionally layered. Reviewable worker output can create an
approval record; approval tokens provide the local human confirmation surface;
policy code decides whether a downstream action is allowed to proceed.

## Magic-Link Approval Surface

The local approval endpoint lives in `apps/api/approval_endpoint.py`.
Approval links carry HMAC-signed tokens from
`packages/policies/approval_tokens.py`, persisted by
`packages/db/approval_token_store.py`.

Tokens are:

- short-lived
- single-use
- device-audited
- classified as default or P0

Default actions can be approved with one local confirmation. P0 actions require
a second confirmation inside the configured window before the approval can move
to `approved`.

## What Remains Manual

The system still does not treat approval as blanket authority. Humans inspect
diffs, artifacts, release state, and generated metadata before allowing
irreversible effects. The platform prepares reviewable output, records the
approval decision, and leaves an audit trail for the action that consumed it.
