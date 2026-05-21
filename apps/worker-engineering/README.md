# worker-engineering

The generic software implementation lane. Wraps Codex inside a
controlled sequence so engineering work is reproducible and auditable.

## Owns

- preparing structured engineering task packets
- syncing the managed repo into [state/repos/](../../state/repos/)
- creating isolated worktrees under [state/worktrees/](../../state/worktrees/)
- invoking Codex CLI locally
- validating the resulting diff against shared policy
- persisting [task-run records](../../packages/schemas/task_run.py) and
  the structured testing-policy outcome
- reporting structured results back to the platform

## Does not own

- product strategy or scope decisions
- release policy or deployment policy
- iOS-specific build, sign, or simulator orchestration (that's
  [worker-ios](../worker-ios/))
- App Store submission, metadata, or review responses (that's
  [worker-appstore](../worker-appstore/))
- approval decisions (the magic-link endpoint is the only writer)
- bypassing the tests-with-code policy

## Entrypoint

[main.py](main.py)

Engineering-specific helpers live under [engineering/](engineering/).
Codex-facing utilities live in
[packages/tools/codex_tools/](../../packages/tools/codex_tools/).

## Task types accepted

- generic engineering changes against repos registered in
  [infra/repos.json](../../infra/repos.json)
- changes that fit within one bounded worktree
- changes whose Codex prompt + acceptance criteria fit in a packet
  small enough to finish within the configured Codex timeout

## Allowed edit boundaries

- `state/worktrees/<repo-id>/<task-id>/`
- `state/artifacts/engineering/<task-id>/`
- `state/logs/engineering/`
- `state/checkpoints/platform/task_runs/`

## Forbidden areas

- [packages/policies/](../../packages/policies/) and
  [packages/schemas/](../../packages/schemas/) — change only via the
  shared-policy review path
- [infra/](../../infra/)
- [docs/](../../docs/) — the engineering lane doesn't edit docs as a
  side-effect of code changes
- anything outside the assigned worktree
- the source-of-truth managed repo path (the worker syncs *into*
  `state/repos/`, never mutates the upstream tree)
- `.claude/skills/`, `skills/canonical/`, `skills/adapters/` — skill
  edits are not engineering-lane work

## Validation expectations

After every Codex run, the worker performs structured validation:

- worktree exists and is the expected path
- task packet was rendered and written into the worktree
- Codex execution result was captured (stdout, stderr, exit code, timings)
- Codex exit code is zero
- diff artifact exists in `state/artifacts/engineering/<task-id>/`
- the tests-with-code policy was satisfied — logic-bearing changes ship
  with lane-matching tests, or carry a valid machine-readable
  `no_test_reason_code`

A missing-tests failure classifies as `VALIDATION_FAILED` with a
specific failure code (e.g. `missing_tests_for_logic_change`) so the
reason is queryable from the persisted task-run record.

## Related docs

- [docs/engineering-flow.md](../../docs/engineering-flow.md)
- [docs/codex-worker.md](../../docs/codex-worker.md)
- [AGENTS.md](../../AGENTS.md) and
  [docs/agent-model.md](../../docs/agent-model.md)
- [docs/approval-policy.md](../../docs/approval-policy.md) — what
  remains approval-gated even when an engineering task succeeds
