# Contributing

This repository is public for evaluation, but the code is proprietary. Treat
contributions as local development guidance, not an open-source invitation.

## Fast Evaluation Path

```bash
./scripts/evaluator_check.sh
make demo
python3 -m venv .venv
.venv/bin/python -m pip install -e ".[test]"
./scripts/test_python.sh
```

`make demo` has no external dependencies. It runs the control loop end to end
and writes schema-faithful sample artifacts to `docs/examples/`.
`./scripts/evaluator_check.sh` wraps that path and verifies the main files an
evaluator is likely to inspect.

## Repo Boundaries

- `apps/` contains thin runtime entrypoints.
- `packages/` contains shared schemas, policies, stores, queues, and tools.
- `products/` contains the iOS apps produced by the system.
- `docs/` contains platform docs plus generated run/spec output.
- `state/` is runtime-owned and must not be used as source.
- `todos/` is the agent backlog, not polished documentation.

## Testing Contract

Logic-bearing changes ship with lane-matching tests.

- Python changes under `apps/` or `packages/` need tests under
  `tests/python/`.
- iOS logic changes under `products/*/Sources/` need matching tests under that
  product's `Tests/` tree.
- No-test exceptions must use explicit, machine-readable reason codes.

Run the narrowest relevant test while working, then run `./scripts/test_python.sh`
before handing off platform changes.

## Runtime State

Do not commit runtime output from `state/`, `.codex/`, `.claude/worktrees/`,
Xcode user state, virtualenvs, or caches. If a workflow needs a durable example,
write a small schema-faithful fixture under `docs/examples/` instead.

## Approval Boundaries

Irreversible or externally visible actions require human approval. That includes
protected-branch merges, production deploys, destructive data changes, billing,
DNS, App Store submission, App Review replies, and public release activation.

Approval rules belong in `packages/policies/` and should be consumed by workers;
they should not live only in prompts.

## Documentation Changes

When architecture changes materially, update these together:

- `README.md`
- `AGENTS.md`
- `docs/agent-model.md`
- `docs/architecture.md`

Employer-facing claims should point to files a skeptical engineer can verify in
minutes. Prefer softening a claim over making a claim that only makes sense with
private context.
