# worker-supervisor

The coordination lane. Inspects a goal, decomposes it into structured
task packets, and routes each to a specialist worker lane. It
coordinates and routes — it does not deliver work.

## Owns

- inspecting an incoming [`Goal`](../../packages/schemas/task_packet.py)
- decomposing a goal into one or more
  [`TaskPacket`](../../packages/schemas/task_packet.py) records
- selecting the worker lane (engineering / iOS / App Store) from goal
  signal text
- assigning a `RiskLevel` to each task
- attaching base execution constraints (isolated worktree, structured
  reporting, no policy bypass)
- augmenting packet constraints from learned worker signals
- flagging risky actions so the platform can route them for approval

## Does not own

- executing tasks or mutating repos (that is the specialist workers:
  [worker-engineering](../worker-engineering/),
  [worker-ios](../worker-ios/), [worker-appstore](../worker-appstore/))
- product strategy or scope decisions
- release or deployment policy
- approval policy — it flags, it does not decide

## Entrypoint

[main.py](main.py) — `plan_goal(goal)` is the current scaffold: a
deterministic goal-to-task decomposition. There is no autonomous loop
here; the platform drives it.

## Inputs and outputs

- **Input:** a `Goal` (title, summary, description).
- **Output:** a list of `TaskPacket` records with lane, risk level,
  and constraints set.

## Boundaries

- The supervisor is not a general-purpose execution worker. Per
  [docs/agent-model.md](../../docs/agent-model.md), it coordinates,
  routes, and reviews; it must not directly mutate repos or perform
  specialist delivery work.
- Workers do not own policy. Policy lives in
  [packages/policies/](../../packages/policies/).

## Validation

Python lane — `./scripts/test_python.sh`.

## Related docs

- [docs/agent-model.md](../../docs/agent-model.md)
- [docs/architecture.md](../../docs/architecture.md)
- [docs/approval-policy.md](../../docs/approval-policy.md)
- [AGENTS.md](../../AGENTS.md)
