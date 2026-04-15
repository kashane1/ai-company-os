# macOS Keychain Approval-Signing Migration Plan

**Status:** proposed
**Author:** Claude Opus 4.6 (security remediation pass on PR #8)
**Date:** 2026-04-15
**Precondition:** Phase 3 (skill self-evolution loop) has landed with
the Option B HMAC primitive at
`packages/tools/primitives/approvals.py`.
**Parent threat model:** security-sentinel review of Phase 3 PR #8,
critical findings C1 and C2.

## Why this plan exists

The Phase 3 approval primitive uses HMAC-signed magic-link tokens
to gate human approval of self-evolved skills. The HMAC signing
secret is the entire trust root — anyone who can read it can forge
arbitrary tokens and approve any proposal.

The Phase 3 first landing stores the signing secret as a
filesystem file at
`state/checkpoints/platform/approval_signing_key` (mode 0600,
symlink-refused, atomic bootstrap). PR #8's remediation pass closed
the easy wins: no write-then-chmod race, no symlink follow, no
empty-key acceptance. But the architectural gap remains:

**A same-uid compromised sibling worker can read the key with
`os.open(..., O_NOFOLLOW)` and sign arbitrary tokens.**

Option B's threat model explicitly calls out same-uid worker
compromise as in-scope — earlier-phase workers are "semi-trusted"
and attackers may control the files they emit. Under that threat
model, filesystem-based secret storage is security theater:
hardening the file stops an attacker who tampers with the file,
but not one who simply reads it.

macOS Keychain provides a same-uid defense: a process can store a
secret with an ACL that names which binaries are allowed to read
it, and the Keychain Services daemon enforces the ACL
out-of-process. A compromised sibling worker whose binary path
isn't on the ACL gets denied even though it runs as the same uid.

This plan migrates the approval signing secret from filesystem
storage to Keychain storage, with a binary-ACL lock so only the
approval-reviewer CLI and the skill-evolution worker can read it.

## Scope

**In scope:**

- Move the HMAC signing key out of the filesystem and into the
  macOS Keychain under a named generic-password item.
- Configure a Keychain ACL so only the specific binaries involved
  in the skill-evolution flow can read the key without a user
  prompt: `.venv/bin/python` (when running the worker entrypoint),
  the approval-reviewer CLI, and the dry-run test harness.
- Replace `_load_signing_secret` in
  `packages/tools/primitives/approvals.py` with a Keychain-backed
  reader that falls through to the filesystem path only if an
  explicit environment flag is set (for CI and non-macOS platforms).
- Add a one-shot bootstrap command
  (`python -m apps.approval_reviewer bootstrap-keychain`) that:
  - Generates a fresh 32-byte secret.
  - Stores it in Keychain with the correct ACL.
  - Deletes the existing filesystem key if it exists.
- Update `docs/runbooks/skill-evolution-revert.md` with the key
  rotation procedure (Keychain version).
- Add tests that exercise the Keychain path on macOS CI runners
  and skip cleanly on Linux CI.

**Out of scope:**

- Moving the signature itself out of the filesystem. The signature
  lives in the token store today (`state/checkpoints/platform/approval_tokens/<id>.json`).
  Moving IT to Keychain would need a different shape — Keychain is
  not a general-purpose database, and one-item-per-proposal is
  clumsy. A separate follow-up will address signature-at-rest
  differently: either by not persisting the signature at all
  (compute once at issue, require the reviewer to paste it from
  out-of-band) or by encrypting the token store with a Keychain-
  resident key.
- Cross-platform Keychain support. macOS only. Linux / Windows
  fall through to the filesystem path with a loud warning in the
  module docstring.
- HSM / hardware key support.

## Design

### Keychain item shape

```
service  = "ai-company-os"
account  = "approval_signing_key"
kind     = generic_password
acl      = allow-reads-without-prompt: [
             /Users/simons/ai-company-os/.venv/bin/python,
             /Users/simons/ai-company-os/apps/approval-reviewer/main.py,
           ]
```

Stored via:

```bash
security add-generic-password \
  -a approval_signing_key \
  -s ai-company-os \
  -w "$(python -c 'import secrets; print(secrets.token_hex(32))')" \
  -T /Users/simons/ai-company-os/.venv/bin/python \
  -T /Users/simons/ai-company-os/apps/approval-reviewer/main.py \
  -U
```

Read via:

```bash
security find-generic-password \
  -a approval_signing_key \
  -s ai-company-os \
  -w
```

The `-T` flags on `add-generic-password` add trusted applications
to the ACL. A non-listed binary reading the item triggers a GUI
prompt for the user to grant access — a compromised sibling worker
script run from an unexpected path never gets silent access.

### `_load_signing_secret` rewrite

```python
def _load_signing_secret() -> bytes:
    raw_env = os.environ.get(SIGNING_KEY_ENV_VAR)
    if raw_env:
        return _decode_env_secret(raw_env)  # unchanged

    if sys.platform == "darwin" and not os.environ.get(
        "AI_COMPANY_OS_APPROVAL_KEY_FORCE_FILE"
    ):
        try:
            return _read_keychain_secret()
        except KeychainNotFound:
            raise RuntimeError(
                "approval signing key not found in Keychain. "
                "Run `python -m apps.approval_reviewer bootstrap-keychain` "
                "once to create it."
            )
        except KeychainAccessDenied as exc:
            raise RuntimeError(
                f"refusing to sign with filesystem fallback: "
                f"Keychain access denied ({exc}). "
                f"If this process is legitimately allowed to sign, "
                f"add its binary to the Keychain item ACL. "
                f"Filesystem fallback is intentionally disabled on "
                f"macOS to preserve the threat-model guarantees."
            )

    # Non-macOS (Linux CI, Windows) or explicit force-file override.
    return _read_filesystem_secret()
```

The `KeychainAccessDenied` branch deliberately refuses to fall
through to the filesystem path, because silent fallback would
undo the whole point of the migration. A legitimate caller that
gets denied must explicitly add its binary to the ACL.

### Bootstrap command

`apps/approval-reviewer/main.py` grows a new subcommand
`bootstrap-keychain`:

```bash
python -m apps.approval_reviewer bootstrap-keychain
```

This:

1. Refuses to run if the Keychain item already exists (operator
   must delete it first — rotation is a deliberate action).
2. Generates 32 random bytes via `secrets.token_bytes(32)`.
3. Calls `security add-generic-password` via subprocess with the
   right `-T` flags.
4. If `state/checkpoints/platform/approval_signing_key` exists on
   disk, prompts the operator for explicit "yes, delete the old
   filesystem key" confirmation before removing it.
5. Prints the Keychain item path so the operator can verify via
   `security find-generic-password -s ai-company-os`.

A separate `rotate-keychain` subcommand will add the same flow
but without the "refuse if exists" step — it's the expected way
to roll the key.

### Revocation

When a key leaks:

```bash
security delete-generic-password -a approval_signing_key -s ai-company-os
python -m apps.approval_reviewer bootstrap-keychain
```

Every outstanding token becomes unverifiable because the new key
is different. Workers blocked on approvals will fail on next
poll with a signature-mismatch error. Operators re-enqueue those
tasks.

## Tests

### macOS-only tests (skipped on Linux CI)

- `test_keychain_bootstrap_creates_item` — run the bootstrap
  command against a fresh Keychain, verify the item exists,
  verify the secret round-trips through `_load_signing_secret`.
- `test_keychain_bootstrap_refuses_existing` — bootstrap, then
  bootstrap again, assert the second call errors without
  touching the existing item.
- `test_keychain_access_denied_does_not_fall_through` — mock
  `security find-generic-password` to return exit 51 (access
  denied), assert `_load_signing_secret` raises `RuntimeError`
  with the expected message, NOT fall through to the filesystem.
- `test_keychain_force_file_override` — set
  `AI_COMPANY_OS_APPROVAL_KEY_FORCE_FILE=1`, assert the filesystem
  path is taken even on macOS. This is the CI escape hatch.

### Cross-platform tests (run everywhere)

- `test_filesystem_fallback_on_linux` — mock `sys.platform =
  "linux"`, assert the function uses the filesystem path.
- All existing `test_skill_evolution_approvals_primitive.py`
  cases must continue passing. They currently use the env-var
  path (`AI_COMPANY_OS_APPROVAL_SIGNING_KEY=00...`) which is
  platform-independent.

## Rollback

1. Revert the Phase 4 migration PR.
2. Run `python -m apps.approval_reviewer bootstrap-filesystem`
   (added in the same migration PR for symmetry) to re-create the
   filesystem key from scratch.
3. The token store is untouched by this migration — outstanding
   tokens that were signed under the old filesystem key will
   verify cleanly against the newly-bootstrapped filesystem key
   IF the rollback is done before the Keychain key is rotated.
   After rotation, old tokens are permanently invalidated and
   must be re-enqueued.

## Sequencing relative to Phase 3

**Phase 3 first landing ships WITHOUT this migration.** The
filesystem key is hardened (symlink-refused, atomic bootstrap,
mode-0600 enforced) which closes the easy-wins from
security-sentinel C2. The migration plan ships alongside as the
answer to security-sentinel C1 — "filesystem storage doesn't
defend against same-uid read."

**Sequence:**

1. Phase 3 first landing (PR #8, now) — filesystem + hardening.
2. This plan — Keychain migration.
3. Follow-up — signature-at-rest redesign (either "don't
   persist" or "encrypt token store").

Step 2 MUST land before Phase 3 is marked "done" per the plan's
72-hour observation window. Running the skill-evolution worker in
production with filesystem-based signing is acceptable as a
short-term trade (it's still better than no HMAC at all), but it
is not an acceptable steady state.

## Open questions

- **Does the Keychain prompt a user once and remember?** Yes, the
  "always allow" button on the first prompt persists. For a
  non-interactive worker running from launchd, we pre-seed the
  ACL at bootstrap time so no prompt ever fires.
- **What about Linux / non-macOS dev machines?** The filesystem
  fallback stays. Non-macOS developers get a loud warning in
  logs on every worker startup.
- **Does `AI_COMPANY_OS_APPROVAL_SIGNING_KEY` env var override
  still work?** Yes, for CI hermeticity. Set to any hex string,
  Keychain is bypassed, filesystem is bypassed. The env var is
  the highest-precedence source.
- **What happens when `.venv/bin/python` is recreated?** The
  Keychain ACL is keyed on binary path + inode + signature. A
  recreated venv gets a new inode and the ACL stops trusting
  it. The operator re-runs `bootstrap-keychain --add-current`
  (a sub-flag of the bootstrap command) to extend the ACL to
  the new binary. Documented in the runbook.

## Definition of Done

- `security find-generic-password -s ai-company-os -a approval_signing_key -w`
  returns a 32-byte hex secret on the production machine.
- Running `apps/worker-skill-evolution/main.py` succeeds without
  any prompt or filesystem key.
- The filesystem key at
  `state/checkpoints/platform/approval_signing_key` has been
  deleted on the production machine.
- `docs/runbooks/skill-evolution-revert.md` has a Keychain
  rotation section.
- Phase 3 72-hour observation window is re-started from zero
  after this lands (the threat model changed).

## References

- Apple Keychain Services documentation:
  <https://developer.apple.com/documentation/security/keychain_services>
- `security(1)` man page: `man security`
- security-sentinel review of Phase 3 PR #8 (the document that
  triggered this plan)
- `packages/tools/primitives/approvals.py:_load_signing_secret`
  (the function this plan replaces)
