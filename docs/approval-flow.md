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

## Local configuration and exact review binding

Bind the API to `127.0.0.1`. Generic `POST /approvals/{id}/decision` calls
require `Authorization: Bearer <local capability>` and the corresponding
`AI_COMPANY_OS_LOCAL_OPERATOR_BEARER_TOKEN` environment variable. Missing
configuration returns 503; a missing or incorrect bearer returns 401. This is a
local operator capability, not authentication between mutually untrusted users.

P0 approval cannot be granted through that generic decision route. Use the
signed confirmation surface; the first confirmation leaves the approval
pending, and the second must arrive within its allowed window. Rejection is
terminal and cannot be overwritten by a later confirmation. Replays are refused.
These are two confirmations using one token/device, not independent MFA.

The endpoint and approval primitives share `AI_COMPANY_OS_APPROVAL_SIGNING_KEY`:
a hex-encoded secret of at least 32 bytes. The configured local credential
provider may supply it when the environment does not. Tests use deterministic
fake values and do not require the author's credential store. Keep both secrets
in the process environment or local ignored configuration, never in source.

Production web deployment and prospect promotion require a stored approved
record with matching `approval_type`, `subject_type`, `subject_id`, `action`, and
`reviewed_revision`. The revision helpers are in
[approval_bindings.py](../packages/policies/approval_bindings.py); promotion also
exposes `promotion_reviewed_revision` in
[promotion.py](../packages/agency/promotion.py). Include the resulting revision
when requesting the approval. Review the actual action inputs before deciding it.

- Web deployment binds the Netlify site, production mode, and the entire `dist/`
  tree's relative paths and file bytes. Symlinks are refused. Changing the build
  or destination requires a new approval.
- Promotion binds the prospect identity, selected bundle, and resulting product
  and service configuration. A typed name or boolean flag is insufficient.
- Old records without a revision remain readable but cannot authorize these two
  writers. Token expiry limits the confirmation window; stored approvals remain
  tied to their reviewed revision rather than becoming general permission.

Local same-user code can access the same files and credentials. This design
helps prevent accidental or misrouted actions within a trusted local workflow;
it does not isolate malicious code running under the operator's account.
