# Failure Modes — Engineering Lane

Phase 1.4. Every row must have either a detection test under
`tests/python/integration/` or an explicit `no_test_reason_code` with
justification. Failure codes follow the `packages/schemas/testing.py`
pattern.

| Condition | Detection | Recovery | failure_code | Who resolves |
|---|---|---|---|---|
| Codex CLI not on PATH | `scripts/preflight_codex.sh` at supervisor startup | Supervisor marks engineering lane `blocked:codex_not_on_path` in status file; morning briefing surfaces | `codex_not_on_path` | Founder installs codex |
| Codex auth expired | `codex --version` ok but `codex exec` returns auth error | Lane `blocked:codex_auth_expired`; briefing asks founder to re-auth | `codex_auth_expired` | Founder runs `codex login` |
| Codex exec non-zero exit | Worker catches exit, emits result `status=failed` with stdout tail | Task retried once, then parked on `failure_code` | `codex_exec_failed` | Engineering worker (auto retry) / founder (if persistent) |
| Worktree deleted mid-run | Worker's worktree path missing after claim | Result `status=failed`, worktree re-created on next claim | `worktree_missing` | Engineering worker |
| Git index.lock present on claim | Worker stat check before `git worktree add` | Task re-queued, cleanup script run (non-auto-remove) | `git_index_lock` | Founder |
| Disk full | Write to worktree fails with ENOSPC | All lanes paused; supervisor writes red status; briefing surfaces first | `disk_full` | Founder |
| Mac asleep during dispatch | Claim succeeds but no progress; stale_claim_ms elapsed | Task re-queued by queue reaper | `stale_claim_timeout` | Queue reaper |
| Protected-branch merge attempted without approval | `packages/policies/release_readiness.py` | `PolicyViolation` raised, result `status=failed` | `merge_approval_missing` | Founder |
| Network outage during remote push | `git push` non-zero | Result `status=failed`, retried once | `remote_push_failed` | Worker / founder |
| Runtime-supervisor launchd plist not loaded | `launchctl print` absent at briefing | Briefing surfaces, include install command in output | `supervisor_not_running` | Founder |

`no_test_reason_code` for environment-only rows (`codex_not_on_path`,
`codex_auth_expired`, `disk_full`, `supervisor_not_running`):
`environmental_only`. All other rows must have an integration test.
