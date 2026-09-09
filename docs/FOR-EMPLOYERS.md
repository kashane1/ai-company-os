# For employers: start here

`ai-company-os` is my personal project for coordinating AI coding agents
across software projects. It combines Python workers, task records, validation,
and approval policies with the product source those workflows help develop.

**If you only have two minutes, this page is enough.** For code, demo commands,
and tests, continue to the [evaluator walkthrough](EVALUATOR-WALKTHROUGH.md).
You can read both entirely on GitHub.

## My role and the agents' role

I choose what to build, define the architecture and operating rules, direct
the agents, and review their output. AI coding agents contribute implementation,
tests, documentation, and iteration. This is a project to evaluate how I design
and operate an engineering system with AI; it is not a claim that I manually
wrote every line.

The decisions I would start a technical conversation with are:

- **Separate policy from execution.** Workers call shared policy code; release
  actions have explicit approval requirements.
- **Make work inspectable.** Engineering and iOS task-run records link execution
  details, validation results, review artifacts, and approval IDs.
- **Keep delivery lanes separate.** General engineering, iOS implementation,
  and App Store work have distinct entrypoints and responsibilities.

## What you can inspect

| Question | Start here | What to look for |
|---|---|---|
| How is work represented? | [Task-run schema](../packages/schemas/task_run.py) and [parsing tests](../tests/python/unit/test_typed_tool_surface.py) | Execution and validation fields; rejection of unknown enum values during parsing |
| Where do approval rules live? | [Approval policy](../packages/policies/approvals.py) and [policy tests](../tests/python/unit/test_approvals.py) | Risk/keyword classification and the explicit release-action list |
| How does an approval get recorded? | [Magic-link endpoint](../apps/api/approval_endpoint.py) and [integration tests](../tests/python/integration/test_approval_tokens.py) | Expiry, signature rejection, single-use tokens, and the extra confirmation step for P0 actions |
| What happens when an audit write fails? | [Postmortem store](../packages/db/postmortem_store.py) and [failure-injection test](../tests/python/integration/test_audit_artifact_crash_safety.py) | Temporary-file replacement and preservation of the previous record after a write error |
| What proves that verification ran? | [Verification runner](../packages/tools/verification.py) and [failure-path tests](../tests/python/unit/test_worker_verification.py) | Configured commands, exit codes, timeouts, redacted logs, and detection of changes made during verification |
| How do the workers fit together? | [Runtime supervisor](../apps/runtime-supervisor/README.md) and [engineering flow](engineering-flow.md) | Worker lifecycle, task preparation, validation, and review handoff |

These links show specific implemented behavior. They do not establish that
every possible action is protected or that the system is suitable for an
untrusted, internet-facing deployment.

## Product work

The repository contains three managed iOS source trees at different stages.
Source code and development logs are evidence of implementation, not proof of
an App Store launch, user adoption, or revenue.

| Product | What is available to review |
|---|---|
| [Life Clock](../products/life-clock-ios/README.md) | SwiftUI/SwiftData health app with engines, HealthKit integration, subscription code, and test targets; the [polish walkthrough](flagship-simulator-driven-polish.md) traces one development workflow |
| [Catchbook](../products/catchbook-ios/README.md) | Fishing logbook source with trip/catch/history flows and unit/UI tests |
| [After Plans](../products/after-plans-ios/README.md) | SwiftUI app with an offline in-memory default, optional Supabase adapter, lifecycle/visibility tests, and an onboarding-to-plan UI test; deployed service status is not established here |

## Scope and limitations

- This is a solo development system. It is not evidence of operating a
  multi-tenant service or managing an engineering team.
- The fixture demo illustrates schemas. A separate
  [worker demonstration](../scripts/worker_demo.py) executes the actual local
  ledger worker, injects a write failure, and records a successful replacement
  task with synthetic data. Neither demonstration invokes Codex or performs
  external delivery. The walkthrough explains how to run and inspect both.
- The approval API assumes a trusted local operator environment. Generic
  approval decisions require a configured local bearer capability, and P0
  approvals must use the signed confirmation route. Its P0 “second factor” is
  a second confirmation using the same token/device, not independent MFA.
  This does not defend against another process running as the same user with
  access to the local runtime state.
- The App Store worker models local release state; external submission is
  manual. The worker runs release readiness before recording the local
  `submit_appstore` transition and persists the outcome; it does not upload,
  submit, or release anything through Apple. The
  [workflow notes](flagship-simulator-driven-polish.md) explain that boundary.
- Some workflows are implemented in Python; others are instructions followed
  by an agent/operator. A skill document describes the intended procedure,
  not automatic proof that every run followed it.
- The first commit is dated March 27, 2026. Commit and branch counts change
  and do not measure quality, manual authorship, or production reliability.
- The [CI workflow](../.github/workflows/tests.yml) defines Python 3.11/3.12
  tests, all three managed iOS product suites, lint, dependency auditing, and
  secret scanning. Check the latest run for its current result and recorded
  skips. Other product experiments have their own verification boundaries.

## Next step

Follow the [evaluator walkthrough](EVALUATOR-WALKTHROUGH.md) for a short code
review and optional local checks. For a design discussion, the
[reliability notes](reliability-lessons.md) pair decisions with their evidence
and limits.
