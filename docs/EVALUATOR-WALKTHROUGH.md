# Evaluator walkthrough

Start with [For employers](FOR-EMPLOYERS.md) for the project and my role.
This page gives you a bounded review path. You do not need to start the runtime,
configure credentials, or browse the backlog to evaluate the engineering.

## Five minutes on GitHub

1. Open the [sample task-run record](examples/sample-task-run.json). It is a
   **synthetic fixture**, not a log of a real agent run. Notice the execution
   result, validation checks, classification, and linked approval ID.
2. Compare it with [TaskRun](../packages/schemas/task_run.py). Follow `from_dict`
   and `to_dict` to see which fields are parsed, which enums are checked, and
   how the record is serialized. Type annotations alone do not validate inputs.
3. Read [the approval rules](../packages/policies/approvals.py), starting at
   `requires_human_approval` and `requires_release_action_approval`, then their
   [tests](../tests/python/unit/test_approvals.py). The classifier uses risk,
   keywords, and an explicit release-action list.
4. Read [the token integration tests](../tests/python/integration/test_approval_tokens.py).
   The expired-token, tampered-signature, single-use, and P0 confirmation cases
   exercise actual policy/endpoint code with isolated test state.

At this point you have seen a data contract, a policy boundary, and tests of
that boundary. None of these alone proves that the entire runtime is safe to
leave unattended.

## Optional local check

The [license](../LICENSE) permits prospective employers to clone the repository
and run these documented checks locally to evaluate the author's work.

Requires Git, Bash, and **Python 3.10+** (CI uses 3.12). On Windows, use WSL.
The default check needs no third-party Python packages, external services,
API keys, or model calls.

```bash
git clone https://github.com/kashane1/ai-company-os.git
cd ai-company-os
python3 --version
./scripts/evaluator_check.sh
```

The check narrates a fixture, checks the review paths, and validates sample
records. It rewrites the three JSON fixtures in `docs/examples/`; timestamps,
commands, identities, and outcomes in those records are invented demonstration
data. It does not execute the command printed inside the sample record.

Expected result: `Evaluator check passed.` Read the output for which checks ran.
The default command does **not** run Python tests. To see only the illustration,
run `./scripts/demo.sh` (`make demo` is an alias if Make is installed).

## Fifteen to twenty minutes: tests and one design decision

Use **Python 3.11+** for the application and test dependencies (3.12 matches
CI). The standalone fixture only needs 3.10. Create a virtual environment and
install the test dependencies. This step downloads packages; the fixture check
above does not.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e ".[test]"
./scripts/evaluator_check.sh --with-tests
```

The fast subset checks sample records, enum parsing, approval rules, and
token/endpoint behavior. It uses test state rather than your operator state.
It does not call a coding agent or perform a real release.

Then choose one thread to follow:

| Interest | Read | Question to assess |
|---|---|---|
| Reliability | [Postmortem store](../packages/db/postmortem_store.py) and [crash-safety test](../tests/python/integration/test_audit_artifact_crash_safety.py) | Does a failed write preserve the previous record? What failures remain outside the test? |
| Agent workflow | [Recurring approval sweep](recurring-approval-sweep.md) | Which parts are executable enforcement, and which rely on an operator following instructions? |
| Product development | [Life Clock workflow](flagship-simulator-driven-polish.md) | How are design intent, simulator fixtures, and review evidence connected? |

## Deeper review

The full Python suite is optional and may take longer than the short review:

```bash
./scripts/evaluator_check.sh --full-tests
```

This delegates to `./scripts/test_python.sh` and writes test/coverage reports
under `build/`. CI enforces the configured Python coverage threshold; a local
run only enforces it when `PYTHON_COVERAGE_MIN` is set. A failure is a finding
to inspect, not evidence to skip in favor of the fixture demo.

For architecture, read the [runtime supervisor](../apps/runtime-supervisor/README.md),
[architecture](architecture.md), and [agent model](agent-model.md). For product
source, use the [product table](FOR-EMPLOYERS.md#product-work).
Building iOS requires macOS, Xcode, and XcodeGen. The top-level
`./scripts/test_ios.sh` tests **Catchbook only**; Life Clock and After Plans
are separate projects.

## Troubleshooting

- **Python missing or too old:** the fixture needs 3.10+, and application/tests
  need 3.11+. Python 3.12 matches CI.
- **`No module named pytest` or another dependency error:** complete the virtual
  environment/install commands above and retry.
- **Selecting an interpreter:** set `PYTHON_BIN=/absolute/path/to/python3` before
  the command if the repository's `.venv` is not the interpreter you want.
- **A link, fixture, or test fails:** keep the error and the commit hash from
  `git rev-parse HEAD`. The check is intended to expose drift rather than hide it.
