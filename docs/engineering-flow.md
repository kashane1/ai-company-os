# Engineering Flow

This document explains the first real engineering lane in `ai-company-os`.

## Task Lifecycle

The current lifecycle is intentionally simple:

1. the platform creates and persists an engineering task
2. the task is routed to `worker-engineering`
3. the worker loads the task from persisted state
4. the worker prepares the repo and isolated worktree
5. the worker renders a Codex task packet
6. the worker invokes Codex CLI locally
7. the worker validates the run and captures a diff artifact
8. the worker persists task run metadata and updates task status

This keeps the task flow visible from input through execution.

## Repo Sync Behavior

Repo configuration is loaded from `infra/repos.json`.

For the current scaffold phase:

- the configured source path is treated as the source of truth
- the engineering worker syncs that source tree into `state/repos/<repo-id>/`
- runtime state is excluded from the sync

This gives the worker a managed local repo snapshot without mutating the source path directly.

## Worktree Rules

Every engineering task gets its own isolated workspace under `state/worktrees/<repo-id>/<task-id>/`.

Rules:

- the worker operates only inside the task worktree
- the worktree is prepared from the managed repo snapshot
- git history is not mutated
- resulting file changes remain uncommitted for inspection

## Codex Packet Generation

The worker renders a markdown task packet into the worktree before execution.

The packet includes:

- task objective
- execution rules
- explicit constraints
- structured testing contract fields such as `tests_required`, `test_lane`, and allowed no-test reason codes

This packet is the direct instruction source for the local Codex CLI invocation.

## Codex CLI Execution Flow

The worker runs `codex exec` locally with:

- the worktree as the working directory
- the rendered task packet passed through stdin
- workspace-write sandboxing
- no auto-commit or git-history mutation

The worker captures:

- the exact command invoked
- stdout
- stderr
- exit code
- start and end timestamps
- the last agent message written by Codex

## Validation Flow

After execution, the worker currently validates:

- worktree exists
- packet exists
- Codex result output exists
- Codex exit code is zero
- diff artifact exists
- lane-matching tests were created or modified for logic-bearing changes, or a valid machine-readable no-test exception was supplied

Validation stays explicit and persisted. A missing-tests failure still classifies as `VALIDATION_FAILED`, but task-run and review records now carry a specific failure code such as `missing_tests_for_logic_change` so humans can see the reason immediately.

## Persisted Artifacts And Checkpoints

The main persisted outputs are:

- task record in `state/checkpoints/platform/tasks/`
- task run record in `state/checkpoints/platform/task_runs/`
- repo metadata in `state/checkpoints/platform/repos/`
- worktree metadata in `state/checkpoints/platform/worktrees/`
- rendered task packet in the worktree
- Codex stdout and stderr logs in `state/logs/engineering/`
- diff artifact in `state/artifacts/engineering/<task-id>/`
- structured testing-policy outcome and failure codes in the task-run record
- testing-policy summary in the review artifact

The goal is that a human can inspect what happened without guessing.
