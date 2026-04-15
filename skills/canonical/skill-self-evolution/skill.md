# Skill: skill-self-evolution

Kind: agentic
Owner: supervisor
Runtimes: claude

## Purpose

Observe recent task outcomes, identify a canonical skill whose contract
is producing friction (repeated failures, drift between validator and
fixtures, a pattern the existing skill does not capture), and stage a
proposal to edit that skill's `skill.md`, `contract.yaml`, `validator.py`,
or `fixtures/**` — bounded by the per-skill boundary enforced by
`packages/policies/skill_evolution.py`.

**Never auto-merges.** Every proposal ends by calling
`packages.tools.primitives.approvals.request_evolution_approval`, which
writes a pending approval record + HMAC-signed magic-link token. The
worker then blocks on `BLOCKED_AWAITING_APPROVAL` until a human runs
`apps/approval-reviewer/main.py sign ...` against the pending record.

The skill is NOT self-evolvable. Evolving the evolution skill itself
requires a human-authored PR, and the registry entry enforces this with
`self_evolvable: false`. This is the privilege-escalation gate.

## Contract

**Inputs** (passed in the task packet payload):

- `target_skill_id: str` — the canonical skill this proposal will touch
- `rationale: str` — short human-readable reason for why this skill
  needs to change
- `input_snapshot_ref: str` — path under `state/checkpoints/platform/`
  to a hash-pinned snapshot of the task outcomes that triggered the
  proposal. The worker reads this through `dispatch_health_reader`,
  not by opening JSONL directly — the reader verifies signatures on
  attacker-influenceable logs.

**Outputs** (fields on the returned `TaskResult`):

- `status: TaskStatus.BLOCKED` — successful proposal always ends blocked
  on the human approval gate. `status: TaskStatus.FAILED` if any policy
  check in `check_evolution_allowed` raises.
- `approval_id: str` — the id of the pending `ApprovalRecord`
  (prefixed `skill-evo-`). The reviewer CLI consumes this to list and
  sign.
- `artifacts: [...]` — absolute paths to the staged proposal dir under
  `state/artifacts/skill-evolution/<proposal_id>/`, containing at
  minimum `diff.patch`, `rationale.md`, and
  `input_snapshot.sha256`.

**Policy checks** run (in this order) via `check_evolution_allowed`:

1. Config-path denylist — no touching `packages/config/**`,
   `.github/workflows/**`, `packages/policies/**`,
   `packages/schemas/**`, sibling primitives, etc. Raises
   `CONFIG_MUTATION_REQUIRES_HUMAN`.
2. Third-file smuggling guard — the diff may only touch files
   matching `{skill.md, contract.yaml, validator.py, fixtures/**}`
   under the target skill's canonical directory. Anything else is
   `THIRD_FILE_SMUGGLING`.
3. Fixture/skill atomicity — validator edits MUST ship with fixture
   edits and vice versa. `FIXTURE_SKILL_DRIFT` otherwise.
4. Allowlist — the target skill must carry `self_evolvable: true` in
   the registry. Default is false. `SKILL_NOT_SELF_EVOLVABLE` otherwise.
5. Runtime expansion guard — first PR of a self-evolved skill is
   claude-only. Adding codex or acp requires a human PR.
   `RUNTIME_EXPANSION_REQUIRES_HUMAN`.
6. Concurrent-run lock check — no other worker holds the
   per-skill-id lock. `CONCURRENT_EVOLUTION_IN_PROGRESS` otherwise.

## Edit boundaries

The worker may write to:

- `state/artifacts/skill-evolution/<proposal_id>/` — the staged
  proposal artifact dir (diff, rationale, input snapshot)
- `state/checkpoints/platform/approvals/` — via `ApprovalStore.save`
- `state/checkpoints/platform/approval_tokens/` — via
  `ApprovalTokenStore.save`
- `skill_evolution_locks` table in the control plane DB — via
  `SkillEvolutionLockStore.acquire` / `heartbeat` / `release`
- `state/logs/dispatch-health.jsonl` — for post-completion metrics

The worker MUST NOT write to:

- `skills/canonical/**` — the proposal is staged under
  `state/artifacts/`; applying it is a reviewer action, not a worker
  action
- `skills/registry.yaml` — registry updates that accompany a new skill
  are part of the human-authored approval step, not the worker's
  staging run
- `packages/**`, `apps/**`, `docs/**` — none of these are in the
  proposal surface
- Git: no `git commit`, no `git push`, no `gh pr create`. Option B
  means the proposal ends in a signed artifact on disk, not a PR.

## Failure modes

- **Policy rejection** — any check in `check_evolution_allowed` raises.
  Worker marks task `FAILED` with the `PolicyViolationCode` in
  `failure_codes`. No approval record written.
- **Lock acquire failure** — another worker holds the skill-id lock.
  Task marked `BLOCKED` with reason `concurrent_evolution_in_progress`
  and re-queued by the supervisor.
- **Kill switch engaged** — `state/flags/skill_evolution_frozen`
  exists. Worker refuses to claim any new task and returns idle from
  `_refuse_if_blocked()`.
- **Approval rejected** — reviewer marks the approval
  `REJECTED`. Worker's next poll sees the flip, marks the task
  `FAILED`, and quarantines the staged artifact dir under
  `state/quarantine/skill-evolution/<proposal_id>/`.
- **Approval expired** — HMAC token TTL elapses before a reviewer
  signs. Worker marks the task `FAILED` with reason
  `approval_token_expired`. Reviewer can re-enqueue the proposal
  manually after fixing whatever held up the review.

## Observability

Every terminal transition (`staged`, `approved`, `rejected`, `expired`,
`policy_denied`) writes one line to
`state/logs/dispatch-health.jsonl` with
`{lane: "skill_evolution", task_id, skill_id, reason_code,
duration_ms}`. `scripts/skill-evolution-metrics.py` (deferred) will
consume this stream.
