# Recurring Approval Sweep

This is the concrete recurring workflow behind the README claim that operator
workflows are designed around approval gates.

The sweep is intentionally conservative: it observes approval state and links
evidence, but it does not decide approvals. The local magic-link endpoint is the
only writer allowed to flip an approval to `approved`.

## Schedule

The operator prompt lives at
[`scripts/scheduled/approval_sweep_session.md`](../scripts/scheduled/approval_sweep_session.md).
It is written for a Cowork `scheduled-tasks` session that runs every 15 minutes.

The prompt exists because Gmail access is available from a scheduled Claude
session, not from a long-running Python daemon. That keeps the credentialed
inbox surface out of worker daemons while still letting the platform reconcile
approval evidence on a rhythm.

## Approval Path

1. A worker or policy creates an approval request and emits an
   `approval_requested` event.
2. A magic-link token is issued through
   [`packages/policies/approval_tokens.py`](../packages/policies/approval_tokens.py).
   Tokens are HMAC-signed, short-lived, single-use, and classified as either
   default or P0.
3. The token is persisted by
   [`packages/db/approval_token_store.py`](../packages/db/approval_token_store.py)
   under gitignored runtime state.
4. Kashane opens the local approval URL served by
   [`apps/api/approval_endpoint.py`](../apps/api/approval_endpoint.py).
5. For default actions, `POST /approvals/{token_id}/confirm` burns the token and
   marks the approval approved.
6. For P0 actions, the primary click leaves the approval awaiting a second
   factor; `POST /approvals/{token_id}/second-factor` must land inside the
   configured window before the approval becomes approved.

## Sweep Behavior

Every run scans platform events for approvals that have been requested but not
decided. It may inspect Gmail-visible approval threads for magic-link token ids,
then cross-checks those ids against the token store.

Allowed writes are append-only events and a briefing artifact under
`state/artifacts/briefings/`. The sweep records what it observed:

- pending token not clicked
- token burned and approval already approved by the endpoint
- P0 primary click without second factor
- expired token
- drift between token state and approval state
- unavailable Gmail or token-store surfaces

That distinction is the important safety property. The scheduled session can
surface stale or drifted approval state, but cannot grant authority by parsing
email text.

## Why This Is Evidence

This workflow ties together all three parts of the approval-gate claim:

- recurring operator rhythm: `scripts/scheduled/approval_sweep_session.md`
- typed approval/token policy: `packages/policies/approval_tokens.py`
- local approval enforcement: `apps/api/approval_endpoint.py`

It is not a production-soak claim. It is a traced implementation path showing
how recurring work is constrained so that irreversible decisions still require a
local human approval action.
