# worker-gtm

The go-to-market content lane. Claims GTM tasks and runs a content
chain — draft, voice guardrail, social-post safety, schedule —
with publishing held behind approval.

## Owns

- claiming and executing GTM-lane tasks from the control plane
- the content chain: draft → voice-guardrail → social-post-safety →
  schedule
- honoring the GTM kill switch before every claim and every MCP call
- honoring the MCP threat-model acknowledgment: if the recorded
  threat-model checksum has drifted, the worker refuses to claim and
  emits a lane-blocked event

## Does not own

- publishing content without approval — publish is approval-gated
- product source code
- App Store submission
- approval policy

## Entrypoint

[main.py](main.py) — a thin claim loop mirroring
[worker-engineering](../worker-engineering/). GTM-specific logic lives
under [gtm/](gtm/) (`runner.py`, `validator.py`).

## Boundaries

- **Kill switch:** the worker checks `state/flags/gtm_frozen` and
  stops cleanly when it is set.
- **Publish is approval-gated** — drafting and scheduling are safe to
  automate; outbound publishing is not.
- Workers do not own policy. Policy lives in
  [packages/policies/](../../packages/policies/).

## Validation

Python lane — `./scripts/test_python.sh`.

## Related docs

- [docs/skills-index.md](../../docs/skills-index.md) — GTM skills and
  trigger phrases
- [docs/agent-model.md](../../docs/agent-model.md)
- [docs/approval-policy.md](../../docs/approval-policy.md)
