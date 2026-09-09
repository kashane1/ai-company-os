# runtime-supervisor

The local runtime operator. A launchd-friendly process that manages
worker loop lifecycles on an always-on Mac. It is a thin runtime
operator flow, not a full orchestration system.

## Owns

- starting, stopping, and reporting status of the local runtime
  supervisor
- managing the engineering, iOS, App Store, API, skill-evolution, billing-poller,
  outreach, and reply-sync process lifecycles; see the
  [default process specs](supervisor/specs.py) for the current list
- clean shutdown: a stop-request file is watched and honored by the
  running supervisor loop
- fail-closed process health: an unexpected child exit marks the supervisor
  failed and stops the remaining managed workers

## Does not own

- claiming tasks or performing any worker work
- worker business logic
- goal decomposition or task routing (that is
  [worker-supervisor](../worker-supervisor/) — a distinct concern
  despite the similar name)

## Entrypoint

[main.py](main.py) is a launchd entrypoint shim. Real logic lives in
the sibling [supervisor/](supervisor/) subpackage:

- `supervisor/core.py` — `RuntimeSupervisor` class and poll loop
- `supervisor/specs.py` — default worker specs
- `supervisor/dispatch_router.py` — `target_runtime` → provider routing

Operated via [cli.py](cli.py), wrapped by `./scripts/runtime`:

```bash
./scripts/runtime start
./scripts/runtime status
./scripts/runtime stop
```

`status` reads the persisted supervisor status file under
`state/checkpoints/platform/`; `stop` writes a stop-request file the
running loop honors.

Queue reconciliation is a separate stopped-worker maintenance action. Inspect
the proposed repairs first, then apply them only after the worker processes are
stopped:

```bash
python3 scripts/control_plane_db.py reconcile-queue
python3 scripts/control_plane_db.py reconcile-queue --apply --workers-stopped
```

This repairs dispatch records from canonical task state. It does not make task
execution exactly once. Redis idle reclaim remains experimental and disabled by
default because workers do not publish execution heartbeats or per-attempt claim
tokens.

## Boundaries

- The supervisor manages worker loop processes only. It does not
  claim tasks or perform work.
- Queue reconciliation does not run automatically inside the supervisor.
- Current scope is a thin local runtime operator flow, per
  [docs/local-dev.md](../../docs/local-dev.md) — not a full
  orchestration system.

## Validation

Python lane — `./scripts/test_python.sh`.

## Related docs

- [docs/local-dev.md](../../docs/local-dev.md)
- [docs/architecture.md](../../docs/architecture.md)
