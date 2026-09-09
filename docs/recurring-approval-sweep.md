# Recurring Approval Sweep

This is the concrete recurring workflow behind the README claim that operator
workflows are designed around approval gates.

The sweep prompt instructs the agent to observe approval state and link
evidence without deciding approvals. Its intended path records decisions through
the local magic-link endpoint. The control-plane API also exposes a direct
approval-decision route, so this is a workflow restriction rather than exclusive
write access enforced across the entire application.

## Schedule

The operator prompt lives at
[`scripts/scheduled/approval_sweep_session.md`](../scripts/scheduled/approval_sweep_session.md).
It is written for a Cowork `scheduled-tasks` session intended to run every
15 minutes. The repository contains the prompt, not a deployed scheduler
configuration or proof that the schedule is currently active.

The prompt exists because the intended Gmail access is through a scheduled Claude
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
5. For default actions, `POST /magic/approvals/{token_id}/confirm` burns the token and
   marks the approval approved.
6. For P0 actions, the primary click leaves the approval awaiting a second
   factor; `POST /magic/approvals/{token_id}/second-factor` must land inside the
   configured window before the approval becomes approved. This is a second
   confirmation with the same token/device, not an independent MFA factor.

## Sweep Behavior

The prompt instructs each run to scan platform events for approvals that have been requested but not
decided. It may inspect Gmail-visible approval threads for magic-link token ids,
then cross-checks those ids against the token store.

Allowed writes are append-only events and a briefing artifact under
`state/artifacts/briefings/`. The requested output records what the sweep observed:

- pending token not clicked
- token burned and approval already approved by the endpoint
- P0 primary click without second factor
- expired token
- drift between token state and approval state
- unavailable Gmail or token-store surfaces

That distinction is the important safety property. The procedure tells the scheduled session to
surface stale or drifted approval state and prohibits it from granting authority
by parsing email text. The prompt alone is not a capability sandbox.

## Why This Is Evidence

This workflow ties together all three parts of the approval-gate claim:

- intended operator rhythm: `scripts/scheduled/approval_sweep_session.md`
- typed approval/token policy: `packages/policies/approval_tokens.py`
- local approval enforcement: `apps/api/approval_endpoint.py`

It is not a production-soak claim. It connects an operator procedure to an implemented local approval path.
See the [token integration tests](../tests/python/integration/test_approval_tokens.py)
for executable evidence of that path, and the
[employer guide](FOR-EMPLOYERS.md#scope-and-limitations) for its limits.
