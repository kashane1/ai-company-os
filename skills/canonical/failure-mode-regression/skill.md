---
id: failure-mode-regression
name: Failure Mode Regression Capture
purpose: Convert every observed platform failure into a regression fixture so the next similar failure is caught by an automated test instead of re-appearing at runtime.
owner_agent: supervisor
target_runtimes: [claude]
kind: validator
---

# Failure Mode Regression

## When it runs

Invoked from the observability rollup (Phase 4.3) for any `failure_code`
it finds in lane logs, and from the control plane's
`task_result_rejected` path when the post-run-validation skill rejects a
task.

## Dedupe window

One fixture per `failure_code` per 24 hours. The skill looks at
`state/artifacts/failure-fixtures/index.json` and refuses to write a
new fixture if `last_captured_at` for that code is less than 24h old.
This prevents runaway fixture spam if the same upstream failure fires
repeatedly.

## Redaction

Every log excerpt and payload written to the fixture passes through
`packages.tools.observability.redaction.redact` before being persisted.
The `hits` count is stored in the fixture metadata so the founder can
see, at a glance, whether credentials were present in the raw stream.

## Self-failure meta code

If this skill itself fails to capture a fixture (disk full, redaction
crash, anything), it emits `failure_code=capture_pipeline_self_failure`
**out-of-band** via the events store — it does NOT try to re-capture
that failure recursively.

## Output

```json
{
  "verdict": "ok" | "skipped" | "fail",
  "failure_code": "<input code or self-failure meta>",
  "fixture_path": "<path or empty>",
  "reason": "<human readable>"
}
```

- `ok` — new fixture written
- `skipped` — within dedupe window
- `fail` — capture pipeline itself broke
