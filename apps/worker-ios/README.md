# worker-ios

The iOS implementation lane. Claims iOS-lane tasks, runs iOS code
changes and build/simulator workflows, and prepares release-candidate
artifacts for the App Store lane.

## Owns

- claiming and executing [`WorkerLane.IOS`](../../packages/schemas/task_packet.py)
  tasks from the control plane
- iOS bugfix and feature implementation via the `ios/` runner
- Xcode build and simulator workflows
- iOS-specific validation under the shared tests-with-code contract
- preparing release-candidate artifacts and handing them to the App
  Store lane

## Does not own

- App Store submission, metadata, screenshots, or review responses
  (that is [worker-appstore](../worker-appstore/))
- general Python engineering (that is
  [worker-engineering](../worker-engineering/))
- approval decisions — irreversible actions are routed for approval

## Entrypoint

[main.py](main.py) — `execute_claimed_task()` claims one `IOS` task
and runs it. iOS-specific logic lives under [ios/](ios/).

## Task types accepted

- iOS bugfix and feature tasks against `products/catchbook-ios/`

## Validation

iOS lane — `./scripts/test_ios.sh`. This regenerates the Xcode project
from `products/catchbook-ios/project.yml`, runs `xcodebuild test`, and
reports target coverage.

Per the shared tests-with-code policy, logic-bearing iOS changes under
`products/catchbook-ios/Sources/` must ship with created or modified
tests under `products/catchbook-ios/Tests/`, unless a machine-readable
no-test exception is valid.

## Boundaries

- iOS implementation and App Store release are separate lanes by
  design. This worker prepares release-ready artifacts; it does not
  interact with App Store Connect.
- Workers do not own policy. Policy lives in
  [packages/policies/](../../packages/policies/).

## Related docs

- [docs/ios-lane.md](../../docs/ios-lane.md)
- [docs/ios-conventions.md](../../docs/ios-conventions.md)
- [docs/codex-worker.md](../../docs/codex-worker.md)
- [docs/agent-model.md](../../docs/agent-model.md)
