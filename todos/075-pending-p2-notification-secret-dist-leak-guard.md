---
status: pending
priority: p2
issue_id: "075"
tags: [code-review, security, secrets, better-business-web, agency]
dependencies: []
---

# Problem Statement

§7 says "configure a notification (email/Slack)" but never specifies where the
Slack webhook / email credential lives. A Slack incoming-webhook URL is a bearer
secret. Because the file-digest deploy (§4) uploads whatever is in `dist/`, an
accidentally-inlined webhook (client-side JS or baked HTML) would ship publicly.

## Findings

- Notification config underspecified — [LANDING_PAGE_PLAN.md:160](../docs/products/better-business-web/LANDING_PAGE_PLAN.md:160).
- File-digest deploy uploads `dist/` contents wholesale — [deploy.py:159](../packages/web/deploy.py:159).

## Proposed Solutions

### Option 1: Server-side Netlify form notifications + deploy-time leak check (recommended)
Configure notifications only in Netlify's form settings; webhook/email creds
never in repo, never in `dist/`, never in client JS. Add a deploy-time check that
`dist/` contains no `hooks.slack.com` / credential-shaped strings, failing closed.

Pros:
- Keeps the secret off the public artifact; defense-in-depth at deploy

Cons:
- Small deploy-time scan to maintain

Effort: small
Risk: low

### Option 2: Document the rule only
State "never inline the webhook" without an automated check.

Pros:
- Zero code

Cons:
- Relies on discipline; one slip leaks publicly

Effort: tiny
Risk: medium

## Recommended Action

Adopt Option 1: server-side notification config + a `dist/` secret-leak guard in
the deploy path.

## Technical Details

- `packages/web/deploy.py` is a natural place for the pre-upload scan.

## Acceptance Criteria

- [ ] Notification secrets configured server-side only; never in repo/`dist/`/JS.
- [ ] Deploy fails closed if `dist/` contains credential-shaped strings.

## Work Log

### 2026-06-02 - Initial review capture
Surfaced by security-sentinel during `/review`.
