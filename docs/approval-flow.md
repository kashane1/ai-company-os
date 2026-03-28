# Approval Flow

This document explains the review and approval boundary for the engineering lane.

## When A Run Becomes Reviewable

An engineering run becomes reviewable only when:

- Codex execution finishes successfully
- validator checks pass
- the worktree contains tracked file changes worth inspecting

That result is classified as `safe_for_review`.

If execution fails, the result is `execution_failed`.

If execution succeeds but validation fails, the result is `validation_failed`.

If execution succeeds and there are no tracked file changes, the result is `no_change`.

## Artifacts Available For Inspection

For each run, the system persists:

- task record
- task run record
- worktree metadata
- rendered Codex packet
- Codex stdout and stderr logs
- diff artifact
- review summary artifact

These are intended to make manual inspection explicit instead of guesswork.

## What Approval Is Intended To Gate Later

The approval record created for `safe_for_review` runs is scaffolding for future phases.

It is intended to gate actions such as:

- commit creation
- branch updates
- push
- pull request creation
- merge

None of those actions are implemented yet.

## What Remains Manual For Now

For the current phase, all git history mutation remains manual.

That means:

- no auto-commit
- no auto-push
- no auto-PR
- no auto-merge
- no auto-approval

The platform only prepares reviewable output and a pending approval record.
