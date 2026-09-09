# Reliability decisions and their limits

The useful part of building this system has been deciding how to inspect
agent output and recover when a step fails. These examples distinguish code
and tests from procedures that still depend on an operator or agent following
them.

## Preserve the previous record when a write fails

[PostMortemStore.save](../packages/db/postmortem_store.py) writes a temporary
file and replaces the destination with `os.replace`. The
[failure-injection test](../tests/python/integration/test_audit_artifact_crash_safety.py)
checks that a serialization error preserves the previous record and removes
the temporary file. This is evidence for that failure case, not a blanket
power-loss or concurrent-writer durability guarantee.

## Keep lifecycle writes inside one database boundary

Control-plane lifecycle methods use the shared transaction context in
[`ControlPlaneDatabase`](../packages/db/control_plane_db.py). Task, goal,
approval, event, and database-backed dispatch writes either commit together or
roll back together, including calls made through separate store instances. The
[transaction tests](../tests/python/unit/test_control_plane_transactions.py)
exercise nested commits, rollback, and reuse after a failed transaction.

Task completion also fails closed. The control plane checks claim ownership and
runs the lane's post-run validator against listed artifacts and already-persisted
task events. Missing evidence, an unavailable validator, or a malformed verdict
records a failed task instead of accepting completion. The
[failure-recovery tests](../tests/python/integration/test_control_plane_failure_recovery.py)
cover write failures and retry behavior; they do not establish exactly-once
execution of worker code or external effects.

## Treat Redis recovery as an operator action

For Redis Streams, database state is canonical and delivery is at least once.
Acknowledgement is bound to the current worker claim and deferred until the
database lifecycle commit succeeds. The queue reconciliation command is a dry
run by default:

```bash
python3 scripts/control_plane_db.py reconcile-queue
python3 scripts/control_plane_db.py reconcile-queue --apply --workers-stopped
```

The apply form is for a stopped-worker maintenance window. It removes orphaned
or terminal queue entries, restores missing pending entries, and preserves
active nonterminal entries. Automatic idle reclaim is experimental and off by
default because there is no execution heartbeat or per-attempt claim token; a
restarted process using the same worker ID cannot be fenced as a distinct
attempt. The
[Redis failure-recovery tests](../tests/python/integration/test_redis_queue_recovery.py)
cover these bounded cases.

An abandoned active task has a separate dry-run/apply recovery path:

```bash
python3 scripts/control_plane_db.py recover-task TASK_ID --reason "worker stopped"
python3 scripts/control_plane_db.py recover-task TASK_ID --reason "worker stopped" --apply --workers-stopped
```

Apply marks the original attempt failed and creates a pending replacement under
a child goal, preserving the earlier record. Review any external effects before
restarting workers; replacement execution is not automatically safe to repeat.
For Redis, run the reconciliation preview/apply again to remove the old terminal
dispatch and check the new pending entry. The
[real worker demo](../scripts/worker_demo.py) and its
[integration test](../tests/python/integration/test_real_worker_demo.py) show an
offline outreach success and a preserved failed attempt through the real worker
path.

## Fail the supervised process group when a child exits

The [runtime supervisor](../apps/runtime-supervisor/supervisor/core.py) treats an
unexpected managed-child exit as a supervisor failure and stops the remaining
workers. Its [process tests](../tests/python/unit/test_runtime_supervisor.py)
verify the persisted failed status and sibling shutdown. This surfaces process
loss; it does not restart work or decide whether an in-progress task is safe to
retry.

## Validate the fields that cross a parsing boundary

[TaskRun.from_dict](../packages/schemas/task_run.py) converts worker lane,
classification, and status through enums. The
[typed-surface tests](../tests/python/unit/test_typed_tool_surface.py) cover
unknown enum values and missing required fields. Direct dataclass construction
and type annotations do not provide complete runtime validation; several
fields are coerced and some policy values remain strings.

## Test the approval mechanism independently of its illustration

The [offline demo](../scripts/demo/run_demo.py) constructs sample approval
records. It does not demonstrate authorization. The
[token integration tests](../tests/python/integration/test_approval_tokens.py)
exercise signature rejection, expiry, single-use tokens, and local endpoint
state changes instead.

The API assumes a trusted local environment. P0 actions require a second
confirmation with the same token/device; the name “second factor” in code does
not imply independent MFA. This is a bounded local mechanism, not a complete
security boundary for an internet-facing service.

## Define when an iteration should stop

The [simulator polish skill](../skills/canonical/simulator-driven-polish/skill.md)
sets decision tiers, recurrence limits, and a build-failure stop condition.
These make operator expectations explicit. They are agent instructions; the
skill itself does not prove automatic enforcement or successful golden-image
comparison on every run. Review a
[recorded session](products/life-clock/polish-2026-05-05.md) alongside the procedure.

## Keep development fixtures behind a build boundary

[LifeClockLaunchConfiguration.swift](../products/life-clock-ios/Sources/App/LifeClockLaunchConfiguration.swift)
uses `#if DEBUG` for its environment-based fixtures and supplies production
defaults in Release. The
[configuration tests](../products/life-clock-ios/Tests/LifeClockLaunchConfigurationTests.swift)
show expected fixture behavior. This is evidence about this configuration
surface, not a claim that every test hook throughout the product was audited.

## Scope redaction and retention precisely

[PostMortem](../packages/schemas/postmortem.py) applies redaction to selected
fields, including notes, excerpts, remediation text, and fixture paths. The
engineering and iOS Codex runners separately redact subprocess stdout and
stderr plus selected execution metadata before writing platform-owned logs and
records.
The [engineering](../tests/python/unit/test_codex_runner.py) and
[iOS](../tests/python/unit/test_ios_codex_runner.py) runner tests plant
credential-shaped canaries. The Codex CLI's separate last-message output is
outside this redaction claim. These checks do not prove that every artifact or
Git history is free of secrets.

[Postmortem retention policy](../packages/policies/postmortem_retention.py)
controls visibility and stale-record checks. Its time window is not automatic
deletion of all runtime artifacts. Likewise, loading a serialized task-run
record is not the same as replaying the original agent execution.

For runnable verification and the scope of each check, use the
[evaluator walkthrough](EVALUATOR-WALKTHROUGH.md).
