# api

The control-plane HTTP surface. This is where founder intent enters
the system and where oversight happens. It stays thin and delegates
business logic to services and policy.

## Owns

- the HTTP API for goals, tasks, approvals, and task claims
- the magic-link approval endpoint, mounted under `/magic/approvals`
- control-plane service wiring (`ControlPlaneService`)

## Does not own

- worker execution or repo mutation
- policy decisions — those delegate to
  [packages/policies/](../../packages/policies/)
- durable scheduling or worker routing

## Entrypoint

[main.py](main.py) builds the FastAPI `app` and mounts the approval
router. Supporting modules:

- [control_plane.py](control_plane.py) — `ControlPlaneService` and
  payload helpers
- [approval_endpoint.py](approval_endpoint.py) — magic-link approval
  routes
- [platform.py](platform.py) — platform seed/inspection helpers
- [server.py](server.py) — server entry

## Boundaries

- The API remains thin and delegates business logic to services and
  workers, per [docs/architecture.md](../../docs/architecture.md).
- The current repo includes a minimal real control-plane slice for
  persisted goals, tasks, approvals, events, and task claims. A
  dashboard remains a documented future surface — do not assume it
  exists.

## Validation

Python lane — `./scripts/test_python.sh`.

## Related docs

- [docs/architecture.md](../../docs/architecture.md)
- [docs/approval-flow.md](../../docs/approval-flow.md)
- [docs/approval-policy.md](../../docs/approval-policy.md)
