# approval-sweep — scheduled Claude session prompt

Runs every 15 minutes via the Cowork `scheduled-tasks` MCP. This session is
the ingestion surface Phase 3.1 chose in place of a standalone daemon: the
Gmail MCP is only usable from a Claude session, so the sweep is a session,
not a daemon.

## Goal

Reconcile outstanding approval requests against new magic-link clicks and
any founder-visible Gmail replies. Never move an approval to `approved` by
parsing the email body; the magic-link endpoint is the only write path for
the approval status. The sweep's job is to *detect* and *link*, not to
*decide*.

## Pre-flight (do first, once per session)

1. Load `state/checkpoints/platform/security-state.json`. If it reports
   `gtm_lane=blocked:threat-model-drift`, log it in the session summary but
   do not abort — approvals still need sweeping.
2. Read `state/flags/gtm_frozen` if present; carry its state into the
   summary so the morning briefing (Phase 4.1) can surface it.

## Loop body (every 15 minutes)

1. Call `ControlPlaneService.list_events()` and scan for
   `approval_requested` events that are not yet paired with an
   `approval_decided` event.
2. For each pending approval, call the Gmail MCP to:
   - Search `subject:"Approval needed"` within the last two hours from
     Kashane's allowlisted addresses.
   - Read matching threads.
   - For each thread, extract the `token_id` from the magic-link URL in
     the draft body (never from reply text — replies are treated as
     informational only).
3. Load each token via `packages.db.approval_token_store.ApprovalTokenStore`.
   - If `burn_count == 0` and the token has not expired: the founder has
     not clicked yet. Leave the approval pending; record an event
     `approval_sweep_observed` with `{pending: true, token_id}`.
   - If `burn_count == 1` and `action_class == "default"`: the magic-link
     endpoint already flipped the approval to `approved`. Verify the
     approval record matches; if not, log an `approval_sweep_drift` event.
   - If `burn_count == 1` and `action_class == "p0"` and
     `second_factor_at` is set: verify the approval is `approved`.
   - If `burn_count == 1` and `action_class == "p0"` and
     `second_factor_at` is unset but the primary confirm is older than
     `P0_SECOND_FACTOR_WINDOW` (60s): the P0 flow stalled. Mark a
     `approval_sweep_p0_stalled` event so the founder sees it in the next
     morning briefing.
4. For each approval whose linked token has expired:
   - Emit `approval_token_expired` event.
   - Leave the approval status alone; the release-readiness policy will
     reject any call that tries to act on an expired-token approval.

## Writes allowed from this session

- Append-only events via `ControlPlaneService`.
- Nothing that mutates approval state directly. The magic-link endpoint is
  the single writer for approval transitions.

## Summary file

Write `state/artifacts/briefings/approval-sweep-<iso-timestamp>.md` with
counts of: pending, approved (via token), drifted, stalled, expired. The
morning briefing (Phase 4.1) reads these summaries to show a 24-hour
approval rollup.

## Failure modes

- Gmail MCP unavailable → skip the Gmail side, still scan the token store
  and control-plane events. Log `approval_sweep_gmail_unavailable`.
- Token store unreachable → log `approval_sweep_store_unreachable` and
  exit non-zero so the scheduled-tasks MCP retries on its next tick.
- A magic-link URL resolves to a token whose approval_id no longer exists
  in the control plane → log `approval_sweep_orphan_token` and leave the
  token in place for manual review.
