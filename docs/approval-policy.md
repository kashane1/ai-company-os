# Approval Policy

This document defines the default approval stance for `ai-company-os`.

The goal is meaningful autonomy without vague or unsafe authority.

## Default Stance

When an action is irreversible, high-risk, externally visible, expensive, security-sensitive, or poorly understood, require human approval.

When the system cannot confidently classify an action, default to approval required.

Unknown risky actions should never silently proceed.

## Safe Automated Actions

These are usually safe to automate:

- creating goals and tasks
- drafting implementation plans
- creating worktrees
- syncing repos
- running tests, lint, and builds
- generating code changes in isolated worktrees
- opening pull requests
- drafting release notes
- preparing metadata drafts
- preparing screenshots
- generating internal artifacts
- summarizing incidents or blockers

Safe does not mean invisible. These actions should still be logged.

## Approval-Required Actions

These usually require human approval:

- merging to protected branches
- production deploys
- destructive database operations
- security-sensitive config changes
- billing or pricing changes
- high-spend actions
- App Store submission
- App Review replies
- bulk outbound communication
- domain or DNS changes
- public release activation

## Forbidden Actions

These actions should be blocked unless the platform explicitly adds a governed workflow for them:

- bypassing approval checks in worker code
- force-pushing protected branches by default
- exfiltrating secrets or user data
- mutating unrelated repos or worktrees outside task scope
- performing destructive production actions without rollback planning
- allowing OpenClaw or any chat interface to own routing or policy

## Worker Examples

### Supervisor

Usually safe:

- decomposing goals into tasks
- reprioritizing queued work
- escalating risky work for approval

Should not do directly:

- repo mutation
- merges
- deploys

### Engineering

Usually safe:

- worktree creation
- Codex execution
- validation runs
- PR preparation

Requires approval:

- merging protected branches
- production deployment hooks
- destructive migrations

### iOS

Usually safe:

- simulator runs
- build validation
- release candidate artifact preparation

Requires approval:

- signing or shipping flows that trigger public release effects

### App Store

Usually safe:

- metadata drafting
- screenshot preparation
- TestFlight state preparation

Requires approval:

- final submission
- review-response submission
- public release actions

## Policy Implementation Guidance

Approval rules should live in shared code under `packages/policies/`, not in prompts.

Workers should consume approval decisions from shared policy helpers and return explicit `requires_approval` state when they encounter risky next steps.

The platform should remain the final enforcement point.
