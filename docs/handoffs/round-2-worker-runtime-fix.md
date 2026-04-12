# Round 2 worker-runtime fix — Claude Code handoff

You are Claude Code running on Kashane's Mac against the `ai-company-os` repo at `~/ai-company-os`. A prior Cowork session landed Round 1 fixes on `staging` (PRs #3, #4, #5 already merged to `staging`). Round 1 was incomplete — 13 tests still fail. Your job is to apply Round 2, get `pytest tests/python -q` green on `staging`, then fast-forward `main` to `staging`.

Do NOT run this work on `main`. Everything lands on `staging` first. `main` only moves via fast-forward after tests pass.

## Environment pre-flight

1. `cd ~/ai-company-os`
2. Ensure the runtime-supervisor is unloaded so Spotlight / launchd don't race on `.git/index.lock`:
   ```
   launchctl unload ~/Library/LaunchAgents/com.ai-company-os.runtime-supervisor.plist || true
   ```
3. If `.git/index.lock` exists, check `lsof .git/index.lock`. If only `mds_stores` (Spotlight) holds it, `rm .git/index.lock` is safe. Long-term: add `~/ai-company-os` to System Settings → Spotlight → Search Privacy.
4. `git fetch origin && git checkout staging && git pull --ff-only origin staging`
5. Confirm working tree has these uncommitted files from the prior session (they should exist; don't recreate if missing):
   - `CLAUDE.md` — modified to add a "use codex cloud" trigger-phrase row
   - `docs/codex-cloud-dispatch.md` — new playbook

## Commit A — commit the uncommitted playbook + trigger

```
git add CLAUDE.md docs/codex-cloud-dispatch.md
git commit -m "docs: add Codex Cloud dispatch playbook and CLAUDE.md trigger row"
```

If either file is missing from the working tree, skip this commit and note it in your final report.

## Commit B — pytest importmode fix

`tests/python/unit/` and `tests/python/integration/` both contain a file named `test_approval_token_audit_skill.py`. Legacy "prepend" import mode errors on collection. Fix:

Edit `pyproject.toml` under `[tool.pytest.ini_options]`. Add:
```
importmode = "importlib"
```

Verify collection works:
```
pytest tests/python --collect-only -q
```

Commit:
```
git add pyproject.toml
git commit -m "test: switch pytest to importlib mode to handle duplicate test basenames"
```

## Commit C — Round 2 code fixes (bundle as one commit)

### Fix 1: control-plane gate leniency

**File:** `apps/api/control_plane.py`
**Function:** `ControlPlaneService.submit_task_result`

The post-run validation gate currently runs whenever status is COMPLETED, using `artifacts or []` and `events or []`. That conflates "caller did not pass the kwargs" with "caller passed an empty list". Direct-service test callers don't pass the kwargs and get downgraded to FAILED.

**Change:** skip `_run_post_run_validation(...)` entirely when **both** `artifacts is None` AND `events is None`. When either is an explicit list (even empty), run the gate as before. The signature should keep defaults as `None`, not `[]` — do not change the kwarg defaults from `None`.

Worker mains already pass `artifacts=list(...)` and `events=[...]` after Round 1, so production enforcement is preserved.

### Fix 2: codex_runner metadata cleanup

**File:** `apps/worker-engineering/engineering/codex_runner.py`
**Function:** `execute_codex`

Remove `session_id` from `metadata_payload` entirely. The value still flows through `CodexExecutionRecord` — don't touch that. The test asserts the payload has exactly these 11 keys:
```
command, command_display, cwd, exit_code, finished_at, packet_path,
started_at, stderr_path, stdout_path, task_id, timed_out
```
The current conditional-on-not-None approach fails on Kashane's machine because he has real codex session logs, so the key gets added. Drop it from the metadata payload unconditionally.

### Fix 3: xcode.py scheme derivation

**File:** `packages/tools/ios_tools/xcode.py`
**Function:** `default_build_command`

Round 1 hardcoded `scheme="Catchbook"`, which regressed `test_render_task_packet_uses_ios_implementation_defaults` (that test uses `FishingLogbook.xcodeproj`). Derive the scheme from the basename of `project_reference`:

```python
def default_build_command(project_reference: str) -> str:
    basename = project_reference.rsplit("/", 1)[-1]
    scheme = basename.removesuffix(".xcworkspace").removesuffix(".xcodeproj")
    return build_command(
        scheme=scheme,
        destination="platform=iOS Simulator,name=iPhone 16",
        project_reference=project_reference,
    )
```

This should satisfy both `test_default_build_command_uses_catchbook_defaults` and `test_render_task_packet_uses_ios_implementation_defaults`.

### Run the suite

```
pytest tests/python -q
```

Expected: all previously-failing tests now pass. Remaining xfails in `tests/python/conftest.py::_PREEXISTING_FAILURES` should be re-evaluated — if any are now passing with `strict=False`, shrink the frozenset.

If `test_appstore_worker_*` still fails, it is likely the same gate issue: inspect the failing caller, confirm it's a direct-service call without artifacts/events kwargs, and confirm Fix 1 covers it. Do not weaken tests. Do not delete the shim wholesale.

### Commit

```
git add apps/api/control_plane.py apps/worker-engineering/engineering/codex_runner.py packages/tools/ios_tools/xcode.py
git commit -m "fix(worker-runtime): round 2 — gate leniency, codex metadata, xcode scheme

- control_plane.submit_task_result: skip post-run validation when artifacts
  and events kwargs are both None (distinct from empty list). Workers still
  pass explicit lists, so production enforcement is preserved.
- codex_runner.execute_codex: drop session_id from metadata_payload so the
  11-key shape holds on machines with real codex session logs.
- xcode.default_build_command: derive scheme from project_reference basename
  so both Catchbook and FishingLogbook test fixtures resolve correctly."
```

## Commit D — shrink the shim

**File:** `tests/python/conftest.py`

After the suite is green, remove every nodeid from `_PREEXISTING_FAILURES` whose test now passes. If the set is empty, leave the frozenset empty (don't delete the hook or the shim infrastructure — it's load-bearing for future regressions).

```
git add tests/python/conftest.py
git commit -m "test: shrink _PREEXISTING_FAILURES after round 2 fixes land"
```

Re-run `pytest tests/python -q` one more time to confirm no strict-xfail upgrades broke anything.

## Push staging

```
git push origin staging
```

## Promote staging → main (fast-forward only)

```
git checkout main
git pull --ff-only origin main
git merge --ff-only staging
git push origin main
git checkout staging
```

If `--ff-only` fails, STOP. Do not force-push. Report to Kashane — it means `main` has commits staging doesn't, which is a policy violation that needs human investigation.

## Post-merge

Reload the runtime-supervisor:
```
launchctl load ~/Library/LaunchAgents/com.ai-company-os.runtime-supervisor.plist
```

## Guardrails (hard)

- Never edit `_PREEXISTING_FAILURES` to *add* entries. Only shrink.
- Never weaken or skip assertions to make tests pass.
- Never edit files under `packages/policies/` or `skills/canonical/` without stopping and asking Kashane — those require explicit approval.
- Never force-push. Never `git reset --hard` on a shared branch.
- Never merge to `main` unless fast-forward is clean.
- If any fix produces a diff larger than ~15 lines in a file you weren't told to touch, stop and report before committing.

## Final report format

End your session with:
- Commits created (SHA + subject)
- Final `pytest tests/python -q` pass/fail/xfail counts
- Entries removed from `_PREEXISTING_FAILURES`
- Any tests you couldn't make pass and why
- Confirmation that `main` fast-forwarded and supervisor is reloaded
