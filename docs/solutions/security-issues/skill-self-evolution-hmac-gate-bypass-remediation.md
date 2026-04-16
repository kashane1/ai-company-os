---
title: "Skill Self-Evolution HMAC Gate Bypass — Four-Reviewer Remediation"
problem_type: security-architecture-gap
component: skill-evolution-approval-primitive
modules:
  - packages/tools/primitives/approvals.py
  - packages/policies/skill_evolution.py
  - apps/worker-skill-evolution/main.py
  - apps/approval-reviewer/main.py
  - packages/policies/approval_tokens.py
severity: critical
date: 2026-04-15
prs:
  under_review: "#8"
  keychain_follow_up: "#9"
remediation_commit: aa8f5f6
reviewers:
  - security-sentinel
  - kieran-python-reviewer
  - code-simplicity-reviewer
tags:
  - hmac
  - keychain
  - approval-tokens
  - skill-evolution
  - phase-3
  - security-review
  - four-reviewer-pass
  - option-b
---

# Skill Self-Evolution HMAC Gate Bypass — Four-Reviewer Remediation

## Problem

PR #8 (Phase 3 skill self-evolution loop) shipped an HMAC-signed
approval-token primitive that claimed to be the "load-bearing security
boundary between autonomous worker code and human-reviewed skill
changes." The PR was reviewed by four independent automated reviewers
(security-sentinel, kieran-python, code-simplicity, docs-reviewer) who
collectively found that the claim was false against the stated threat
model.

The stated threat model: "gates must hold even if the worker itself is
compromised, and attackers may control the files workers emit under
`state/checkpoints/`."

The actual implementation: the HMAC signing key, the signed token with
its signature, and the CLI that reads both were all stored under the
same uid on the same filesystem. A compromised sibling worker could
approve its own proposals with four lines of Python.

## Findings (ordered by severity)

### Critical

**C1 — HMAC gate collapsed to decoration.** The `approval-reviewer
sign` CLI auto-loaded the HMAC signature from the on-disk token store
when `--signature` was omitted. Since the token store lives under
`state/checkpoints/platform/approval_tokens/` — the same uid as the
worker — running `approval-reviewer sign <id>` with no args was a
free approval. No out-of-band secret needed. (`security-sentinel`)

**C2 — Signing secret readable by same-uid processes.** The HMAC key
lived at `state/checkpoints/platform/approval_signing_key` with mode
0600. Mode 0600 protects against other users but not against a same-
uid compromised sibling worker, which is the primary adversary in the
Phase 3 threat model. (`security-sentinel`)

### High

**H1 — Device fingerprint check disabled.** `expected_device_fingerprint`
was left `None` at token issue time, short-circuiting the burn-side
check in `verify_and_burn_token` and accepting any device.
(`security-sentinel`)

**H2 — `skill_evolution_apply` not in `P0_ACTIONS`.** The action got a
30-minute token TTL instead of 5 minutes, with no second-factor
requirement. Self-evolved canonical skill code is at least as dangerous
as protected-branch merges. (`security-sentinel`)

**H3 — Sidecar path injection.** `load_sidecar` accepted absolute
paths, `..` traversal, null bytes, and non-normalized POSIX paths from
`state/checkpoints/platform/skill_evolution_proposals/<task_id>.json` —
which is attacker-writable if a sibling worker is compromised.
(`security-sentinel`)

**H4 — Reviewer identity forgeable.** `_default_reviewer` used
`os.environ["USER"]` which any caller can set to anything.
(`security-sentinel`)

### Correctness blockers

**K1 — Fixture/skill atomicity check was a no-op.** The
`check_fixture_skill_atomicity` function gated on
`"validator.py" in diff.removed_paths` — which only fires when the
validator is *deleted*. A realistic "add a new fixture to an existing
skill without touching the validator" drift case bypassed the gate
silently. (`kieran-python`)

**K2 — Burn-before-validate DoS.** `submit_evolution_approval` called
`verify_and_burn_token` before checking `approval_id`. An attacker
with a valid `(token_id, signature)` pair could permanently burn the
token by submitting with a wrong `approval_id`, DoS'ing the legitimate
reviewer. (`kieran-python`)

**K5 — Integration test bypassed the HMAC path entirely.** The
"happy path" integration test simulated the reviewer by calling
`ApprovalStore.update_status` directly — never exercising
`verify_and_burn_token`. All HMAC checks could have been broken and
the test would still have passed. (`kieran-python`)

### Simplicity

**S1 — `check_regression_fixture_gate` stub.** A `NotImplementedError`
stub existed "so the symbol is importable" — inviting a future PR to
wire it into the composite just to make it exist. Deleted.
(`code-simplicity`)

**S2 — `write_sidecar` helper.** Tests were the only caller. Tests now
write JSON directly. (`code-simplicity`)

**S3 — Runbook Section 2.** Described a `git revert` flow for a cherry-
pick that cannot happen in Option B (the worker never mutates
`skills/canonical/`). Cut. (`code-simplicity`)

## Root Cause

The root cause is a gap between the stated threat model and the
implementation's actual defense perimeter. The threat model says
"same-uid sibling worker compromise is in scope." The implementation
stored every secret and every artifact on the same filesystem under the
same uid. No amount of HMAC hardening (symlink refusal, atomic
bootstrap, mode-0600 enforcement) can close that gap — the adversary
reads the key and forges the signature, because they have the same
filesystem access the legitimate reader has.

The secondary root cause is "decorative testing" — the integration test
for the HMAC path tested the wrong thing (store-level status flip
instead of the actual `verify_and_burn_token` call), giving false
confidence that the security path was covered.

## Solution

### Phase 1 — In-PR remediation (commit `aa8f5f6`)

Every finding except C2 was fixed on the same branch before merge:

| Finding | Fix | Regression test |
|---|---|---|
| C1 | `--signature` mandatory on `cmd_sign`; `cmd_list` hides signature | Argparse `required=True`; new test |
| H1 | Bind `expected_device_fingerprint` at issue time (hostname default) | `test_submit_with_wrong_device_fingerprint_is_rejected` |
| H2 | Add `skill_evolution_apply` to `P0_ACTIONS`; reduce worker max_wait to 240s | Structural assertion on `P0_ACTIONS` membership |
| H3 | `_require_safe_id` + `_require_safe_path` in `load_sidecar`; new `SidecarValidationError` | `test_sidecar_with_absolute_path_is_rejected`, `test_sidecar_with_parent_traversal_is_rejected`, etc. |
| H4 | `pwd.getpwuid(os.getuid()).pw_name` instead of `os.environ["USER"]` | Verified in dry-run walkthrough |
| K1 | Filesystem-based incumbent check (`validator.py` exists on disk?) via `canonical_root` kwarg | `test_fixture_only_diff_is_drift_when_incumbent_exists` |
| K2 | Load and check `approval_id` BEFORE calling `verify_and_burn_token` | `test_submit_with_mismatched_approval_id_does_not_burn_token` |
| K5 | Rewritten to use `submit_evolution_approval` with real HMAC path; asserts `burn_count==1` | `test_end_to_end_approved` |
| S1-S3 | Deleted stub, helper, and runbook section | N/A |

### Phase 2 — Keychain migration (PR #9, commit `4b9df7d`)

Addresses C2 — moves the signing key into macOS Keychain:

- `_load_signing_secret()` routes through `/usr/bin/security
  find-generic-password` on macOS by default.
- On `KeychainAccessDenied`, the function **refuses to fall through**
  to the filesystem — silent fallback would defeat the migration.
- `KeychainUserCancelled` (user clicked Deny on the first dialog)
  gets its own error class with a distinct recovery hint.
- Bare `KeychainError` (timeout, missing binary, unrecognized exit)
  is caught and wrapped with an operator-actionable `RuntimeError`
  naming the `FORCE_FILE` escape hatch.
- `bootstrap-keychain` CLI subcommand creates the item with a
  binary-path ACL; `rotate-keychain --confirm rotate` replaces it.
- `_is_access_denied_stderr` markers trimmed to three
  (`"interaction is not allowed"`, `"not authorized"`, `"-25308"`)
  per three-reviewer consensus. Dropped `"authorization"` (too
  broad), `"operation not permitted"` (EPERM), `"-128"`
  (user-cancelled, now separate class).
- Filesystem fallback preserved for non-macOS + explicit
  `AI_COMPANY_OS_APPROVAL_KEY_FORCE_FILE=1` escape hatch.

## Prevention Strategies

### Secret handling

- **Co-location is a design bug, not a hardening problem.** If the
  secret and the artifact it protects live under the same uid, the
  signing is decorative regardless of file permissions. Review
  checklist: "Can the same process that reads the protected artifact
  also read the signing key?" If yes, move the key out of the
  filesystem.
- **No-arg footgun scan.** CLIs that perform privileged actions
  (sign, approve, deploy) must require at least one explicit
  argument that cannot be auto-populated from local state. Review
  any `default=` or auto-load behavior on security-sensitive flags.
- **Bootstrap must be atomic.** `write → chmod` is a TOCTOU race.
  Use `os.open(O_CREAT|O_EXCL|O_WRONLY|O_NOFOLLOW, 0o600)` for
  the create path and `os.open(O_RDONLY|O_NOFOLLOW)` + `fstat`
  mode-check for the read path.
- **Reject empty/whitespace secret material loudly.** A
  whitespace-only env var decoded as hex gives `b""` — a valid but
  trivially forgeable HMAC key. Enforce a minimum length (32 bytes
  = 256 bits) at every load site.

### Test design

- **The mock boundary must be outside the security-critical path.**
  If the threat model says "HMAC verification prevents forged
  approvals," the test must call the same entry point an attacker
  would call — not a store-level helper that skips the HMAC check.
  An integration test that mocks the component it claims to test
  is decorative.
- **Assert the artifact, not just the status.** After a signing test,
  assert `burn_count == 1` and `device_fingerprint` is set on the
  stored token. Status-level assertions (`outcome == "approved"`)
  pass even when the underlying mechanism is broken.

### Code review patterns

- **Burn-before-validate inversion.** Any token consumption
  (delete/invalidate) must happen after all validation passes.
  Search for store mutations before conditional checks.
- **Path traversal on attacker-writable inputs.** Every path sourced
  from a config file under `state/` is attacker-controlled if a
  sibling worker is compromised. Reject absolute paths, `..`,
  null bytes, and non-normalized POSIX forms.
- **Stated threat model vs actual implementation.** When a PR claims
  "X is the security boundary," run four independent reviewer
  agents against it and see if the claim holds. In this case, four
  agents found six separate ways the claim was false.

### Using independent reviewer agents effectively

- **Security-sentinel** caught C1, C2, H1-H4 — every cryptographic
  and secret-handling issue. Best at: threat-model-aware reviews
  where the attacker surface is defined.
- **Kieran-python** caught K1, K2, K5 — every correctness and
  test-coverage gap. Best at: line-by-line code walkthrough,
  TOCTOU reasoning, assertion quality.
- **Code-simplicity** caught S1-S3 + flagged `_is_access_denied_stderr`
  over-broad markers. Best at: "is this earning its keep?" questions.
- All three independently flagged the `"authorization"` stderr
  marker as too broad — consensus across reviewers is a strong
  signal.

## Related Documentation

- [Hermes platform upgrade plan](../../plans/2026-04-14-feat-hermes-inspired-platform-upgrade-plan.md) — parent plan, Phase 3 section
- [Keychain migration plan](../../plans/2026-04-15-macos-keychain-approval-signing-migration.md) — follow-up plan for PR #9
- [Primitives subpackage ADR](../../adr/2026-04-14-primitives-subpackage.md) — convention that forced lazy subprocess imports
- [Canonical skill layout ADR](../../adr/2026-04-14-canonical-skill-layout.md) — per-skill-dir layout for `skill-self-evolution`
- [Revert runbook](../../runbooks/skill-evolution-revert.md) — updated with Keychain rotation section
- [Revert dry-run record](../integration-issues/skill-evolution-revert-dryrun-2026-04-15.md)
- [Phase 2 spike findings](../../research/2026-04-hermes-spike-findings.md)
- GitHub PRs: [#7](https://github.com/kashane1/ai-company-os/pull/7), [#8](https://github.com/kashane1/ai-company-os/pull/8), [#9](https://github.com/kashane1/ai-company-os/pull/9)

## The Compounding Value

First time this class of problem is encountered (HMAC gate that
doesn't hold against its own threat model): 6+ hours of four-reviewer
analysis, remediation, Keychain migration, runbook dry-run, and
observation-window setup.

Second time: search `docs/solutions/security-issues/` → find this
file → apply the prevention checklist → catch it in the first review
pass, not the fourth.

The secret-handling principles, the "decorative testing" pattern, and
the "stated threat model vs actual implementation" review technique
are reusable across every future approval gate, not just
skill-evolution.
