# worker-appstore

The App Store release-operations lane. Handles everything between "we
have a release-ready build" and "the app is live" — with human
approval gates on irreversible actions.

## Owns

- TestFlight preparation
- metadata, screenshots, and release-notes drafting
- App Store Connect submission-state tracking
- release-state tracking via the release store
- requesting human approval before irreversible release actions

## Does not own

- application source code or Xcode builds (that is
  [worker-ios](../worker-ios/))
- iOS implementation or bugfixes
- product strategy or feature decisions
- approval decisions — it requests, the approval surface decides

## Entrypoint

[main.py](main.py) — `execute_release_action(release_id, action,
approval_id)` runs a release action. Actions that require approval
return a `BLOCKED` result with next-action signals until an approval
record is supplied.

## Inputs and outputs

- **Input:** a release-ready build artifact from the iOS lane plus a
  release/submission task.
- **Output:** updated release state under
  `state/checkpoints/platform/releases/`, metadata drafts, and
  approval requests for irreversible actions.

## Approval gates

Per [docs/approval-policy.md](../../docs/approval-policy.md):

- **Approval-gated:** `submit_testflight`, `submit_appstore`,
  `release_to_store`.
- **Safe to automate:** `prepare_testflight`, drafting metadata and
  release notes, validating checklist completeness.

## Validation

Python lane — `./scripts/test_python.sh`.

## Boundaries

- App Store release and iOS implementation are separate lanes. If a
  review rejection needs a code change, this worker creates a new iOS
  task — it does not fix code itself.

## Related docs

- [docs/appstore-lane.md](../../docs/appstore-lane.md)
- [docs/ios-lane.md](../../docs/ios-lane.md)
- [docs/approval-policy.md](../../docs/approval-policy.md)
- [docs/approval-flow.md](../../docs/approval-flow.md)
