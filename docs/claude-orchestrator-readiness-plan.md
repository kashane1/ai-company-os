# Claude Orchestrator Readiness Plan

Purpose: upgrade `ai-company-os` from "Claude can be a provisional orchestrator" to "Claude can be the lead orchestrator" by closing the specific gaps identified in the orchestrator audit (2026-04-10).

This plan has been hardened against the compound-engineering document-review skill (seven reviewer personas — coherence, feasibility, adversarial, scope-guardian, security, product-lens, design-lens). See the review log at the bottom for the full audit trail of findings and how each was addressed.

## Guiding constraints

- Do not violate the repo's architectural rules. Platform owns orchestration, policies live in `packages/policies/`, runtime state lives in `state/`, iOS and App Store stay separate lanes.
- Every new piece of state must be a typed record, not free prose.
- Every automation surface must be safe to disable: stopping the runtime-supervisor LaunchAgent leaves the system coherent.
- Every new code path ships with lane-matching tests under `tests/python/` as the repo's testing policy requires, and an explicit failure-modes table listing detection, recovery, and `failure_code`.
- No new process supervisor. The existing `apps/runtime-supervisor/` is the one lifecycle manager. launchd runs the runtime-supervisor; runtime-supervisor runs everything else.
- No denormalized runtime state in source-controlled config files. Derived views live under `state/checkpoints/platform/`, never in `infra/`.
- Secrets never read from ad-hoc `.env` parsing inside daemons. All new code uses `packages/config/secrets.py` (see Phase 0.4).
- Every canonical skill ships with eval fixtures before it is allowed in `skills/registry.yaml` (see Phase 0.5). No skill goes live without a measurable pass bar.
- External skills and plugins (e.g. from `anthropics/skills`, compound-engineering-plugin) go through a written intake policy before any file lands in `skills/canonical/` (see Phase 5.5).
- Any MCP surface that carries publish or spend authority (Postiz, Gemini, Gmail drafts, scheduled-tasks) requires a written threat model before the GTM worker is allowed to use it (see Phase 2.0).

## Priority reframing (product-lens)

The single largest gap identified by the review is that the original plan optimized for engineering-lane autonomy while Kashane's actual near-term bottleneck is GTM. The locked fishing-logbook launch is a GTM push, not an engineering push. The repo already ships `packages/tools/social_tools/postiz_client.py` and `packages/tools/content_tools/gemini_images.py`, and memory records that Kashane wants agents to make marketing decisions autonomously and surface summaries only.

Phases are therefore reordered: GTM autonomy is elevated to **Phase 2**, before the engineering-lane hardening in what is now Phase 3. ROI notes are attached to each phase so the plan can early-stop cleanly once the April launch is unblocked.

---

## Phase 0 — Pre-flight and basics (day 0)

ROI: removes risk that any later phase silently fails on a hidden assumption.

### 0.0 Filesystem round-trip handshake (new, blocks all dispatch work)

The Claude sandbox writes files through a bridge and the Mac-side daemons read from the mounted repo. Before investing in any dispatch pattern, prove the round-trip works.

- Write `state/handshake/claude-<timestamp>.ping` from the Claude sandbox.
- A tiny one-shot script `scripts/handshake_echo.sh` run from the Mac reads the ping and writes a matching `.pong`.
- Claude reads back the pong and asserts timestamp, content equality, and sub-second visibility.
- Failure modes: pong never appears (filesystem not shared), pong has stale content (caching), unicode mangled (encoding).
- Acceptance: three successful round-trips across three separate Claude sessions. Until this passes, all dispatch-by-file-drop work in Phase 3 is blocked and the fallback is "Claude writes task packets, Kashane runs the on-Mac worker-engineering loop manually."

### 0.1 Python interpreter alignment

Preferred approach: bump the Claude sandbox interpreter to 3.12, keeping `pyproject.toml`'s `requires-python = ">=3.12"` floor intact. If the sandbox interpreter is not controllable from this repo, fall back to relaxing the floor to `>=3.10` *only after* running the verification command below.

- Verification: `grep -RnE 'match [A-Za-z_][A-Za-z0-9_]*:' apps/ packages/` to find any `match` statements (3.10-compatible but syntax-check), and `python3.10 -c "import ast; [ast.parse(open(p).read()) for p in <collected>]"` to catch 3.12-only syntax.
- Test: `pytest tests/python -q` runs clean on the chosen interpreter.
- Acceptance: Claude can `pip install -e ".[test]"` from the sandbox without a version error, and the full test suite is green.

### 0.2 Git worktree hygiene (scoped down)

- File: `scripts/cleanup_agent_worktrees.sh` (new) — prunes `.git/worktrees/` entries whose target path no longer exists, using `git worktree prune` (safe, git-native). Does **not** remove `index.lock`. Instead, if `index.lock` is present, the script logs and exits non-zero so the founder can inspect — auto-removing an index.lock risks corrupting an in-progress git operation.
- File: `.claude/worktrees/` cleanup — delete dirs older than 7 days *only if* `git -C <dir> status --porcelain` is empty AND `git -C <dir> stash list` is empty.
- Wired as: an on-demand script, not a scheduled job, until it has been run manually three times without incident.
- Test: `tests/python/unit/test_worktree_cleanup.py` covers prune-stale-entry and refuse-to-delete-dirty-worktree.
- Acceptance: `git worktree list` and `git status` run clean on both the Mac and the sandbox.

### 0.3 Per-session worktree convention

- File: `docs/claude-session-conventions.md` (new).
- Rule: every Claude session that mutates code creates `state/worktrees/claude/<session-id>/` via `SupervisorSession` (Phase 3.3) and removes it on close if clean. Sessions that leave uncommitted work must write a `handoff.md` in the worktree before closing.
- Exercised by: `tests/python/integration/test_supervisor_session.py`.

### 0.4 Secrets loading helper (new)

- File: `packages/config/secrets.py` (new).
- API:
  ```python
  def get_secret(name: str, *, source: Literal["env", "keychain"] = "env") -> str
  def require_secret(name: str, *, source=...) -> str  # raises if missing
  ```
- Loads from `.env` by default, from macOS Keychain via `security find-generic-password -s <service> -a <account> -w` when `source="keychain"`.
- Rule: App Store Connect API keys and any credential touching approval-gated actions must come from Keychain, not `.env`. Postiz, Gemini, and other third-party keys may come from `.env` if the founder prefers.
- Every new daemon or script added in later phases uses this helper. No ad-hoc `os.environ.get("FOO_KEY")` in new code.
- Test: `tests/python/unit/test_secrets.py` with a fake subprocess for the keychain path.

### 0.5 Skill hygiene and eval gate (new)

**Skill kinds — disambiguation.** Skills under `skills/canonical/` come in two kinds, and the difference is load-bearing:

- **`kind: validator`** — pure Python. Deterministic, side-effect free, no LLM round-trip. Safe to call from hot paths (`ControlPlaneService.submit_task_result`, `release_readiness.py`). Implementation lives at `skills/canonical/<id>/validator.py` exposing a `run(input) -> Result` function.
- **`kind: agentic`** — LLM-backed. Called only from already-LLM-driven contexts (the GTM worker's runner, the morning briefing session, a `SupervisorSession`). Never called from synchronous policy code.

`skills/registry.yaml` grows a `kind` column. The loader (`packages/tools/skills/loader.py`) refuses to load an `agentic` skill from a context marked `synchronous=true`, and refuses to load a `validator` skill that attempts an LLM call. This distinction eliminates the hot-path latency risk.

Mapping for the skills introduced in this plan:
- `content-voice-guardrail`: **agentic** (runs inside GTM worker).
- `social-post-safety`: **validator** for FTC / TOS / dead-link checks + **agentic** fallback for ambiguous rewrites — split into two skill entries if needed.
- `aso-keyword-refresh`: **agentic**.
- `creator-outreach-draft`: **agentic**.
- `approval-token-audit`: **validator** (pure HMAC + store replay, no LLM needed).
- `post-run-validation`: **validator** (contract check against declared outputs).
- `failure-mode-regression`: **validator** (log scan + file write + dedupe window).


Rationale: after reviewing public skill ecosystems (`anthropics/skills`, `EveryInc/compound-engineering-plugin`, GitHub Agent Skills), the conclusion is that the repo's canonical skill system is the right backbone, but we need a measurable gate before any skill — homegrown or borrowed — is allowed to run autonomously. Without this gate the "skill zoo" failure mode is cheap to hit and expensive to unwind.

- Directory: every canonical skill under `skills/canonical/<skill-id>/` gains a sibling `fixtures/` directory with at minimum three eval cases — `happy_path.yaml`, `boundary.yaml`, `adversarial.yaml`. Cases are declarative: input, expected output contract, tolerated variations.
- **Bootstrap rule — skills must ship with fixtures at creation.** The Phase 0.5 gate applies to *all* skills, not just pre-existing ones. Any new skill added in Phases 2-4 (content-voice-guardrail, social-post-safety, aso-keyword-refresh, creator-outreach-draft, approval-token-audit, post-run-validation, failure-mode-regression) must include a `fixtures/` directory in the same PR that introduces the skill. No skill is allowed to be merged in a "to be evaluated later" state. This removes the bootstrap paradox: skills created in Phase 2 are already eligible for autonomous mode on merge.
- Runner: `infra/scripts/eval-skills.sh` (new) invokes **promptfoo** for `agentic` skills and plain `pytest` for `validator` skills against their fixtures. Promptfoo is scoped specifically to agentic skills, not to every LLM call in the system.
- **Runner location**: eval runs on the Mac under the user session, not in the Claude sandbox. Node runtime (required by promptfoo) is assumed available on the Mac; if absent, `eval-skills.sh` exits with a clear "install Node 20+" message and the pre-commit hook warns without blocking.
- **Cost bound**: promptfoo runs on change (skill file modified) and on a nightly cron via scheduled-tasks MCP, not on every commit. Nightly full-sweep budget capped at 200 LLM calls. Per-skill-edit run capped at 9 calls (3 fixtures × 3 variance runs). Budget enforcement via a `--max-calls` flag in `eval-skills.sh` that aborts the run and reports rather than silently consuming tokens.
- Registry enforcement: `skills/registry.yaml` grows a `fixture_status` column with values `passing` / `failing` / `missing`. `packages/tools/skills/loader.py` (new) refuses to load any skill whose row is not `passing` when the caller requests `mode="autonomous"`. `mode="manual"` still allows unrated skills but tags every output with `skill_unrated=true` in the event store.
- CI hook: `eval-skills.sh` runs on any change under `skills/canonical/**` via a pre-commit hook at `infra/hooks/pre-commit-skills`. The hook is advisory (warn + exit 0) for the first 10 days so fixture backfill does not block other work, then switches to blocking.
- Variance tolerance: eval cases use the skill-creator skill's variance-analysis pattern — three runs per case, pass bar is "all three match the contract." This catches skills that are flaky, not just wrong.
- Credential safety: promptfoo must never touch production credentials during eval. Fixtures use stubbed backends only. Enforced by a lint pass in `eval-skills.sh` that rejects fixtures containing `$ENV.` references to known-production secret names.
- Acceptance:
  - `infra/scripts/eval-skills.sh` exists and is invocable locally.
  - Every skill currently in `skills/registry.yaml` has at least a `happy_path.yaml` fixture (backfill for the existing eight: product-artifact-chain, codex-claude-handoff, ios-ui-polish-review, ios-to-appstore-handoff, supervisor-goal-decomposition, app-store-positioning-pack, and the two skills added in Phase 2 below).
  - The loader refuses `mode="autonomous"` for any skill with `fixture_status != passing`.
  - The pre-commit hook flips from advisory to blocking 10 days after Phase 0.5 exit.
- Test: `tests/python/unit/test_skills_loader.py` covers the autonomous/manual gate logic and the refusal path.
- Failure modes: promptfoo crash (runner returns non-zero, loader falls back to `manual` mode), fixture drift (CI warns on hash change), provider API outage during eval (runner marks cases `skipped`, not `passing`).

---

## Phase 1 — Use the existing workers and runtime-supervisor under launchd (days 1-2)

ROI: unlocks headless engineering and iOS execution without writing a second process supervisor. Delivers most of the original Phase 1 value in a fraction of the scope.

The original plan proposed two new "bridge" daemons (`apps/worker-codex-bridge/`, `apps/worker-xcode-bridge/`). The scope-guardian review correctly flagged this as reinvention — `apps/worker-engineering/` and `apps/worker-ios/` already exist, already wrap Codex and Xcode, already claim tasks from the control plane, and already report structured results. The right fix is to run what the repo already has.

### 1.1 Runtime-supervisor as a macOS LaunchAgent

- File: `infra/launchd/com.ai-company-os.runtime-supervisor.plist` (new).
- Type: **UserAgent** (`~/Library/LaunchAgents/`), not a LaunchDaemon, so it runs inside Kashane's login session with GUI access. This is required because Xcode, simulator, and codex CLI auth all live in the user session.
- Behavior: `RunAtLoad=true`, `KeepAlive=true`, `StandardOutPath` and `StandardErrorPath` point at `state/logs/runtime-supervisor/launchd.log`.
- Command: `<abs-path>/scripts/runtime start`.
- Installation: one-time `launchctl bootstrap gui/<uid> ~/Library/LaunchAgents/com.ai-company-os.runtime-supervisor.plist`. Disable path: `launchctl bootout gui/<uid>/com.ai-company-os.runtime-supervisor`.
- Acceptance: after reboot, the runtime-supervisor is running, its status file at `state/checkpoints/platform/runtime-supervisor-status.json` reflects `running`, and both `worker-engineering` and `worker-ios` show up in its managed workers list.

### 1.2 Codex auth pre-flight for the daemon context

The whole engineering lane assumes `codex exec` runs successfully from a user-session daemon. Verify this *before* declaring Phase 1 done, not after.

- Script: `scripts/preflight_codex.sh` (new). Runs `codex --version` and a trivial `codex exec` on a scratch worktree containing a README with a one-line task ("add a comment to README.md").
- Invoked by: the runtime-supervisor at startup, logging to `state/logs/runtime-supervisor/preflight.log`. If preflight fails, the runtime-supervisor marks the engineering lane `blocked` in its status file and the failure reason is surfaced in the next morning's briefing (Phase 4.1).
- Same pattern for `scripts/preflight_xcode.sh` — `xcodebuild -version` and `xcodegen generate` on a catchbook scratch copy.
- Acceptance: on a clean Mac with codex and Xcode installed, preflight is green; on a Mac missing either, the status file clearly reports which lane is blocked.

### 1.3 Enqueue path for Claude to hand tasks to the existing workers

The existing workers already claim tasks from `ControlPlaneService`. Claude just needs a clean enqueue path.

- File: `packages/tools/supervisor/enqueue.py` (new) — thin wrappers around `ControlPlaneService.create_task` that take typed task definitions and return the persisted task record.
- Claude calls this from `SupervisorSession` (Phase 3.3). The existing worker loops handle the rest.
- Test: `tests/python/integration/test_enqueue_for_existing_workers.py` enqueues a synthetic engineering task and asserts the engineering worker's claim path picks it up.

### 1.4 Failure-modes table for the engineering and iOS lanes (new discipline)

- File: `docs/failure-modes/engineering-lane.md` and `docs/failure-modes/ios-lane.md`.
- Columns: condition, detection, recovery, `failure_code`, who resolves. Covers at minimum: codex auth expired, codex exit non-zero, worktree deleted mid-run, xcodebuild timeout, simulator boot failure, project.yml regeneration failure, disk full, Mac asleep during dispatch, git operation in progress.
- Reuses the existing `packages/schemas/testing.py` `failure_codes` pattern. Every new failure mode gets a code that the worker can emit.
- Acceptance: every row has a detection test in `tests/python/integration/` or an explicit `no_test_reason_code=environmental_only` with justification.

---

## Phase 2 — GTM and content autonomy (days 3-5)

ROI: **this is the phase that directly serves the locked April launch.** If the plan early-stops here, Kashane still gets the highest-leverage autonomy win.

Memory records: (a) Kashane's GTM decisions are locked for the April fishing-logbook launch, (b) Kashane's weakness is GTM, not engineering, (c) Kashane has explicitly asked for agents to make marketing decisions autonomously and surface summaries only, (d) the repo already has `packages/tools/social_tools/postiz_client.py` and `packages/tools/content_tools/gemini_images.py` scaffolded. The original plan had no GTM phase at all. That was the biggest product-lens miss.

### 2.0 MCP threat model (hard gate before 2.1) (new)

The GTM worker hands publish authority and image-gen authority to autonomous runs. Before any credentials are wired, a written threat model must exist. Without this, a prompt-injected draft or a compromised upstream MCP becomes a publish-path exploit with no containment.

- File: `docs/security/mcp-threat-model.md` (new).
- Required sections:
  1. **Surface map** — every MCP the GTM lane touches (Postiz, Gemini, Gmail drafts, scheduled-tasks, mcp-registry), the exact operations the worker is allowed to call, and the scope of the credentials involved.
  2. **Confused-deputy scenarios** — enumerated: (a) Gemini returns text containing instructions that the scheduler then interprets, (b) a drafted social post contains a URL that a later skill fetches and acts on, (c) a scheduled task created by one skill triggers another skill outside its intended lane, (d) a Gmail draft body is read back by the approval-sweep session and parsed as an approval directive.
  3. **Credential scoping** — Postiz key restricted to specific account IDs (not account-admin), Gemini key restricted to image-gen endpoint only, Gmail scope is drafts-only (no send), scheduled-tasks scope is create-only (not delete). Each scoping is asserted by `preflight_gtm.sh`.
  4. **Blast radius** — worst-case outcome per surface if a credential is leaked or a call is adversarially steered. For each, the documented containment: rate limits, approval gate, redaction pass, kill switch.
  5. **Kill switch** — a single `scripts/gtm_freeze.sh` (new) that writes `state/flags/gtm_frozen` which the GTM worker checks (a) before every task claim (becomes a no-op), (b) before every MCP call inside an in-flight task (raises `GtmFrozenError`, which the runner catches and re-queues the task with `status=paused:frozen` rather than failing it). This means engaging the freeze mid-task does not strand work — tasks are paused cleanly and resume automatically when the flag is cleared via `scripts/gtm_unfreeze.sh`.
- **Time box**: the threat model is a 2-3 hour founder sitting producing a 1-2 page document, not a multi-week security program. Phase 2 slips if it exceeds one day of effort — if it does, descope to the minimum surface-map + kill-switch and open a strategic task for deeper review.
- **Re-acknowledgment path**: `scripts/acknowledge_threat_model.sh` (new) recomputes the file hash and writes it to `state/checkpoints/platform/security-state.json`, requiring a `--read` flag as a lightweight "I actually reviewed the diff" gesture. Running the script is the only way to clear `blocked:threat-model-drift`. The diff that was acknowledged is appended to `state/checkpoints/platform/security-log.jsonl` so the audit trail survives.
- Acceptance: the threat model is reviewed (by Kashane) and committed before `preflight_gtm.sh` is allowed to return green. The runtime-supervisor reads a `security/mcp-threat-model.md:checksum` entry from `state/checkpoints/platform/security-state.json`; if the file's hash differs from the recorded checksum the GTM lane is marked `blocked:threat-model-drift` until `acknowledge_threat_model.sh` is run.
- Test: `tests/python/integration/test_gtm_freeze.py` verifies that setting the freeze flag makes the GTM worker claim zero tasks, and that the threat-model-drift guard fires on content change.

### 2.1 GTM lane as a first-class worker

- File: `apps/worker-gtm/main.py` (new), modeled on `apps/worker-engineering/main.py`.
- File: `apps/worker-gtm/gtm/runner.py`, `gtm/validator.py`, `gtm/postiz_runner.py`, `gtm/content_runner.py`.
- Task types (added to `packages/schemas/task_packet.py`): `CONTENT_DRAFT`, `CONTENT_IMAGE_GEN`, `SOCIAL_POST_SCHEDULE`, `GTM_CAMPAIGN_BRIEF`, `ASO_METADATA_REFRESH`.
- Policy: **external posts are approval-gated**, internal drafts are not. Draft-and-schedule runs autonomously; the final "publish now" transition always requires an approval record. Approval policy lives in `packages/policies/approvals.py` (add `is_gtm_publish_action(...)`).
- Autonomy mode matches memory's "make marketing decisions autonomously, surface summaries only": the worker creates drafts, schedules, and tracks engagement without prompting; the morning briefing (Phase 4.1) is the surface.
- Test: `tests/python/integration/test_gtm_worker.py` with a fake Postiz backend and a fake Gemini image backend.

### 2.2 Postiz and Gemini credential wiring

- Both clients already exist. Ensure they load via `packages/config/secrets.py` (Phase 0.4), not raw env access.
- Add a `scripts/preflight_gtm.sh` that verifies Postiz auth and Gemini auth, same pattern as `preflight_codex.sh`.

### 2.3 GTM artifact chain for catchbook

- Files under `docs/products/catchbook/gtm/`: `campaign-calendar.md`, `content-backlog.md`, `hook-library.md`, `hashtag-strategy.md`, `performance-log.md`. These are the artifacts the GTM worker reads from and writes to.
- Validator: `packages/tools/product_artifacts/gtm_chain.py` — mirrors the artifact chain validator in Phase 5.1 but for GTM.
- Acceptance: catchbook has a populated content backlog of at least 14 days pre-launch by Phase 2 exit.

### 2.4 Failure-modes table for GTM

- File: `docs/failure-modes/gtm-lane.md`. Conditions: Postiz auth expired, Gemini quota hit, account warming cooldown, post rejected by platform, analytics fetch failure, credential rotation, kill-switch engaged, threat-model-drift block.

### 2.5 GTM skill pack (new)

These are the concrete canonical skills the GTM worker calls. All four are scoped narrowly — no single skill owns the full post lifecycle, so a failure in one cannot cascade into a bad publish. Each skill is canonical under `skills/canonical/<id>/` with a Claude adapter under `skills/adapters/claude/<id>.md` and a thin routing pointer under `.claude/skills/<id>.md`. Each ships Phase 0.5 fixtures at creation time.

- **content-voice-guardrail** — `skills/canonical/content-voice-guardrail/`. Inputs: a draft post + `docs/products/catchbook/gtm/voice.md` (brand voice guide). Outputs: `pass` / `fail` with a diff of off-voice phrases and suggested rewrites. Called by the GTM worker before every `CONTENT_DRAFT` result is persisted. Fails closed — an unparseable voice guide blocks the draft rather than letting it through.
- **social-post-safety** — `skills/canonical/social-post-safety/`. Inputs: a draft post, the target platform (TikTok, Instagram, Threads), the campaign record. Checks FTC disclosure presence when the campaign is paid, platform-TOS compliance (TikTok affiliate rules, IG paid-partnership tags), dead-link detection (fetches linked URLs, refuses if 4xx/5xx or redirected to an unexpected host), and profanity/PII scan. Must pass before `SOCIAL_POST_SCHEDULE` is allowed to run. Hard gate.
- **aso-keyword-refresh** — `skills/canonical/aso-keyword-refresh/`. Inputs: the current catchbook App Store metadata from `docs/products/catchbook/app-store/metadata.md` and a keyword-rank snapshot from App Store Connect. Outputs: a diff plus a recommendation. If the recommended diff exceeds a configurable threshold it files a `APPSTORE_METADATA_DRAFT` strategic task rather than editing metadata directly. Scheduled weekly via the scheduled-tasks MCP.
- **creator-outreach-draft** — `skills/canonical/creator-outreach-draft/`. Inputs: a target creator list at `docs/products/catchbook/gtm/creator-targets.md` and a campaign brief. Outputs: personalized outreach DMs written to `state/artifacts/outreach/<date>/<creator>.md`. **Explicit non-automation boundary**: this skill drafts only. There is no skill that sends DMs. Kashane copies from the artifact and sends manually. The boundary is enforced by: (a) no MCP send capability wired, (b) a lint check in the skill adapter that refuses any output containing "I have sent" or similar first-person send claims, (c) a failure-mode entry for "attempted auto-send".

Additional scheduling: the GTM worker honors a per-platform cooldown table at `packages/policies/gtm_cooldowns.py` so `SOCIAL_POST_SCHEDULE` tasks cannot post more frequently than the platform's safe cadence.

Acceptance:
- All four skills exist under `skills/canonical/` with fixtures, adapters, and routing pointers.
- `packages/tools/skills/loader.py` can load each in `mode="autonomous"` (which requires Phase 0.5 eval pass).
- `tests/python/integration/test_gtm_skill_chain.py` runs a fake campaign through draft → voice-guardrail → social-post-safety → schedule and asserts each gate fires correctly.
- `creator-outreach-draft` integration test asserts no send path exists in the codebase: `grep -r "postiz.*send\|outreach.*send" apps/worker-gtm/` returns empty.

---

## Phase 3 — Claude supervisor session and approval surface (days 6-8)

ROI: closes the control-plane loop Claude drives, and makes approvals real.

### 3.1 Approval surface — Claude-session based, not daemon based

The original plan proposed `apps/worker-approval-inbox/` as a launchd Python daemon that would ingest Gmail replies. The feasibility review caught two problems: (a) the Gmail tooling Cowork has is MCP, not a daemon-callable Python library, so a daemon can't use it, and (b) email-reply approval is spoofable and replayable even with a sender allowlist. Both are fatal to the original design.

The fix is to pick one ingestion model — a scheduled Claude session — and to harden the auth channel.

- **Scheduling**: the scheduled-tasks MCP runs a Claude session every 15 minutes called `approval-sweep`. That session uses the Gmail MCP (not a daemon) to search for unread messages matching the approval workflow pattern, reads them, validates, and writes to the approval store via `ControlPlaneService.update_approval`.
- **Auth channel**: not plain email reply. Approval requests are delivered as Gmail drafts containing a single **magic-link** URL to `http://127.0.0.1:<port>/approvals/<token>`, where `<token>` is a fresh HMAC-signed value with:
  - A short TTL (default 30 minutes; 5 minutes for P0 actions like App Store submission, protected-branch merges, billing, DNS).
  - Single-use: the token is burned in the approval store on first successful read.
  - Device-bound: the approval endpoint records the approving device fingerprint in the approval record's audit trail.
- **Local approval endpoint**: a small FastAPI app inside `apps/api/` exposing `GET /approvals/<token>` which renders a one-page confirm screen. No auth beyond possession of the token plus a localhost bind. Kashane approves from his Mac only. Remote approvals are out of scope for Phase 3; revisit only if needed.
- **Second-factor for P0**: App Store submission, protected-branch merges, billing, and DNS require a second confirmation — Kashane reopens the approval page and clicks "confirm submit" within a 60-second window. Not a separate device, just a separate click with a separate HMAC.
- **Sender verification**: because the ingestion channel is now magic-link not reply-parsing, sender spoofing is no longer load-bearing. The allowlist is retained as defense in depth but is not the primary control.
- Files: `packages/policies/approval_tokens.py` (new), `apps/api/approval_endpoint.py` (new), `scripts/scheduled/approval_sweep_session.md` (new — the Claude session prompt).
- Test: `tests/python/integration/test_approval_tokens.py` covers TTL, single-use, second-factor, and tampered-token rejection.

### 3.2 Release-readiness policy (unchanged from original plan, now with explicit helper)

- File: `packages/policies/release_readiness.py` (new).
- Helper added to `packages/policies/approvals.py`: `is_approval_granted(approval_id: str, expected_type: str) -> bool`. Short addition, directly testable.
- Rule: `approve_app_store_submission(release_id)` raises `PolicyViolation` unless (a) the product's `submission-checklist.md` has zero unchecked items, (b) an approval record exists and is `approved`, (c) the release record is in `ready` status, and (d) the approval is of type `app_store_submission`.
- Wired into the App Store worker's release-prep seeding in `apps/api/platform.py`.
- Test: `tests/python/unit/test_release_readiness.py` covers each failure mode.

### 3.2a approval-token-audit skill (new)

- Canonical: `skills/canonical/approval-token-audit/`.
- Purpose: before any P0 action executes, replay the magic-link HMAC chain for the cited approval and verify: token issuance matches the expected action and subject, TTL was honored, single-use flag was burned exactly once, second-factor confirmation exists and is within the 60-second window, device fingerprint matches, and the approval record transitioned through expected states in the audit trail. This is the eval counterpart to Phase 3.1 — Phase 3.1 creates the token machinery, this skill verifies it at call-time.
- Kind: **validator** (pure Python; no LLM round-trip), per Phase 0.5 disambiguation. Safe to call synchronously from hot-path policy code.
- Called from: `packages/policies/release_readiness.py::approve_app_store_submission`, protected-branch merge policy, billing action policy, DNS action policy. Integration point: the policy calls the validator via `packages/tools/skills/loader.py::load_validator("approval-token-audit").run(...)`.
- **Fail closed**: any exception from the validator (parse error, store unreachable, unexpected state) is caught by the policy wrapper and converted to `PolicyViolation("approval_audit_unavailable")`. Under no circumstance does a validator failure produce an "approved" outcome. Test suite includes an explicit "validator raises → policy raises" case.
- Fixtures at creation per Phase 0.5: happy path, expired token, reused token, missing second-factor, tampered HMAC, wrong action type, device mismatch.
- Test: `tests/python/integration/test_approval_token_audit_skill.py`.

### 3.3 Typed supervisor entrypoint for Claude (with defined dispatch semantics)

- File: `packages/tools/supervisor/claude_entrypoint.py` (new).
- API:
  ```python
  class SupervisorSession:
      def __init__(self, session_id: str, actor: str = "claude"): ...
      def open(self) -> SessionHandle: ...
      def create_strategic_task(self, *, task_type, title, lane, constraints, testing_policy) -> Task: ...
      def enqueue_engineering(self, *, task_def) -> Task: ...   # returns immediately
      def enqueue_ios(self, *, task_def) -> Task: ...
      def enqueue_gtm(self, *, task_def) -> Task: ...
      def request_approval(self, *, subject_type, subject_id, action, summary) -> ApprovalRecord: ...
      def append_event(self, *, event_type, payload) -> Event: ...
      def read_result(self, *, task_id) -> Optional[TaskResult]: ...  # non-blocking
      def close(self, *, summary_md: str) -> None: ...  # validates strategic task outputs inline
  ```
- **Dispatch semantics**: fire-and-forget. Enqueue methods persist a task into the control plane and return immediately. The existing `worker-engineering`, `worker-ios`, and `worker-gtm` loops (running under the runtime-supervisor) claim and execute. Results are read back by `read_result()` on the next Claude session, or by the morning briefing (Phase 4.1). No blocking waits inside a Claude session — a 30-minute codex run cannot stall a conversation.
- **Strategic task validation** happens inside `close()`, not in a separate worker. The scope-guardian and coherence reviews both caught that "strategic worker that only validates" is a contradictory role. Collapsing it into `SupervisorSession.close()` removes an unnecessary daemon.
- Test: `tests/python/integration/test_claude_entrypoint.py` runs open → enqueue → close → (separately) read_result cycle.

---

## Phase 4 — Daily operator rhythm and observability (days 9-10)

ROI: converts all the Phase 1-3 plumbing into a founder-visible flow.

### 4.1 Morning briefing via scheduled Claude session

- Scheduled task (via Cowork scheduled-tasks MCP): every weekday at 07:30 local time, spawn a Claude session called `morning-briefing`.
- That session:
  1. Reads the control plane (`TaskStore`, `EventStore`, `ApprovalStore`, `ReleaseStore`) directly.
  2. Reads the runtime-supervisor status file.
  3. Runs the product artifact chain validator (Phase 5.1) and the GTM artifact chain validator (Phase 2.3).
  4. Runs the observability rollup (Phase 4.3).
  5. Checks preflight status for codex, xcode, postiz, gemini.
  6. Writes `state/artifacts/briefings/<date>-morning.md` and creates (not sends) a Gmail draft with the same content.
- Acceptance: on a normal day the briefing file appears by 07:31 and the Gmail draft is visible in Kashane's drafts folder. The briefing explicitly highlights any blocked lanes, pending approvals, and GTM posts scheduled for the day.

### 4.2 Evening close and weekly digest

- 19:00 daily: evening session writes `state/artifacts/briefings/<date>-evening.md`, updates any touched product `HANDOFF.md`, and closes the supervisor session with a summary.
- Friday 17:00: weekly digest aggregating the week's tasks-by-status, approvals-by-state, GTM engagement snapshot, and blockers carried into next week.

### 4.3 Observability rollup

- File: `packages/tools/observability/rollup.py` (new).
- Inputs: `state/logs/<lane>/*.log` and the event store.
- Outputs: counts of dispatched / completed / failed per lane, top failure codes, tail excerpts of the last N errors, preflight status for each lane.
- **Redaction**: strips common credential patterns (`sk-...`, `ghp_...`, JWT-shaped strings, AWS `AKIA...`, bearer tokens) before emitting any summary. Redaction spec is centralized in `packages/tools/observability/redaction.py` with unit tests.
- Test: `tests/python/unit/test_observability_rollup.py` seeds a log dir with planted credentials and asserts they never appear in output.

### 4.4 Approval sweep

Addressed fully in Phase 3.1.

### 4.5 post-run-validation skill (new)

- Canonical: `skills/canonical/post-run-validation/`.
- Purpose: after any worker reports a task result, run a contract check against the task's declared outputs. Checks include: declared files exist and parse, referenced IDs resolve, tests marked required ran and passed, no banned paths were touched, `failure_code` is set when status is `failed`, and for GTM tasks the post-chain artifacts (voice-guardrail + social-post-safety outputs) are attached to the result.
- Called from: `ControlPlaneService.submit_task_result` as a final gate. On skill failure, the task result is persisted as `status=rejected` with the validation report attached; the worker loop re-raises so the task can be retried or surfaced in the briefing.
- Scope: applies to every lane (engineering, iOS, appstore, GTM), with lane-specific contract files under `skills/canonical/post-run-validation/contracts/<lane>.yaml`.
- Fixtures at creation per Phase 0.5.
- Test: `tests/python/integration/test_post_run_validation_skill.py` covers each lane's contract path.

### 4.6 failure-mode-regression skill (new)

- Canonical: `skills/canonical/failure-mode-regression/`.
- Purpose: when any failure-modes-table entry fires in production (detected by `failure_code` appearing in the event store), auto-capture the trace — task packet, worker log excerpt, control-plane snapshot — into `tests/regression/<failure_code>/<timestamp>/` and file a `FAILURE_REGRESSION_FIXTURE` strategic task. This operationalizes the currently static failure-modes tables: any fired failure becomes a permanent test fixture.
- Called from: the observability rollup (Phase 4.3) on its event-store sweep. It runs in the morning and evening briefing sessions.
- Privacy: the capture pipeline runs through the same redaction pass as the observability rollup (Phase 4.3). The redaction test suite must be extended to cover any new fields the capture writes.
- Bounded output: the skill writes at most one capture per `failure_code` per 24 hours, to avoid cascade events spamming the regression dir.
- **Meta failure code**: if the capture pipeline itself errors, it emits `failure_code=capture_pipeline_self_failure` to the event store via a minimal out-of-band path that does not recursively call the skill. The observability rollup surfaces this code at the top of the briefing so silent capture failures become visible within one day.
- Test: `tests/python/integration/test_failure_mode_regression.py` seeds a planted failure event and asserts the capture lands with credentials redacted and the dedupe window is honored. A second test injects a write error and asserts `capture_pipeline_self_failure` is emitted exactly once.

---

## Phase 5 — Strategic task support and product registry (days 11-12)

ROI: incremental, not must-have. Can be deferred if the April launch is tight.

### 5.1 Product artifact chain validator

- File: `packages/tools/product_artifacts/validator.py` (new) and `packages/tools/product_artifacts/chain.yaml` (new — the link graph).
- Checks per registered product: required files exist, forward links are consistent, positioning / metadata / MVP spec use the same app name / tagline / primary promise, submission-checklist items map to known IDs.
- Consumers: runtime-supervisor `build_work_summary`, `SupervisorSession.close()`, CI.
- Test: `tests/python/unit/test_product_artifact_chain_validator.py` against both catchbook and after-plans.

### 5.2 Strategic task types (enum additions only, no new worker)

- Add to `packages/schemas/task_packet.py`: `PRODUCT_BRIEF_UPDATE`, `MVP_SPEC_UPDATE`, `APPSTORE_POSITIONING_REFRESH`, `APPSTORE_METADATA_DRAFT`, `SCREENSHOT_PLAN_REFRESH`, `ARTIFACT_CHAIN_REVIEW`, `FOUNDER_BRIEF_INTAKE`, `GTM_CAMPAIGN_BRIEF` (shared with Phase 2.1).
- No new worker. Validation happens in `SupervisorSession.close()`.
- Testing policy: strategic tasks set `tests_required=False` with reason code `strategic_artifact_non_logic`. The artifact-chain validator runs instead.
- Test: `tests/python/unit/test_strategic_task_types.py` exercises enum additions and validator integration.

### 5.3 Product registry — static only, derived view separate

- `infra/products.json` stays static: `id`, `slug`, `platform`, `repo_id`, `source_path`, `docs_root`, `phase` (new, enum-constrained: `discovery` / `mvp-build` / `app-store-submission` / `live` / `maintenance`). `phase` is the only runtime-ish field allowed because it changes rarely and is a human decision.
- Derived view: `state/checkpoints/platform/products/<id>.projection.json`, written by runtime-supervisor `build_work_summary` on each pass. Contains `current_release_id`, `active_approval_ids`, `open_task_counts_by_lane`, `last_claude_session_id`, `last_artifact_chain_status`. Never committed (already under `state/` which is gitignored).
- `packages/config/products.py::load_products()` reads the old shape and the new `phase` field additively.
- Test: `tests/python/unit/test_product_registry.py`.

### 5.4 Claude-output validator

- File: `packages/policies/claude_output.py` (new).
- Checks: strategic artifact outputs include required header, `last_updated` date, `source_session_id`, and link to parent artifact in the chain.
- Called from `SupervisorSession.close()` before the session is marked complete.

### 5.5 External skill intake policy (new)

Rationale: `anthropics/skills`, `EveryInc/compound-engineering-plugin`, and any future public skill pack are attractive borrowing targets. Without a written policy the repo drifts into a skill zoo — the exact failure mode we avoided by rejecting Langfuse/LangGraph speculation.

- File: `docs/skills/intake-policy.md` (new). Canonical checklist that must be completed and checked into the repo before any file is copied from an external source into `skills/canonical/`:
  1. Source repo actively maintained (last commit within 90 days).
  2. License permissive and compatible (MIT / Apache-2.0 / BSD).
  3. No embedded secrets, credentials, or account-specific IDs.
  4. No network calls that are not declared in the skill's manifest.
  5. Permissions narrow: only the MCPs the skill demonstrably needs.
  6. Human-written rationale explaining *why this skill, why now, and what it replaces or augments.*
  7. Phase 0.5 fixtures written locally — **upstream fixtures are not trusted.**
  8. Security review: Kashane has read the skill end-to-end before the PR that introduces it.
  9. Provenance tag `source=external:<repo>@<commit>` added to `skills/registry.yaml`.
  10. Quarterly review cadence with a named owner. External skills without a recorded review in 90 days are auto-demoted to `mode="manual"` by the loader.
- Enforcement: `infra/scripts/validate-skill-intake.sh` (new) checks the registry against the policy and runs as part of the Phase 0.5 pre-commit hook. **The script includes an actual secret scan** — it invokes `gitleaks detect --source skills/canonical/ --no-git` (or an equivalent regex pass if gitleaks is not installed, with a loud warning) against every file under `skills/canonical/` so "no embedded secrets" is a checked invariant rather than a text rule. Any hit blocks the commit.
- Acceptance: policy exists, validator runs, pre-existing external skills (currently zero) would be flagged until compliant.
- Deliberate non-adoption captured in the policy so the rationale is not re-litigated: **Langfuse** (violates lightweight/local-first; Phase 4.3 rollup already covers the need), **LangGraph** (not adopted until the task-packet model provably strains), **founder-pack-to-prd** (duplicates `product-artifact-chain` + `supervisor-goal-decomposition`), **GitHub Agent Skills portability work** (zero value until a second runtime exists).

---

## Phase 6 — Infra migration (deferred, days 13+)

Unchanged from original plan. Do not start until Phases 0-5 are stable in daily use for at least a week. `packages/db/postgres_backend.py` and `packages/queue/redis_backend.py` use the existing contract interfaces. Run the integration suite against both SQLite and Postgres via a fixture switch.

---

## Execution order, parallelism, ROI, and early-stop checkpoints

Sequential chain with ROI framing:

| Phase | Effort | ROI anchor | Early-stop state |
|---|---|---|---|
| 0 | 1-1.5 days (0.5 added for 0.5 skill gate) | De-risks every later phase. 0.0 handshake is the single most important gate; 0.5 prevents skill-zoo drift. | Round-trip works, interpreter aligned, git hygiene scoped, secrets helper in place, skill eval gate live. |
| 1 | 1-2 days | Unlocks headless engineering and iOS via existing workers, no new daemons. | Runtime-supervisor runs under launchd, preflights are green, existing workers claim enqueued tasks. |
| 2 | **3-4 days (was 2-3; +1 for GTM skill pack + threat model)**, highest near-term leverage | **Directly serves the April catchbook launch. If time is tight, stop here.** | GTM worker drafts content with voice-guardrail + social-post-safety gates, publishes only after approval, kill switch exists, MCP threat model committed. |
| 3 | 2-3 days | Closes the control-plane loop and the approval surface. | SupervisorSession exists, magic-link approvals work, release-readiness policy enforces submission gates. |
| 4 | 1-2 days | Makes all prior phases visible to Kashane through the morning briefing. | Daily briefing + evening close + observability rollup running. |
| 5 | 1-2 days | Incremental quality and strategic-task support. Defer if launch pressure. | Validators and registry v2 live. |
| 6 | multi-day | Concurrency and multi-machine. Not relevant until Phases 0-5 are stable. | — |

Early-stop checkpoints by verdict upgrade:

- **After Phase 0:** filesystem and interpreter assumptions verified. Verdict still partial.
- **After Phase 1:** Claude can enqueue engineering and iOS work to the running workers. Verdict moves from provisional to "yes, within the existing worker lanes."
- **After Phase 2:** GTM autonomy is live. **This is the early-stop point that best serves the April launch.** Verdict: yes for GTM and provisional orchestrator for engineering.
- **After Phase 3:** approval surface is real. Verdict: yes, with approval-gated production actions.
- **After Phase 4:** self-running daily rhythm. Verdict: yes, full lead orchestrator.
- **After Phase 5:** polish.
- **After Phase 6:** scale.

## Cross-cutting requirements

- Every new module ships with lane-matching tests under `tests/python/` or an explicit `no_test_reason_code`.
- Every new launchd plist has a disable command documented in `infra/launchd/README.md`.
- Every new state directory is documented in `state/README.md`. New entries introduced by this plan: `state/handshake/`, `state/checkpoints/platform/runtime-supervisor-status.json`, `state/checkpoints/platform/products/`, `state/checkpoints/platform/security-state.json`, `state/checkpoints/platform/security-log.jsonl`, `state/flags/gtm_frozen`, `state/artifacts/briefings/`, `state/artifacts/outreach/`, `state/logs/runtime-supervisor/`, `state/worktrees/claude/`.
- Every new schema or task type is referenced in `AGENTS.md` and `docs/architecture.md`.
- Every new daemon or subsystem ships with a failure-modes table under `docs/failure-modes/<subsystem>.md` using the `failure_code` pattern already in `packages/schemas/testing.py`.
- All new credential access goes through `packages/config/secrets.py` (Phase 0.4). No ad-hoc `os.environ.get(...)` for secrets in new code.
- Derived runtime state lives under `state/`, never in `infra/*.json`.
- No change to `.claude/skills/` except routing pointer additions. Skill logic stays in `skills/canonical/` with a `skills/adapters/claude/` translation, per `skills/WIRING.md`.
- One process supervisor only: `apps/runtime-supervisor/`. launchd runs *it*, not individual workers.
- Every canonical skill must have a `fixtures/` directory with happy-path, boundary, and adversarial cases, and a passing `fixture_status` in `skills/registry.yaml`, before any caller can load it in `mode="autonomous"` (Phase 0.5).
- No external skill enters `skills/canonical/` without the Phase 5.5 intake policy checklist completed.
- GTM lane is blocked until `docs/security/mcp-threat-model.md` exists and its checksum is recorded in `state/checkpoints/platform/security-state.json` (Phase 2.0).
- `scripts/gtm_freeze.sh` must no-op GTM task claims within one worker-loop tick when the flag file is present.
- `creator-outreach-draft` and every other draft-only skill must have an enforced non-send boundary (no MCP send capability wired, lint assertion, failure-mode entry for attempted auto-send).

## Definition of done for "Claude as lead orchestrator"

All of the following must hold:
1. Phase 0.0 filesystem round-trip handshake passes three consecutive sessions.
2. Runtime-supervisor is running under launchd, managing worker-engineering, worker-ios, worker-appstore, and worker-gtm.
3. Preflight for codex, xcode, postiz, and gemini are all green or explicitly reported as blocked with a named recovery action.
4. Claude can open a `SupervisorSession`, enqueue typed tasks to any lane, and close the session — with fire-and-forget dispatch semantics and result reads in the next session.
5. Every approval-required action is blocked until a magic-link-backed approval exists in `approved` state. P0 actions require second-factor confirmation.
6. The product artifact chain validator and GTM artifact chain validator both run in CI and in the morning briefing.
7. Morning briefing lands as a Gmail draft daily with no manual action.
8. `git worktree list` and `git status` are clean on both Mac and sandbox.
9. `pytest tests/python` is green on the chosen interpreter.
10. Observability rollup output contains zero credential fragments in the redaction test suite.
11. GTM worker drafts, schedules, and reports on content autonomously for catchbook; publishes only after approval.
12. `docs/security/mcp-threat-model.md` exists, its checksum is tracked, and `scripts/gtm_freeze.sh` provably halts GTM within one worker tick.
13. Every canonical skill in `skills/registry.yaml` has a passing `fixture_status`, and `packages/tools/skills/loader.py` refuses `mode="autonomous"` for any skill without one.
14. The GTM skill chain (`content-voice-guardrail` → `social-post-safety` → schedule) runs green end-to-end on a fake campaign, and `creator-outreach-draft` has no reachable send path.
15. `approval-token-audit` is wired into every P0 policy check; `post-run-validation` runs on every task result; `failure-mode-regression` captures at least one fired failure into `tests/regression/`.
16. `docs/skills/intake-policy.md` exists and `infra/scripts/validate-skill-intake.sh` runs clean.

When all sixteen hold, Claude is lead orchestrator for `ai-company-os`.

---

## Review log

This plan was reviewed against the compound-engineering document-review skill (https://github.com/EveryInc/compound-engineering-plugin). Seven personas were considered; six activated (design-lens skipped — no UX surface in this plan).

| Finding | Persona | Severity | Confidence | Status |
|---|---|---|---|---|
| Phase 1 reinvents existing workers instead of running `worker-engineering`/`worker-ios` under launchd | scope-guardian | P0 | 0.92 | **Addressed** — Phase 1 collapsed to "runtime-supervisor under launchd + preflights + enqueue path." Two bridge daemons removed. |
| Plan misses the actual founder bottleneck (GTM, not engineering) | product-lens | P0 | 0.88 | **Addressed** — Phase 2 is now GTM autonomy and is the top early-stop anchor for the April launch. |
| Filesystem round-trip between sandbox and Mac assumed, never tested | adversarial | P0 | 0.85 | **Addressed** — Phase 0.0 adds a handshake gate that blocks all dispatch work until proven. |
| codex CLI auth status on the Mac assumed, not verified | feasibility | P0 | 0.82 | **Addressed** — Phase 1.2 adds `preflight_codex.sh`; runtime-supervisor reports lane blocked if preflight fails. |
| Gmail approval path conflates MCP-only tools with Python daemons | adversarial + feasibility | P0 | 0.85 | **Addressed** — Phase 3.1 picks one model: a scheduled Claude session ingests approvals via Gmail MCP. No daemon. |
| Email-reply approval is spoofable and replayable | security | P0 | 0.80 | **Addressed** — Phase 3.1 replaces reply-parsing with magic-link HMAC tokens with TTL, single-use, second-factor for P0 actions. |
| Product registry v2 denormalizes derived data into source-controlled config | scope-guardian | P0 | 0.85 | **Addressed** — Phase 5.3 keeps `infra/products.json` static; derived view lives at `state/checkpoints/platform/products/<id>.projection.json`. |
| Auto-removing `index.lock` is dangerous | coherence | P1 | 0.85 | **Addressed** — Phase 0.2 removes the auto-remove; script logs and exits non-zero instead. |
| `SupervisorSession` dispatch wait semantics undefined | feasibility | P1 | 0.78 | **Addressed** — Phase 3.3 makes dispatch fire-and-forget, defines `read_result()` and `close()`. |
| Two orchestration loops in parallel (runtime-supervisor + launchd daemons) | adversarial | P1 | 0.78 | **Addressed** — Phase 1.1 commits to one supervisor. launchd runs only the runtime-supervisor. |
| Happy-path only; failure modes unnamed | adversarial | P1 | 0.75 | **Addressed** — Phase 1.4 requires a failure-modes table per lane using the existing `failure_code` pattern; cross-cutting requirement added. |
| New daemons have no secrets-path convention | security | P1 | 0.78 | **Addressed** — Phase 0.4 adds `packages/config/secrets.py` with keychain support for high-stakes credentials. |
| Strategic worker contradicts its own purpose | coherence | P1 | 0.80 | **Addressed** — Strategic worker deleted; validation moved into `SupervisorSession.close()` (Phases 3.3 and 5.2). |
| launchd implementation detail left to implementer | feasibility | P1 | 0.70 | **Addressed** — Phase 1.1 specifies UserAgent (not LaunchDaemon), `launchctl bootstrap gui/<uid>`, `RunAtLoad`, `KeepAlive`. |
| Event emission inconsistent between original §1.1 and §1.2 | coherence | P2 | 0.70 | **Addressed** — moot after Phase 1 collapse; existing workers already emit control-plane events consistently. |
| Python floor relaxation was an investigation, not a guarantee | coherence/feasibility | P2 | 0.70 | **Addressed** — Phase 0.1 prefers bumping the sandbox interpreter; fallback is explicit. |
| No log redaction strategy | security | P2 | 0.65 | **Addressed** — Phase 4.3 mandates redaction in the observability rollup with a test suite. |
| Plan size vs. near-term ROI not estimated | product-lens | P2 | 0.65 | **Addressed** — per-phase ROI table and early-stop checkpoints added above. |
| `is_approval_granted` helper assumed to exist in `packages/policies/approvals.py` | feasibility | P2 | 0.65 | **Addressed** — Phase 3.2 names the helper explicitly. |
| Strategic task types may be unnecessary | scope-guardian | P2 | 0.70 | **Addressed** — Phase 5.2 demotes them to nice-to-have enum additions, no new worker. |
| Product registry schema migration undefined | feasibility | P2 | 0.65 | **Addressed** — Phase 5.3 specifies additive read in `load_products()`. |
| Design-lens reviewer (no UX surface) | design-lens | — | — | Skipped per skill protocol. |
| **Second review pass — findings on the skill-system additions (2026-04-10)** | — | — | — | — |
| Bootstrap paradox: Phase 0.5 blocks autonomous mode for skills without fixtures, but new skills in Phases 2-4 would need autonomous mode before their fixtures exist | coherence + feasibility | P0 | 0.90 | **Addressed** — Phase 0.5 now requires fixtures to ship in the same PR as the skill. No "to be evaluated later" state. |
| Skill invocation from synchronous Python hot paths (post-run-validation from `submit_task_result`, approval-token-audit from `release_readiness.py`) conflates LLM-backed and pure-validator skills | feasibility + scope-guardian | P0 | 0.88 | **Addressed** — Phase 0.5 introduces `kind: validator` vs `kind: agentic` distinction in `skills/registry.yaml`; loader refuses agentic skills from synchronous contexts and vice versa. All hot-path skills mapped to `validator`. |
| approval-token-audit could fail open if the skill invocation errors | security | P0 | 0.85 | **Addressed** — Phase 3.2a now specifies fail-closed semantics: validator exception → `PolicyViolation("approval_audit_unavailable")`, with an explicit test. |
| MCP threat-model re-acknowledgment path undefined | feasibility | P1 | 0.75 | **Addressed** — Phase 2.0 adds `scripts/acknowledge_threat_model.sh --read` with append-only audit log at `state/checkpoints/platform/security-log.jsonl`. |
| promptfoo runtime location and cost unbounded | feasibility | P1 | 0.75 | **Addressed** — Phase 0.5 specifies Mac-side execution, Node 20+ requirement, `--max-calls` budget cap (9 per edit, 200 nightly), on-change + nightly cron frequency. |
| Phase 2.0 threat-model effort could blow Phase 2 | product-lens | P1 | 0.72 | **Addressed** — 2-3 hour time box, 1-2 page target, descope path named. |
| Intake policy "no embedded secrets" is a text rule with no detection | security | P1 | 0.78 | **Addressed** — Phase 5.5 now requires `gitleaks detect --source skills/canonical/` inside `validate-skill-intake.sh`. |
| GTM freeze flag doesn't handle in-flight tasks cleanly | adversarial | P2 | 0.70 | **Addressed** — Phase 2.0 specifies (a) no-op at claim, (b) `GtmFrozenError` mid-task catches and re-queues as `paused:frozen`, (c) clean resume via `gtm_unfreeze.sh`. |
| failure-mode-regression can silently fail its own capture pipeline | adversarial | P2 | 0.70 | **Addressed** — Phase 4.6 adds `capture_pipeline_self_failure` meta failure code emitted out-of-band, surfaced in briefing rollup. |
| New `state/` paths (security-state, security-log, flags, etc.) not documented in `state/README.md` | coherence | P2 | 0.65 | **Addressed** — cross-cutting requirements section now enumerates every new state path. |
| `creator-outreach-draft` lint is brittle as secondary control | adversarial | P2 | 0.60 | **Addressed** — primary control is "no MCP send wired"; CI grep assertion is already in acceptance criteria. Lint is explicitly labeled belt-and-suspenders. |
| Skill zoo — 7 new canonical skills introduced at once | scope-guardian | P2 | 0.65 | **Acknowledged not addressed** — the count is real, but each skill is narrow, replaces inline logic, and is gated by Phase 0.5 fixtures. Phase 2 effort budget bumped to 3-4 days to reflect. Revisit if the delta exceeds estimate. |

Where a finding depended on a specific earlier finding's fix (for example, the event-emission inconsistency becoming moot after the Phase 1 collapse), the dependency is noted inline. Every P0 and P1 finding has a direct line-of-sight fix in the hardened plan above.
