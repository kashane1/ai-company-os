# Contributing

This repository is public for evaluation, but the code is proprietary. Treat
contributions as local development guidance, not an open-source invitation.

## Fast Evaluation Path

```bash
./scripts/evaluator_check.sh
make demo
uv sync --frozen --extra test --group quality --python 3.12
./scripts/test_python.sh
```

`make demo` has no external dependencies. It exercises the deterministic demo
control-loop fixture and writes schema-faithful sample artifacts to
`docs/examples/`; it does not start persistent workers, contact third-party
services, or prove an external deployment. `./scripts/evaluator_check.sh`
wraps that path and verifies the main files an evaluator is likely to inspect.

The platform supports Python 3.11 and 3.12, tested separately in CI. The frozen
setup uses uv 0.9.22 and the checked-in lockfile; run commands from the repository
root. This is a source-checkout application, not an installable library or wheel
distribution. `packages = []` in the build configuration is deliberate: the
editable install provides dependencies and project metadata, and source imports
resolve from the checkout. The zero-dependency fixture also supports Python 3.10.

For dependency changes, edit `pyproject.toml`, run `uv lock`, then verify a fresh
`uv sync --frozen --extra test --group quality`. To include the optional Gmail
adapter, add `--extra reply-sync`; it is not needed to evaluate the core platform.

```bash
.venv/bin/ruff check apps packages scripts tests
mkdir -p build
uv export --frozen --all-extras --group quality --no-emit-project \
  --output-file build/audit-requirements.txt > /dev/null
.venv/bin/pip-audit --requirement build/audit-requirements.txt --no-deps --disable-pip
```

CI enforces correctness/import lint rules; it does not gate source paragraph
length. Coverage includes API and worker entrypoints. A passing aggregate reports
all selected Python versions and all three iOS projects; inspect individual jobs
for failures or product-specific coverage.

## Repo Boundaries

- `apps/` contains thin runtime entrypoints.
- `packages/` contains shared schemas, policies, stores, queues, and tools.
- `products/` contains the iOS apps produced by the system.
- `docs/` contains platform docs plus generated run/spec output.
- `state/` is runtime-owned and must not be used as source.
- `todos/` is the agent backlog, not polished documentation.

## Testing Contract

Logic-bearing changes ship with lane-matching tests.

- Python changes under `apps/` or `packages/`, plus Python/shell scripts under
  `scripts/`, need tests under `tests/python/`.
- iOS logic changes need tests in each affected product's `Tests/` or `UITests/`
  tree. Tests from another product do not satisfy that requirement.
- Web source changes need tests in the affected product's mapped test area.
  [The testing policy](packages/policies/testing.py) defines the source and test
  paths, including exclusions for generated files and static assets.
- No-test exceptions must use explicit, machine-readable reason codes.

Run the narrowest relevant test while working, then run `./scripts/test_python.sh`
before handing off platform changes.

## Publication

Publish through a pull request and wait for all required checks, including
maintenance and security. Main's protection applies to routine owner/admin
changes too. Keep the `## Testing` section in the PR body: merge and squash
commits retain that reviewed metadata so post-merge checks can evaluate explicit
test exceptions. Rebase merging is disabled because it would discard that body.

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
