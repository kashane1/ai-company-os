---
title: Hermes-Inspired Platform Upgrade — Autonomous Dispatch, Skill Self-Evolution, ACP Interop
type: feat
status: active
date: 2026-04-14
---

# Hermes-Inspired Platform Upgrade

## Enhancement Summary

**Deepened on:** 2026-04-14
**Agents run:** kieran-python-reviewer, architecture-strategist, code-simplicity-reviewer, agent-native-reviewer, security-sentinel, performance-oracle, pattern-recognition-specialist, data-integrity-guardian, deployment-verification-agent, framework-docs-researcher, best-practices-researcher, Explore (real-world self-evolving systems), general-purpose (agent-native-architecture skill application).

### Factual corrections the deepening surfaced

- **ACP has a production Python SDK** (`pip install agent-client-protocol`, org `agentclientprotocol`, Zed-affiliated — *not* the zed-industries org). **Hermes v0.7.0 already ships an ACP server** at `acp_adapter/server.py` (`HermesACPAgent` subclasses `acp.Agent`). Phase 4 is therefore writing an **ACP client**, not a wire-format renderer. Drop the hand-rolled `render_skill_as_acp` concept; import from `acp` and use `spawn_agent_process()` + `conn.initialize()` + `conn.new_session()` + `conn.prompt([text_block(...)])`. There is no `skill/invoke` method — ACP uses session-based `prompt` with `ContentBlock[]`. [agentclientprotocol.com](https://agentclientprotocol.com/) · [python-sdk](https://github.com/agentclientprotocol/python-sdk)
- **Hermes version pin: use the tag `v2026.4.3` (not the ambiguous commit `abf1e98`)** or upgrade to `v2026.4.13` (v0.9.0) which includes the `AuthMethod → AuthMethodAgent` rename that matches `agent-client-protocol ≥ 0.9.0`. Pin both package versions together.
- **`~/.hermes/cli-config.yaml` is the exact location** of `skills.external_dirs`. Semantics: paths expanded and resolved to absolute; external dirs are read-only (skill creation always writes to `~/.hermes/skills/`); local skills take precedence on collision; discovery keys on **directory name**, not frontmatter `id`. **Flat-layout files under `canonical/shared/*.md` will almost certainly NOT be discovered by Hermes** — the Phase 2 spike must explicitly test both layouts.
- **Real-world self-evolving skill systems** (Hermes `skill_manager_tool.py::_create_skill`, ByteDance deer-flow RFC #1865, Cursor Bugbot) all converge on: atomic write via `tempfile.replace()`, LLM-based moderation (not regex) for skill content, per-skill append-only `HISTORY.jsonl`, evidence-based rule activation (Bugbot), and never ship unsupervised skill modification. Hermes's `skills_guard.py` ships 168+ threat patterns. **None of them have the partial-refactor + PR-approval gate this plan specs — that's the differentiator.**

### Key improvements (ranked by impact)

1. **SQLite WAL + `busy_timeout=30000` + `synchronous=NORMAL` bootstrap is missing from the plan and is the single biggest scaling risk.** Add as a Phase 0 deliverable — `packages/db/connection.py` helper that every store calls. Python's `sqlite3` default `busy_timeout=0` will produce `SQLITE_BUSY` flakes under Phase 3 concurrent writers.
2. **Registry parsing is currently re-done on every `load_validator`/`load_agentic` call** (~2–5 ms YAML parse per call). Phase 5's command-scan hot path will pay this cost on every shell invocation. Add `functools.lru_cache` keyed on `(path, mtime_ns)` to `load_registry()` in Phase 0. This is the largest per-call perf win available.
3. **ACP peer lifecycle must be spawn-once-keep-alive, not per-dispatch spawn.** Hermes cold start from `uv run` is 1.5–4 s. Plan was ambiguous; make it explicit. Per-peer `asyncio.Lock` serializes stdio framing; idle-reap after 30 min.
4. **Command-scan must use a real shell parser (`bashlex`), not regex.** Regex-based denylists for `rm -rf`, `curl | bash`, `$(...)`, `eval`, IFS tricks will be bypassed within days. Also: scan the **(argv, env) tuple at the `subprocess.run` site**, not just the top-level command string — env-variable injection via `PATH`, `LD_PRELOAD`, `GIT_SSH_COMMAND`, `PAGER` is the real gap.
5. **Phase 3 `skill_evolution_lock_store` must use `ControlPlaneDatabase`, not a sidecar SQLite file** — `control_plane_db.py` already supports Postgres via `DATABASE_URL`, and a sidecar silently breaks the moment the operator flips backends. Also: pure-TTL locks are unsafe for stuck-but-alive holders; add a `heartbeat_at` column the holder extends, plus a `holder_token` (uuid4) that `release()` verifies.
6. **`SELF_EVOLUTION_DENYLIST` should flip to an allowlist model.** Require `self_evolvable: true` on the canonical skill frontmatter; default false. Denylist maintenance is a known anti-pattern; allowlist is forget-proof.
7. **Voyager/DSPy regression-fixture gate is missing from Phase 3.** Every proposed skill replacement must be required to **beat the incumbent on the incumbent's fixture set**. Without this, the loop can propose worse skills that pass their own freshly-generated fixtures. Add to `packages/policies/skill_evolution.py`: reject PRs where the new skill fails on the incumbent's fixture set. [Voyager](https://voyager.minedojo.org/) · [DSPy assertions](https://dspy.ai/learn/programming/assertions/)
8. **`runtime-supervisor/main.py` is trending toward god-object** — Phases 3, 4, 6 all touch it. Refactor **as Phase 0 prelude** into three files: `supervisor.py` (poll loop), `worker_specs.py` (default worker specs, Phase 3 touches only this), `dispatch_router.py` (target_runtime → provider resolution, Phases 4+6 touch only this).
9. **Every UI action exposed by the plan lacks a matching agent-callable primitive.** `scripts/dispatch-health.py` should be `packages/tools/primitives/dispatch_health_reader.py` with typed `summarize(since, lane) -> DispatchHealthSummary`. `state/flags/*` kill switches need `packages/tools/primitives/kill_switches.py:get_switch(name)` (read-only from agents, file-only from humans). `packages/config/peer_runtimes.yaml` needs `list_peer_runtimes()` / `get_peer_health(peer_id)` / `dispatch_to_peer(task_id, peer_id)` agent tools in `packages/tools/primitives/peer_runtimes.py`. Approval verdict `require_approval` in command-scan needs `request_command_approval(command, context, rationale) -> ApprovalToken` in `packages/tools/primitives/approvals.py` to be a productive third verdict rather than dead code. **All of these live under `packages/tools/primitives/` per the X4a subpackage convention, not flat under `packages/tools/`.**
10. **Python idiom corrections (Phase 0 pre-req):** `PolicyViolationCode(str, Enum)` instead of string literals at raise sites; `Provider` is `typing.Protocol` not ABC; `PeerTransport(str, Enum)` not inline `Literal` union; `target_runtimes.py` is a stdlib-only leaf module; `ProviderRegistry` is module-level functions (not a class), built once at import.

### Simplifications accepted from the simplicity reviewer

- **Delete `packages/tools/providers/placeholders.py` and `list_available()` placeholder rows.** Pure cargo cult; no automated consumer. Add providers when they have implementations.
- **Delete `PeerRuntime.transport: "stdio" | "unix_socket"` union.** Only stdio has a caller. Add `unix_socket` when a second peer exists.
- **Merge Phase 1 reconciliation CI into the existing unit test run**, drop the dedicated `.github/workflows/skill-reconciliation.yml` file.
- **Do not write runbooks before the first real incident.** Delete `docs/runbooks/dispatch-health-triage.md` from Phase 0 deliverables; write it when the first triage happens.

### Simplifications explicitly rejected (and why)

- **"Defer Phase 3 (self-evolution) entirely"** — rejected. The whole point of this plan is to close the autonomous loop. Deferring Phase 3 leaves the platform at Phase 2 indefinitely. The risks are real but are exactly what the hardening layers address.
- **"Defer Phase 6 (provider overlay) entirely"** — rejected. Phase 4 commits to `target_runtimes: [claude, codex, acp]` which already implies overlay semantics; not landing Phase 6 means `runtime-supervisor` grows a third hardcoded branch. The overlay is not speculation once Phase 4 lands.
- **"Delete `TaskPacket.provider_hint`"** — rejected. Agent-native review says it's the only path to data-driven dispatch routing; without it, agents cannot compose "route these three tasks to Hermes" from existing primitives. Keep it, expose it via an agent-callable `dispatch_to_peer` primitive.
- **"Delete `state/flags/` kill switches"** — rejected. Security review relies on them as a one-file rollback primitive; the redundancy with the runtime-supervisor worker disable is a feature, not a bug. Mitigation: add an agent-readable tool for `get_switch()` per agent-native review.

### New considerations discovered

- **Proposal input provenance (Phase 3 security).** Inputs from `state/checkpoints/` and `state/logs/` are writable by earlier-phase workers. A poisoned log line could steer the evolution worker. Require hash-pinned, signed-by-emitting-worker input snapshots.
- **`content-voice-guardrail` is passing without a validator.** This is a latent trust exploit today. Phase 1's `1.3a` triage step must be a HARD gate on Phases 2–5 starting, not just a checklist item inside Phase 1.
- **Self-evolved skills must be locked to `target_runtimes: [claude]` on first landing.** Adding `codex` or `acp` requires a separate human-authored PR. Without this, an evolved skill can target a peer runtime on its first run — untrusted code on Hermes before any human validated the contract for that specific skill.
- **`gh pr create` pushes with ambient token.** Plan relies on GitHub-side controls ("never auto-merges"). Harden: hardcode `--base staging`, assert branch prefix `skill-evolution/`, fine-grained PAT scoped to one repo, `--draft` default, signed commits via machine GPG key, branch protection forbidding force-push to `main`.
- **`state/runtime/acp-peers/` does NOT exist in the current `state/` layout.** Use `state/handshake/acp-peers/` instead (semantically appropriate — `handshake/` is literally for peer handshake state). Or explicitly declare `state/runtime/` as a new convention and update `state/README.md`.
- **State directory hygiene:** `state/quarantine/`, `state/archives/`, `state/health/` are all introduced implicitly by the plan but don't exist. Acknowledge each creation explicitly in Phase 0 and update `state/README.md` atomically.
- **macOS 14+ launchd Background Items approval** triggers the first time each `.plist` loads. Document in the runbook so the operator isn't surprised.
- **macOS `sandbox-exec` is deprecated but remains the only practical primitive** for sandboxing the Hermes peer. Pick a supported fallback (dedicated launchd user) and document before Phase 4 lands. Without this, any Hermes RCE is a full-platform compromise.

### Cross-reference to deepening agent outputs

Each phase below has a "Research Insights" block carrying the concrete findings. Where a finding spans multiple phases it lives in the new [Cross-Cutting Enhancements](#cross-cutting-enhancements) section.

## Overview

`ai-company-os` has a mature canonical-skill system, a typed task queue, and a bank of specialized workers, but it cannot actually dispatch skills autonomously today. The loader's `fixture_status` gate is closed on every `project_skill` entry, the registry crashes on load because of an unvalidated literal, and the skill loader hard-codes the Claude adapter path so there's no clean way to add peer runtimes. Meanwhile, NousResearch Hermes Agent v0.7.0 has emerged in the last 30 days as a well-validated local-first agent runtime with a mountable external-skills directory, a pluggable provider overlay, a pre-execution command scanner (`tirith`), and an agent-managed skill self-evolution pattern that Bytedance is now trying to copy into deer-flow.

This plan closes the autonomous-dispatch gate, validates Hermes as a peer runtime via a zero-code spike, introduces a skill self-evolution loop as a first-class worker lane with approval gating, and adds the protocol + policy primitives (ACP adapter, command-scan policy, provider overlay) that are now table stakes for any serious local-first agent platform. It is intentionally sequenced so each phase unblocks the next, with a hard gate at Phase 0 for the pre-existing load-crash and a hard gate at Phase 1 for autonomous mode.

**Outcome when shipped:** (1) every `project_skill` entry can dispatch autonomously through `runtime-supervisor`, (2) Hermes runs alongside the platform and can invoke a subset of our canonical skills directly, (3) the platform proposes its own new skills from observed task outcomes through a gated PR loop, (4) any shell command run by a worker goes through a policy-wrapped scanner before execution, and (5) adding Ollama / Qwen / another model provider is a registry entry, not a fork.

## Cross-Cutting Enhancements

These are findings from the deepening pass that don't belong to any single phase. They land as part of Phase 0 (the atomic preconditions PR) or extend the cross-cutting observability stream.

### X1 — Python idioms (Phase 0 deliverable, MUST land before anything else)

- **`PolicyViolationCode(str, Enum)` in `packages/policies/approvals.py`.** Replaces string literals at raise sites. Every new code from Phases 3/4/5/6 lands as an enum member. Members introduced by this plan (complete list — pattern review asked for byte-consistency):
  - Phase 3: `FIXTURE_SKILL_DRIFT`, `REGRESSION_AGAINST_INCUMBENT`, `CONFIG_MUTATION_REQUIRES_HUMAN`, `RUNTIME_EXPANSION_REQUIRES_HUMAN`, `SKILL_NOT_SELF_EVOLVABLE`, `CONCURRENT_EVOLUTION_IN_PROGRESS`, `THIRD_FILE_SMUGGLING`
  - Phase 4: `ACP_PEER_NOT_ALLOWED`, `ACP_PEER_CRASH`, `ACP_PROTOCOL_ERROR`, `ACP_MAX_ATTEMPTS_EXCEEDED`
  - Phase 5: `COMMAND_SCAN_DENIED`, `COMMAND_SCAN_UNAVAILABLE`, `COMMAND_SCAN_REQUIRES_APPROVAL`
  - Phase 6: `PROVIDER_UNAVAILABLE`, `PROVIDER_NOT_REGISTERED`
  - Cross-cutting: `DISPATCH_HEALTH_PAYLOAD_OVERSIZED` (for the 512-byte cap)
  
  Preserves back-compat via `code: PolicyViolationCode | str` in the constructor. Matches the existing `WorkerLane(str, Enum)` precedent at `packages/schemas/task_packet.py:7-13`. Unit test `test_policy_violation_codes_enumerated` asserts every `raise PolicyViolation(...)` call site in `packages/policies/` uses an enum member, not a bare string (grep + AST walk).
- **`Provider` is `typing.Protocol`, not ABC.** `packages/tools/providers/base.py` uses structural typing; no base class inheritance required. `ProviderCapabilities` and `ProviderHealth` are `@dataclass(frozen=True)`. Avoids the circular import risk in `providers/acp.py`.
- **`PeerTransport(str, Enum)` in `packages/schemas/peer_runtime.py`**, not `transport: "stdio" | "unix_socket"` inline literal. Matches `TaskStatus`, `RiskLevel`, `WorkerLane` idiom. `unix_socket` member dropped until a second peer exists.
- **`ProviderRegistry` is module-level functions, not a class.** `packages/tools/providers/__init__.py` exports `resolve(slug) -> Provider`, `list_available() -> list[str]`. Private `_REGISTRY: dict[str, Provider]` built once at import via `_register_defaults()`. Drop `register()` method — YAGNI until there's a plugin loader.
- **`target_runtimes.py` is a leaf module.** Stdlib-only imports (`typing.Literal`, `typing.Final`). `loader.py` imports *from* it, not the reverse. Unit test `tests/python/unit/test_target_runtimes_import_safety.py` asserts `importlib.import_module("packages.tools.skills.target_runtimes")` has no side effects and its transitive closure is stdlib-only. Closes the Phase 5 / Phase 0 import-safety contradiction.

### X2 — SQLite bootstrap helper (Phase 0 deliverable, MUST land)

**New file:** `packages/db/connection.py`

```python
# packages/db/connection.py
import sqlite3
from pathlib import Path

def open_platform_db(path: Path, *, read_only: bool = False) -> sqlite3.Connection:
    """Canonical connection bootstrap for every platform store.
    
    Every caller in packages/db/ and packages/queue/ opens connections
    through this helper so WAL / busy_timeout / synchronous settings are
    guaranteed consistent across the platform. Callers manage their own
    transactions via `with conn:` — this helper does NOT force autocommit.
    
    THREAD SAFETY: This helper passes `check_same_thread=False` so
    background flush threads (dispatch_health, launchd cron scripts) can
    share the returned connection with the main thread. BUT sqlite3's
    statement cache and per-connection transaction state are NOT
    thread-safe even with check_same_thread disabled. Callers MUST either
    (a) hold an external threading.Lock around every `with conn:` block
    that issues multiple statements, or (b) use one connection per thread
    (preferred — thread-local storage, or a contextvar-scoped pool). Do
    NOT share a single connection across threads without a lock.
    """
    uri = f"file:{path}?mode=ro" if read_only else str(path)
    conn = sqlite3.connect(
        uri,
        timeout=30.0,
        check_same_thread=False,          # allow background flush thread access
        uri=read_only,
    )
    # DO NOT set isolation_level=None — that breaks existing `with conn:` callers
    # in approval_store.py, release_store.py, task_queue.py which rely on
    # implicit transactions. Callers that need explicit write locks issue
    # `conn.execute("BEGIN IMMEDIATE")` themselves.
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA busy_timeout=30000")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA temp_store=MEMORY")       # free win, no durability cost
    conn.execute("PRAGMA mmap_size=268435456")     # 256 MiB mmap, free read perf
    return conn
```

**Critical Python correctness note** (from technical review): the earlier draft of this helper set `isolation_level=None` which puts `sqlite3` in autocommit mode and silently breaks every existing caller that uses `with conn:` context-manager transactions (`approval_store.py`, `release_store.py`, `task_queue.py`). The corrected helper leaves `isolation_level` at its default so those callers keep working. The `skill_evolution_locks` store (Phase 3) issues its own `BEGIN IMMEDIATE` where needed.

**Migration:** `packages/db/control_plane_db.py`, `packages/db/approval_store.py`, `packages/db/release_store.py`, `packages/db/approval_token_store.py`, `packages/queue/task_queue.py` — every `sqlite3.connect(...)` call routed through this helper. Integration test `tests/python/integration/test_concurrent_writers.py` spawns N=8 concurrent writers doing 100 cycles each and asserts zero `SQLITE_BUSY` + p99 < 20 ms. Startup assertion in `control_plane_db.__init__` that `PRAGMA journal_mode` returns `'wal'`. **Additionally:** test that `with conn: conn.execute("INSERT ...")` still commits (guards against regression of the autocommit bug).

Without this, Phase 3's concurrent evolution proposals + Phase 1 autonomous dispatch + existing release-readiness writes produce writer starvation under contention. Python's `sqlite3` default `busy_timeout=0` means immediate `SQLITE_BUSY` errors — it's invisible at 20 tasks/week and catastrophic under Phase 3 real load.

### X3 — Registry caching (Phase 0 deliverable, MUST land)

**File:** `packages/tools/skills/loader.py`

```python
import os
from pathlib import Path

@functools.lru_cache(maxsize=None)
def _load_registry_cached(
    path_key: str, mtime_ns: int, inode: int, size: int
) -> tuple[SkillSpec, ...]:
    """Parse registry keyed on (resolved-path, mtime_ns, inode, size).
    
    Returns an immutable tuple so callers cannot corrupt the cache via
    in-place mutation. Atomic `os.replace()` writes (from X9 registry_writer)
    change inode, invalidating the cache correctly.
    """
    ...

def load_registry(path: Path | None = None) -> tuple[SkillSpec, ...]:
    p = (path or _default_registry_path()).resolve()
    # os.fspath(p) normalizes the key so relative vs absolute paths to the
    # same file collide in the cache rather than thrashing it.
    st = p.stat()
    return _load_registry_cached(
        os.fspath(p), st.st_mtime_ns, st.st_ino, st.st_size
    )
```

**Critical Python correctness notes** (from technical review):
- **Return type is `tuple`, not `list`.** `lru_cache` hands back the same object on every hit; a `list` return shares a mutable reference across all callers, so any `.sort()` or `.append()` by one caller corrupts every subsequent reader. Tuples are safe.
- **`maxsize=None`, not `maxsize=1`.** Tests and multi-registry callers pass different paths and would thrash a size-1 cache. The memoization key is `(path, mtime_ns, inode, size)`, so the cache grows with distinct registries — bounded by the number of actual registry files, which is 1 in production and ≤5 in tests.
- **Cache key includes `st_ino` and `st_size`** as belt-and-braces. `st_mtime_ns` alone is reliable on APFS/ext4 (atomic `os.replace()` produces a new inode whose mtime is the write time, so mtime correctly changes). But `st_ino` catches the pathological path of a fast consecutive write with stale mtime, and `st_size` catches a rare truncation-without-mtime-bump. Three-field key is near-zero cost and removes entire classes of TOCTOU.

**Why:** today `_find()` calls `load_registry()` on every `load_validator`/`load_agentic` invocation, which re-reads + re-parses `registry.yaml` (~2–5 ms per call, 287 lines of YAML). Phase 5's command-scan validator lookup happens on every shell command; without caching, every `git`/`uv`/`pytest`/`gh` call in `codex_tools/cli.py` eats 2–5 ms of pure redundant I/O. At ~30 shell calls per task × 20 tasks/week = 600 scans/week × 3 ms = 1.8 s/week of noise. Modest alone; combined with the lazy-loaded validator import (15–40 ms cold) it's a tail-latency footgun. `lru_cache` is a ~10-line change with substantial downstream leverage.

### X4 — runtime-supervisor refactor (Phase 0 prelude, MUST land)

**Split `apps/runtime-supervisor/main.py` into three implementation files, keep `main.py` as a two-line entrypoint shim:**

- `apps/runtime-supervisor/main.py` — **two-line shim** retained for launchd plist compatibility:
  ```python
  from .supervisor import main
  if __name__ == "__main__": main()
  ```
  This is a deployment-hardening concession (delta review D3): the launchd plist and any downstream tooling reference `main.py` directly, and replacing it would require a coordinated plist + shim update. Keeping `main.py` as a shim means the three-file split is a pure internal refactor with zero coordination cost and a one-file revert.
- `apps/runtime-supervisor/supervisor.py` — the poll loop, launchd entrypoint logic, signal handlers. `main()` lives here.
- `apps/runtime-supervisor/worker_specs.py` — `default_worker_specs()`. **Phase 3 touches only this file** when adding `worker-skill-evolution` (plus `worker-supervisor` and `worker-gtm` which are already missing from the current list).
- `apps/runtime-supervisor/dispatch_router.py` — thin call-site (**hard LOC budget: ≤ 50 LOC**) that resolves the target runtime and invokes `providers.resolve(slug).execute(task)`. **Does NOT contain routing policy** — that lives in `packages/policies/provider_resolution.py`. The feature-flag check for `acp_dispatch_enabled` lives in the policy, not the router. **Phases 4 and 6 touch `dispatch_router.py` for call-site wiring only; the bulk of each phase's code lands in `packages/tools/acp/`, `packages/tools/providers/`, and `packages/policies/provider_resolution.py`.**

This prevents the supervisor from becoming a god-object that three phases concurrently edit. It also makes review boundaries obvious: a Phase 3 PR that touches `dispatch_router.py` is a red flag, and any PR that grows `dispatch_router.py` past 50 LOC must explain why.

**LOC budget enforcement:** `tests/python/unit/test_dispatch_router_loc_budget.py` asserts `len(Path("apps/runtime-supervisor/dispatch_router.py").read_text().splitlines()) <= 50`. Arbitrary number, but arbitrary enforced beats squishy aspirational.

### X4a — `packages/tools/primitives/` subpackage convention (Phase 0 ADR addition)

The `packages/tools/` directory today mixes two categories: **subsystem call-outs** (`codex_tools/`, `claude_tools/`, `worktrees.py`, `skills/`) and what X6 is about to add — **agent-callable primitives** (`dispatch_health_reader`, `kill_switches`, `approvals`, `peer_runtimes`). Mixing them erodes the mental model. Introduce a deliberate subpackage:

```
packages/tools/
├── claude_tools/        # existing: subsystem call-out
├── codex_tools/         # existing: subsystem call-out
├── skills/              # existing: skill loader
├── worktrees.py         # existing: subsystem call-out
├── acp/                 # Phase 4: subsystem call-out
├── providers/           # Phase 6: subsystem call-out (provider overlay)
├── dispatch_health.py   # cross-cutting writer (X5)
└── primitives/          # NEW, Phase 0 ADR binding
    ├── __init__.py
    ├── dispatch_health_reader.py
    ├── kill_switches.py
    ├── approvals.py
    └── peer_runtimes.py
```

**Convention rule (binding on Phases 3, 4, 5, 6):** every module under `packages/tools/primitives/` is (a) stateless — no module-level mutable state, (b) importable by any worker or canonical skill without side effects, (c) returns typed values (frozen dataclasses or Protocol instances), (d) contains no orchestration — each function is a single operation. Any module that doesn't meet all four rules goes elsewhere. The rule is tested: `tests/python/unit/test_primitives_conventions.py` asserts each `primitives/*.py` module's top level contains no class instantiations, no file writes, no network calls.

### X4b — Phase 0 split: 0.0 vs 0.5 (ship strategy)

**Phase 0 is not one PR** — the architecture review estimated ~1,700 LOC across loader changes, SQLite bootstrap + 5-store migration + concurrent-writers test, runtime-supervisor three-file split, idioms + schema + registry writer, and the baseline benchmark. Unreviewable as one PR. Split:

**Phase 0.0 — Hard crash fix ONLY.** Ships same day. ~50 LOC. No deliverables beyond:
- Remove `content-performance-review` entry from `skills/registry.yaml` (the crash cause)
- Unit test asserting `load_registry()` returns a non-empty list without exception
- Nothing else. This PR exists only to unblock `load_registry()` callers that are broken today.

**Phase 0.5 — Everything else**, split into ordered sub-PRs that land sequentially:

1. **0.5a — Baseline benchmark (lands FIRST, standalone, parallelizable with 0.5b).** `tests/python/perf/test_dispatch_baseline.py` captures `claim_task → submit_task_result` median and p99 into `state/benchmarks/2026-04-14-pre-phase-0.json`. Every subsequent PR compares against this file. Without this, the "<100 ms regression" NFR is uncheckable.
   - **D1 hardening rule:** 0.5a MUST NOT import from `packages/db/connection.py`. The benchmark uses `sqlite3.connect(...)` directly against a temp DB path to measure what's on `main` today. Otherwise 0.5a silently depends on 0.5b and the parallel-with-0.5b promise is broken.
2. **0.5b — SQLite bootstrap (X2).** `packages/db/connection.py` + migration of `control_plane_db`, `approval_store`, `release_store`, `approval_token_store`, `task_queue` to use it. `test_concurrent_writers.py` + the autocommit-regression guard test. One PR because the migration is atomic across stores — partial migration leaves the platform in a state where half the writers have WAL defaults and half don't.
   - **D2 hardening rule:** within 0.5b, commits land in a forced order — (1) helper introduced, (2) all five stores switch `busy_timeout ≥ 30000`, (3) all five stores switch `journal_mode=WAL`. WAL is a file-level property so mixed-caller windows aren't a correctness hazard; the real risk is that an unmigrated store with default `busy_timeout=0` will `SQLITE_BUSY` under WAL's concurrent readers. Enforcing the commit order makes the PR bisectable at commit granularity.
   - **D6 hardening rule:** the autocommit regression test uses an existing table (`tasks` or `approvals`) — NEVER references `skill_evolution_locks` or any other table introduced in Phase 1+. Otherwise Phase 0 takes a forward dependency on Phase 3.
   - **D7 hotfix path:** add an env flag read inside `open_platform_db`: `if os.environ.get("AI_COMPANY_OS_DISABLE_WAL") == "1": skip PRAGMA journal_mode`. File-header WAL persists once set, but the flag prevents NEW DBs from going WAL and lets the operator nuke `state/db/*.db-wal` + restart as a hotfix if the concurrent-writers test regresses on `main` after merge. Documented in `docs/runbooks/sqlite-wal-hotfix.md` (created with 0.5b).
3. **0.5c — runtime-supervisor three-file split (X4) with `main.py` shim.** Pure refactor, no behavior change. Keeps `apps/runtime-supervisor/main.py` as a 2-line shim (`from .supervisor import main; main()`) so the launchd plist reference stays valid. Includes the LOC-budget test for `dispatch_router.py`. Tests updated to import from the new module paths.
4. **0.5d.1 — Schema additions only** (D5 split, part 1). Adds `self_evolvable: false` as a default in the registry schema (X10), extends `PolicyViolationCode(str, Enum)` with the members from X1's enumerated list, adds the path-traversal guard on `spec.adapters[*]`. Pure additive, no loader behavior change, ~80 LOC. Easy revert.
5. **0.5d.2 — Loader soften + idioms + lru_cache + registry writer** (D5 split, part 2). Includes X3 (`lru_cache` on `load_registry`), X9 (atomic `registry_writer.py`), loader adapter-path softening, `target_runtimes.py` leaf module. Ships AFTER 0.5d.1 so the schema fields and enum members already exist when the loader changes observe them.
6. **0.5e — Canonical layout ADR + dual-layout fixture discovery + primitives convention.** `docs/adr/2026-04-14-canonical-skill-layout.md` committed. `docs/adr/2026-04-14-primitives-subpackage.md` committed. Fixture discovery test covers both layouts. Mostly docs + a small loader change.
   - **D9 hardening rule:** the 0.5e fixture-discovery test uses synthetic fixtures at `tests/python/fixtures/_discovery/`, NOT any `skills/canonical/*/fixtures/` path. Otherwise 0.5e takes a forward dependency on Phase 1's actual fixture writes.

Each sub-PR has its own review and its own rollback. Phase 0.0 is same-day ship; 0.5a → 0.5e are serialized over the Phase 0 window. **Phase 1 cannot start until 0.5e is in.**

**Why the strict ordering:** 0.5b must land before 0.5d.2 because 0.5d.2's loader tests touch the DB via the new helper. 0.5c must land before 0.5d.2 because the loader test fixtures reference the three-file runtime-supervisor split. 0.5a is standalone and can ship in parallel with 0.5b if a reviewer is available, **provided D1 is honored**. 0.5d.1 can ship before 0.5c if convenient (it's schema-only, no runtime-supervisor touch), but the plan defaults to sequential for simplicity.

**Forward-fix zone after 0.5c:** once 0.5c lands, any subsequent PR that imports from `apps/runtime-supervisor/supervisor.py` or `worker_specs.py` (rather than `main.py`) makes 0.5c forward-fix-only — reverting 0.5c would leave those imports broken. The `main.py` shim (D3) is the mitigation: it means `main.py` never stops existing, so a revert of 0.5c is a straight `git revert` without manual fixup. Document explicitly in the 0.5c PR description.

**Rollback of 0.5b specifically:** setting `AI_COMPANY_OS_DISABLE_WAL=1` in the launchd plist environment + restarting + nuking `state/db/*.db-wal` is the hotfix-without-revert path. If that doesn't resolve the issue, a full git revert of 0.5b is needed; see `docs/runbooks/sqlite-wal-hotfix.md`.

### X5 — Dispatch-health as agent-native primitive (cross-cutting)

**Promote `scripts/dispatch-health.py` to `packages/tools/primitives/dispatch_health_reader.py`** (per X4a subpackage convention) exposing typed calls:

```python
def summarize(since: timedelta, lane: WorkerLane | None = None) -> DispatchHealthSummary: ...
def read_events(since: timedelta, lane: WorkerLane | None = None, 
                event_types: list[str] | None = None) -> list[DispatchEvent]: ...
def get_stalled_tasks(older_than: timedelta) -> list[TaskRef]: ...
```

The CLI script becomes a 5-line wrapper. **Every worker and the skill-self-evolution loop consume the same typed surface** instead of each re-parsing JSONL. The skill-self-evolution canonical skill reads task outcomes through this, so it's portable across runtimes (Claude, Codex, ACP) — the skill contract doesn't depend on a file path.

**Also:** `dispatch_health.record()` writes via a background flush thread + `queue.Queue`, not a blocking buffered writer. Caller-thread latency < 1 μs (queue put, no syscall). **No fsync on flush** — liveness over durability for a health stream. Buffered writes lose POSIX `O_APPEND` atomicity, so the background writer uses raw `os.write(fd, line)` with `O_APPEND` per flush to preserve atomic-per-line semantics for lines < 512 bytes. Add assertion: each event payload must serialize to < 512 bytes; oversized events are dropped with a warning.

**Payload whitelist** (security): `dispatch_health.record(event_type, payload)` accepts only `{task_id, lane, skill_id, duration_ms, reason_code}` — never the full task payload, which may carry secrets.

### X6 — Agent-native primitive layer (cross-cutting; each phase adds its piece)

Every human-facing affordance in the plan gets a matching agent-callable primitive. This is additive — no deliverable is removed.

| Human affordance | Agent primitive | Phase |
|---|---|---|
| `tail -f state/logs/dispatch-health.jsonl` | `dispatch_health_reader.summarize()` | X5 (cross-cutting) |
| `touch state/flags/skill_evolution_frozen` (set) | human-only — no agent primitive | 3 |
| `stat state/flags/*` (read) | `kill_switches.get_switch(name)` | 3 |
| Edit `packages/config/peer_runtimes.yaml` | `peer_runtimes.register(spec)` / `retire(peer_id)` | 4 |
| `launchctl list` for peer health | `peer_runtimes.get_health(peer_id)` | 4 |
| Route tasks to Hermes via config | `dispatch_to_peer(task_id, peer_id)` | 4 + 6 |
| `gh pr create` evolution proposal | `propose_skill_evolution(skill_id, rationale)` | 3 |
| `require_approval` verdict (currently dead) | `request_command_approval(cmd, ctx, rationale) → Token` + `submit_approval_token(token)` | 5 |
| `verify_peer_contract <peer>` (CI only) | agent-callable version of the negative contract test | 4 |

The canonical skill `skill-self-evolution` is rewritten in Phase 3 to orchestrate atomic primitives (`read_recent_task_outcomes`, `load_canonical_skill`, `stage_diff_to_artifacts`, `run_reconciliation_in_worktree`, `open_evolution_pr`) rather than embedding orchestration in `apps/worker-skill-evolution/main.py`. The worker is a thin claim loop; the prompt-defined orchestration lives in `skill.md`. This directly resolves rejected-alternative #5's concern ("hard-coding the logic into the worker creates a second source of truth") — the plan partially committed to canonical-skill framing but left orchestration in Python. Finish the job.

### X7 — Performance budgets (testable, concrete)

The plan's "<1ms per-call overhead" and "<100ms end-to-end regression" claims were unsupported. Replace with concrete budgets:

| Metric | Budget | Enforced by |
|---|---|---|
| `load_registry()` (cached) | < 50 μs median after first call | X3 lru_cache test |
| `load_validator()` cold-call (first use) | < 60 ms (15–40 ms Python import + 5–20 ms lazy transitive imports) | Phase 5 warmup test |
| `load_validator()` warm-call | < 500 μs median | Phase 5 integration test |
| `assert_command_allowed()` warm-call | < 500 μs median, < 2 ms p99 | Phase 5 integration test |
| `ProviderRegistry.resolve(slug)` warm | < 50 μs median (not < 1 ms) | Phase 6 integration test |
| Provider dispatch via Protocol | < 2 μs median warm, < 20 ms first call (lazy import) | Phase 6 integration test |
| ACP dispatch (warm peer, N-th call) | < 100 ms median round-trip | Phase 4 integration test |
| ACP peer cold start (first call ever) | < 5 s (Hermes cold start budget) | acknowledged one-shot |
| `dispatch_health.record()` caller-thread | < 1 μs (queue put) | `test_dispatch_health_latency.py` |
| `claim_task → submit_task_result` end-to-end | within +100 ms of pre-Phase-0 baseline | `test_dispatch_baseline.py` captured in Phase 0 |

**Phase 0 adds:** `tests/python/perf/test_dispatch_baseline.py` captures today's `claim_task → submit_task_result` median and p99 **before any other phase lands**, into `state/benchmarks/2026-04-14-pre-phase-0.json`. Without a baseline, the "<100 ms regression" NFR is uncheckable. Benchmarks use `pytest-benchmark` with `min_rounds=1000`, `warmup=True`.

### X8 — State directory hygiene (Phase 0 ADR extension)

The plan introduces `state/runtime/acp-peers/`, `state/quarantine/`, `state/archives/command-scan/`, `state/health/*`, `state/flags/*` — none of which exist in the current `state/` layout. The Phase 0 ADR must explicitly enumerate each new top-level subdirectory and add it to `state/README.md`. Use `state/handshake/acp-peers/` instead of `state/runtime/acp-peers/` — `handshake/` already exists and is semantically the right home (peer handshake/registration state).

Also: `state/logs/dispatch-health.jsonl` as a top-level flat file diverges from the existing convention where `state/logs/` holds per-worker subdirectories. Either move to `state/logs/dispatch-health/YYYY-MM-DD.jsonl` (directory with daily rollover) or document why cross-cutting streams live flat.

### X9 — Atomic registry write helper (Phase 0 deliverable)

`skills/registry.yaml` is edited by Phase 0, Phase 1, and implicitly by future skill registrations. No atomic-write helper exists. Add `packages/tools/skills/registry_writer.py` with `update_registry(mutator: Callable[[dict], dict])` that loads → mutates → writes to `registry.yaml.tmp` → `os.replace()`. Every registry edit (Phase 0 cleanup, Phase 1 fixture flips, Phase 3 self-evolution PRs that add new skills) must go through this helper. Without it, a worker loading the registry mid-edit can see a truncated YAML file.

### X10 — Canonical skills carry `self_evolvable: true` (Phase 0 schema addition)

Flip Phase 3's denylist to an allowlist model. Add `self_evolvable: false` as the **default** in the registry schema. A skill can be evolved by `worker-skill-evolution` only if its registry entry explicitly sets `self_evolvable: true`. This removes the denylist-maintenance anti-pattern entirely — new sensitive skills added in the future inherit `false` by default. Human-authored PRs to flip `self_evolvable` are the explicit privilege-escalation gate.

Also add a **path-pattern denylist** inside `check_evolution_allowed`: any proposed diff touching `packages/config/policies.yaml`, `packages/policies/command_scan.py`, `packages/config/peer_runtimes.yaml`, `packages/config/runtime_supervisor.yaml`, `.github/workflows/`, or `packages/db/connection.py` is auto-rejected with `PolicyViolation(PolicyViolationCode.CONFIG_MUTATION_REQUIRES_HUMAN)`. Config paths are not in the skill registry at all, so the allowlist model doesn't cover them — they need a separate path guard.

## Problem Statement

### The autonomous-dispatch gate is closed

Repo research confirms that `packages/tools/skills/loader.py:142-146` refuses to load any skill in `mode="autonomous"` unless `fixture_status == "passing"`:

```python
if mode == "autonomous" and spec.fixture_status != "passing":
    raise SkillNotEvaluated(
        f"skill {skill_id!r} fixture_status={spec.fixture_status!r}; "
        "refuse to load in mode='autonomous'"
    )
```

Out of 21 registered skills, 7 are `passing` (all validator-kind) and 13 are `missing`. Every single entry in the CLAUDE.md trigger-phrase table — `product-artifact-chain`, `codex-claude-handoff`, `supervisor-goal-decomposition`, `ios-ui-polish-review`, `ios-to-appstore-handoff`, `app-store-positioning-pack`, `niche-research-brief`, `gtm-artifact-refresh`, `content-factory`, `content-scheduler` — is `missing`. These are the routing targets humans invoke through Claude Code; they also need to be the routing targets `runtime-supervisor` and `worker-supervisor` invoke autonomously. Today only a human-in-the-loop Claude Code session can trigger them.

### The registry is un-loadable

`skills/registry.yaml:272` sets `fixture_status: planned` for the `content-performance-review` skill. The loader validates fixture_status against the literal set `"passing" | "failing" | "missing"` (`loader.py:28`). `load_registry()` at `loader.py:98-102` raises `SkillLoadError` on that entry. Until this is fixed, **anyone calling `load_registry()` end-to-end crashes.** This is a pre-existing bug, not a Hermes-integration concern, but it blocks every phase below.

### The adapter lookup is hard-coded

`packages/tools/skills/loader.py:208-210` resolves the adapter path as `skills/adapters/claude/<skill_id>.md` regardless of what the registry says. The registry already carries a per-runtime `adapters:` map (`registry.yaml:19` onwards), but the loader ignores it. Adding an ACP adapter lane is blocked on this 5-line fix.

### Two canonical layouts coexist and the plan must choose

Phase-0 skills live as flat markdown files under `canonical/shared/`, `canonical/handoffs/`, and `canonical/products/catchbook/`. Phase-2.5+ skills live as per-skill directories with a `fixtures/` subdirectory. The loader assumes the directory layout when looking for `validator.py`. A plan that writes fixtures for `product-artifact-chain` and `codex-claude-handoff` must either migrate them to the directory layout or extend fixture discovery to handle the flat layout. Leaving this decision implicit guarantees drift.

### `fixture_status: passing` is trusted without validation for agentic skills

`content-voice-guardrail` is marked `fixture_status: passing` with `kind: agentic` and has no `validator.py`. The loader trusts the registry entry without any automated check that the fixtures actually pass. A self-evolving system that trusts `fixture_status: passing` autonomously is a phantom-skill risk: a bad fixture lands, nothing validates it, autonomous dispatch proceeds. This gap must close in Phase 1 before Phase 3 can safely propose new skills.

### External-runtime interop is missing

Every serious AI host in the last 30 days has added Hermes as a peer runtime — paperclipai/paperclip PR #1867, multica-ai/multica PR #611, coleam00/Archon #1106, bytedance/deer-flow #1865, beclab/apps #2227. The emerging protocol is **ACP (Agent Client Protocol) over JSON-RPC 2.0/stdio**, used for runtime-to-runtime orchestration. Our platform has `skills/adapters/claude/` and `skills/adapters/codex/` but no protocol adapter, no peer-runtime concept in `runtime-supervisor`, and no path to dispatch a task to Hermes, Ollama, or any non-Anthropic, non-Codex execution context.

### No pre-execution command scanning exists

`packages/policies/` has approval routing, release gating, GTM cooldowns, testing-lane enforcement, and output sanitization. It has **no shell-command scanner.** `worker-engineering` and `worker-gtm` call out to `packages/tools/codex_tools/cli.py` and `packages/tools/worktrees.py` without a policy pass on the actual commands. Hermes ships `tirith` for this exact problem; the pattern is sound and the composition pattern is already in-house (`packages/policies/release_readiness.py:31` composes `load_validator` into a fail-closed policy wrapper).

### Provider pluggability is hard-coded

Adding a new model provider means writing a new sibling to `packages/tools/codex_tools/` or `packages/tools/claude_tools/`. Hermes's `HERMES_OVERLAYS` pattern (a slug→provider class map, referenced in NousResearch/hermes-agent issue #6455) is a well-validated alternative. Every Hermes fork in the wild is benefiting from this. We should too, before we have three runtimes wired in hard-coded style.

## Proposed Solution

A six-phase sequence with a hard precondition gate (Phase 0), a dispatch unblock gate (Phase 1), an exploration phase (Phase 2) that feeds the two capability phases (Phase 3 and Phase 4), and two hardening phases (Phase 5 and Phase 6). Cross-cutting: a dispatch-health observability stream every phase writes to.

- **Phase 0 — Platform Preconditions.** Ship in a single atomic PR. Fix the registry load crash, soften the loader's hard-coded adapter path, make a binding decision on canonical layout, extend fixture discovery to cover both layouts. Everything below assumes this shipped.
- **Phase 1 — Close the Fixture Gate.** Pick three project_skill entries with the smallest surface area, write fixtures, triage existing `passing` agentic skills to plug the trust-without-validation hole, verify autonomous dispatch works end-to-end. At the end of this phase, `runtime-supervisor` can dispatch three skills without a human.
- **Phase 2 — Hermes Integration Spike.** Install Hermes v0.7.0 from source, point its `skills.external_dirs` at our canonical directory, invoke our skills through Hermes CLI, document the gap. Zero code changes to our repo. Findings feed Phase 3 and Phase 4 planning without reordering them.
- **Phase 3 — Skill Self-Evolution Loop.** New worker lane `worker-skill-evolution` that reads recent task outcomes from `state/` and proposes new canonical skills or patches as PRs against `skills/canonical/`. Never auto-merges. Gated by a new policy in `packages/policies/`. Concurrent-run lock. **Allowlist model:** only skills with `self_evolvable: true` in the registry can be evolved (default is `false`), plus a path-pattern denylist for config files and CI workflows. Revert runbook. Metrics dashboard.
- **Phase 4 — ACP Protocol Adapter.** New adapter lane `skills/adapters/acp/`, new `target_runtimes` literal value, runtime-supervisor learns ACP dispatch behind a feature flag, first consumer is the Hermes instance from Phase 2, first negative contract test prevents silent payload regressions.
- **Phase 5 — Command-Scan Policy.** New validator-kind canonical skill `command-scan`, new `packages/policies/command_scan.py` wrapping it with fail-closed `PolicyViolation`, wired into shell-exec call sites with a defensive import so a Phase-0 regression can't take down worktree creation.
- **Phase 6 — Provider Overlay Registry.** New `packages/tools/providers/registry.py` with a slug→class map, migration of Claude/Codex tool invocations through the overlay, explicit decision on whether `TaskPacket.provider_hint` is in or out.

**Cross-cutting observability:** Every phase writes to `state/logs/dispatch-health.jsonl` on task claim/complete/fail. A 10-line `scripts/dispatch-health.py` summarizer gives a single read of what the platform is doing without chasing per-worker logs.

## Technical Approach

### Architecture

The platform continues to own orchestration. Hermes is treated as a **peer runtime** dispatched through ACP, not as an orchestrator. The self-evolution loop is a **worker lane**, not a supervisor capability — it inherits the existing worker contract (typed payloads, queue-claimed, observable, approval-gated for risky writes). The command-scan policy is a **thin policy wrapper** around a new validator-kind skill, exactly like `release_readiness.py` wraps `approval-token-audit`.

Three architectural invariants the plan preserves:

1. **Platform owns orchestration. Workers specialize. Codex writes code.** (CLAUDE.md:9-15)
2. **Policies live in `packages/policies/`. Workers do not own policy.** — the command-scan wrapper lives in `packages/policies/command_scan.py`, not in any worker.
3. **Runtime state lives in `state/`.** — self-evolution proposals live in `state/artifacts/skill-evolution/`, dispatch health in `state/logs/dispatch-health.jsonl`, command-scan audit log in `state/logs/command-scan/`.

### Implementation Phases

---

#### Phase 0 — Platform Preconditions

**Goal:** Make the skill registry loadable end-to-end and the loader adapter-path flexible, so every subsequent phase has a working foundation.

**Preconditions:** None. This phase has no dependencies.

**Deliverables (single atomic PR):**

- `skills/registry.yaml` — remove or re-status the `content-performance-review` entry at line 272. Either delete it entirely (defer to the GTM content engine plan already tracking it) or add `"planned"` to the loader's literal set. **Decision:** remove the entry. `content-performance-review` is already tracked in `docs/plans/2026-04-13-feat-gtm-multi-platform-content-engine-plan.md`; duplicating it with an invalid status is an accident waiting to happen.
- `packages/tools/skills/loader.py:208-210` — replace the hard-coded `adapters/claude/<skill_id>.md` path with a registry-driven lookup reading `spec.adapters[runtime_slug]`. Fall back to the current Claude path only when the registry has no adapters map for the requested runtime. Add a test in `tests/python/unit/test_skills_loader.py` asserting both paths.
- `packages/tools/skills/loader.py:28` — extend the `fixture_status` literal to whatever the post-removal set is. No change if `content-performance-review` is removed; add `"planned"` if the decision flips.
- `docs/adr/2026-04-14-canonical-skill-layout.md` — new ADR documenting the decision: **new skills use the per-skill-dir layout under `canonical/<skill-id>/` with `skill.md`, `contract.yaml` (optional for validator-kind), `validator.py` (required for validator-kind), and `fixtures/`. Phase-0 flat files under `canonical/shared/`, `canonical/handoffs/`, `canonical/products/catchbook/` stay flat; fixture discovery resolves both layouts.** This is binding on Phase 1+.
- `packages/tools/skills/loader.py` — extend fixture discovery to resolve `<canonical_dir>/fixtures/` for directory-layout skills and `<canonical_dir>/<skill_id>.fixtures.yaml` (sibling) for flat-layout skills. Add unit tests covering both.
- `packages/tools/skills/target_runtimes.py` (new) — extract the list of valid target-runtime slugs (`claude`, `codex`, and prepped `acp` slot added as an explicit `Literal`) into a module-level constant so Phase 4 doesn't have to touch the loader again.

**Definition of Done** (rolling, one criterion per sub-PR per X4b split):

*Phase 0.0 done when:*
- `load_registry()` returns a non-empty list with no exceptions (crash fix verified).

*Phase 0.5a done when:*
- `state/benchmarks/2026-04-14-pre-phase-0.json` exists with baseline `claim_task → submit_task_result` median and p99 captured.

*Phase 0.5b done when:*
- Every `sqlite3.connect(...)` in `packages/db/` and `packages/queue/` routes through `packages/db/connection.py:open_platform_db`.
- `tests/python/integration/test_concurrent_writers.py` passes (N=8 writers, 100 cycles each, zero `SQLITE_BUSY`, p99 < 20 ms).
- Autocommit regression test passes (`with conn: conn.execute("INSERT ...")` still commits).
- Startup assertion `PRAGMA journal_mode == 'wal'` fires on every store.

*Phase 0.5c done when:*
- `apps/runtime-supervisor/main.py` is replaced by `supervisor.py` + `worker_specs.py` + `dispatch_router.py`.
- `tests/python/unit/test_dispatch_router_loc_budget.py` passes (≤ 50 LOC).
- All existing import sites updated.
- `launchctl kickstart -k` runtime-supervisor boots cleanly.

*Phase 0.5d.1 done when:*
- `self_evolvable` defaults to `false` in the registry schema; existing skills' effective value is still `false`.
- `PolicyViolationCode` enum exists with every member enumerated in X1 above.
- Path-traversal guard on `spec.adapters[*]` rejects `../../../etc/passwd`.
- Unit test `test_policy_violation_codes_enumerated` passes (no bare-string raise sites in `packages/policies/`).

*Phase 0.5d.2 done when:*
- Unit test `test_loader_adapter_lookup_honors_registry` passes against a fake registry entry with `adapters: {acp: adapters/acp/test.md}`.
- Unit test `test_target_runtimes_import_safety.py` passes.
- `lru_cache` on `load_registry()` verified (same tuple instance on repeat calls with unchanged file; different tuple after atomic `os.replace()` write).
- Registry writer helper in place, every registry edit goes through it.

*Phase 0.5e done when:*
- `docs/adr/2026-04-14-canonical-skill-layout.md` committed and linked from `skills/WIRING.md`.
- `docs/adr/2026-04-14-primitives-subpackage.md` committed.
- Unit tests `test_loader_discovers_flat_layout_fixtures` and `test_loader_discovers_dir_layout_fixtures` both pass.

**Rollback:** Each sub-PR has its own revert. Phase 0.0 is a one-line registry edit; `git revert <0.0-sha>` + restart reverts. Phase 0.5b rollback is non-trivial once stores have migrated — requires coordinated revert of all five store files + one migration test. **DO NOT revert 0.5b incrementally** or you'll half-migrate the platform.

**Risks:**
- Removing `content-performance-review` from the registry may surprise the GTM content engine plan; mitigated by linking the removal to that plan's Phase 6 which explicitly defers it.
- Extending fixture discovery without matching test coverage creates silent holes — mitigated by the explicit test requirements above.

**Research Insights (Phase 0):**

- **Atomic PR feasibility:** borderline. 6 deliverables × (loader.py + registry.yaml + target_runtimes.py + fixture discovery + ADR + tests) ≈ 250–400 LOC diff. Ship as **one PR with ordered commits** so `load_registry()` is never half-fixed on main: (1) registry cleanup, (2) target_runtimes extraction, (3) registry-driven adapter path + fallback, (4) dual-layout fixture discovery, (5) ADR + WIRING link, (6) tests for (3) and (4). If diff balloons past ~500 LOC, split commit 1 into its own PR merged first — it's the only hard crash-fix and needs no ADR.
- **Phase 0 absorbs these cross-cutting deliverables** from the deepening pass: X1 (Python idioms including `PolicyViolationCode`), X2 (SQLite `connection.py` helper + migration of existing stores + concurrent-writers test), X3 (`lru_cache` on `load_registry`), X4 (runtime-supervisor three-file refactor), X7 (baseline benchmark), X8 (state directory hygiene in the ADR), X9 (atomic registry writer), X10 (`self_evolvable: false` default in registry schema).
- **Pre-deployment verification commands:**
  ```bash
  python -c "from packages.tools.skills.loader import load_registry; r=load_registry(); print(len(r))"  # no crash
  python -c "from packages.tools.skills.target_runtimes import TARGET_RUNTIMES; print(TARGET_RUNTIMES)"  # ('claude','codex','acp')
  python -c "import sqlite3, packages.db.connection as c; conn=c.open_platform_db(':memory:'); print(conn.execute('PRAGMA journal_mode').fetchone())"  # ('wal',)
  pytest tests/python/unit/test_skills_loader.py tests/python/unit/test_target_runtimes_import_safety.py tests/python/integration/test_concurrent_writers.py -q
  test -f docs/adr/2026-04-14-canonical-skill-layout.md
  grep -c 'content-performance-review' skills/registry.yaml  # expect 0
  ```
- **Rollback:** `git revert -m 1 <phase0-sha> && launchctl kickstart -k gui/$(id -u)/com.ai-company-os.runtime-supervisor`. No persistent state is created by Phase 0; ADR can stay committed (harmless).
- **Failure-mode playbook:**
  - *`load_registry()` still crashes:* `grep -nE 'fixture_status:' skills/registry.yaml | grep -vE 'passing|failing|missing'` to find a second bad literal. Hotfix by extending the `Literal` set rather than reverting the whole PR.
  - *Adapter fallback breaks Claude skills:* grep for `_skills_root() / "adapters" / "claude"` call sites; ensure fallback reached when `spec.adapters` is empty dict AND when the key is missing entirely.
- **Path-traversal guard on `spec.adapters[runtime_slug]`:** new registry field must be regex-constrained to `^skills/adapters/[a-z]+/[a-z0-9_-]+\.md$`. Without this the loader happily resolves `../../../etc/passwd` if a malicious registry entry lands. Add to the loader in the same PR and test both happy and adversarial cases. (Security N10)

---

#### Phase 1 — Close the Fixture Gate

**Goal:** Three `project_skill` entries dispatch end-to-end through `runtime-supervisor` in `mode="autonomous"` without any human in the loop, and the registry↔fixture reconciliation check closes the trust-without-validation gap on existing `passing` agentic skills.

**Preconditions:** Phase 0 shipped. `load_registry()` works. Fixture discovery handles both layouts.

**Targets (smallest surface area first):**
1. **`supervisor-goal-decomposition`** — `apps/worker-supervisor/main.py:13` already implements this with deterministic keyword-based lane routing. Fixtures can assert lane-routing output against canned Goal inputs without any LLM round-trip. Arguably should be reclassified `kind: validator`.
2. **`product-artifact-chain`** — canonical file already enumerates `validation_steps`. Fixture runs against a fake `docs/products/<id>/` tree asserting gap-report shape.
3. **`codex-claude-handoff`** — structured handoff protocol with enumerable input/output. Happy-path + missing-field fixtures.

**Deliverables:**

- `skills/canonical/supervisor-goal-decomposition/` — migrate from flat `shared/supervisor-goal-decomposition.md` to directory layout per the Phase 0 ADR. Add `fixtures/{happy_path,boundary,adversarial}.yaml`. Add `validator.py` that replays the deterministic routing function from `worker-supervisor/main.py:13`. Flip `kind: agentic` → `kind: validator` in `skills/registry.yaml`.
- `skills/canonical/product-artifact-chain/` — migrate from flat `shared/product-artifact-chain.md`. Add `fixtures/{happy_path,boundary_missing_artifact,adversarial_extra_artifact}.json` pointing at seeded `state/fixtures/product-artifact-chain/<name>/` trees. Keep `kind: agentic`; write an agentic-style fixture that records expected gap-report structure.
- `skills/canonical/codex-claude-handoff/` — migrate from flat `handoffs/codex-claude-handoff.md`. Add `fixtures/{happy_path,boundary_missing_context,adversarial_stale_token}.yaml`.
- **1.3a — Triage existing `passing` agentic skills.** `content-voice-guardrail` (`registry.yaml:163-164`), `aso-keyword-refresh`, `creator-outreach-draft`. For each: either add a `validator.py` that replays the fixtures, or downgrade `fixture_status` to `missing` with a rationale comment, or add explicit `validator: none` opt-out in the registry schema with a rationale. **No silent trust.**
- `packages/tools/skills/reconciliation.py` (new) — module exposing `reconcile_fixtures_against_registry()`. Reads every `passing` entry in the registry, asserts that (a) fixtures exist where the layout says they should, (b) for validator-kind a `validator.py` exists, (c) the fixtures parse. Returns a structured diff.
- `tests/python/unit/test_skill_reconciliation.py` — new. Runs reconciliation on the real registry. Hard-fails CI on any drift.
- `.github/workflows/skill-reconciliation.yml` (or equivalent in the existing CI config) — wire the reconciliation test into CI.
- `tests/python/integration/test_autonomous_dispatch.py` — **three** separate end-to-end tests, one per skill, each using a temp SQLite DB and temp `state/` root to avoid order-dependent flakes. Each test enqueues a synthetic task, lets `runtime-supervisor` claim and execute it, asserts the output artifact and the autonomous-mode flag on the result.
- `skills/registry.yaml` — flip `fixture_status: missing` → `passing` on the three target skills, ONLY after 1.3a is complete and reconciliation passes.

**Definition of Done (precise, per SpecFlow feedback):**
- All three project_skills dispatch end-to-end through `runtime-supervisor` in `mode="autonomous"`.
- Zero `fixture_status: missing` entries among the three.
- Reconciliation check runs in CI on every push, not as a one-shot script.
- All existing `passing` agentic skills have either a `validator.py`, a downgrade, or an explicit `validator: none` with rationale.
- Each end-to-end test runs against an isolated temp queue and temp state root.

**Rollback:** Flip `fixture_status` back to `missing` in the registry; the loader crash-closes and autonomous mode stops dispatching. Fixtures and reconciliation code can stay; they're inert without the flip.

**Risks:**
- Fixtures that shell out to the real codex_tools will flake in CI — mitigated by the isolation requirement (temp state root) and by keeping the first three fixture sets deterministic (no LLM calls).
- Migrating flat → directory layout may break existing imports of those canonical paths — mitigated by a grep pass before migration and by keeping a symlink or a one-line re-export for the transition PR.

**Research Insights (Phase 1):**

- **Split into 4 PRs, not one:** PR-1a (triage: validator backfill / downgrade / `validator: none` opt-out on every existing `passing` agentic skill + reconciliation module + CI wire-up) → verify → PR-1b (supervisor-goal-decomposition) → PR-1c (product-artifact-chain) → PR-1d (codex-claude-handoff). A loader bug surfaced by PR-1b isolates to one skill and doesn't stall the others. After PR-1a each subsequent PR is a single-commit revert.
- **Phase 1 feature flag (missing from original plan):** add `state/flags/autonomous_dispatch_frozen` check in `loader.py` in Phase 0. A one-file `touch` disables all autonomous dispatch without any git revert — matches Phase 3's kill-switch pattern and gives Phase 1 a sub-5-second rollback primitive instead of requiring a registry flip + restart.
- **1.3a is a HARD GATE on Phases 2–5 starting, not just a Phase 1 checklist item.** Specifically: until every existing `fixture_status: passing` agentic skill has either a real `validator.py` that replays fixtures, a downgrade to `missing`, or an explicit `validator: none` with rationale, no other phase can start. `content-voice-guardrail` is the canonical example. Security audit finding C7 makes this a blocking precondition, not advisory.
- **Pytest fixture pattern for isolated_platform:** function-scoped, not session-scoped (the three end-to-end tests mutate queue state; session scope leaks). Use `monkeypatch.setenv("AICO_DB_PATH", str(tmp_path / "control_plane.db"))` and `monkeypatch.setenv("AICO_STATE_ROOT", str(tmp_path / "state"))` with a `@pytest.fixture` yielding a `PlatformHandle`. **Precondition:** if `control_plane_db` or `loader.py` read paths at import time, that's a Phase 0 fix — all path reads must be lazy/env-driven so tests can inject roots. Audit in Phase 0.
- **Mandatory `pytest-timeout`** on `test_autonomous_dispatch.py` (20 s hard cap). Without it, a hanging claim loop becomes a stalled CI run, not a failing test. The plan's original deliverables missed this.
- **Reconciliation test runs in the existing unit test job, not a dedicated workflow file.** Simplicity reviewer: drop `.github/workflows/skill-reconciliation.yml` as a standalone file; add the test to `tests/python/unit/` and let the existing pytest run pick it up. One fewer CI artifact to maintain.
- **Fixture schema versioning:** every fixture file adds `schema_version: 1` frontmatter; the loader asserts it on discovery. A future schema change forces a coordinated bump, making silent drift impossible. (Data-integrity B6)

---

#### Phase 2 — Hermes Integration Spike

**Goal:** Answer one question with a written artifact: *can our canonical skills be consumed by a local Hermes v0.7.0 instance via its native `skills.external_dirs` hook with zero code changes to our repo?*

**Preconditions:** Phase 1 shipped. At least three project_skills can be dispatched autonomously so the spike has real skills to invoke.

**Deliverables:**

- `~/hermes/` (outside the repo, local only) — `git clone --branch v0.7.0 https://github.com/NousResearch/hermes-agent.git` and install via `uv` per the source tree's `pyproject.toml`. **Do not use** the curl|bash install script (upstream issues #7066, #6393, #6360 are all install-script breakage). **Do not use** the Docker image (#9153 dashboard missing) or the Nix flake (#9305 fastapi missing, #9526 sphinx pin). Pin to commit `abf1e98` which the upstream has validated as clean v0.7.0.
- Hermes config fragment stored at `docs/research/2026-04-hermes-spike/hermes-config.yaml` (documented, not executed from the repo) — sets `skills.external_dirs: ["/Users/simons/ai-company-os/skills/canonical"]`.
- `docs/research/2026-04-hermes-spike-findings.md` — the spike writeup. Must cover: (a) which of the three Phase 1 skills Hermes could load at all, (b) which could execute without modification, (c) what schema or frontmatter fields Hermes expects that our canonical shape does not provide, (d) what tool invocations our skills expect that Hermes does not expose, (e) whether `skills.external_dirs` picks up our directory-layout or flat-layout files or both, (f) Telegram slash command registration status (known bug — upstream #8110).
- Decision record at the bottom of the findings doc: **small gap** (< 5 schema additions, no runtime changes) → proceed to Phase 4 with confidence that the ACP adapter is the right abstraction; **large gap** → open a follow-up plan for `skills/adapters/hermes/` before Phase 4 ACP work hardens a schema.

**Definition of Done:**
- Hermes v0.7.0 running locally from source.
- At least one canonical skill invoked through Hermes CLI end-to-end, with output captured in the findings doc.
- Written gap analysis covering the six bullets above.
- Decision recorded.

**Sequencing rule (per SpecFlow feedback):** Phase 2 findings can *accelerate* Phase 4 planning but **cannot reorder it ahead of Phase 3**. Phase 3 pressure-tests the canonical skill layout before ACP freezes a schema around it.

**Rollback:** None needed — zero code changes to the repo. Worst case, the spike fails and we have a document explaining why.

**Risks:**
- Upstream regression between the commit pin and HEAD — mitigated by pinning to a specific SHA.
- Safari/Firefox cookie permissions on macOS affecting Hermes's own auth paths — out of scope; Hermes manages its own auth.

**Research Insights (Phase 2):**

- **Pin the tag, not the SHA.** Use `git clone --branch v2026.4.3 --depth 1 https://github.com/NousResearch/hermes-agent.git ~/hermes` — `v2026.4.3` is the v0.7.0 release tag. The earlier "commit `abf1e98`" pin is ambiguous because SHA resolution can drift across rebases. Alternatively, upgrade to `v2026.4.13` (v0.9.0, released 2026-04-13) which includes the `AuthMethod → AuthMethodAgent` rename that matches `agent-client-protocol ≥ 0.9.0`. If you go v0.9.0, pin both Hermes AND the ACP Python package version together.
- **Exact config location:** `~/.hermes/cli-config.yaml` (example at `cli-config.yaml.example` in the repo root). The `skills.external_dirs` block:
  ```yaml
  skills:
    creation_nudge_interval: 15
    external_dirs:
      - /Users/simons/ai-company-os/skills/canonical
  ```
  Paths are `~`/`${VAR}`-expanded and resolved to absolute. **External dirs are read-only**; Hermes's own skill creation still writes to `~/.hermes/skills/`. **Local skills take precedence on collision.**
- **Flat-layout discovery is almost certainly broken.** Hermes discovers skills by directory, expecting `SKILL.md` per per-skill dir (agentskills.io standard). Files under `canonical/shared/*.md` flat-layout will likely not be discovered. The spike must explicitly test both layouts and record the result. **If confirmed, flat skills are effectively Claude-only forever** unless migrated — this is load-bearing for the Phase 0 ADR's "keep flat flat" decision.
- **Install path:** `uv venv venv --python 3.11` inside `~/hermes` (isolated from ai-company-os's venv), then `uv sync` (not `uv pip install -e .`). **Do not** install Hermes as a dependency of ai-company-os — it must be a peer process, not an import. The existing `uv.lock` in v2026.4.3 is present and stable.
- **uv/Nix/Docker caveats reconfirmed:** don't touch `curl | bash` install script (upstream #7066, #6393, #6360 — breakage), don't touch Docker image (#9153), don't touch Nix flake (#9305, #9526). uv-from-source is the only path.
- **ACP Python SDK exists as a first-class package.** `pip install agent-client-protocol` (package name `acp`, org `agentclientprotocol`). **Hermes v0.7.0 already ships an ACP server** at `acp_adapter/server.py` where `HermesACPAgent` subclasses `acp.Agent`. This means the Phase 4 work is **writing an ACP client**, not a protocol layer from scratch. The spike should verify this server runs and accepts a minimal `initialize` → `new_session` → `prompt` sequence from `agent-client-protocol.Agent.connect_to_agent()`.
- **Phase 2 findings doc must cover six items:** (a) which of the three Phase 1 skills Hermes could load, (b) which could execute unchanged, (c) frontmatter/schema gaps, (d) missing tool-call expectations, (e) discovery of directory vs flat layout, (f) Telegram slash-command registration (#8110). Add a seventh: (g) ACP server sanity check — does Hermes's ACP server actually accept a client handshake from the Python SDK?

---

#### Phase 3 — Skill Self-Evolution Loop

**Goal:** A new worker lane observes recent task outcomes, proposes a new canonical skill or patch as a PR against `skills/canonical/`, and ships the first accepted proposal through a 72-hour production observation window without revert.

**Preconditions:** Phase 1 shipped (reconciliation check in CI, three skills dispatchable autonomously). Phase 2 findings in hand.

**Architecture decision:** The self-evolution loop is a **new worker lane**, NOT a capability of `worker-supervisor`. Reasoning: worker-supervisor owns goal decomposition, which is planning under human-set direction. Skill evolution proposes changes to the canonical source of truth, which has a materially different approval boundary. Mixing them makes approval scoping impossible.

**Deliverables:**

- `packages/schemas/worker_lane.py` — add `SKILL_EVOLUTION = "skill_evolution"` to the `WorkerLane` enum (currently at `packages/schemas/task_packet.py:7-13`).
- `apps/worker-skill-evolution/main.py` — new worker following the `worker-gtm` template. Claims tasks from the queue with `lane=SKILL_EVOLUTION`. Runs pre-claim gates via a single `_refuse_if_blocked()`-shaped function composing: kill-switch at `state/flags/skill_evolution_frozen`, `self_evolvable: true` allowlist check, path-pattern denylist for config files, concurrent-run lock acquisition. Executes the proposal task. Submits result via `ControlPlaneService.submit_task_result`.
- `apps/runtime-supervisor/worker_specs.py` (see X4 split) — extend `default_worker_specs()` to include `worker-skill-evolution` AND `worker-supervisor` AND `worker-gtm` (the latter two are already missing from the launchd entrypoint per repo research). Without this the evolution worker never starts.
- `skills/canonical/skill-self-evolution/` — new canonical skill (per-skill-dir layout per the Phase 0 ADR). `skill.md` describes the proposal contract (inputs: recent task outcomes, outputs: a PR branch spec) and is the source of truth for orchestration (not embedded in `main.py`, per X6). `fixtures/{happy_path_patch_existing,boundary_new_skill,adversarial_self_reference}.yaml`. `kind: agentic`. **Registry entry: `self_evolvable: false`** (evolution of the evolution skill itself requires human-authored PR — this is the allowlist default). `target_runtimes: [claude]` initially; `codex` added if/when the spike finds codex can execute it. **Never `acp`** on a self-evolved skill's first landing (X6 rule).
- `packages/policies/skill_evolution.py` — new policy module matching the `release_readiness.py` composition pattern. Exposes:
  - `check_evolution_allowed(task: TaskPacket, proposed_diff: ProposedDiff) -> None` — **composite entry point** that the worker calls once per proposal. Raises `PolicyViolation(PolicyViolationCode.*)` for: (a) target skill does not have `self_evolvable: true` in the registry, (b) proposed diff touches any path-pattern denylist entry (see below), (c) concurrent in-flight proposal exists on the same skill (checked via the lock store), (d) proposed diff adds `codex` or `acp` to a self-evolved skill's `target_runtimes` (requires human PR per X6). **Internally delegates to `check_fixture_skill_atomicity` and `check_regression_fixture_gate` for conditions (e) and (f).** The two sibling functions exist as named entry points so unit tests can exercise each check in isolation, but the worker never calls them directly — only `check_evolution_allowed`.
  - **Allowlist enforcement:** the function reads the target skill's registry entry via `load_registry()` and refuses if `self_evolvable != True`. No hardcoded denylist of skill IDs — the allowlist is the denylist's negation, and it's maintained in `skills/registry.yaml` where the rest of skill metadata lives. Default is `false`; flipping requires a human PR.
  - **Path-pattern denylist (for non-registry paths):** `_CONFIG_DENY_PATTERNS: tuple[str, ...]` — glob patterns for files that are not registered skills but still must not be modified by an evolution proposal: `packages/config/policies.yaml`, `packages/config/peer_runtimes.yaml`, `packages/config/runtime_supervisor.yaml`, `packages/policies/command_scan.py`, `packages/policies/skill_evolution.py`, `packages/db/connection.py`, `.github/workflows/**`, `infra/launchd/**`, `infra/sandbox/**`. Any diff touching these raises `PolicyViolation(PolicyViolationCode.CONFIG_MUTATION_REQUIRES_HUMAN)`.
  - **Third-file smuggling guard** (security H4): the diff may only touch files matching `skills/canonical/<skill_id>/{skill.md,contract.yaml,validator.py,fixtures/**}`. Any other file in the diff — including `helpers.py`, `__init__.py`, or anything at the package level — is an automatic reject unless an elevated-approval token is present.
  - `check_fixture_skill_atomicity(diff: ProposedDiff) -> None` — asserts that a diff modifying a canonical skill's `validator.py` also modifies at least one file under its `fixtures/` and vice versa. Fail-closed `PolicyViolation(PolicyViolationCode.FIXTURE_SKILL_DRIFT)`.
  - `check_regression_fixture_gate(diff: ProposedDiff) -> None` (Voyager/DSPy gate) — runs the proposed new validator against the **incumbent's fixture set** and asserts every verdict matches or exceeds the incumbent's verdict. Fail-closed `PolicyViolation(PolicyViolationCode.REGRESSION_AGAINST_INCUMBENT)`.
- `packages/db/locks/skill_evolution.py` (per architecture review, NOT a sidecar file) — per-`skill_id` lock store backed by `packages/db/control_plane_db.ControlPlaneDatabase` (same backend as the rest of the platform; supports Postgres via `DATABASE_URL`). See X2 for the connection bootstrap. See the Phase 3 Research Insights section for the corrected SQL schema and UPSERT grammar.
- `state/artifacts/skill-evolution/<proposal-id>/` — output directory. Contains the proposed diff, the input snapshot from `state/checkpoints/`, and the reconciliation report. Never written directly into `skills/canonical/` — always staged here first.
- PR authoring pipeline: the worker uses `git worktree add` into `state/worktrees/skill-evolution/<proposal-id>/`, applies the diff, runs the reconciliation check from Phase 1, commits, pushes a branch, opens a PR via `gh pr create`. **Never auto-merges.**
- `docs/runbooks/skill-evolution-revert.md` — new. Procedure for reverting a shipped evolution: (a) revert the PR, (b) drain the queue of `lane=SKILL_EVOLUTION` tasks, (c) quarantine `state/artifacts/skill-evolution/<bad-proposal-id>/` by moving to `state/quarantine/`, (d) file a `docs/solutions/integration-issues/` post-mortem entry.
- `scripts/skill-evolution-metrics.py` — summarizes `state/logs/dispatch-health.jsonl` filtered on `lane=skill_evolution`, producing counts of proposals generated / accepted / reverted per day. Output goes to `state/artifacts/skill-evolution/metrics/YYYY-MM-DD.json`.
- `tests/python/unit/test_skill_evolution_policy.py` — covers denylist enforcement, concurrent-lock acquisition, fixture-skill atomicity, and the `packages/policies/` elevated-approval branch.
- `tests/python/integration/test_skill_evolution_dry_run.py` — end-to-end dry run: enqueue an evolution task targeting a benign canonical skill, assert it writes to `state/artifacts/skill-evolution/`, opens a PR branch (against a test remote), and never touches the real canonical dir.

**Definition of Done:**
- One proposal generated, reviewed by a human, merged, and observed in production for 72 hours without revert.
- Metrics dashboard (`scripts/skill-evolution-metrics.py`) exists and runs on a daily cron.
- Revert runbook exists and has been walked through by a human at least once against a synthetic proposal.
- Self-evolution denylist is enforced by test.
- Concurrent-run lock is enforced by test.

**Rollback:** Three layers. (1) Kill-switch file `state/flags/skill_evolution_frozen` — worker refuses to claim any new tasks while present. (2) Disable the worker in `apps/runtime-supervisor/worker_specs.py:default_worker_specs()` (post-X4 split) — launchd stops starting it. (3) Revert the shipped PR via the revert runbook; the only mutable surface the worker touches is git itself, so a PR revert is a complete rollback.

**Risks:**
- **The worker proposes a bad skill that looks fine on review and passes fixtures but misbehaves in production.** Mitigations: 72-hour observation window in the Definition of Done; dispatch-health metrics captured for every new skill; atomic fixture+skill diff policy prevents silent contract drift.
- **The worker evolves its own skill or the command-scan skill.** Mitigation: explicit denylist, tested.
- **Concurrent proposals race on the same target.** Mitigation: per-`skill_id` lock at the worker-claim layer.
- **PR branches accumulate.** Mitigation: a daily cron garbage-collects `skill-evolution/` worktrees older than 7 days that have no associated open PR.

**Research Insights (Phase 3):**

- **Lock store uses ControlPlaneDatabase, not a sidecar SQLite file.** `packages/db/control_plane_db.py` already supports a Postgres backend via `DATABASE_URL`. A hard-coded SQLite sidecar silently breaks the moment the operator flips backends. **Move to `packages/db/locks/skill_evolution.py`** (per Architecture review — avoids grab-bag drift in `packages/db/`), using the same `ControlPlaneDatabase` connection pattern as `approval_store.py`, `release_store.py`. (Data-integrity A1/A2)
- **Lock schema (INTEGER timestamps, not TEXT):**
  ```sql
  CREATE TABLE IF NOT EXISTS skill_evolution_locks (
    skill_id          TEXT PRIMARY KEY,
    holder_worker_id  TEXT    NOT NULL,
    holder_token      TEXT    NOT NULL,  -- uuid4 hex per acquire
    acquired_at_us    INTEGER NOT NULL,  -- unix epoch microseconds, numeric compare
    expires_at_us     INTEGER NOT NULL,  -- unix epoch microseconds
    heartbeat_at_us   INTEGER NOT NULL   -- extended by holder every 60s
  );
  CREATE INDEX IF NOT EXISTS idx_skill_evo_locks_expires
    ON skill_evolution_locks(expires_at_us);
  ```
  **Why INTEGER, not TEXT ISO-8601** (kieran review): lexicographic string comparison over ISO-8601 only works if every timestamp is exactly the same length, same tz suffix, and UTC. `2026-04-14T10:00:00Z` vs `2026-04-14T10:00:00.123456+00:00` silently misorders. Epoch-microseconds as `INTEGER` is numeric-compared, DST-immune, tz-immune, and faster.
- **Acquire statement (conditional UPSERT with RETURNING):**
  ```sql
  INSERT INTO skill_evolution_locks
    (skill_id, holder_worker_id, holder_token,
     acquired_at_us, expires_at_us, heartbeat_at_us)
  VALUES
    (:skill_id, :worker_id, :token, :now_us, :expires_us, :now_us)
  ON CONFLICT(skill_id) DO UPDATE SET
    holder_worker_id = excluded.holder_worker_id,
    holder_token     = excluded.holder_token,
    acquired_at_us   = excluded.acquired_at_us,
    expires_at_us    = excluded.expires_at_us,
    heartbeat_at_us  = excluded.heartbeat_at_us
  WHERE skill_evolution_locks.heartbeat_at_us < :stale_threshold_us
  RETURNING holder_token;
  ```
  **Correctness notes** (kieran review):
  - The `WHERE` clause qualifies the `DO UPDATE SET` and **must** reference the table name (`skill_evolution_locks.heartbeat_at_us`), not bare `heartbeat_at_us` — the bare form is ambiguous in UPSERT context.
  - `excluded.col` refers to the new (proposed) row; bare `col` (or `skill_evolution_locks.col`) refers to the existing row.
  - **Use `RETURNING holder_token` + application-side check that the returned token equals the caller's token**. Do NOT trust `cursor.rowcount` — SQLite's rowcount behavior for "conflict + WHERE false → no-op" is inconsistent across versions. If `RETURNING` returns no rows OR a different token, the caller did not acquire the lock.
  - **Single-statement UPSERT is atomic on its own** — `BEGIN IMMEDIATE` is NOT required for acquire. **Release DOES require `BEGIN IMMEDIATE`** because release is read-then-write: `SELECT holder_token ... FOR UPDATE` equivalent, then `DELETE ... WHERE holder_token = :token`.
- **Heartbeat extended every 60 s by the holder**; stale-threshold = 180 s (three missed heartbeats). `now_us = int(time.time() * 1_000_000)` at the call site, wall-clock not monotonic (monotonic doesn't survive process restart, and multi-host is out of scope for this platform).
- **Release contract:**
  ```sql
  DELETE FROM skill_evolution_locks
   WHERE skill_id = :skill_id AND holder_token = :token
   RETURNING skill_id;
  ```
  A single conditional `DELETE` is atomic on its own — SQLite wraps it in an implicit transaction and evaluates the `WHERE` during the write. **No `BEGIN IMMEDIATE` needed** (kieran delta review: the earlier version of this snippet wrapped the DELETE in `BEGIN IMMEDIATE; ... COMMIT;`, which contradicts the acquire-section's own "single-statement UPSERT is atomic" note and uselessly extends lock hold time by one round-trip). Use `RETURNING skill_id` + application-side check — if the result set is empty, the lock was already stolen (clock drift past stale_threshold), and **the caller MUST abandon the worktree and NOT push its branch**.
- **TTL alone is unsafe for stuck-but-alive holders.** The original plan's "Lock TTL matches worker's max task duration" is wrong semantics — a worker hanging past its TTL will have its lock stolen while still holding the worktree. Two workers then race on the same worktree and PR branch. Heartbeat + holder_token is the fix.
- **TTL alone is unsafe for stuck-but-alive holders.** The original plan's "Lock TTL matches worker's max task duration" is wrong semantics — a worker hanging past its TTL will have its lock stolen while still holding the worktree. Two workers then race on the same worktree and PR branch. Heartbeat + holder_token is the fix.
- **Allowlist, not denylist.** Per X10 above: `self_evolvable: false` is the default in the registry schema. Only skills with `self_evolvable: true` can be targeted. This eliminates denylist maintenance. Sensitive skills (`command-scan`, `approval-token-audit`, `skill-self-evolution` itself, `post-run-validation`) inherit false by default; no per-skill configuration needed.
- **Path-pattern denylist still required for non-registry paths.** Config files and CI workflows aren't in the registry, so the allowlist doesn't cover them. Hard-reject any proposal diff touching: `packages/config/policies.yaml`, `packages/policies/command_scan.py`, `packages/config/peer_runtimes.yaml`, `packages/config/runtime_supervisor.yaml`, `.github/workflows/**`, `packages/db/connection.py`, `packages/schemas/**`. Fail with `PolicyViolationCode.CONFIG_MUTATION_REQUIRES_HUMAN`.
- **Regression-fixture gate (Voyager/DSPy pattern).** Every replacement skill must **beat the incumbent on the incumbent's fixture set** before the PR is allowed to open. `check_evolution_allowed` runs both the old validator (from the current canonical) and the new validator (from the proposed diff) against the incumbent fixtures; new must match or exceed old verdict on every fixture. Without this, the loop can propose a worse skill that passes its own freshly-generated fixtures — the classic self-evolution pathology documented in Voyager. Reference: [voyager.minedojo.org](https://voyager.minedojo.org/), [dspy.ai/learn/programming/assertions/](https://dspy.ai/learn/programming/assertions/).
- **Self-evolved skills lock to `target_runtimes: [claude]` on first PR.** Adding `codex` or `acp` requires a separate human-authored PR. This is the Phase 3 ↔ Phase 4 interplay boundary — agent-native review flagged it as currently invisible. Enforce in `check_evolution_allowed` with `PolicyViolationCode.RUNTIME_EXPANSION_REQUIRES_HUMAN`.
- **Hardening `gh pr create`:** (i) hardcode `--base staging` (never `main`), (ii) assert `git symbolic-ref HEAD` starts with `skill-evolution/`, (iii) use a fine-grained PAT scoped to `contents:write` on this one repo with branch protection forbidding force-push to `main`, (iv) `--draft` by default, (v) signed commits via a dedicated machine GPG key (do NOT disable signing with `--no-gpg-sign`), (vi) LLM-generated PR bodies are HTML-escaped and backtick-escaped before posting to prevent markdown injection. (Security C2, N7)
- **Signed proposal inputs.** Inputs from `state/checkpoints/` and `state/logs/` are attacker-writable if an earlier worker is compromised. Require hash-pinned (sha256), signed-by-emitting-worker input snapshots. The worker reads `dispatch_health_reader.read_events(...)` through the typed primitive from X5, not by opening JSONL directly — the reader verifies signatures. Treat checkpoints as untrusted. (Security C1)
- **Self-review pass before `gh pr create`** (Sweep.dev / Devin pattern). A second model call critiques the generated diff and either approves or sends back for revision (bounded at 2 revisions). Devin's public write-ups say the self-review pass is load-bearing — without it, ~60% of agent PRs fail CI on submit. [cognition.ai/blog/dont-build-multi-agents](https://cognition.ai/blog/dont-build-multi-agents)
- **Branch namespace reservation** (all mature systems: Sweep `sweep/`, Copilot `copilot/`, Devin `devin/`). Use `skill-evolution/*` prefix for every proposal branch. Add an `infra/github/auto-close-stale-agent-prs.yml` GitHub Action that auto-closes such PRs after 7 days of no human interaction. Cleanup is then a one-liner.
- **Per-proposal worktree workflow:**
  ```bash
  git config --local extensions.worktreeConfig true  # bootstrap, once
  git worktree add -b skill-evolution/<proposal-id> \
    state/worktrees/skill-evolution/<id>/ origin/main
  git -C state/worktrees/skill-evolution/<id>/ config --worktree \
    user.email "skill-evolution-bot@local"
  # ... apply diff, run reconciliation test, commit ...
  # GC via:
  git worktree remove --force state/worktrees/skill-evolution/<id>/
  ```
  Use `-b` (not `--detach`), root at `origin/main` not current HEAD, and use `git worktree remove --force` (not `prune`) as the primary GC primitive. Wrap `git worktree add` in an `fcntl.flock()` over `state/locks/worktree-add.lock` — `git worktree add` is not atomic against concurrent processes adding different worktrees in the same parent dir.
- **`state/artifacts/skill-evolution/context.md` accumulated memory.** Every proposal reads and appends to this file. Captures "we tried evolving skill X this way last month and it was reverted" across proposals. This is the skill's "Improvement Over Time" flywheel; without it the self-modification layer has no learning mechanism. (Agent-native review)
- **Worker is atomic primitives + `skill.md` orchestration.** `apps/worker-skill-evolution/main.py` is a thin claim loop that exposes primitives (`read_recent_task_outcomes`, `load_canonical_skill`, `stage_diff_to_artifacts`, `run_reconciliation_in_worktree`, `open_evolution_pr`, `complete_task`). The `skills/canonical/skill-self-evolution/skill.md` prompt orchestrates them. Rewriting behavior is editing prose, not Python. (Agent-native review, "workflow-shaped tools" anti-pattern)
- **`SkillEvolutionFrozenError`** analog to `GtmFrozenError` for mid-task freeze. A proposal that takes 20 minutes can be told "stop cleanly and re-queue as BLOCKED" mid-run by touching the kill-switch file. Without this, a freeze only takes effect on the next claim. (Pattern consistency review)
- **`complete_task` completion signal.** Explicit primitive the worker calls to declare the proposal done. Feeds directly into the dispatch-health metrics stream with a structured summary. No heuristic completion detection. (Agent-native review)
- **`propose_skill_evolution(skill_id, rationale)` as agent-callable primitive.** Currently the worker is a queue-consumer only — no agent can *request* a proposal. Expose as an MCP tool so `worker-supervisor`, on noticing repeated failures, can enqueue an evolution task. (Agent-native review parity gap)
- **Proposal sandbox:** generate in a subdirectory with `PYTHONDONTWRITEBYTECODE=1` set and no `__pycache__` escape, so a malicious proposal can't plant `.pyc` time-bombs. (Security N2)
- **Atomicity policy third-file smuggling.** `check_fixture_skill_atomicity` pairs validator edits to fixture edits, but an adversarial proposal can add a `helpers.py` next to `validator.py` that does the dangerous work. Harden: the diff policy denies any new file outside `{skill.md, contract.yaml, validator.py, fixtures/**}` without elevated approval. (Security H4)
- **Document a "trusted-skill tier" as an explicit non-goal** in Alternative Approaches. Future evolution might auto-merge after N≥20 human-reviewed accepted proposals with zero reverts — but that's a separate plan, not this one. Writing it down now prevents ad-hoc relaxation later.
- **Rollback runbook checkpoints:** (1) touch `state/flags/skill_evolution_frozen`, (2) `launchctl kickstart -k` runtime-supervisor, (3) `sqlite3 control_plane.db "DELETE FROM tasks WHERE lane='skill_evolution' AND status='claimed'"`, (4) `mv state/artifacts/skill-evolution/<bad-id>/ state/quarantine/skill-evolution/<bad-id>/` (must be same-filesystem `os.rename`, not `shutil.move`), (5) `gh pr close --delete-branch <bad-pr>`, (6) post-mortem entry in `docs/solutions/integration-issues/`.

---

#### Phase 4 — ACP Protocol Adapter

**Goal:** `runtime-supervisor` can dispatch a canonical skill to the local Hermes instance over ACP JSON-RPC 2.0/stdio, behind a feature flag, with a negative contract test guarding the wire format.

**Preconditions:** Phase 0 shipped (target_runtimes module + softened loader). Phase 2 findings recorded. Phase 3 has pressure-tested the canonical skill schema with at least one real self-evolved skill.

**Deliverables:**

- `skills/adapters/acp/` — new directory. README documenting the adapter shape: a thin markdown file per skill with frontmatter `canonical_source:` + `acp_session_prompt_template:`, mirroring the `adapters/claude/` convention. **Note:** ACP has no "skill invocation" method — skill dispatch is encoded as a `session/prompt` call with a structured `TextContent` block, so the adapter file's job is to document how the canonical skill's inputs translate to the prompt content, not to render a custom JSON-RPC payload.
- `packages/tools/acp/client.py` — new. Wraps the `agent-client-protocol` Python SDK to dispatch a canonical skill to a peer runtime. **Does NOT contain a wire-format renderer** — the SDK owns framing. Handles peer lifecycle: starts the peer if not running (spawn-once, keep-alive per the Research Insights below), applies a 30-second request timeout, reaps on timeout or crash, **quarantines after 1 crash** (not 3 — the original "3-attempt retry" conflates timeouts with crashes; crashes are quarantined immediately per the Security review). Writes peer state to `state/handshake/acp-peers/<peer-id>.json`. See Research Insights for the client code sketch (marked `# VERIFY:` pending the ACP SDK import spike).
- ~~`packages/tools/acp/renderer.py`~~ — **DROPPED.** The "render skill as JSON-RPC" idea was a misread of the protocol; the ACP Python SDK owns wire-format rendering. See Research Insights.
- `packages/schemas/peer_runtime.py` — new. `PeerTransport(str, Enum)` with member `STDIO = "stdio"` only (`unix_socket` deferred until a second peer exists — YAGNI per simplicity review). `PeerRuntime` frozen dataclass: `{id, runtime_slug, transport: PeerTransport, command, args, working_dir, healthcheck}`. Registered peers live in `packages/config/peer_runtimes.yaml`.
- `packages/tools/skills/target_runtimes.py` — add `acp` to the literal set (the module was created in Phase 0 specifically to avoid reopening `loader.py` for this).
- `skills/registry.yaml` — add `target_runtimes: [claude, codex, acp]` where the skill supports it; leave others at `[claude, codex]`.
- `apps/runtime-supervisor/dispatch_router.py` (post-X4 split) — add the ACP branch to the existing runtime-slug resolution. Because routing *policy* lives in `packages/policies/provider_resolution.py`, the router itself only grows by a few lines: "ask the policy which provider to use, then `providers.resolve(slug).execute(task)`." The `acp_dispatch_enabled` feature-flag check lives in the **policy**, not the router, keeping the router under its 50-LOC budget. **No changes to `main.py` or `supervisor.py` in Phase 4.**
- `packages/policies/acp_dispatch.py` — new. `assert_acp_peer_allowed(peer_id: str, skill_id: str) -> None`. Fail-closed policy — the platform only dispatches to peers explicitly allow-listed in `packages/config/peer_runtimes.yaml:allowed_skills`.
- `tests/python/unit/test_acp_client.py` — happy path (mock peer stream responds with valid `PromptResponse`), boundary (empty prompt content), adversarial (peer sends malformed JSON-RPC).
- **`tests/python/unit/test_acp_contract_negative.py`** — **the mandatory negative test**. Sends a deliberately malformed ACP request to a mock peer and asserts the peer's error response is captured, surfaced as a `PeerRuntimeError`, and the task is marked `FAILED` rather than silently `COMPLETED`. This is the guardrail against the multi-tool orchestration anti-pattern.
- `tests/python/integration/test_acp_dispatch_hermes_local.py` — end-to-end dispatch to the real Hermes instance from Phase 2. Marked `@pytest.mark.integration` so CI can opt in.

**Definition of Done:**
- `acp_dispatch_enabled: true` in a local config file results in one canonical skill being executed by the local Hermes instance, end-to-end.
- Negative contract test passes.
- Feature flag default is `false` in the repo; only the local Mac flips it.
- Rollback is one config flip — no code revert required.

**Rollback:** Set `acp_dispatch_enabled: false`. The supervisor immediately stops routing to ACP. Any in-flight ACP tasks are allowed to finish or time out (30s max).

**Risks:**
- **Peer crashes mid-dispatch leave the queue in an inconsistent state.** Mitigation: explicit timeout + reap + requeue with attempt counter in the dispatcher.
- **ACP protocol drift between Hermes versions.** Mitigation: negative contract test catches wire-format regressions; Hermes version pinned in `packages/config/peer_runtimes.yaml:hermes_local.version`.
- **Feature flag forgotten and accidentally enabled in prod.** Mitigation: default `false`, flag read at task-claim time (not startup), assertion test in CI that the repo's committed value is `false`.

**Research Insights (Phase 4):**

- **Use the `agent-client-protocol` Python SDK; do NOT hand-roll JSON-RPC framing.** `pip install agent-client-protocol` gives you server and client base classes. Hermes v0.7.0 already ships `acp_adapter/server.py` with `HermesACPAgent` subclassing the SDK's `Agent` base. The Phase 4 work is writing an **ACP client** in `packages/tools/acp/client.py`.
- **⚠ PRECONDITION — SDK import spike before any code against it** (kieran review). The exact API names I wrote during deepening (`spawn_agent_process`, `Client(proc)`, `TextContentBlock`, `stopReason="error"`) are a **best guess** based on the ACP spec shape — I did not verify them against the actual published PyPI package. Multiple shapes likely differ:
  - The SDK almost certainly uses `ClientSideConnection(agent_factory, stream_to_agent, stream_from_agent)` taking **already-opened asyncio streams** that the caller obtained via `asyncio.create_subprocess_exec(...)` and `proc.stdin` / `proc.stdout`. The SDK does not own subprocess spawning.
  - `TextContentBlock` is probably `TextContent` (discriminated-union member with `type: "text"`, `text: str`), not a block-named class.
  - `PromptResponse.stop_reason` values are `"end_turn" | "max_tokens" | "refusal" | "cancelled"`. There is **no `"error"` variant** — errors surface as JSON-RPC error responses raising a typed exception, not as a stop_reason. Wrap `client.prompt()` in `try/except` and map `stopReason="refusal"` or `"cancelled"` to an error result.
  - `initialize(protocolVersion=...)` — parameter is likely camelCase over the wire; Python SDK may accept snake_case. The current ACP spec version is `"0.1.0"` (string) in some SDKs, not integer `1`. Do not hardcode.
  - **Action:** add a Phase 2 subtask — **"ACP SDK import spike"**: `pip install agent-client-protocol`, run `python -c "import acp; help(acp)"`, capture the output into `docs/research/2026-04-hermes-spike/acp-sdk-api.md`, and confirm the exact class names, method signatures, and handshake shape. Only after that note is in place does Phase 4 write code.
- **Sketch (VERIFY before implementing — API names unverified):**
  ```python
  # packages/tools/acp/client.py (SKETCH — VERIFY API names in Phase 2 spike)
  # ⚠ The symbols below are likely wrong; resolve via SDK introspection first.
  import asyncio, json
  from agent_client_protocol import ClientSideConnection, TextContent  # VERIFY
  
  async def dispatch_skill_via_acp(
      peer: PeerRuntime, skill_id: str, payload: Mapping[str, Any]
  ) -> AcpResult:
      proc = await asyncio.create_subprocess_exec(
          peer.command, *peer.args,
          cwd=peer.working_dir,
          stdin=asyncio.subprocess.PIPE,
          stdout=asyncio.subprocess.PIPE,
          stderr=asyncio.subprocess.PIPE,
          env=_clean_env(peer),                    # Security C3: whitelist env
      )
      try:
          conn = ClientSideConnection(              # VERIFY class name
              agent_factory=None,                   # no reverse calls yet
              stream_to_agent=proc.stdin,
              stream_from_agent=proc.stdout,
          )
          await conn.initialize(...)                # VERIFY method + params
          session_id = await conn.new_session(cwd=peer.working_dir, mcp_servers=[])
          response = await conn.prompt(
              session_id,
              content=[TextContent(                 # VERIFY class name
                  type="text",
                  text=json.dumps(
                      {"skill": skill_id, "payload": dict(payload)},
                      ensure_ascii=False,           # preserve non-ASCII exactly
                      separators=(",", ":"),
                  ),
              )],
          )
          return AcpResult.from_prompt_response(response)  # maps stop_reason
      finally:
          # Always clean up the peer process on exception paths.
          # Close stdin FIRST (sends EOF → Hermes exits cleanly on its own).
          # Only escalate to terminate/kill if Hermes ignores EOF.
          if proc.returncode is None:
              try:
                  if proc.stdin is not None and not proc.stdin.is_closing():
                      proc.stdin.close()
                      await proc.stdin.wait_closed()
              except (BrokenPipeError, ConnectionResetError):
                  pass
              try:
                  await asyncio.wait_for(proc.wait(), timeout=1.0)
              except asyncio.TimeoutError:
                  proc.terminate()
                  try:
                      await asyncio.wait_for(proc.wait(), timeout=5.0)
                  except asyncio.TimeoutError:
                      proc.kill()
                      await proc.wait()
  ```
- **`ensure_ascii=False`** is deliberate — the default `json.dumps` produces `\u00e9` instead of `é`, which Hermes may handle differently and breaks round-trip fidelity. Force UTF-8 throughput with `ensure_ascii=False, separators=(",", ":")`.
- **Process cleanup in `finally`** is mandatory — the original sketch leaked subprocess handles on any exception between spawn and prompt completion. **Close `proc.stdin` before `terminate()`** — `terminate()` can arrive before the client has flushed its last JSON-RPC write, producing SIGPIPE in Hermes and a confusing stderr trace. Sending EOF via stdin close lets Hermes shut down cleanly on its own.
- **`_clean_env(peer: PeerRuntime) -> dict[str, str]`** is referenced in the sketch above. **To be defined in `packages/tools/acp/env.py`** (new file, Phase 4 deliverable): whitelist-based env-var passthrough derived from `peer.required_secrets` in `packages/config/peer_runtimes.yaml`. Default allowed: `PATH`, `HOME`, `USER`, `LANG`, `LC_ALL`, `TZ`. Nothing else. Secrets are fetched from macOS Keychain by handle at spawn time and injected into the returned dict.
- **Drop `packages/tools/acp/renderer.py` as a separate concept.** The "render skill as JSON-RPC" idea was from a misread of the protocol. Replace with `packages/tools/acp/client.py` that wraps the ACP SDK (after the import spike verifies the exact API).
- **Peer lifecycle: spawn-once, keep-alive.** Hermes cold start from `uv run` is 1.5–4 seconds. Per-dispatch spawn at 20 tasks/week is tolerable in the prototype (~60 s/week wasted) but becomes a 10× latency regression vs Claude/Codex once volume rises. Required:
  - Peer is spawned **once at `runtime-supervisor` startup** (or on first ACP-targeted task) and kept alive via persistent stdio pipe.
  - `PeerRuntime` frozen dataclass tracks `pid`, `stdin_fd`, `stdout_fd`, `last_used_at`, `healthcheck_status`, `version_id`.
  - Per-peer `asyncio.Lock` serializes stdio request/response framing (JSON-RPC ids are useful but do not help if stdout bytes interleave across concurrent requests).
  - **Idle-reap policy:** reap peer after 30 min idle; respawn on demand. Prevents long-running supervisors from leaking peer processes.
  - On `runtime-supervisor` shutdown: reap all peers via signal cascade (SIGTERM → 5 s grace → SIGKILL).
- **Peer state lives under `state/handshake/acp-peers/<peer-id>.json`** (not `state/runtime/acp-peers/` — `state/runtime/` doesn't exist; `state/handshake/` already exists and is semantically the right home for peer handshake/registration state). Update `state/README.md` to document the `acp-peers/` convention.
- **Poison-pill quarantine after 1 crash, not 3.** The original "requeue with attempt counter, max 3" conflates transient timeouts with crash-class errors. A deterministically crashing payload fails three workers before quarantining — that's a DoS on the queue. Revision:
  - **Timeouts (transient):** retry ≤ 3 times with exponential backoff (5 s, 30 s, 2 min), then quarantine.
  - **Peer crashes (crash-class):** quarantine immediately (attempt 1). Move payload to `state/quarantine/acp-poison/<task-id>/` and alert via `dispatch_health.record("acp_poison", task_id=...)`.
  - Distinguishing: if the peer exits with non-zero before any valid JSON-RPC response was received, it's crash-class.
- **JSON-RPC parser DoS hardening.** Python's stdlib `json` has no depth limit and will recurse until the Python stack limit on a crafted payload. Required:
  - Length-cap stdio frames at 1 MiB (reject longer frames as protocol violation).
  - Reject non-UTF-8 early.
  - **Prefer LSP-style `Content-Length` framing over newline-delimited** — actually NO: verified that ACP Python SDK uses line-delimited JSON, so use that for compatibility. The SDK handles framing; we don't reinvent it.
  - Add explicit `sys.setrecursionlimit()` guard or bounded-depth decoder if a crafted response hangs the client. Test with a 1000-deep nested JSON response.
- **macOS sandbox for Hermes peer** (Security C3). `sandbox-exec` is deprecated but remains the only practical primitive. Provide a `.sb` profile at `infra/sandbox/hermes.sb` that:
  - Denies network except to an allowlist (Anthropic API, OpenAI API if needed).
  - Denies write access to `skills/canonical/`, `packages/`, `apps/`.
  - Allows read+write to `state/handshake/acp-peers/` and Hermes's own `~/.hermes/` dir.
  - Passes a clean env: no `GITHUB_TOKEN`, no `ANTHROPIC_API_KEY` unless the peer explicitly needs it (declared in `packages/config/peer_runtimes.yaml:hermes_local.required_secrets`).
  - Fallback for when `sandbox-exec` is finally removed: dedicated launchd user with its own home, loaded via a helper plist.
- **Peer config secrets at rest** (Security H1). `packages/config/peer_runtimes.yaml` must never contain raw tokens. Reference by macOS Keychain handle: `auth_token_keychain_item: "ai-company-os.hermes.anthropic"`. The dispatcher calls `security find-generic-password` at peer-spawn time to fetch the actual token. `.gitignore` excludes any `*.secret.yaml` sibling; pre-commit hook scans for token-like strings in the peer config.
- **Resource limits on peer:** `RLIMIT_AS` (virtual memory), `RLIMIT_CPU` (CPU seconds), `RLIMIT_NOFILE` (file descriptors). macOS supports all three via `setrlimit` before `execve`. Set before `spawn_agent_process`. (Security N6)
- **Negative contract test becomes `test_acp_contract_negative.py`** using the SDK's own error types (`acp.PromptResponse.stop_reason == "error"` handling) rather than hand-parsing JSON-RPC. Plus a wire-format fuzzer using `hypothesis` against the dispatcher (strategy: generate random valid-but-unexpected JSON-RPC messages, assert the client either processes cleanly or raises a typed `AcpProtocolError`, never crashes). (Security N1)
- **`verify_peer_contract(peer_id)` as agent-callable primitive.** The negative contract test is currently CI-only. Expose it as a tool callable from the dispatch loop when a peer comes up after restart; called in the peer-lifecycle health check. ACP drifts between Hermes versions (Hermes #5502 regression precedent); the agent should be able to re-run the contract check on the fly, not wait for CI. (Agent-native review)
- **CRUD completeness on peers.** Add `list_peer_runtimes()`, `get_peer_health(peer_id)`, `register_peer_runtime(spec)`, `retire_peer_runtime(peer_id)` as agent-callable primitives in `packages/tools/primitives/peer_runtimes.py` (per X4a subpackage convention). The human edits `peer_runtimes.yaml` and restarts; the agent uses the tools. Both paths write through the same `packages/policies/acp_dispatch.py` allow-list gate. (Agent-native review)
- **Feature-flag CI assertion.** `tests/python/unit/test_config_invariants.py` asserts that `packages/config/runtime_supervisor.yaml:acp_dispatch_enabled` is `false` in every committed revision. A bad PR that accidentally flips it fails CI. Same pattern applied to Phase 5's `command_scan.enforcement`. (Security N5)
- **`state/handshake/acp-peers/<peer-id>.json` race hardening.** Two tasks racing on the same peer start both write the file; last writer wins. Fix: acquire the same per-`peer_id` lock via `packages/db/locks/` (reuse Phase 3 lock infrastructure for peers as well), or hold an advisory `fcntl.flock()` on the peer state file during transitions. (Data-integrity B5)

---

#### Phase 5 — Command-Scan Policy

**Goal:** Every shell command executed by a worker goes through a policy-wrapped validator skill before execution, with an audit log rotation so autonomous dispatch doesn't fill the disk.

**Preconditions:** Phase 1 shipped (the validator skill can be written and loaded). Phase 0 shipped (loader is robust).

**Deliverables:**

- `skills/canonical/command-scan/` — new validator-kind canonical skill (per-skill-dir layout). `skill.md`, `contract.yaml`, `validator.py`, `fixtures/{happy_path,boundary_long_pipeline,adversarial_destructive_rm,adversarial_curl_bash,adversarial_secret_exfil}.yaml`. The validator parses the command, returns `verdict: allow | deny | require_approval`, and attaches reasons.
- `packages/policies/command_scan.py` — new. Mirrors `packages/policies/release_readiness.py:31-60` composition pattern exactly. Exposes `assert_command_allowed(command: str, context: CommandContext) -> None`. **Import-safe:** module-level imports are side-effect-free; the validator is loaded lazily on first call so that a Phase-0 registry regression cannot take down worktree creation at import time.
- `packages/tools/codex_tools/cli.py` — wire `assert_command_allowed()` in front of every shell invocation. Must call it **before** the command runs, not in parallel.
- `packages/tools/worktrees.py` — same wiring. Special-cased so the initial `git worktree add` is allow-listed (otherwise we can't bootstrap a worktree to scan commands inside it).
- `state/logs/command-scan/` — audit log directory. Format: `YYYY-MM-DD.jsonl`, one entry per scan. Rotated daily via a cron entry in `infra/launchd/`. Retention: 30 days, then archived to `state/archives/command-scan/`.
- `scripts/command-scan-retention.py` — daily rotation script.
- `tests/python/unit/test_command_scan_policy.py` — happy, boundary, all three adversarial cases.
- `tests/python/integration/test_command_scan_worker_integration.py` — enqueue a worker task, assert the policy is called before the shell command runs, assert a denied command produces `PolicyViolation("command_scan_denied")` and the task ends `FAILED`.

**Definition of Done:**
- Every shell call in `packages/tools/codex_tools/` and `packages/tools/worktrees.py` is preceded by `assert_command_allowed()`.
- Adversarial fixtures are rejected by the validator.
- `state/logs/command-scan/` grows daily, rotates nightly, archives after 30 days.
- Load-order test asserts `from packages.policies.command_scan import assert_command_allowed` has no side effects on import.

**Rollback:** Set `command_scan.enforcement: advisory` in `packages/config/policies.yaml` — the policy module logs violations but does not raise `PolicyViolation`. Full rollback: revert the wiring in `codex_tools/cli.py` and `worktrees.py`.

**Risks:**
- **False positives block legitimate commands.** Mitigation: `advisory` mode first, graduate to enforce after 72 hours of clean audit.
- **The validator itself shells out.** Mitigation: the validator is pure Python pattern-matching and AST parsing, no subprocess calls.
- **Import-time side effects.** Mitigation: explicit load-order test.

**Research Insights (Phase 5):**

- **Use `bashlex`, not regex.** Regex-based denylists for `rm -rf`, `curl … | bash`, `$(…)`, `eval`, backtick expansion, here-docs, and IFS tricks (`rm$IFS-rf /`) will be bypassed within days. Bind `validator.py` to `bashlex` (or `shlex` plus an explicit grammar layer); commands that fail to parse are denied. Reference: Claude Code's glob-based allowlist is the minimum bar; Semgrep's `p/bash` ruleset is the reference for AST-level scanning in production. [semgrep.dev/p/bash](https://semgrep.dev/p/bash), [shellcheck.net](https://www.shellcheck.net/)
- **Scan the `(argv, env)` tuple at the `subprocess.run` site, not the top-level command string** (Security C6). Attacker-controlled fields flow through env vars (`PATH`, `LD_PRELOAD`, `GIT_SSH_COMMAND`, `PAGER`, `EDITOR`, `GIT_EDITOR`) and later-stage subprocess spawns inside the child. Concretely:
  - `assert_command_allowed(argv: list[str], env: dict[str, str], context: CommandContext) -> None`
  - Callers pass the full argv list and the env they're about to hand `subprocess.run`, not a shell string.
  - **Forbid `shell=True`** in policy. Add a `ruff` rule `S602` (subprocess-popen-with-shell-equals-true) that fails CI on new call sites. Audit existing call sites and refactor.
  - Drop to a whitelisted env: only `PATH`, `HOME`, `USER`, `LANG`, and explicitly-declared task-specific vars pass through.
- **Warmup validator import at worker boot.** First `load_validator("command-scan")` call is 15–40 ms Python import + 50–150 ms if bashlex is imported transitively. This cost lands on the first shell command after worker startup — usually `git worktree add`, which is allow-listed per the original plan. Still, front-load it: call `assert_command_allowed(["true"], {}, CommandContext.bootstrap())` at `worker.startup()` as a no-op warmup so the first real command doesn't eat the tail spike.
- **Audit log must log allowed commands too, not just denied** (Devin pattern). Every `assert_command_allowed()` call writes one JSONL line: `{ts, worker_id, task_id, verdict, argv_hash, reason}`. Post-hoc audit is the point. Denied commands write the full argv (with secrets redacted); allowed commands write the argv hash only (for volume reasons). Reference: Aider, Devin, Cursor all converged on parse+allowlist+audit-log, not regex matching.
- **Secrets redaction in audit log** (Security H5). Shell commands carry tokens in argv: `curl -H "Authorization: Bearer …"`, `gh auth login --with-token`, `AWS_SECRET_ACCESS_KEY=… aws …`. Storing full argv for 30 days is a secrets-at-rest exposure. Required:
  - Known secret-bearing argv positions redacted before write: `Authorization: Bearer <REDACTED>`, `--token <REDACTED>`, any arg matching `^(sk|ghp|pk|xoxb)_[a-zA-Z0-9_]{10,}` → `<REDACTED_SECRET>`.
  - `chmod 600` on `state/logs/command-scan/` at directory creation.
  - Unit test `test_command_scan_redaction.py` with known secret shapes from Anthropic (`sk-ant-`), OpenAI (`sk-`), GitHub (`ghp_`, `gho_`), AWS (`AKIA`), Stripe (`pk_live_`, `sk_live_`).
- **Wire scanner into `worker-skill-evolution`'s own shell calls.** Phase 3 worker shells out to `git worktree add`, `git commit`, `gh pr create` — these should pass through `assert_command_allowed()` too, not bypass it. Otherwise the most dangerous shell caller in the platform is the only one without a scanner. (Security N4, Agent-native review)
- **Advisory mode is config, and config is CI-asserted.** `packages/config/policies.yaml:command_scan.enforcement` must be `advisory` OR `enforce`. CI asserts committed value is `enforce` before any merge to `main`. Ship `advisory` only on the local Mac via a per-host override file at `~/.ai-company-os/policies.override.yaml` that's gitignored. Prevents a bad PR silently flipping enforcement. (Security N5)
- **Load-order audit.** `packages/tools/worktrees.py` runs `git worktree add` during setup, before the policy layer is guaranteed initialized. The `command_scan` policy module must be importable without side effects and must not fail on registry-load failure (it's imported via `packages/tools/worktrees.py:import`). Add `test_command_scan_import_safety.py` that imports the module with a deliberately broken registry and asserts no exception at import time. The validator is loaded lazily on first call, not at module load.
- **Policies-as-code, policy-data-as-YAML** (Best-practices research). Extract the allow/deny pattern sets, allowed-command-prefixes, and redaction regex list from `validator.py` into `skills/canonical/command-scan/patterns.yaml` — so humans can review and edit patterns without a Python PR. Validator reads the YAML at first call (and caches it). This matches the LangGraph 2026 consensus: code policies, declarative policy data. [langchain-ai.github.io/langgraph](https://langchain-ai.github.io/langgraph/)
- **Log retention without archive ceremony** (Simplicity). Drop `scripts/command-scan-retention.py` as a separate cron + archive directory + heartbeat file. Use 30-day rotation with hard delete — `state/logs/command-scan/` caps at 30 files, oldest dropped on new day. Heartbeat becomes a single `state/health/dispatch-health-summary.json` shared across all cron jobs (see X5), not a per-job file.
- **`require_approval` verdict becomes productive.** Today it's a dead code path — no agent path to satisfy it. Add `request_command_approval(argv, context, rationale) -> ApprovalToken` and `submit_approval_token(token)` as module-level functions in `packages/tools/primitives/approvals.py` (per X4a subpackage convention — single `.py` file, NOT a subdirectory). When the scanner returns `require_approval`, the worker calls `request_command_approval` and blocks the task as `BLOCKED_AWAITING_APPROVAL`. A human (or a higher-privileged agent in the future) calls `submit_approval_token` to release it. The token is HMAC-signed, single-use, TTL-bounded. This also sets up the plumbing for Phase 3's evolved-skill approvals. (Agent-native review)

---

#### Phase 6 — Provider Overlay Registry

**Goal:** Adding a new model provider is a single registry entry, not a sibling directory under `packages/tools/`.

**Preconditions:** Phase 4 shipped (ACP gives us the first real cross-runtime dispatch pattern, which the overlay needs to reason about).

**Deliverables:**

- `packages/tools/providers/__init__.py` — new. Exports `ProviderRegistry`.
- `packages/tools/providers/registry.py` — new. `ProviderRegistry` class with slug→`Provider` class map. Methods: `register(slug, provider_cls)`, `resolve(slug) -> Provider`, `list_available() -> list[str]`.
- `packages/tools/providers/base.py` — new. `Provider` protocol / ABC defining the contract: `execute(task_payload) -> TaskResult`, `health_check() -> ProviderHealth`, `capabilities() -> ProviderCapabilities`.
- `packages/tools/providers/claude.py` — wraps existing `packages/tools/claude_tools/` behind the Provider protocol. Registers `slug="claude"`.
- `packages/tools/providers/codex.py` — wraps existing `packages/tools/codex_tools/` behind the Provider protocol. Registers `slug="codex"`.
- `packages/tools/providers/acp.py` — wraps the Phase 4 ACP dispatcher. Registers `slug="acp"`.
- `packages/tools/providers/placeholders.py` — registers no-op placeholders for `ollama`, `hermes-native`, `gemini`, `xai`. These raise `ProviderNotImplemented` on `execute()` but appear in `list_available()` so the UI/CLI can show them as "known but not wired."
- `packages/policies/provider_resolution.py` + `apps/runtime-supervisor/dispatch_router.py` (post-X4 split) — the policy reads `TaskPacket.provider_hint`, falls back to the skill's `target_runtimes`, and returns a slug. The router calls `providers.resolve(slug)` and invokes `execute(task)`. **No `if/elif` on runtime slug in the router itself** — the overlay is the point. `dispatch_router.py` stays under its 50-LOC budget.
- **Decision on 6.4 (TaskPacket.provider_hint) — COMMIT, not optional.** Reasoning: without it, ACP dispatch targets remain code-driven (hard-coded in `runtime-supervisor`) instead of data-driven. That defeats the point of the overlay. Spec: `provider_hint: str | None = None` added to `TaskPacket` (`packages/schemas/task_packet.py:66-77`), with a hint-resolution policy in `packages/policies/provider_resolution.py` that picks a provider when hint is None based on skill `target_runtimes`.
- `packages/policies/provider_resolution.py` — new. Deterministic provider selection. Respects `provider_hint` when set; falls back to first available `target_runtime` from the skill spec; fails closed if no provider is available.
- `tests/python/unit/test_provider_registry.py` — registration, resolution, capability queries, placeholder behavior.
- `tests/python/unit/test_provider_resolution_policy.py` — hint priority, fallback order, no-provider failure.

**Definition of Done:**
- All existing Claude and Codex tool invocations route through `ProviderRegistry.resolve()`.
- `TaskPacket.provider_hint` field exists, tested, honored by the resolution policy.
- Adding a new provider placeholder is a single file touching `packages/tools/providers/`, not a new directory.
- `list_available()` shows both wired and placeholder providers.

**Rollback:** The Provider wrappers delegate to existing code unchanged. Deleting the new providers/ directory and reverting the two call-site rewrites in `runtime-supervisor` reverts cleanly.

**Risks:**
- **Indirection tax on existing invocations.** Mitigation: the wrappers are thin delegators; benchmark shows <1ms overhead per call (measured in the integration test).
- **Circular imports between `providers/acp.py` and `packages/tools/acp/dispatcher.py`.** Mitigation: providers/acp.py imports the dispatcher lazily inside `execute()`.

**Research Insights (Phase 6):**

- **Evaluate LiteLLM as the underlying provider adapter layer.** [LiteLLM](https://github.com/BerriAI/litellm) already ships 100+ provider shims behind a single OpenAI-compatible interface; it's production-battle-tested at scale (used by Anthropic Console, Replit, thousands of deployments). Three real reasons not to use it as-is in a local-first context: (a) ~50 MB dep tree pulls `openai`, `anthropic`, etc. you may already have installed separately, (b) proxy mode adds a process boundary you don't want on a single-Mac deployment, (c) **fail-open defaults**: LiteLLM's default fallback-to-another-provider-on-error can silently mask policy violations. Decision: **wrap LiteLLM inside `packages/tools/providers/registry.py` with `fallbacks=[]` and `num_retries=0` to force fail-closed semantics.** This gives 100+ providers without the fail-open footgun. The slug→class map becomes a slug→LiteLLM-model-string map; ~5 lines of code instead of a class hierarchy per provider. If LiteLLM's dep tree is too heavy, write thin wrappers around the existing `packages/tools/claude_tools/` and `packages/tools/codex_tools/` as originally specced — both paths still land the same Protocol shape.
- **`Provider` is a `typing.Protocol`, NOT `@runtime_checkable`.** The earlier draft used `@runtime_checkable` with an instance attribute (`slug: str`), which per PEP 544 makes `isinstance(x, Provider)` check **only that `slug`, `execute`, `health_check`, and `capabilities` are present as attributes** — it does NOT check that `slug` is a `str`, that `execute` is `async`, or that signatures match. Any object with four matching attribute names passes. That's worse than useless — it's a false sense of security. Drop `@runtime_checkable` entirely; get full mypy coverage without it. For runtime validation, call an explicit `_assert_provider()` at registration time:
  ```python
  # packages/tools/providers/base.py
  from __future__ import annotations
  from typing import Protocol, TYPE_CHECKING
  from collections.abc import Mapping
  
  if TYPE_CHECKING:
      from packages.schemas.task_result import TaskResult
  
  class Provider(Protocol):
      @property
      def slug(self) -> str: ...
      async def execute(self, task_payload: Mapping[str, object]) -> "TaskResult": ...
      def health_check(self) -> "ProviderHealth": ...
      def capabilities(self) -> "ProviderCapabilities": ...
  
  def _assert_provider(obj: object) -> Provider:
      """Runtime validator called by the registry at registration time.
      
      Raises TypeError, NOT assert — asserts are stripped under `python -O`
      and would let a broken Provider ship silently. Split the slug check
      into two messages so "missing" and "wrong type" produce distinct errors.
      """
      import inspect
      if not hasattr(obj, "slug"):
          raise TypeError(f"provider {obj!r} missing slug attribute")
      if not isinstance(obj.slug, str):
          raise TypeError(
              f"provider {obj!r}.slug must be str, got {type(obj.slug).__name__}"
          )
      if not inspect.iscoroutinefunction(obj.execute):
          raise TypeError(f"provider {obj!r}.execute must be async def")
      return obj  # type: ignore[return-value]
  ```
  Key Python corrections (kieran review):
  - **`slug` is a `@property`, not an instance attribute.** Attributes on Protocols are invariant; properties are covariant on return type. Implementers can hardcode `return "claude"` without touching `__init__`.
  - **`task_payload: Mapping[str, object]`**, not `dict`. Read-only input, structurally typed, no 2021-era `dict` idiom.
  - **`from __future__ import annotations`** gives forward refs for free; drop the string quotes on `"TaskResult"`.
  - **No `@runtime_checkable`.** Call `_assert_provider()` at registration in `providers/__init__.py` — that's the real guard.
- **`ProviderRegistry` always takes the lock for the lazy ACP branch** — the earlier draft used double-checked locking, which is broken on free-threaded Python 3.13+ (PEP 703 `--disable-gil`) because dict write-publishes lack release-acquire barriers. Taking the lock unconditionally on the cold path is ~100 ns overhead that happens once per process lifetime. Correct on both GIL and free-threaded:
  ```python
  # packages/tools/providers/__init__.py
  from __future__ import annotations
  import threading
  from .base import Provider, _assert_provider
  from .claude import ClaudeProvider
  from .codex import CodexProvider
  
  _REGISTRY: dict[str, Provider] = {
      "claude": _assert_provider(ClaudeProvider()),
      "codex":  _assert_provider(CodexProvider()),
  }
  _LOCK = threading.Lock()
  _KNOWN_SLUGS = frozenset({"claude", "codex", "acp"})
  
  def resolve(slug: str) -> Provider:
      # Hot path: dict read. CPython's GIL makes `in` atomic; on
      # free-threaded Python 3.13+, dict reads are per-object-locked.
      if slug in _REGISTRY:
          return _REGISTRY[slug]
      # Cold path: lazy construction of ACP (spawns Hermes subprocess).
      # Always take the lock — do NOT double-check unlocked, which is
      # unsafe under free-threaded Python.
      if slug == "acp":
          with _LOCK:
              if "acp" not in _REGISTRY:  # re-check under lock
                  from .acp import AcpProvider  # lazy to break cycles
                  _REGISTRY["acp"] = _assert_provider(AcpProvider())
          return _REGISTRY["acp"]
      raise KeyError(f"unknown provider slug: {slug}")
  
  def list_available() -> list[str]:
      return sorted(set(_REGISTRY.keys()) | _KNOWN_SLUGS)
  ```
  Key Python corrections (kieran + delta review):
  - **Always lock for the cold `"acp"` path** — not double-checked locking. Double-check was broken under free-threaded Python 3.13+ and saved only one lock acquisition on the cold path (which happens once per process lifetime). The check-then-lock-then-recheck shape is still inside the `"acp"` branch so uncontended hits on claude/codex stay lock-free, but the second check under the lock is the single authoritative read.
  - **`list_available()` uses `set` union**, not `sorted(...) + ["acp"]`. The original returned `"acp"` twice after the first `resolve("acp")` call (once from `_REGISTRY.keys()`, once from the concatenation).
  - **`_KNOWN_SLUGS` is a frozenset constant**, not a hardcoded append — makes the set of "known but lazy" providers obvious and grep-able.
  - **`resolve()` raises `KeyError` on unknown slug**, doesn't fall through to `_REGISTRY[slug]` with a less-informative KeyError from the dict itself.
  
  Phase 6 integration test asserts `resolve("claude")` returns the same instance on repeated calls AND that `list_available()` returns `["acp", "claude", "codex"]` (exactly, no duplicates) both before and after `resolve("acp")` has been called.
- **Drop `packages/tools/providers/placeholders.py` entirely.** The "ollama / hermes-native / gemini / xai" placeholder rows raise `ProviderNotImplemented` and serve no automated consumer. Add a provider when it has a real implementation. `list_available()` returns only wired providers.
- **Commit to `TaskPacket.provider_hint` — it's the only path to data-driven dispatch.** Without it, `runtime-supervisor` keeps routing logic in code, and an agent cannot compose "route these three content-factory tasks to Hermes" from primitives. Simplicity reviewer wanted to drop it; agent-native review overrides: keep.
  ```python
  # packages/schemas/task_packet.py
  @dataclass(frozen=True)
  class TaskPacket:
      # ... existing fields ...
      provider_hint: str | None = None  # resolves via provider_resolution policy
  ```
  `packages/policies/provider_resolution.py` honors hint when set; falls back to first available `target_runtime` from the skill spec; fails closed if no provider is available. Replaces the dispatch branch in `runtime-supervisor`.
- **Performance budget: `< 50 μs` median, not `< 1 ms`.** The original plan's `<1ms` claim had 500× headroom and would hide a 100× regression. Concrete budgets per X7:
  - Protocol dispatch (warm): < 2 μs median
  - `resolve(slug)` dict hit: < 50 ns
  - First-call lazy import (`providers/acp.py`): < 20 ms one-shot
  - Enforce via `tests/python/perf/test_provider_overlay_overhead.py` with `pytest-benchmark`, `min_rounds=1000`, `warmup=True`.
- **MCP server lane alongside ACP — recognize they're complementary, not competing.** The canonical skill system is *exactly* the kind of bounded procedure MCP was designed to expose. ACP lets Hermes *drive* our platform; MCP lets Hermes *call* our skills as tools. Different layers. **Not in scope for Phase 6**, but document as a future consideration: `packages/tools/mcp_server/` wrapping `skills/registry.yaml` as an MCP server. Filed under "Future Considerations" below.
- **Freeze the registry after startup.** `ProviderRegistry.register()` (if kept) must reject duplicate slugs and be a no-op after `runtime-supervisor.start()` completes. Prevents runtime provider swap via a later import. (Security N8)

---

### Cross-cutting — Dispatch Health Observability (all phases write here)

**Goal:** A single append-only JSONL stream the operator can `tail -f` to understand what the platform is doing. Without this, the first symptom of a Phase 3 or Phase 4 regression is "nothing shipped this weekend" — the exact failure mode this entire platform exists to prevent.

**Deliverables (start in Phase 0, grow through every phase):**

- `state/logs/dispatch-health.jsonl` — append-only. One line per `claim`, `complete`, `fail`, `requeue`, `block`, `evolve_propose`, `evolve_accept`, `evolve_revert`, `command_scan_deny`, `acp_dispatch`, `acp_timeout`, `acp_fail`.
- `packages/tools/dispatch_health.py` — new. Thin writer module. Every worker imports `dispatch_health.record(event_type, payload)` and calls it on each lifecycle transition. Import is side-effect-free; writing is buffered with a 1-second flush.
- `scripts/dispatch-health.py` — 10-line summarizer. `python scripts/dispatch-health.py --since 24h` prints counts per event type, per lane, and the three oldest unclaimed tasks.
- `docs/runbooks/dispatch-health-triage.md` — procedure for when the summarizer shows a stall.

**Definition of Done (cross-cutting):** Every worker in the platform writes to the stream on claim/complete/fail. The summarizer runs cleanly against a day's worth of events.

---

## Alternative Approaches Considered

**1. Build `skills/adapters/hermes/` first, skip the `external_dirs` spike.**
Rejected. The spike is an afternoon's work and answers a concrete question before committing to an adapter layer. If `skills.external_dirs` works natively, the adapter is either unnecessary or much smaller. Writing the adapter first risks solving a problem Hermes already solved for us upstream.

**2. Put the self-evolution loop inside `worker-supervisor`.**
Rejected. `worker-supervisor` owns goal decomposition, which runs under human-set direction. Skill evolution proposes changes to the canonical source of truth, which has a materially different approval boundary. Co-locating them makes approval scoping impossible and violates the AGENTS.md rule that workers are single-lane.

**3. Use MCP instead of ACP for the peer-runtime adapter.**
Rejected. MCP is tool-level: "expose my tools to another agent." ACP is runtime-level: "dispatch a task to another agent." The problem we're solving is the second one. Using MCP for it would force us to model "run a whole task" as "call one tool," which loses the task lifecycle (claim, result, approval hooks). MCP is a valuable separate track — the `skills/registry.yaml`-as-MCP-server idea from earlier conversation remains viable but is not this plan.

**4. Containerize everything (follow paperclipai/paperclip's production-container pattern).**
Rejected for now. The cluster of open Hermes upstream bugs (#9153, #9305, #9526) in the Docker and Nix paths is an active warning. The platform is local-first on an always-on Mac (CLAUDE.md:1-6). Container work is a separate effort contingent on upstream stability; revisit when #9305 closes.

**5. Ship a new worker-skill-evolution without a new canonical skill.**
Rejected. The worker IS a consumer of a skill, same as any other worker. Encoding its logic as a canonical skill means (a) it can itself be reviewed, patched, and versioned through the same system, (b) it can run under `mode="autonomous"` with the same fixture gate, (c) it's portable to Hermes via the Phase 4 ACP adapter. Hard-coding the logic into the worker creates a second source of truth.

**6. One giant PR for Phases 0 + 1.**
Rejected. Phase 0 is a single atomic PR. Phase 1 is three distinct fixture sets plus a reconciliation check plus CI wiring. Merging them risks blowing up the review size and coupling unrelated rollbacks. Phase 0 → land → Phase 1 starts.

## System-Wide Impact

### Interaction Graph

**Phase 1 ripple (autonomous dispatch, first three skills):**
`runtime-supervisor.poll()` → `ControlPlaneService.claim_task(lane=...)` → `load_agentic(skill_id, mode="autonomous")` → `loader.py:201-206` gate check → fixture reconciliation cached result → adapter path lookup → skill execution via `packages/tools/claude_tools/` → `submit_task_result()` → `packages/db/control_plane_db` write → `dispatch_health.record("complete", ...)`. Two levels deeper: `submit_task_result` triggers `release_readiness.check()` if the task belongs to a release lane, which itself loads `approval-token-audit` validator. A Phase 0 regression in `load_registry()` breaks this chain at every level.

**Phase 3 ripple (self-evolution proposal):**
`worker-skill-evolution.claim_task()` → `check_evolution_allowed(task, proposed_diff)` → `packages.db.locks.skill_evolution.acquire(skill_id, holder_token)` → load target skill canonical + current fixtures → run proposal logic → write diff to `state/artifacts/skill-evolution/<id>/` → `git worktree add state/worktrees/skill-evolution/<id>/` → apply diff → run `tests/python/unit/test_skill_reconciliation.py` in the worktree → commit → `gh pr create` → `dispatch_health.record("evolve_propose", ...)` → `packages.db.locks.skill_evolution.release(skill_id, holder_token)`.

**Phase 4 ripple (ACP dispatch):**
`runtime-supervisor.poll()` → claim → check `acp_dispatch_enabled` flag → check `target_runtimes` on skill spec → `assert_acp_peer_allowed(peer, skill)` → `ProviderRegistry.resolve("acp")` → `acp.dispatcher.dispatch_acp(request, peer)` → peer process lifecycle (start if absent / timeout / reap) → JSON-RPC stdio write → read response → map response to `TaskResult` → `submit_task_result()` → `dispatch_health.record("acp_dispatch", ...)`.

### Error & Failure Propagation

- `SkillLoadError` at `loader.py:96` propagates up through `load_agentic` / `load_validator` → caught by worker loop → task marked `FAILED` → `dispatch_health.record("fail", reason="skill_load_error")`.
- `PolicyViolation("command_scan_denied")` raised by `command_scan.assert_command_allowed()` propagates up through the codex tool call → caught by worker → task marked `FAILED` → audit log entry in `state/logs/command-scan/YYYY-MM-DD.jsonl`.
- `PolicyViolation("fixture_skill_drift")` from `skill_evolution.check_fixture_skill_atomicity()` → propagates up through evolution worker → task marked `FAILED` → proposal directory moved to `state/artifacts/skill-evolution/rejected/<id>/`.
- `PeerRuntimeError` from ACP dispatcher timeout/crash → worker catches, requeues with attempt counter, after 3 attempts marks `FAILED` → `dispatch_health.record("acp_fail", attempt=3)`.
- `SkillNotEvaluated` is the existing gate — still surfaces as a hard refusal in autonomous mode.

**Retry conflicts:** The ACP dispatcher's 3-attempt retry must not stack with any retry logic in the peer runtime itself. The peer runtime config in `packages/config/peer_runtimes.yaml` must document the peer's own retry behavior so attempt counts don't multiply.

### State Lifecycle Risks

- **Phase 1 fixture isolation.** Each end-to-end test must use a temp SQLite DB and temp `state/` root. Without this, tests on a shared queue produce order-dependent flakes (SpecFlow gap).
- **Phase 3 worktree orphans.** `state/worktrees/skill-evolution/<id>/` must be garbage-collected when the associated PR closes or after 7 days with no PR. A `cron` entry in `infra/launchd/` handles this.
- **Phase 3 lock orphans.** If the worker crashes holding a skill-evolution lock, the heartbeat timeout in `packages/db/locks/skill_evolution` lets the next acquire steal it (via the conditional UPSERT's `WHERE heartbeat_at_us < :stale_threshold_us` clause). The holder_token-based release contract prevents the original holder from reviving after stale-steal. Tested explicitly via a fake-clock fixture.
- **Phase 4 peer process orphans.** If `runtime-supervisor` crashes while an ACP peer is running, the peer must either be reaped on restart (preferred) or be resilient to orphaning. Tested via `tests/python/integration/test_acp_peer_orphan_recovery.py`.
- **Phase 5 log directory unbounded growth.** Rotation cron in `infra/launchd/` caps at 30 days; archives to `state/archives/command-scan/`. If rotation fails silently, disk fills. Mitigation: the rotation script writes a heartbeat to `state/health/command-scan-rotation.txt`; a dispatch-health check asserts it's newer than 48 hours.

### API Surface Parity

- `loader.py` exposes `load_validator`, `load_agentic`. Phase 0 adds no new exports but changes adapter-path resolution internals. Every caller (`release_readiness.py`, `worker-supervisor/main.py`, future `command_scan.py`, future `skill_evolution.py`) stays on the same API.
- `TaskPacket` schema gains `provider_hint` in Phase 6. All constructors at current call sites default it to `None`, so Phase 6 is backward-compatible for existing callers.
- `PolicyViolation` stays the single error type for policy rejection. Phase 3 adds `fixture_skill_drift`, Phase 4 adds `acp_peer_not_allowed`, Phase 5 adds `command_scan_denied`, `command_scan_unavailable`. New codes, same exception class.

### Integration Test Scenarios (cross-layer, unit tests can't catch)

1. **Autonomous dispatch survives a registry reload.** Enqueue three Phase 1 tasks, start `runtime-supervisor`, mid-run touch `skills/registry.yaml`, assert dispatch continues without crash and subsequent tasks pick up the new registry.
2. **Self-evolution proposal is blocked by the concurrent-run lock.** Enqueue two proposals against the same target skill id, assert exactly one runs and the other is queued behind the lock, assert both complete in order.
3. **Self-evolution proposal is rejected for policy-directory targeting.** Enqueue a proposal targeting `packages/policies/skill_evolution.py`, assert `PolicyViolation` raised before any filesystem write.
4. **ACP dispatch survives peer crash mid-task.** Start a task targeted at Hermes, kill Hermes mid-execution, assert the dispatcher reaps and requeues, assert attempt counter reaches 3, assert task ends `FAILED` with `reason="acp_peer_max_attempts"`.
5. **Command-scan audit log rotation runs cleanly.** Fast-forward the clock, invoke the rotation script, assert yesterday's log is archived, assert today's is active, assert the heartbeat is updated.

## Acceptance Criteria

### Functional Requirements

- [ ] **Phase 0:** `load_registry()` returns successfully against the real `skills/registry.yaml`; unit tests cover the softened adapter-path lookup and dual-layout fixture discovery; ADR at `docs/adr/2026-04-14-canonical-skill-layout.md` is committed.
- [ ] **Phase 1:** `supervisor-goal-decomposition`, `product-artifact-chain`, `codex-claude-handoff` all have `fixture_status: passing`; reconciliation test runs in CI on every push; existing `passing` agentic skills either have a validator, are downgraded, or have explicit `validator: none` with rationale; three isolated end-to-end tests pass.
- [ ] **Phase 2:** `docs/research/2026-04-hermes-spike-findings.md` exists with a gap analysis and a recorded decision; at least one canonical skill successfully invoked through Hermes CLI.
- [ ] **Phase 3:** `apps/worker-skill-evolution/` lane exists and starts from `runtime-supervisor`; one proposal merged and observed in production for 72 hours without revert; denylist and concurrent-lock tested; `docs/runbooks/skill-evolution-revert.md` has been walked through once.
- [ ] **Phase 4:** `acp_dispatch_enabled: true` results in a canonical skill executing through the local Hermes instance end-to-end; negative contract test passes; feature flag defaults `false`.
- [ ] **Phase 5:** every shell invocation in `packages/tools/codex_tools/` and `packages/tools/worktrees.py` is preceded by `assert_command_allowed()`; audit log rotates daily and archives after 30 days; load-order test passes.
- [ ] **Phase 6:** all Claude/Codex tool invocations route through `ProviderRegistry.resolve()`; `TaskPacket.provider_hint` field exists and is honored; at least one placeholder provider registered and visible in `list_available()`.
- [ ] **Cross-cutting:** every worker writes to `state/logs/dispatch-health.jsonl`; `scripts/dispatch-health.py --since 24h` runs and produces useful output.

### Non-Functional Requirements

- [ ] No phase introduces >1ms per-call overhead on hot paths (benchmarked in Phase 6 integration test).
- [ ] No phase increases autonomous-dispatch latency by more than 100ms end-to-end.
- [ ] Every new canonical skill follows the per-skill-dir layout from the Phase 0 ADR.
- [ ] Every new policy module is import-safe (no side effects at import time).
- [ ] Every new worker lane has a kill-switch file under `state/flags/`.
- [ ] Every new error code is a named `PolicyViolation` subclass constant, not a string literal at the raise site.

### Quality Gates

- [ ] `tests/python/unit/test_skills_loader.py` passes against the softened adapter-path lookup.
- [ ] `tests/python/unit/test_skill_reconciliation.py` runs in CI and fails on any registry↔fixture drift.
- [ ] Every phase's unit tests cover happy / boundary / adversarial cases for the relevant surface.
- [ ] At least one integration test per phase touches the real queue, real state directory, and real loader.
- [ ] Each phase's Deliverables list is fully crossed off before the phase is marked complete in this plan.

## Success Metrics

**Primary:** Number of tasks per week dispatched autonomously through `runtime-supervisor` without human intervention. Baseline today: **0**. Phase 1 target: **>= 3 per week** (the three project_skills). Phase 3 end-state target: **>= 20 per week** across all lanes.

**Skill evolution health:** Proposals generated, proposals accepted, proposals reverted. Weekly summary from `scripts/skill-evolution-metrics.py`. Target ratio: generated:accepted:reverted within 4:1:0 in the first month.

**Command-scan coverage:** Percentage of shell invocations in `packages/tools/codex_tools/` and `packages/tools/worktrees.py` that pass through the scanner. Target: 100% by end of Phase 5; enforced by integration test.

**ACP dispatch reliability:** Fraction of ACP-targeted tasks completing without requeue. Target: >= 95% over a rolling 7-day window once enabled.

**Observability:** Time from a new failure mode appearing in production to an entry showing up in `dispatch-health.jsonl`. Target: < 1 second.

## Dependencies & Prerequisites

- **Phase 0** depends on nothing.
- **Phase 1** depends on Phase 0.
- **Phase 2** depends on Phase 1 (needs real skills to test with) and on a local Hermes v0.7.0 install (manual, out-of-repo).
- **Phase 3** depends on Phase 1 and Phase 2. Does NOT depend on Phase 4 — the evolution loop produces skills that the existing Claude/Codex adapters can execute.
- **Phase 4** depends on Phase 0 (softened loader), Phase 2 (gap findings), and Phase 3 (canonical-layout pressure test). Phase 2 findings can accelerate Phase 4 planning but **cannot** reorder it ahead of Phase 3.
- **Phase 5** depends on Phase 1 (the validator skill needs to load).
- **Phase 6** depends on Phase 4 (the first real cross-runtime dispatch pattern).
- **Cross-cutting dispatch-health** starts in Phase 0 and grows in every phase.

**External:**
- `gh` CLI installed and authenticated (already true for this machine per `CLAUDE.md`).
- `uv` installed for Hermes source install.
- Gemini API key already configured at `/Users/simons/ai-company-os/.env` (`GEMINI_API_KEY`).
- `yt-dlp` installed (already done).
- `launchd` cron access for log rotation and GC jobs (already used by `infra/launchd/`).

## Risk Analysis & Mitigation

| Risk | Phase | Severity | Mitigation |
|---|---|---|---|
| Registry crash propagates to other tools that import `load_registry` | 0 | High | Single atomic PR, easy revert, broad unit test coverage |
| Fixture migration breaks existing imports of canonical paths | 1 | Medium | Grep pass before migration, symlink or re-export for transition |
| CI fixtures shell out and flake in sandbox | 1 | Medium | Mandatory isolation: temp SQLite DB + temp state root per test |
| Hermes upstream regression between pinned commit and HEAD | 2 | Low | Pin to specific SHA, document in findings doc |
| Self-evolution proposes a bad skill that looks fine on review | 3 | High | 72-hour observation window; dispatch-health metrics; atomic fixture+skill diff policy |
| Self-evolution evolves its own skill | 3 | Critical | Explicit denylist tested in unit + integration |
| Concurrent proposals race on same target | 3 | Medium | Per-skill-id lock with TTL |
| PR branches accumulate from abandoned proposals | 3 | Low | Daily GC cron removes worktrees >7 days without open PR |
| ACP peer crashes mid-task leave queue inconsistent | 4 | High | Timeout + reap + requeue with attempt counter |
| ACP protocol drift between Hermes versions | 4 | Medium | Negative contract test; peer version pinned in config |
| Feature flag accidentally enabled in committed config | 4 | High | Default `false`; CI assertion that committed value is `false` |
| False-positive command-scan blocks legitimate command | 5 | Medium | Advisory mode first, graduate to enforce after 72h clean |
| Command-scan module fails to import at tool-wire-up time | 5 | High | Lazy validator load; explicit import-safety test |
| Command-scan audit log fills disk | 5 | Medium | Daily rotation; 30-day archive; heartbeat check |
| Provider overlay indirection regresses latency | 6 | Low | Benchmark in integration test; <1ms overhead target |
| Circular imports providers/acp.py ↔ tools/acp/dispatcher.py | 6 | Medium | Lazy import inside `execute()` |
| **SQLite writer starvation under concurrent writers** | 0 | **High** | X2: `connection.py` helper + `WAL` + `busy_timeout=30000` + concurrent-writers test |
| **Registry re-parsed on every load_validator call (hot-path regression)** | 0, 5 | **High** | X3: `lru_cache` keyed on `(path, mtime_ns)` |
| **Poisoned `state/checkpoints/` or `dispatch-health.jsonl` steers self-evolution** | 3 | **Critical** | Hash-pinned + signed-by-worker input snapshots; typed reader verifies signatures |
| **Self-evolved skill targets `[acp]` on first landing** | 3, 4 | **Critical** | Lock to `target_runtimes: [claude]`; runtime expansion requires human PR |
| **Self-evolved skill worse than incumbent passes its own fixtures** | 3 | **High** | Voyager/DSPy regression-fixture gate: new must beat old on incumbent fixtures |
| **`gh pr create` pushes to `main` with ambient token** | 3 | **Critical** | Hardcoded `--base staging`, fine-grained PAT, branch-prefix assertion, `--draft` default, signed commits, branch protection |
| **Hermes peer RCE escalates to full-platform compromise** | 4 | **Critical** | `sandbox-exec` profile at `infra/sandbox/hermes.sb`; dedicated launchd user fallback; clean env; RLIMIT_AS/CPU/NOFILE |
| **Per-dispatch peer subprocess spawn (1.5–4 s cold start)** | 4 | **High** | Spawn-once keep-alive, per-peer asyncio.Lock, idle-reap 30 min |
| **Peer crashes on crafted payload → 3-attempt retry amplifies poison-pill** | 4 | **High** | Quarantine after 1 crash (not 3); timeouts retry, crashes don't |
| **JSON-RPC parser DoS via deeply-nested JSON** | 4 | High | 1 MiB frame cap, non-UTF-8 rejection, bounded-depth decoder, hypothesis fuzzer in CI |
| **Peer config YAML contains plaintext tokens** | 4 | **High** | Keychain references only; gitignore `*.secret.yaml`; pre-commit secret scanner |
| **Shell parser bypassed by `rm$IFS-rf` / process substitution / eval** | 5 | **Critical** | `bashlex` AST parser, not regex; parse failure = deny |
| **Env-variable injection bypasses command scanner** | 5 | **Critical** | Scan `(argv, env)` tuple at subprocess.run site; whitelisted env; forbid `shell=True` (ruff S602) |
| **Command audit log contains secrets in argv** | 5 | **High** | Redaction before write; `chmod 600`; unit test with known secret shapes |
| **Stuck-but-alive lock holder stolen → worktree race** | 3 | **High** | Heartbeat column extended every 60 s; `holder_token` verified on release |
| **JSONL append atomicity lost via buffered writer** | cross | Medium | Background flush thread + `os.write(fd, line)` with `O_APPEND`; < 512 B per event |
| **`content-voice-guardrail` passing without validator is a latent trust exploit** | 1 | **High** | 1.3a is HARD gate on Phases 2–5 starting, not a checklist item |
| **Atomicity policy bypassed via `helpers.py` third-file smuggling** | 3 | High | Diff policy denies any file outside `{skill.md, contract.yaml, validator.py, fixtures/**}` |
| **Loader adapter path traversal via malicious registry entry** | 0 | High | Regex-constrain `spec.adapters[*]` to `^skills/adapters/[a-z]+/[a-z0-9_-]+\.md$` |
| **launchd cron job silently fails, no alerting** | cross | Medium | Every entrypoint writes heartbeat to `state/health/<job>.ok`; dispatch-health checks freshness |
| **macOS 14+ Background Items approval blocks launchd on first load** | cross | Low | Document in `infra/launchd/README.md`; first-run manual approval step |

## Future Considerations

- **Expand peer runtimes in Phase 4.** Once Hermes is proven, add Ollama as a second peer for local model execution, and optionally OpenCode. Each addition is a config entry + a registered provider, not a new code path.
- **Promote `skills.external_dirs`-mounted Hermes to production.** If the Phase 2 spike shows near-zero gap, the evolution worker can start proposing skills that target `[claude, codex, hermes]` simultaneously.
- **MCP server wrapping `skills/registry.yaml`.** Out of scope for this plan but the natural follow-up. Would let external MCP hosts consume our canonical skills without any ACP dance.
- **GTM-flavored skills from Hermes community.** The community is 70% GTM. Filter `r/hermesagent` and `r/AISEOInsider` for proven patterns; feed them into the self-evolution proposal input as "external inspiration" signals.
- **Multi-Mac deployment.** If the platform runs on >1 Mac, the ACP adapter generalizes to remote peers over UNIX socket or TCP, not just local stdio. This requires adding new `PeerTransport` enum members (e.g., `UNIX_SOCKET`, `TCP`) — the current enum has `STDIO` only, deliberately YAGNI'd until a second transport has a caller.
- **Containerize when upstream stabilizes.** Monitor [NousResearch/hermes-agent#9305](https://github.com/NousResearch/hermes-agent/issues/9305); when it closes, revisit Docker/Nix distribution for the ai-company-os platform itself.

## Documentation Plan

- `docs/adr/2026-04-14-canonical-skill-layout.md` — Phase 0 ADR on canonical layout.
- `docs/research/2026-04-hermes-spike-findings.md` — Phase 2 spike writeup.
- `docs/runbooks/skill-evolution-revert.md` — Phase 3 revert procedure.
- `docs/runbooks/dispatch-health-triage.md` — cross-cutting observability runbook.
- `skills/WIRING.md` — update to reference the new ADR and the dual-layout convention.
- `AGENTS.md` — add `worker-skill-evolution` to the worker roster with its approval boundaries.
- `CLAUDE.md` — add `skill-self-evolution` trigger phrase row and update the "available Claude project skills" list.
- `packages/policies/README.md` (new if absent) — document the `command_scan`, `skill_evolution`, `acp_dispatch`, `provider_resolution` policy modules and their composition pattern.

## Sources & References

### Institutional Learnings (carry forward)

- **[docs/solutions/integration-issues/incomplete-refactor-auto-detection-behind-empty-state-gate.md](docs/solutions/integration-issues/incomplete-refactor-auto-detection-behind-empty-state-gate.md)** — partial-refactor anti-pattern. Applied directly to Phase 3's atomic fixture+skill diff policy, and to Phase 1's "close the gate atomically with the canonical skill patch" rule.
- **[docs/solutions/integration-issues/content-pipeline-multi-tool-orchestration.md](docs/solutions/integration-issues/content-pipeline-multi-tool-orchestration.md)** — multi-tool orchestration gotchas. Applied to Phase 4's mandatory negative contract test and to Phase 6's pure/impure service layering.

### Internal References

- **Loader gate:** `packages/tools/skills/loader.py:142-146`, `:201-206`
- **Hard-coded adapter path:** `packages/tools/skills/loader.py:208-210`
- **fixture_status literal:** `packages/tools/skills/loader.py:28`
- **Registry load:** `packages/tools/skills/loader.py:98-102`
- **Registry file:** `skills/registry.yaml` (287 lines, 21 skills)
- **Validator-policy composition template:** `packages/policies/release_readiness.py:31`, `:40-60`
- **Fixture file shapes:**
  - `skills/canonical/social-post-safety/fixtures/happy_path.yaml`
  - `skills/canonical/post-run-validation/fixtures/happy_path.json`
  - `skills/canonical/approval-token-audit/fixtures/happy_path.yaml`
- **Worker loop template:** `apps/worker-engineering/main.py:88-140`, `apps/worker-gtm/main.py:46-96`
- **Runtime supervisor default worker specs:** `apps/runtime-supervisor/main.py:75-104`
- **Supervisor planning function:** `apps/worker-supervisor/main.py:13`, `:73`
- **Task queue:** `packages/queue/task_queue.py:20`, `:55-59`
- **Schemas:** `packages/schemas/task_packet.py:7-13` (WorkerLane), `:66-77` (TaskPacket)
- **Policy exception:** `packages/policies/approvals.py:6-15`
- **Architecture rules:** `CLAUDE.md:1-40`
- **Worker boundaries:** `AGENTS.md:179-263`
- **Skill wiring convention:** `skills/WIRING.md`

### External References

- **NousResearch/hermes-agent v0.7.0 (pinned commit `abf1e98`):** https://github.com/NousResearch/hermes-agent
- **skills.external_dirs bug report (config surface confirmed):** [NousResearch/hermes-agent#8110](https://github.com/NousResearch/hermes-agent/issues/8110)
- **Hermes as ACP peer (protocol template):** [multica-ai/multica#611](https://github.com/multica-ai/multica/pull/611)
- **Skill self-evolution RFC (pattern validation):** [bytedance/deer-flow#1865](https://github.com/bytedance/deer-flow/issues/1865)
- **Paperclip adds Hermes as first-party adapter:** [paperclipai/paperclip#1867](https://github.com/paperclipai/paperclip/pull/1867)
- **Docker packaging canary:** [NousResearch/hermes-agent#9305](https://github.com/NousResearch/hermes-agent/issues/9305)
- **HERMES_OVERLAYS pattern reference:** [NousResearch/hermes-agent#6455](https://github.com/NousResearch/hermes-agent/issues/6455)
- **Tirith security scanner reference:** [NousResearch/hermes-agent#6393](https://github.com/NousResearch/hermes-agent/issues/6393)
- **Mac mini + Hermes hardware validation:** [r/macmini thread](https://www.reddit.com/r/macmini/comments/1sct1zf/using_my_mac_mini_as_a_dedicated_ai_agent_server/)
- **OpenClaw vs Hermes philosophy (56 comments):** [r/openclaw thread](https://www.reddit.com/r/openclaw/comments/1sdw7xc/seeing_a_lot_of_migrating_from_openclaw_to_hermes/)

### Added via /deepen-plan research (2026-04-14)

- **Agent Client Protocol (ACP) spec:** https://agentclientprotocol.com/protocol/overview
- **ACP Python SDK:** https://github.com/agentclientprotocol/python-sdk — `pip install agent-client-protocol`; SDK quickstart at https://agentclientprotocol.github.io/python-sdk/quickstart/
- **ACP JSON schema:** https://github.com/agentclientprotocol/agent-client-protocol/blob/main/schema/schema.json
- **Hermes ACP server reference:** `NousResearch/hermes-agent:acp_adapter/server.py` at tag `v2026.4.3` — `HermesACPAgent(acp.Agent)`
- **Hermes cli-config.yaml.example:** https://github.com/NousResearch/hermes-agent/blob/v2026.4.3/cli-config.yaml.example
- **Hermes `skill_manager_tool.py::_create_skill`** — atomic write pattern for self-generated skills (tempfile + os.replace)
- **Hermes `skills_guard.py`** — 168+ threat patterns for skill content security scanning
- **SQLite WAL mode:** https://sqlite.org/wal.html — writer serialization semantics, `busy_timeout` required in every `sqlite3.connect()` call
- **Voyager (NVIDIA, 2023):** https://voyager.minedojo.org/ + https://arxiv.org/abs/2305.16291 — execution-feedback gate for skill library additions
- **DSPy assertions:** https://dspy.ai/learn/programming/assertions/ — metric-regression gate (new prompt beats old on held-out validation)
- **Reflexion:** https://arxiv.org/abs/2303.11366 — scope-limited verbal memory (per-episode, not globalized) to prevent memory poisoning
- **Claude Skills announcement:** https://www.anthropic.com/news/skills — deliberate asymmetry: discovery model-driven, authoring human-driven
- **Cognition "Don't Build Multi-Agents":** https://cognition.ai/blog/dont-build-multi-agents — compounding context drift warning
- **Cursor Bugbot learning loop:** https://cursor.com/blog/bugbot-learning — evidence-based rule activation
- **Sweep.dev post-mortem:** https://docs.sweep.dev/blogs — branch accumulation + flaky CI as the unsustainable failure mode
- **GitHub Copilot coding agent:** https://github.blog/changelog/2025-05-19-github-copilot-coding-agent-in-public-preview/ — branch namespace reservation, auto-close on staleness
- **Aider design notes:** https://aider.chat/docs/faq.html — `--auto-commits` opt-in; human is the PR opener
- **LangGraph interrupts (policy composition):** https://langchain-ai.github.io/langgraph/how-tos/human_in_the_loop/
- **MCP spec (for future MCP server lane):** https://modelcontextprotocol.io/specification
- **Google A2A (alternative peer protocol, heavier):** https://github.com/google/A2A
- **LiteLLM (provider overlay reference):** https://github.com/BerriAI/litellm
- **Semgrep bash ruleset (command-scan reference):** https://semgrep.dev/p/bash
- **shellcheck (shell AST parser reference):** https://www.shellcheck.net/
- **bashlex (Python shell parser for Phase 5):** https://github.com/idank/bashlex
- **uv docs:** https://docs.astral.sh/uv/
- **git-worktree docs:** https://git-scm.com/docs/git-worktree
- **launchd.info (modern per-user plist reference):** https://www.launchd.info/
- **Galileo — Agent failure modes guide:** https://galileo.ai/blog/agent-failure-modes-guide
- **Deer-flow RFC #1865 (skill self-evolution design):** https://github.com/bytedance/deer-flow/issues/1865

### Related Work

- `docs/plans/2026-04-13-feat-gtm-multi-platform-content-engine-plan.md` — tracks `content-performance-review`; the Phase 0 registry cleanup removes the stray entry there and relies on this plan's Phase 6 follow-up.
- `docs/plans/2026-04-12-feat-content-pipeline-skills-plan.md` — shipped the content-factory / content-scheduler stack; those are in the `project_skill` set but not the Phase 1 first-three because their fixture surface is larger.
- `skills/registry.yaml` commit history — context on when each skill was added and why some are agentic vs validator.
