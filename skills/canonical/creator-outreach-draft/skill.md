# Skill: creator-outreach-draft

Kind: agentic
Owner: gtm
Runtimes: claude

## Purpose

Draft personalized outreach DMs to a list of target creators. Writes the
drafts to `state/artifacts/outreach/<date>/<creator>.md`. Kashane copies
and sends manually.

## Non-automation boundary (HARD)

- This skill drafts only.
- There is **no** skill, script, tool, or MCP wired to send DMs.
- The output must not contain first-person send claims
  (e.g. "I have sent", "I sent", "message delivered"). The worker lint
  rejects such outputs.
- Any auto-send attempt emits `gtm_outreach_auto_send_attempt` (see
  `docs/failure-modes/gtm-lane.md`).

## Contract

Inputs:
- `creator_targets`: list of `{handle, platform, notes, recent_post_url}`.
- `campaign_brief`: text.

Outputs:
- `drafts`: list of `{handle, platform, body, artifact_path}`.

Artifact path format:
`state/artifacts/outreach/YYYY-MM-DD/<platform>-<handle>.md`.
