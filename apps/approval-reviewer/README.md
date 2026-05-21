# approval-reviewer

The human-operated review-and-sign CLI for the approval surface. A
deliberately boring command-line tool a human runs to inspect and
decide skill-evolution approvals.

## Owns

- `list` — show every pending skill-evolution approval with its
  staged artifact dir, rationale, and the token id used to sign
- `show <approval_id>` — render the proposal artifact dir contents
  (diff, rationale, manifest) for review in the terminal
- `sign <approval_id> --token-id X --signature Y` — verify the HMAC
  signature and flip the `ApprovalRecord` to `approved`
- `reject <approval_id> --reason "..."` — mark the approval `rejected`
- `bootstrap-keychain` / `rotate-keychain` — manage the signing-secret
  entry in the macOS login Keychain

## Does not own

- approval policy — it is the signing surface, not the policy author
- worker execution
- producing the proposals (that is
  [worker-skill-evolution](../worker-skill-evolution/))

## Entrypoint

[main.py](main.py) — the CLI. It reads its HMAC signing secret via the
same path the worker uses: the macOS login Keychain (bootstrapped on
first run), or a hardened filesystem file on non-macOS hosts.

## Boundaries

- A human runs this tool; it is the local human confirmation surface.
- The `sign` arguments (`--token-id`, `--signature`) are mandatory and
  retrieved out-of-band from the worker's task-output log — they are
  never printed by `list`.
- On macOS, the real authorization for silent Keychain reads is the
  operator clicking "Always Allow" on the first Keychain dialog.

## Validation

Python lane — `./scripts/test_python.sh`.

## Related docs

- [docs/approval-flow.md](../../docs/approval-flow.md)
- [docs/approval-policy.md](../../docs/approval-policy.md)
- [docs/runbooks/skill-evolution-revert.md](../../docs/runbooks/skill-evolution-revert.md)
