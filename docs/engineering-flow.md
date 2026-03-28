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

This is still a placeholder validation pipeline, but it is explicit and persisted.

## Persisted Artifacts And Checkpoints

The main persisted outputs are:

- task record in `state/checkpoints/platform/tasks/`
- task run record in `state/checkpoints/platform/task_runs/`
- repo metadata in `state/checkpoints/platform/repos/`
- worktree metadata in `state/checkpoints/platform/worktrees/`
- rendered task packet in the worktree
- Codex stdout and stderr logs in `state/logs/engineering/`
- diff artifact in `state/artifacts/engineering/<task-id>/`

The goal is that a human can inspect what happened without guessing.
