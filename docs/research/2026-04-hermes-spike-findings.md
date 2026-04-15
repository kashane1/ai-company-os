# Hermes Integration Spike — Findings (2026-04-14)

**Phase**: 2 of the [Hermes platform upgrade plan](../plans/2026-04-14-feat-hermes-inspired-platform-upgrade-plan.md)
**Question**: Can the canonical skills in `skills/canonical/` be consumed by a local Hermes v0.7.0 instance via its native `skills.external_dirs` hook with **zero code changes** to this repo?
**Verdict**: **No.** Zero-code consumption is not achievable. Bridging Hermes requires either a rename-only adapter layer or a skills-adapter that translates our canonical format into `SKILL.md` files at build time.

See also:
- [`acp-sdk-api.md`](2026-04-hermes-spike/acp-sdk-api.md) — verified `agent-client-protocol==0.8.1` public surface (hermes pin)

(The clone, `uv sync`, SDK install, and handshake all succeeded on the
first attempt. No `install-failures.md` is committed.)

## Environment under test

| Component | Value | Notes |
|---|---|---|
| Hermes ref | `abf1e98` (tag `v2026.4.3`, `chore: release v0.7.0`) | `git clone --branch v2026.4.3 --depth 1`. Tag emits a cosmetic "not a commit" warning, but the checked-out commit IS the v0.7.0 release. |
| Python | 3.14.3 | `uv sync` ignored the 3.11 preference because `hermes/pyproject.toml` allows 3.11+. |
| ACP SDK | `agent-client-protocol==0.8.1` | Hermes pins `>=0.8.1,<0.9` in `pyproject.toml`. The single verified incompatibility with 0.9.0 is a direct import in `~/hermes/acp_adapter/server.py:12-40` — `from acp.schema import ... AuthMethod ...`. Reproducing: `uv pip install "agent-client-protocol==0.9.0"; python -m acp_adapter.entry` → `ImportError: cannot import name 'AuthMethod' from 'acp.schema'`. I did NOT audit every other `from acp` import in the hermes codebase against the 0.9 changelog, so this is "first symbol blocks; others may too," not "only this symbol blocks." Treat the pin as necessary but do not assume it is sufficient for a future hermes release that catches up to 0.9. |
| Our repo | main at commit after `eeb633c` | Canonical skills unchanged from PR #6 landing. |

## Findings against the seven required items

### 1. Which Phase 1 target skills does Hermes load at all?

**Zero.**

Hermes's skill discovery is `agent.skill_utils.iter_skill_index_files(skills_dir, "SKILL.md")` — a recursive `os.walk` that matches the literal filename `SKILL.md` (uppercase). It is invoked from three sites in the codebase, all with `filename="SKILL.md"` hardcoded:

- `agent/prompt_builder.py:548` — local skills
- `agent/prompt_builder.py:600` — **external_dirs** (the one we care about)
- `agent/skill_commands.py:176` — `scan_dir.rglob("SKILL.md")`

`skills/canonical/` contains **zero** files named `SKILL.md`. It contains 12 files named `skill.md` (lowercase) in per-skill-dir layout (`find skills/canonical -name skill.md | wc -l` confirms), plus 8 flat files in `canonical/shared/` named `<skill-id>.md`. None match.

This means Hermes pointed at `external_dirs: [skills/canonical]` will register **zero** slash commands, zero context stanzas, zero anything. The three Phase 1 targets (`supervisor-goal-decomposition`, `product-artifact-chain`, `codex-claude-handoff`) are all in the flat layout, and would need two separate rewrites (file rename + layout move) to be visible at all.

### 2. Which could execute unchanged?

**Zero.** Moot — nothing loads.

Even hypothetically, if we trick Hermes into reading a canonical `skill.md`, the content would not execute. See item 3 for the frontmatter gap and item 4 for the tool-call gap.

### 3. Frontmatter / schema fields Hermes expects that our canonical shape does not provide

Hermes's parser (`agent/prompt_builder.py:405` — `_read_skill_metadata`) expects standard YAML frontmatter. Reference shape from `skills/apple/apple-notes/SKILL.md` in the hermes repo:

```yaml
---
name: apple-notes
description: Manage Apple Notes via the memo CLI on macOS ...
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [macos]
metadata:
  hermes:
    tags: [Notes, Apple, macOS, note-taking]
    related_skills: [obsidian]
prerequisites:
  commands: [memo]
---
```

Our canonical skills split into two incompatible forms:

**Form A — no frontmatter at all** (e.g. `content-factory/skill.md`, `niche-research-brief/skill.md`, `gtm-artifact-refresh/skill.md`):

```
# Skill: content-factory

Kind: agentic
Owner: gtm
Runtimes: claude

## Purpose
...
```

Hermes can't parse this — no `---` fence, so no frontmatter object, so no `name` key, so the skill is rejected at registration time even if the filename matched.

**Form B — YAML frontmatter with our own keys** (e.g. `post-run-validation/skill.md`):

```yaml
---
id: post-run-validation
name: Post-Run Validation
purpose: ...
owner_agent: supervisor
target_runtimes: [claude]
kind: validator
---
```

Hermes would read this but:
- ✅ `name` is present (Hermes would use it)
- ⚠ `description` missing (Hermes falls back to `name` but skill picker UX suffers)
- ⚠ `version`, `author`, `license` missing (not required but shown in `hermes skills list`)
- ⚠ `platforms` missing (Hermes treats absence as "all platforms", which may be wrong for our macOS-bound skills)
- ⚠ `prerequisites` missing (Hermes may gate activation on commands we don't declare)
- ❌ `id`, `purpose`, `owner_agent`, `target_runtimes`, `kind` are ignored as unknown keys — our runtime routing (target_runtimes: [claude, codex, acp]) is invisible to Hermes

**Gap summary**: our two forms need migration to one shape, and that shape needs a `description:` field plus either rename or dual-key emit of `purpose → description`.

### 4. Tool-call expectations Hermes has that our skills don't satisfy

Hermes skills describe themselves as **natural-language procedures invoked by the model via slash commands**, backed by Hermes's built-in toolset (shell, file I/O, MCP tools, web search, etc.). The model decides which tools to call; the skill is the instruction text.

Our canonical skills describe **agent-callable procedures with typed inputs/outputs, explicit edit boundaries, and fixture contracts**. They assume:

- A `packages/tools/skills/loader.py` that returns typed `SkillSpec` objects
- A `packages/policies/` layer that blocks out-of-boundary edits
- A `packages/tools/primitives/` layer for agent-callable helpers (kill switches, approvals, peer runtimes)
- A fixture replay harness that verifies skills structurally against real input/output traces
- A registry at `skills/registry.yaml` that tracks lifecycle stage (`active`, `deferred`, `planned`) and fixture_status

**None of this is visible to Hermes.** If Hermes loads a skill file, it treats it as a prompt template. It has no concept of:
- "This skill is not allowed to touch `packages/policies/`"
- "This skill must run its post-run-validation contract"
- "This skill is `deferred` and should not execute even if invoked"

This means even a rewritten skill would degrade into a best-effort prompt when Hermes drives it — the invariants enforced on the Claude/Codex side disappear.

**Implication for Phase 4**: the ACP dispatcher must stay the integration surface. We dispatch *tasks* to Hermes via ACP, not *skills*. The skill selection happens on our side (our supervisor picks which skill applies, translates it to a plain prompt plus tool permission list, and sends that over ACP). Hermes is a peer runtime, not a skill co-host.

### 5. Does Hermes discover our flat Phase 0 layout (`canonical/shared/*.md`) or only per-skill-dir?

**Neither, for the reason in item 1.**

The Phase 0 ADR ([`docs/adr/2026-04-14-canonical-skill-layout.md`](../adr/2026-04-14-canonical-skill-layout.md)) asserts that flat Phase 0 skills "stay flat with sibling fixtures files" and are "Claude-only forever unless migrated." This spike confirms that assumption empirically for flat skills — but **also extends it to per-skill-dir layout**. Our lowercase `skill.md` filename convention makes the per-skill-dir form equally invisible to Hermes.

The ADR's assumption that per-skill-dir is the Hermes-compatible form is **wrong** as stated. The fix is either:

1. Rename `skill.md` → `SKILL.md` in per-skill-dir layout (cheap, invasive to all existing dirs, but no semantic change), or
2. Introduce a build-time adapter at `skills/adapters/hermes/<skill-id>/SKILL.md` that emits from the canonical source (keeps canonical lowercase, adds a translation layer).

The second option is cleaner under the existing `skills/adapters/` convention and matches how `skills/adapters/claude/` already works. Recommended for the follow-up plan.

### 6. Telegram slash command registration status

**Deferred, not answered.** The Telegram gateway requires a bot token and live Telegram reachability that I don't have locally; the seven-question brief included this item but Phase 4 does not depend on it (we're consuming Hermes via ACP, not Telegram). This spike therefore does not verify the status empirically. Treat as a flag on any future plan that wants Hermes as a user-facing chat frontend.

The handoff carries the known upstream bug (#8110) as the working assumption; I have not re-verified that either. A follow-up spike that actually needs Telegram should start from the assumption that the status is unknown.

### 7. ACP server handshake sanity

**✅ WORKS.** This is the most important finding for Phase 4 feasibility.

Spike script (inlined below so this doc is reproducible after `/tmp` is reaped):

```python
# hermes_handshake.py — Phase 2 Finding #7 ACP handshake sanity check.
import asyncio, os, sys, traceback
import acp
from acp.schema import InitializeRequest, ClientCapabilities, Implementation


class MinimalClient(acp.Client):
    pass


async def main() -> int:
    hermes_root = "/Users/simons/hermes"
    python_bin = f"{hermes_root}/.venv/bin/python"
    env = {
        "PATH": os.environ.get("PATH", ""),
        "HOME": os.environ.get("HOME", ""),
        "PYTHONUNBUFFERED": "1",
    }
    print(f"[spike] spawning: {python_bin} -m acp_adapter.entry", file=sys.stderr)
    try:
        async with acp.spawn_agent_process(
            lambda agent: MinimalClient(),
            python_bin,
            "-m",
            "acp_adapter.entry",
            env=env,
            cwd=hermes_root,
        ) as (conn, proc):
            print(f"[spike] subprocess pid={proc.pid}, sending InitializeRequest", file=sys.stderr)
            init_req = InitializeRequest(
                protocolVersion=acp.PROTOCOL_VERSION,
                clientCapabilities=ClientCapabilities(),
                clientInfo=Implementation(name="ai-company-os-spike", version="0.0.1"),
            )
            try:
                init_resp = await asyncio.wait_for(conn.initialize(init_req), timeout=20.0)
            except asyncio.TimeoutError:
                print("[spike] RESULT: TIMEOUT on initialize", file=sys.stderr)
                return 2
            print(f"[spike] RESULT: OK", file=sys.stderr)
            print(f"[spike]   agent_info  = {init_resp.agentInfo}", file=sys.stderr)
            print(f"[spike]   protocol    = v{init_resp.protocolVersion}", file=sys.stderr)
            print(f"[spike]   capabilities= {init_resp.agentCapabilities}", file=sys.stderr)
            return 0
    except Exception as e:
        print(f"[spike] RESULT: FAIL ({type(e).__name__}): {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
```

Output:

```
[spike] spawning: /Users/simons/hermes/.venv/bin/python -m acp_adapter.entry
[spike] subprocess pid=89421, sending InitializeRequest
[spike] RESULT: OK
[spike]   agent_info  = name='hermes-agent' version='0.7.0'
[spike]   protocol    = v1
[spike]   capabilities= session_capabilities=SessionCapabilities(
                          fork=SessionForkCapabilities(),
                          list=SessionListCapabilities(),
                          resume=None),
                        load_session=False,
                        mcp_capabilities=McpCapabilities(http=False, sse=False),
                        prompt_capabilities=PromptCapabilities(
                          audio=False, embedded_context=False, image=False)
```

Confirmed:
- `acp.spawn_agent_process(to_client, command, *args, env=..., cwd=...)` is the correct entry point — returns an async context manager yielding `(ClientSideConnection, asyncio.subprocess.Process)`.
- The handoff's caution that `spawn_agent_process` might not exist and that we'd need to hand-roll streams via `ClientSideConnection(agent_factory, stream_to_agent, stream_from_agent)` was wrong for 0.8.1 — the top-level helper is present and works.
- Hermes v0.7.0's protocol version is `1`. `acp.PROTOCOL_VERSION == 1` at 0.8.1.
- Hermes reports `load_session=False`, so peer resume across crash boundaries is not supported. Phase 4 must design around that: dispatch is session-scoped, crashes lose the session, new task = new session.
- Hermes reports `fork` capability but we should NOT rely on it for normal dispatch — fork is for branching mid-conversation and complicates Phase 4 state tracking.
- `mcp_capabilities.http/sse` both False → Hermes does not expose its MCP tool layer over the ACP session. We cannot reach through ACP to call Hermes's shell, file, or MCP tools. Whatever we prompt, Hermes runs against its own local toolset inside its own sandbox.
- `prompt_capabilities.image/audio/embedded_context` all False → Phase 4 prompt payloads are **text-only**. No image blocks, no file attachments. Any context we want to send must be inlined as text.

## SDK API corrections to apply to the Phase 4 plan

The Phase 4 Research Insights block in the plan (around lines 770-820, marked "⚠ VERIFY") needs these substitutions. All verified against `agent-client-protocol==0.8.1` during this spike:

| Plan assumption | Verified reality |
|---|---|
| `spawn_agent_process(...)` may not exist | **Exists.** Signature: `spawn_agent_process(to_client, command, *args, env=None, cwd=None, transport_kwargs=None, **connection_kwargs) -> AsyncIterator[tuple[ClientSideConnection, asyncio.subprocess.Process]]`. Use it. |
| `ClientSideConnection(agent_factory, stream_to_agent, stream_from_agent)` is the real API | That class is real but you don't need to construct it manually. `spawn_agent_process` does it for you. |
| `TextContent` helper | Helper is `acp.text_block(text: str) -> TextContentBlock`. Schema class is `TextContentBlock`, not `TextContent`. |
| `stop_reason` literal values unverified | **Verified.** `PromptResponse.stopReason: Literal['end_turn', 'max_tokens', 'max_turn_requests', 'refusal', 'cancelled']`. |
| Pin `agent-client-protocol` as a direct dep | **Pin to `>=0.8.1,<0.9`** and do not drift. 0.9.x already broke the `AuthMethod` import surface — any upgrade must wait for a hermes release that moves too. |
| Initialize payload uses camelCase | `acp.schema.InitializeRequest(protocolVersion=..., clientCapabilities=..., clientInfo=...)` — Pydantic models use camelCase field names matching the JSON-RPC schema. |
| Hermes subprocess command | `/Users/simons/hermes/.venv/bin/python -m acp_adapter.entry`. If `hermes-acp` is on `$PATH` from a pipx install, that works too, but for Phase 4 the absolute venv path is what we'll hardcode in the peer config. |
| Minimal env to spawn Hermes | `PATH`, `HOME`, `PYTHONUNBUFFERED=1` are sufficient for the handshake. `HERMES_HOME` or `~/.hermes/.env` aren't required for initialize but will be required once we send a real `PromptRequest` (the model backend needs credentials). |

## Gap summary — what stands between us and "Hermes consumes our skills"

| Gap | Severity | Fix |
|---|---|---|
| Filename case: `skill.md` vs `SKILL.md` | Hard block | Build-time adapter in `skills/adapters/hermes/` (preferred), or rename all 11 per-skill-dir files (rejected — violates ADR's lowercase convention). |
| No frontmatter on ~half of canonical skills | Hard block | Adapter emits a synthetic frontmatter block from our `# Skill: <name>` H1 and the `Kind/Owner/Runtimes` prose fields. |
| Frontmatter key mismatch (`purpose` vs `description`, `target_runtimes` vs `platforms`) | Hard block | Adapter maps keys. Lossy — Hermes ignores `target_runtimes` so dispatch routing is invisible to it. |
| Tool-call model mismatch (Hermes prompt-as-skill vs our typed-contract skill) | Architectural | **Do not try to bridge.** Use ACP dispatch for peer runtime invocation. Treat Hermes as a *task executor*, not a *skill co-host*. |
| Flat Phase 0 skills (`shared/<skill-id>.md`) | Architectural | Keep Claude-only forever. ADR assumption was correct for the flat form even though wrong for per-skill-dir. |

## Decision — proceed to Phase 4 directly, or open a `skills/adapters/hermes/` plan first?

**Recommendation: proceed to Phase 4 directly.** Do not open a `skills/adapters/hermes/` plan.

Reasoning:

1. **Phase 4's goal is peer-runtime dispatch, not skill co-hosting.** This spike demonstrated that tool-call semantics differ enough that bridging the skill layer is a losing game — we'd spend weeks translating only to lose the constraint contracts that make the skill system valuable in the first place. ACP dispatch sidesteps this entirely: our supervisor picks the skill on our side, translates it to a plain prompt, and sends it over ACP. Hermes becomes an LLM provider, not a skill host.

2. **The spike has unblocked Phase 4.** `spawn_agent_process` works, `InitializeRequest` returns, the SDK pin is known, and the capabilities we need (or don't need) are mapped. Every ⚠ VERIFY annotation in the plan's Phase 4 sketch has a real answer.

3. **A `skills/adapters/hermes/` plan would be premature.** It solves a problem nobody has yet (running our skills inside Hermes's TUI). The actual need, once Phase 4 lands, is "dispatch a task to Hermes and get a result back." That's a Phase 4 deliverable. A skills-adapter layer is speculative work at best and mutually exclusive with Phase 4's approach at worst.

4. **Phase 3 still comes first.** This spike does not authorize reordering. Phase 3 pressure-tests the canonical skill layout under self-evolution — if the format turns out to be wrong in ways this spike didn't catch, we want to find that out on our own ground, not while also debugging ACP transport.

**Corollary**: update the Phase 0 ADR to reflect that **per-skill-dir layout is also Claude-only** until a hermes adapter exists, and that Phase 4 does not depend on such an adapter. That's a one-paragraph ADR amendment, not a new plan.

### Skill discovery spike script

Also inlined so the doc is reproducible without the `/tmp` scripts:

```python
# hermes_skill_discovery.py — Phase 2 Findings #1-5 skill discovery check.
import sys, traceback
sys.path.insert(0, "/Users/simons/hermes")
from pathlib import Path

canonical = Path("/Users/simons/ai-company-os/skills/canonical")
print(f"[discover] scanning {canonical}\n")

from agent.skill_utils import iter_skill_index_files

print("[discover] Looking for SKILL.md (hermes's expected filename):")
skill_md_hits = list(iter_skill_index_files(canonical, "SKILL.md"))
for p in skill_md_hits:
    print(f"  HIT: {p.relative_to(canonical)}")
if not skill_md_hits:
    print("  (none found)")
print()

print("[discover] Looking for skill.md (our canonical filename):")
skill_lc_hits = list(iter_skill_index_files(canonical, "skill.md"))
for p in skill_lc_hits:
    print(f"  HIT: {p.relative_to(canonical)}")
if not skill_lc_hits:
    print("  (none found)")
```

## Reproduction

```bash
# Install
brew install uv
git clone --branch v2026.4.3 --depth 1 https://github.com/NousResearch/hermes-agent.git ~/hermes
cd ~/hermes && uv sync
uv pip install "agent-client-protocol>=0.8.1,<0.9"

# Configure external_dirs
mkdir -p ~/.hermes
cat > ~/.hermes/cli-config.yaml <<'YAML'
skills:
  creation_nudge_interval: 0
  external_dirs:
    - /Users/simons/ai-company-os/skills/canonical
YAML

# Save the two scripts above into /tmp (or anywhere) and run:
~/hermes/.venv/bin/python /tmp/hermes_handshake.py        # expect exit 0
~/hermes/.venv/bin/python /tmp/hermes_skill_discovery.py  # expect "zero SKILL.md"
```

## Clean-up state

- `~/hermes/` — left in place, will be deleted by the user or the next Hermes-touching spike
- `~/.hermes/cli-config.yaml` — left in place for Phase 4 development convenience
- Both spike scripts inlined above — the `/tmp/*.py` copies will be reaped by macOS and that is fine
- `agent-client-protocol==0.8.1` — installed into `~/hermes/.venv` only; not added to this repo's pyproject.toml. Phase 4 will add the pin to `packages/tools/acp/pyproject.toml` when the client module lands.

---

**Author**: Claude Opus 4.6, via the ai-company-os Phase 2 spike session
**Date**: 2026-04-14
