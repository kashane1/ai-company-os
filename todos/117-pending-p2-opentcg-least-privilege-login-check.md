---
status: pending
priority: p2
issue_id: "117"
tags: [open-tcg, security, scheduled-task, prompt-injection]
dependencies: []
---

# OpenTCG: shrink the 6 AM sign-in check to least privilege

## Problem Statement

The scheduled task (`~/.claude/scheduled-tasks/opentcg-retailer-login-check/SKILL.md`) is read-only only because its prompt says so. It loads the extension's `navigate` and `computer` tools (click and type), plus Bash and Write, inside the founder's signed-in Brave profile, and it reads five retailer pages. Text injected into one of those pages could try to steer it: navigate elsewhere, click Buy, or run commands. Its notification step also puts model-written text inside a `python -c "..."` shell string, where `$()` and backticks would expand.

## Proposed Solutions

1. **(Recommended)** Drop the `computer` and Bash tools, and read only with `navigate` + `get_page_text`. The model writes only the JSON file. A fixed script (`radar login-status report`) validates it (store allowlist, enum statuses, no free text) and sends the notification itself. Where the extension supports it, limit its site access to the five retailer domains.
2. On the radar side, treat stored post and email text as untrusted wherever a future Claude session might read it. Store the extracted fields rather than full bodies, strip control characters, and cap lengths at ingest (see todo 118).

## Acceptance Criteria

- [ ] The task prompt uses only read tools plus Write for a JSON file. No shell string contains model output.
- [ ] Invalid or unexpected JSON is rejected by the validator and reported as "unknown".
