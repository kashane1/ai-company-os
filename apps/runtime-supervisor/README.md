# runtime-supervisor

The local runtime operator. A launchd-friendly process that manages
worker loop lifecycles on an always-on Mac. It is a thin runtime
operator flow, not a full orchestration system.

## Owns

- starting, stopping, and reporting status of the local runtime
  supervisor
- managing the engineering, iOS, and App Store worker loop lifecycles
- clean shutdown: a stop-request file is watched and honored by the
  running supervisor loop

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

## Boundaries

- The supervisor manages worker loop processes only. It does not
  claim tasks or perform work.
- Current scope is a thin local runtime operator flow, per
  [docs/local-dev.md](../../docs/local-dev.md) — not a full
  orchestration system.

## Validation

Python lane — `./scripts/test_python.sh`.

## Related docs

- [docs/local-dev.md](../../docs/local-dev.md)
- [docs/architecture.md](../../docs/architecture.md)
